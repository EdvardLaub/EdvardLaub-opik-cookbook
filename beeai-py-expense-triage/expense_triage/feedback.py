"""Attach scores to the traces the OpenTelemetry exporter created, using the Opik SDK."""

import time

import opik

from expense_triage.agent import TriageResult
from expense_triage.scoring import grade
from expense_triage.tracing import PROJECT_NAME


def find_trace_id(client: opik.Opik, report_id: str, wait_s: float = 45.0) -> str | None:
    """Newest trace whose metadata.report_id matches. OTLP ingestion is asynchronous, so poll briefly."""
    deadline = time.time() + wait_s
    while time.time() < deadline:
        found = client.search_traces(
            project_name=PROJECT_NAME,
            filter_string=f'metadata.report_id = "{report_id}"',
            max_results=10,
        )
        if found:
            return max(found, key=lambda t: t.start_time).id
        time.sleep(2)
    return None


def attach_scores(results: list[TriageResult]) -> int:
    """Log `decision_correct` and `tool_calls` feedback scores on each report's trace; returns how many were scored."""
    client = opik.Opik(project_name=PROJECT_NAME)
    scores = []
    for r in results:
        trace_id = find_trace_id(client, r.report["id"])
        if trace_id is None:
            print(f"  (no trace found yet for {r.report['id']}; skipped)")
            continue
        value, reason = grade(r)
        scores.append(
            # Feedback scores show up as columns in the Traces table, so wrong decisions can be
            # filtered (decision_correct = 0) and opened to read the thought/tool/observation chain.
            {"id": trace_id, "name": "decision_correct", "value": value, "reason": reason, "project_name": PROJECT_NAME}
        )
        scores.append(
            {"id": trace_id, "name": "tool_calls", "value": float(len(r.tools_called)),
             "reason": ", ".join(r.tools_called) or "no tool called", "project_name": PROJECT_NAME}
        )
    if scores:
        client.log_traces_feedback_scores(scores)
    client.flush()  # feedback scores are batched in the SDK; flush so they are sent before exit
    return len(scores) // 2
