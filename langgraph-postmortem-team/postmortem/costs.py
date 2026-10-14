"""Roll LLM cost and tokens up to the agent (graph node) that spent them."""

import time
from collections import defaultdict

import opik

AGENTS = ("planner", "investigator", "writer")


def cost_by_agent(spans) -> dict[str, dict]:
    """Sum llm-span cost and tokens under each agent node; node passes are counted too.

    Opik records cost on the llm spans only, so the node spans themselves show no cost;
    walking each llm span up its parent chain to the node attributes the spend to an agent.
    """
    by_id = {s.id: s for s in spans}
    totals = defaultdict(lambda: {"passes": 0, "llm_calls": 0, "tokens": 0, "cost": 0.0})
    for s in spans:
        if s.name in AGENTS and s.type == "general":
            totals[s.name]["passes"] += 1
    for s in spans:
        if s.type != "llm":
            continue
        node = s
        while node is not None and node.name not in AGENTS:
            node = by_id.get(node.parent_span_id)
        if node is None:
            continue
        t = totals[node.name]
        t["llm_calls"] += 1
        t["tokens"] += (s.usage or {}).get("total_tokens") or 0
        t["cost"] += s.total_estimated_cost or 0.0
    return {a: totals[a] for a in AGENTS if a in totals}


def format_costs(per_agent: dict[str, dict]) -> str:
    lines = [f"{'agent':<14}{'passes':>7}{'tokens':>9}{'cost (USD)':>13}"]
    for name, t in per_agent.items():
        lines.append(f"{name:<14}{t['passes']:>7}{t['tokens']:>9}{t['cost']:>13.6f}")
    lines.append(f"{'total':<14}{sum(t['passes'] for t in per_agent.values()):>7}"
                 f"{sum(t['tokens'] for t in per_agent.values()):>9}"
                 f"{sum(t['cost'] for t in per_agent.values()):>13.6f}")
    return "\n".join(lines)


def fetch_cost_by_agent(project_name: str, trace_id: str, wait_s: float = 30) -> dict[str, dict]:
    """Read the trace's spans back from Opik (ingestion is async, so poll briefly)."""
    client = opik.Opik(project_name=project_name)
    deadline = time.time() + wait_s
    while True:
        spans = client.search_spans(project_name=project_name, trace_id=trace_id, max_results=500)
        per_agent = cost_by_agent(spans)
        # Done once the writer's llm span, the last one to finish, has its cost.
        if per_agent.get("writer", {}).get("cost") or time.time() > deadline:
            return per_agent
        time.sleep(1.5)
