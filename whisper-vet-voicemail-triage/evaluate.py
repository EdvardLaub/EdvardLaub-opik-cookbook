"""Test suite for the triage step: does each voicemail get the right urgency?

A triage model that under-calls an emergency is the expensive failure, and an
LLM judge grading that call is itself noisy. This suite feeds each Whisper
transcript (cached by main.py) back through `classify` and lets a judge check
plain-English assertions: a per-voicemail one on the urgency, plus two global
ones on whether the callback details are grounded in what was said.

Each `opik.run_tests` call becomes an experiment in Opik. Run main.py first,
or just run this: it triages the voicemails itself when no cache exists.
"""

import json

import opik

from main import OUT_DIR, main as run_pipeline
from triage import classify
from voicemails import VOICEMAILS

SUITE_NAME = "vet-voicemail-triage-suite"

GLOBAL_ASSERTIONS = [
    "The reason is grounded in the transcript: it may restate or clinically "
    "name what the caller describes, but it adds no symptom, medication, "
    "or request the caller never mentioned.",
    "The phone number, if present, matches the digits the caller says in the "
    "transcript, and is null only when the caller gives no number.",
]

URGENCY_MEANING = {
    "emergency": "an emergency that needs a callback right now",
    "same-day": "same-day: sick or in pain but stable, needs a slot today",
    "routine": "routine: no clinical signs, no rush",
}


def task(item: dict) -> dict:
    """Classify one transcript. The judge sees this input and output."""
    decision = classify(item["transcript"])
    return {"input": {"transcript": item["transcript"]}, "output": decision}


def load_transcripts() -> dict[str, str]:
    cache = OUT_DIR / "results.json"
    if not cache.exists():
        run_pipeline()
    return {r["id"]: r["transcript"] for r in json.loads(cache.read_text())}


if __name__ == "__main__":
    transcripts = load_transcripts()

    client = opik.Opik()
    # A test suite = items + plain-English assertions + an execution policy.
    # run_tests turns each run into an experiment with a verdict per assertion.
    suite = client.get_or_create_test_suite(
        name=SUITE_NAME,
        project_name="whisper-vet-voicemail-triage",
        global_assertions=GLOBAL_ASSERTIONS,
        # Judge and classifier are both LLMs, so one run is a coin flip near
        # a boundary. Run every item three times; it passes if 2 of 3 do.
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )

    # Add each voicemail once; re-runs reuse the existing items.
    existing = {item["data"]["voicemail"] for item in suite.get_items()}
    for vm in VOICEMAILS:
        if vm["id"] not in existing:
            suite.insert(
                [
                    {
                        "data": {"voicemail": vm["id"], "transcript": transcripts[vm["id"]]},
                        # Item-level assertion: the ground truth for this call.
                        "assertions": [
                            f"The urgency is classified as {URGENCY_MEANING[vm['expected']]}; "
                            f"the urgency field must be exactly \"{vm['expected']}\"."
                        ],
                    }
                ]
            )

    result = opik.run_tests(test_suite=suite, task=task)
    print(f"\nPass rate: {result.pass_rate:.0%}")
    opik.flush_tracker()
