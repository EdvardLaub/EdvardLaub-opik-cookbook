"""Read the project back from Opik and check that each review is ONE trace holding spans from both processes.

Run after the demo:  uv run python -m grantreview.verify
"""

import sys
import time

import opik

from grantreview.tracing import PROJECT_NAME


def span_tree(spans) -> str:
    lines = []

    def walk(parent_id, depth):
        kids = sorted((s for s in spans if s.parent_span_id == parent_id), key=lambda s: s.start_time)
        for s in kids:
            err = f"  <-- ERROR: {s.error_info.message}" if s.error_info else ""
            cost = f"  {s.usage['total_tokens']} tokens, ${s.total_estimated_cost:.6f}" if s.usage else ""
            lines.append(f"{'  ' * depth}{s.name} [{s.type}]{err}{cost}")
            walk(s.id, depth + 1)

    walk(None, 0)
    return "\n".join(lines)


def main() -> int:
    client = opik.Opik()
    client.flush()
    traces = []
    for _ in range(10):  # ingestion is asynchronous: give the last spans a moment to land
        traces = client.search_traces(project_name=PROJECT_NAME, max_results=50)
        if len(traces) >= 3:
            break
        time.sleep(2)
    ok = bool(traces)
    for t in sorted(traces, key=lambda t: t.name):
        spans = client.search_spans(project_name=PROJECT_NAME, trace_id=t.id, max_results=200)
        # One root (opened by the client) with RunWorkflow / RunActivity spans (only the
        # worker process can emit those) underneath it = a trace that crossed processes.
        roots = [s for s in spans if s.parent_span_id is None]
        worker_spans = [s for s in spans if s.name.startswith(("RunWorkflow", "RunActivity"))]
        attempts = [s for s in spans if s.name == "RunActivity:check_eligibility"]
        failed = [s for s in attempts if s.error_info]
        llm = [s for s in spans if s.type == "llm"]
        print(f"\n== {t.name}: {len(spans)} spans, {len(roots)} root, {len(worker_spans)} worker spans, "
              f"{len(attempts)} eligibility attempts ({len(failed)} failed), {len(llm)} llm spans")
        print(span_tree(spans))
        ok &= len(roots) == 1 and bool(worker_spans) and len(attempts) == 2 and len(failed) == 1 and all(s.usage and s.input and s.output for s in llm) and bool(t.input and t.output)
    print("\nPASS" if ok else "\nFAIL: expected one client root with worker spans under it, 2 eligibility attempts (1 failed) and usage plus input/output on every llm span and on the trace")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
