"""Command line: ask one question, or run the scripted set.

    solar-analyst "Which array produced the most energy in May?"
    solar-analyst --scripted
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from solar_analyst.agent import build_agent
from solar_analyst.checks import grade, ground_truth
from solar_analyst.data import briefing, load_production
from solar_analyst.questions import QUESTIONS
from solar_analyst.tracing import PROJECT_NAME, setup_tracing


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="solar-analyst", description=__doc__.splitlines()[0])
    p.add_argument("question", nargs="?", help="a free-form question about the production data")
    p.add_argument("--scripted", action="store_true", help="run the built-in question set")
    p.add_argument("--no-trace", action="store_true", help="do not export spans to Opik")
    args = p.parse_args(argv)
    if not args.question and not args.scripted:
        p.error("give a question or pass --scripted")
    return args


def ask(agent, text: str) -> str:
    print(f"\n{'=' * 72}\nQuestion: {text}\n{'=' * 72}")
    # One agent.run = one Opik trace (when tracing is on); the prompt is the trace input.
    answer = str(agent.run(briefing() + "\nQuestion: " + text))
    print(f"\nAnswer: {answer}")
    return answer


def run_scripted(agent) -> dict[str, bool]:
    """Ask every scripted question and grade each answer against the CSV's planted anomalies."""
    truth = ground_truth(load_production())
    results = {q.key: grade(q.key, ask(agent, q.text), truth) for q in QUESTIONS}
    print("\nGraded against the data:")
    for key, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key}")
    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Keys live in the repo-root .env (a local .env works too).
    here = Path(__file__).resolve().parent.parent
    load_dotenv(here.parent / ".env")
    load_dotenv(here / ".env")
    os.environ.pop("OPENAI_BASE_URL", None)  # talk to the public API

    provider = None if args.no_trace else setup_tracing()
    agent = build_agent()
    if args.question:
        ask(agent, args.question)
    else:
        run_scripted(agent)

    if provider:
        # Spans are exported in batches; flush so the last trace is not lost at exit.
        provider.force_flush()
        provider.shutdown()
        print(f"\nTraces are in the '{PROJECT_NAME}' project in Opik.")
    return 0
