<div align="center">

# Whisper Vet Voicemail Triage

**`whisper-vet-voicemail-triage`**

*Hear the call that got a dog sent to the front of the queue, from inside the trace.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![OpenAI SDK](https://img.shields.io/badge/openai-2.x-412991?style=flat&logo=openai&logoColor=white)
[![Opik](https://img.shields.io/badge/Opik-2.2.100%2B-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

</div>

---

At Willowbrook Animal Clinic (fictional) nobody answers the phone between 11 pm and 8 am. Owners leave voicemails, and every morning somebody has to decide who gets a call first: the beagle that ate a pack of xylitol gum, or the greyhound that needs heartworm tablets. This example automates that sort. The risk is lopsided: calling a refill customer early costs nothing, but burying a blocked cat under routine requests can cost a life. When the pipeline gets one wrong you need two things the plain logs do not give you: the voice that actually left the message, and a way to grade the triage that does not flip a coin on every run.

## What you'll build

Five scripted voicemails live in `voicemails.py`. At run time each one is spoken with OpenAI text-to-speech (`gpt-4o-mini-tts`, a different voice per caller) and saved as an MP3 in `audio/`, which is git-ignored, so nothing audio is committed. Whisper (`whisper-1`) transcribes the MP3 back to text, and `gpt-4o-mini` classifies the transcript as `emergency`, `same-day` or `routine` and pulls out caller, pet, phone number and how quickly to call back. `main.py` prints the result as a callback list, most urgent first.

Opik shows up in two places. `@opik.track` plus `track_openai` give one trace per voicemail with the MP3 attached. `evaluate.py` then builds an Opik test suite over the transcripts, with an LLM judge and an `execution_policy` of 3 runs per item.

## See it in Opik

Open the `whisper-vet-voicemail-triage` project and look at the traces named `triage-voicemail`. There are five, tagged `emergency`, `emergency`, `same-day`, `same-day` and `routine`, so a tag filter gives you the queue as the pipeline saw it. Open the xylitol one (the `nova` voice): the Attachments tab holds `vm1-xylitol.mp3` at about 270 KB and plays in the browser. Press play, then read the `transcribe` span next to it. The transcript says "My number is 555-0142" where the script spelled out "five five five, zero one four two", so you can check Whisper's digits against the voice in seconds.

Each trace has six spans: `triage-voicemail` at the root, `synthesize-voicemail` with an `audio.speech.create` child, `transcribe`, and `classify` with a `chat_completion_create` child. The two OpenAI children are `llm` spans with token usage and an estimated cost (for the xylitol trace, 435 tokens and about $0.0001 for the chat call, 288 tokens for the speech call). The Whisper call has no child span of its own, because `track_openai` does not wrap `audio.transcriptions`; the `transcribe` span carries the transcript as its output instead.

The experiment is named `working_strawberry_9130` in my run, under the dataset `vet-voicemail-triage-suite`. It has five items, each run three times, so 15 `evaluation_task` traces. The suite passed 5 of 5 items, yet two of the 15 individual runs failed on the "grounded in the transcript" assertion. The judge said one `reason` ("possible xylitol poisoning...") added a diagnosis the caller never stated, and another ("straining to urinate... which can be deadly") added a symptom and a prognosis. Those two items each passed 2 of 3 runs, which clears the threshold of 2. Without the policy, the first of those would have failed the suite on a single run. Your numbers will differ; judges wobble.

## Run it yourself

1. Install [uv](https://docs.astral.sh/uv/) and start Opik: local self-hosted (`opik configure --use_local`) or Opik Cloud.
2. `cp .env.example .env` and add `OPENAI_API_KEY` (a `.env` one directory up is also read).
3. `uv sync`
4. `uv run main.py` generates the voicemails, transcribes and triages them, prints the callback list. About 90 seconds and a few cents.
5. `uv run evaluate.py` runs the test suite over the transcripts main.py just saved to `out/` (if there are none it runs the pipeline first). About 20 seconds.
6. In Opik, open the `whisper-vet-voicemail-triage` project, then Experiments.

Tests are offline: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`.

## Poke around

- Re-run `uv run main.py` and compare Whisper's spelling of the callers with `voicemails.py`. "Lindqvist" has come back as "Lindquist" and "Lingfist" in different runs, which is exactly why you want the audio on the trace.
- In `evaluate.py`, set `runs_per_item` to 1 and `pass_threshold` to 1, and run it a few times. Watch the grounding assertion flip the suite between pass and fail.
- Change the `emergency` rules in `TRIAGE_SYSTEM_PROMPT` (drop the male-cat sentence) and see whether item 2 of the suite goes red.
- Add a sixth voicemail to `voicemails.py` with an ambiguous call (a dog that "threw up once and seems tired") and decide what urgency you want it to get.

## Gotchas we hit

**The suite fails 4/5 and the judge's reason says "not explicitly mentioned".** My first grounding assertion read "the reason cites only signs that appear in the transcript; nothing is invented". The blocked-cat voicemail failed it in 2 of 3 runs, because the judge refused to accept "straining to urinate" for a cat that goes back and forth to the litter box with nothing coming out. The model was right and the assertion was too literal. Fix the assertion, not the retries: it now allows restating or clinically naming what the caller describes, and forbids new symptoms, medications or requests. An execution policy absorbs random noise, not a systematic disagreement.

**No transcription span, or cost looks absent for Whisper.** `track_openai` produces spans for `audio.speech.create` and chat completions but not `audio.transcriptions.create`. Decorate your own `transcribe` function with `@opik.track` (the transcript becomes its output) and expect no token or cost numbers for that step.

## How it's put together

- `voicemails.py`: five fictional voicemail scripts, each with a TTS voice and the urgency a nurse would assign.
- `triage.py`: the pipeline (TTS, Whisper, classification, callback ordering), traced with `@opik.track` and `track_openai`, MP3 attached.
- `main.py`: runs every voicemail, caches transcripts to `out/`, prints the callback list, flushes Opik.
- `evaluate.py`: the test suite, with per-voicemail urgency assertions, two global grounding assertions, and `runs_per_item=3`, `pass_threshold=2`.
- `tests/test_triage.py`: offline tests for the parser, urgency fallback, ordering, fixtures, and a traced call with tracking disabled.
- `.env.example`, `pyproject.toml`, `.gitignore`: configuration; `audio/`, `out/` and test reports are git-ignored.

---

*built with Opik · inspired by Opik's examples and documentation*
