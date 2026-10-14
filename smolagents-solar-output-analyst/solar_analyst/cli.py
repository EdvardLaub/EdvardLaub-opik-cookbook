"""Command line: ask one question, or run the scripted set.

    solar-analyst "Which array produced the most energy in May?"
    solar-analyst --scripted
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from solar_analyst.agent import build_agent
from solar_analyst.data import briefing
from solar_analyst.questions import QUESTIONS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="solar-analyst", description=__doc__.splitlines()[0])
    p.add_argument("question", nargs="?", help="a free-form question about the production data")
    p.add_argument("--scripted", action="store_true", help="run the built-in question set")
    args = p.parse_args(argv)
    if not args.question and not args.scripted:
        p.error("give a question or pass --scripted")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Keys live in the repo-root .env (a local .env works too).
    here = Path(__file__).resolve().parent.parent
    load_dotenv(here.parent / ".env")
    load_dotenv(here / ".env")
    os.environ.pop("OPENAI_BASE_URL", None)  # talk to the public API

    agent = build_agent()
    asked = [args.question] if args.question else [q.text for q in QUESTIONS]
    for i, text in enumerate(asked, 1):
        print(f"\n{'=' * 72}\nQuestion {i}: {text}\n{'=' * 72}")
        answer = agent.run(briefing() + "\nQuestion: " + text)
        print(f"\nAnswer {i}: {answer}")
    return 0
