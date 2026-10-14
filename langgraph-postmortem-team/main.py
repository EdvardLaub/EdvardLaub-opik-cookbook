"""Draft a blameless post-mortem for the fictional Brightloom payments outage."""

import pathlib

import dotenv
import opik
from langchain_openai import ChatOpenAI

from postmortem.checks import score_postmortem
from postmortem.costs import fetch_cost_by_agent, format_costs
from postmortem.team import build_graph
from postmortem.tracing import PROJECT_NAME, make_retrieve, trace_graph

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

    # The tracer remembers the trace it just created; attach the rule-based scores to it so they
    # show as feedback-score columns next to the trace in the Opik table.
    trace_id = tracer.created_traces()[0].id
    scores = score_postmortem(result["postmortem"])
    client = opik.Opik(project_name=PROJECT_NAME)
    client.log_traces_feedback_scores(
        [{"id": trace_id, "name": n, "value": v, "reason": "rule-based check"} for n, v in scores.items()],
        project_name=PROJECT_NAME,
    )

    # Traces are sent from a background thread; flush so a short script doesn't exit before they land.
    tracer.flush()
    opik.flush_tracker()

    print("\nScores:", scores)
    print("\nCost per agent (read back from the trace's llm spans):")
    print(format_costs(fetch_cost_by_agent(PROJECT_NAME, trace_id)))
    print(f"\nOpen project '{PROJECT_NAME}' in Opik; trace id {trace_id}")


if __name__ == "__main__":
    main()
