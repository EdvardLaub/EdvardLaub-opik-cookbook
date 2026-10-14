"""Run the overnight triage over every voicemail and print the callback list."""

import json

import opik

from triage import AUDIO_DIR, OUT_DIR, build_callback_list, triage_voicemail
from voicemails import VOICEMAILS


def main() -> None:
    AUDIO_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)

    results = []
    for voicemail in VOICEMAILS:
        print(f"Triaging {voicemail['id']} ...")
        results.append(triage_voicemail(voicemail))

    # evaluate.py reads these cached transcripts as its test-suite items.
    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2))

    print("\nCALLBACK LIST (most urgent first)")
    for r in build_callback_list(results):
        print(
            f"[{r['urgency'].upper():9}] {r['caller']} ({r['pet']}) "
            f"tel {r['phone'] or '?'} - call within {r['callback_within']}\n"
            f"            {r['reason']}"
        )

    # Traces ship from a background thread; flush so none are lost at exit.
    opik.flush_tracker()
    print("\nDone. Open the whisper-vet-voicemail-triage project in Opik.")


if __name__ == "__main__":
    main()
