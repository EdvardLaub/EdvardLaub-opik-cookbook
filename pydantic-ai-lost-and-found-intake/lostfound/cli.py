"""Command line for the lost-and-found desk: `lostfound extract|intake|suite`."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .agent import MODEL, intake_note
from .grounding import ungrounded_fields
from .notes import NOTES
from .tracing import flush, traced

traced_intake = traced(intake_note)  # each call becomes one Opik trace named intake_note


def cmd_extract(args: argparse.Namespace) -> int:
    record = traced_intake(args.note)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    flush()
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    print(f"Logging {len(NOTES)} desk notes with {MODEL}...\n")
    flagged = 0
    for note in NOTES:
        record = traced_intake(note)
        print(f"  {note[:64]!r}...")
        print(f"    -> {json.dumps(record, ensure_ascii=False)}")
        bad = ungrounded_fields(record, note)
        if bad:
            flagged += 1
            print(f"    !! not in the note: {bad}")
        print()
    print(f"{flagged}/{len(NOTES)} records contain words the note never used")
    flush()  # without this the last spans never leave the process
    return 0


def cmd_suite(args: argparse.Namespace) -> int:
    from .suite import run_suite

    return run_suite()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lostfound", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("extract", help="turn one note into a FoundItemRecord")
    p.add_argument("note", help="the desk note text")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("intake", help="log every built-in desk note and flag ungrounded words")
    p.set_defaults(func=cmd_intake)

    p = sub.add_parser("suite", help="run the Opik test suite over the built-in notes")
    p.set_defaults(func=cmd_suite)
    return parser


def main(argv: list[str] | None = None) -> int:
    # Secrets come from the repo-root .env; a local .env works too.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    load_dotenv()
    args = build_parser().parse_args(argv)
    from .tracing import setup_tracing

    setup_tracing()  # must run before the first agent call
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
