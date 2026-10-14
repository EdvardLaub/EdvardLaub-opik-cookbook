"""Grading: compare the agent's decision with the label stored next to each report."""

from expense_triage.agent import TriageResult


def grade(result: TriageResult) -> tuple[float, str]:
    """(score, reason): 1.0 when the decision matches the report's expected label, else 0.0."""
    expected = result.report["expected"]
    if result.decision is None:
        return 0.0, f"no decision produced (expected {expected})"
    if result.decision == expected:
        return 1.0, f"decided {result.decision}, as expected"
    return 0.0, f"decided {result.decision}, expected {expected}"


def summary_line(results: list[TriageResult]) -> str:
    ok = sum(grade(r)[0] for r in results)
    return f"{int(ok)}/{len(results)} decisions match the expected label"
