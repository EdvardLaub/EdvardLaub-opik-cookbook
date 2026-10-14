import pytest

from solar_analyst import cli


class StubAgent:
    """Stands in for the CodeAgent: answers each scripted question correctly, no model call."""

    ANSWERS = {
        "multi-day outage": "Pond Edge was down from 2026-05-11 to 2026-05-16.",
        "dropped relative": "Barn Roof fell about 25% from May.",
        "physically impossible": "Hillside Tracker on April 9, 2026 read 2950 kWh.",
    }

    def run(self, prompt: str) -> str:
        return next(a for k, a in self.ANSWERS.items() if k in prompt)


def test_scripted_run_grades_every_question(capsys):
    results = cli.run_scripted(StubAgent())
    assert results == {"outage": True, "underperformer": True, "glitch": True}
    assert "PASS  glitch" in capsys.readouterr().out


def test_cli_needs_a_question_or_flag():
    with pytest.raises(SystemExit):
        cli.parse_args([])
    assert cli.parse_args(["--scripted"]).scripted
