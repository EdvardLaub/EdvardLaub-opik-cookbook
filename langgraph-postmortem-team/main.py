"""Draft a blameless post-mortem for the fictional Brightloom payments outage."""

import pathlib

import dotenv
import opik
from langchain_openai import ChatOpenAI

from postmortem.team import build_graph
from postmortem.tracing import make_retrieve, trace_graph

# Secrets live in the repo-root .env (OPENAI_API_KEY).
dotenv.load_dotenv(pathlib.Path(__file__).parents[1] / ".env")

INCIDENT = (
    "On 2026-10-02 Brightloom's payments API (ledger-api) failed for most checkouts. "
    "Write the blameless post-mortem for this incident."
)


def main() -> None:
    graph = build_graph(ChatOpenAI(model="gpt-4o-mini", temperature=0), retrieve=make_retrieve())
    app, tracer = trace_graph(graph.compile())
    result = app.invoke({"incident": INCIDENT})

    print("Evidence questions:")
    for i, q in enumerate(result["questions"], 1):
        print(f"  {i}. {q}")
    print("\n" + result["postmortem"])

    # Traces are sent from a background thread; flush so a short script doesn't exit before they land.
    tracer.flush()
    opik.flush_tracker()


if __name__ == "__main__":
    main()
