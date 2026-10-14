"""Command line: triage the built-in reports, or one by id.

    expense-triage            # all reports
    expense-triage R-1003     # one report
"""

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from expense_triage import data
from expense_triage.scoring import grade, summary_line
from expense_triage.tracing import setup_tracing


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="expense-triage", description=__doc__.splitlines()[0])
    p.add_argument("--max-iterations", type=int, default=8, help="ReAct iteration budget (try 2 to starve the agent)")
    p.add_argument("--no-trace", action="store_true", help="do not export spans to Opik")
    p.add_argument("report_id", nargs="?", help="a report id such as R-1003 (default: all)")
    return p.parse_args(argv)


def select(report_id: str | None) -> list[dict]:
    chosen = [r for r in data.reports() if report_id in (None, r["id"])]
    if not chosen:
        raise SystemExit(f"No report with id {report_id!r}")
    return chosen


async def run(reports: list[dict], max_iterations: int) -> list:
    from expense_triage.agent import triage_report

    results = []
    for report in reports:
        print(f"\n=== {report['id']}: {report['employee']}, {report['category']} {report['amount_usd']:.2f} USD ({report['city']})")
        result = await triage_report(report, max_iterations=max_iterations)
        print(result.text)
        results.append(result)
    return results


def print_grades(results: list) -> None:
    print("\nGraded against the expected decisions:")
    for r in results:
        score, reason = grade(r)
        print(f"  {'PASS' if score else 'FAIL'}  {r.report['id']}  {reason}  tools={r.tools_called}")
    print(summary_line(results))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Keys live in the repo-root .env (a local .env works too).
    here = Path(__file__).resolve().parent.parent
    load_dotenv(here.parent / ".env")
    load_dotenv(here / ".env")
    os.environ.pop("OPENAI_BASE_URL", None)  # talk to the public API
    provider = None if args.no_trace else setup_tracing()
    results = asyncio.run(run(select(args.report_id), args.max_iterations))
    print_grades(results)
    if provider is not None:
        # BatchSpanProcessor exports in the background; without this flush the last spans
        # can be lost when the process exits and the final trace shows up incomplete.
        provider.force_flush()
        provider.shutdown()
        from expense_triage.feedback import attach_scores

        print(f"Scored {attach_scores(results)} traces in Opik (decision_correct, tool_calls).")
        print('\nDone. Open the "beeai-py-expense-triage" project in Opik to see the traces.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
