"""Voicemail triage pipeline: speak -> transcribe -> classify -> callback list.

For each fictional voicemail we synthesize an MP3 with OpenAI TTS (the
"answering machine"), transcribe it with Whisper, and have gpt-4o-mini sort
it into emergency / same-day / routine with the caller details a nurse needs
to ring them back.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

EXAMPLE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = EXAMPLE_DIR / "audio"
OUT_DIR = EXAMPLE_DIR / "out"

load_dotenv(EXAMPLE_DIR.parent / ".env")
load_dotenv(EXAMPLE_DIR / ".env")
os.environ.pop("OPENAI_BASE_URL", None)

from openai import OpenAI

TTS_MODEL = "gpt-4o-mini-tts"
TRANSCRIBE_MODEL = "whisper-1"
TRIAGE_MODEL = "gpt-4o-mini"

URGENCY_ORDER = ["emergency", "same-day", "routine"]

TRIAGE_SYSTEM_PROMPT = """\
You are the overnight triage nurse for Willowbrook Animal Clinic. You read a
voicemail transcript (speech-to-text, so names and numbers may be slightly
off) and decide how fast someone must call the owner back. Reply with JSON
only, in exactly this shape:

{
  "urgency": "emergency | same-day | routine",
  "reason": "one sentence naming the clinical signs or the request",
  "caller": "the caller's name as spoken",
  "pet": "the pet's name and species",
  "phone": "the callback number exactly as spoken, digits only, or null",
  "callback_within": "e.g. 'now', '2 hours', 'end of day', '3 days'"
}

Urgency rules:
- emergency: possible poisoning (xylitol, chocolate, rat bait, grapes,
  medication), a male cat straining to urinate with nothing coming out,
  trouble breathing, collapse, seizures, heavy bleeding, bloat. Call back now.
- same-day: sick or painful but stable (appetite loss, persistent limp,
  vomiting without other danger signs). Needs a slot today.
- routine: refills, boarding, vaccines, paperwork, questions. No clinical
  signs.
When in doubt between two levels, pick the more urgent one.
"""

_client = OpenAI()


def synthesize_voicemail(voicemail: dict, audio_path: Path) -> Path:
    """Speak the script with OpenAI TTS and save it as an MP3."""
    response = _client.audio.speech.create(
        model=TTS_MODEL,
        voice=voicemail["voice"],
        input=voicemail["script"],
        response_format="mp3",
    )
    audio_path.write_bytes(response.content)
    return audio_path


def transcribe(audio_path: Path) -> str:
    """Speech-to-text with Whisper; the transcript is plain text."""
    with audio_path.open("rb") as audio_file:
        return _client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL, file=audio_file, response_format="text"
        )


def parse_triage(raw: str) -> dict:
    """Validate the model's JSON; unknown urgency falls back to emergency.

    A voicemail we cannot classify must never be silently demoted, so any
    value outside the three levels is escalated for a human to look at.
    """
    data = json.loads(raw)
    urgency = str(data.get("urgency", "")).strip().lower().replace(" ", "-")
    if urgency not in URGENCY_ORDER:
        urgency = "emergency"
    phone = data.get("phone")
    if phone is not None:
        phone = "".join(ch for ch in str(phone) if ch.isdigit()) or None
    return {
        "urgency": urgency,
        "reason": str(data.get("reason", "")).strip(),
        "caller": str(data.get("caller", "")).strip(),
        "pet": str(data.get("pet", "")).strip(),
        "phone": phone,
        "callback_within": str(data.get("callback_within", "")).strip(),
    }


def classify(transcript: str) -> dict:
    """Transcript -> structured triage decision with gpt-4o-mini."""
    response = _client.chat.completions.create(
        model=TRIAGE_MODEL,
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        response_format={"type": "json_object"},
    )
    return parse_triage(response.choices[0].message.content)


def triage_voicemail(voicemail: dict) -> dict:
    """The full pipeline for one voicemail."""
    audio_path = AUDIO_DIR / f"{voicemail['id']}.mp3"
    synthesize_voicemail(voicemail, audio_path)
    transcript = transcribe(audio_path)
    decision = classify(transcript)
    return {
        "id": voicemail["id"],
        "received": voicemail["received"],
        "transcript": transcript,
        **decision,
    }


def build_callback_list(results: list[dict]) -> list[dict]:
    """Most urgent first; `sorted` is stable, so arrival order holds within a level."""
    return sorted(results, key=lambda r: URGENCY_ORDER.index(r["urgency"]))
