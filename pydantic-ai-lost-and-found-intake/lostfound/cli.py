"""Command line for the lost-and-found desk: `lostfound extract|intake|suite`."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .agent import MODEL, intake_note
from .notes import NOTES


def cmd_extract(args: argparse.Namespace) -> int:
    print(json.dumps(intake_note(args.note), indent=2))
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    print(f"Logging {len(NOTES)} desk notes with {MODEL}...\n")
    for note in NOTES:
        print(f"  {note[:64]!r}...")
        print(f"    -> {json.dumps(intake_note(note))}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lostfound", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("extract", help="turn one note into a FoundItemRecord")
    p.add_argument("note", help="the desk note text")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("intake", help="log every built-in desk note")
    p.set_defaults(func=cmd_intake)
    return parser


def main(argv: list[str] | None = None) -> int:
    # Secrets come from the repo-root .env; a local .env works too.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    load_dotenv()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
