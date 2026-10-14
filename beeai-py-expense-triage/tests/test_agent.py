import asyncio
from types import SimpleNamespace

import pytest

from expense_triage import agent, data
from expense_triage.scoring import grade, summary_line


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Decision: approve\nReason: fine", "approve"),
        ("Decision: needs-receipt  \nReason: x", "needs-receipt"),
        ("\nDecision: **Escalate**\nReason: x", "escalate"),
        ("I think this is fine.", None),
    ],
)
def test_parse_decision(text, expected):
    assert agent.parse_decision(text) == expected


class FakeAgent:
    def __init__(self, text=None, error=None):
        self.text, self.error = text, error

    async def run(self, prompt, **kwargs):
        if self.error:
            raise self.error
        it = SimpleNamespace(state=SimpleNamespace(tool_name="get_prior_claims"))
        return SimpleNamespace(last_message=SimpleNamespace(text=self.text), iterations=[it])


def test_triage_report_runs_under_the_noop_tracer(monkeypatch):
    # No provider configured: the OpenTelemetry span in triage_report is a no-op, so unit tests
    # run offline and untouched by tracing.
    monkeypatch.setattr(agent, "build_agent", lambda: FakeAgent("Decision: escalate\nReason: dup"))
    report = data.reports()[4]
    result = asyncio.run(agent.triage_report(report))
    assert result.decision == "escalate" and result.tools_called == ["get_prior_claims"]
    assert grade(result) == (1.0, "decided escalate, as expected")


def test_failed_run_is_returned_not_raised(monkeypatch):
    monkeypatch.setattr(agent, "build_agent", lambda: FakeAgent(error=RuntimeError("out of iterations")))
    result = asyncio.run(agent.triage_report(data.reports()[0], max_iterations=1))
    assert result.decision is None and "out of iterations" in result.text
    assert grade(result)[0] == 0.0
    assert summary_line([result]) == "0/1 decisions match the expected label"
