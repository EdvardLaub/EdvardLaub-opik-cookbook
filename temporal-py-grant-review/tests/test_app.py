"""Offline tests: no provider key, no Temporal server, no Opik (run with OPIK_TRACK_DISABLE=true)."""

import dataclasses
import json
from types import SimpleNamespace

import pytest
from temporalio.testing import ActivityEnvironment

from grantreview import llm
from grantreview.activities import check_eligibility, eligibility_problems
from grantreview.data import APPLICATIONS, PASS_MARK
from grantreview.models import Score
from grantreview.workflows import decide

ORCHARD, FOOTBALL, GALLERY = APPLICATIONS


def activity_env(attempt: int) -> ActivityEnvironment:
    env = ActivityEnvironment()
    env.info = dataclasses.replace(env.info, attempt=attempt)
    return env


def test_eligibility_rules():
    assert eligibility_problems(ORCHARD, "registered") == []
    assert "dissolved" in eligibility_problems(GALLERY, "dissolved")[0]
    far = dataclasses.replace(ORCHARD, postcode="XX1 1XX", amount_requested=9_000)
    assert len(eligibility_problems(far, "registered")) == 2


async def test_first_attempt_fails_and_retry_succeeds():
    # The flaky register lookup is what produces the errored RunActivity span in Opik.
    with pytest.raises(ConnectionError, match="timed out"):
        await activity_env(1).run(check_eligibility, ORCHARD)
    result = await activity_env(2).run(check_eligibility, ORCHARD)
    assert result.eligible


def test_parse_score_clamps_out_of_range_values():
    raw = '{"community_benefit": 9, "feasibility": "3", "value_for_money": 0, "rationale": " ok "}'
    score = llm.parse_score(raw)
    assert (score.community_benefit, score.feasibility, score.value_for_money) == (5, 3, 1)
    assert score.rationale == "ok"


def test_decision_threshold():
    assert decide(PASS_MARK) == "approved"
    assert decide(PASS_MARK - 1) == "declined"
    assert Score(4, 4, 5, "").total == 13


def test_letter_prompt_carries_decision_and_reasons():
    text = llm.letter_prompt(GALLERY, "declined", ["register says dissolved"])
    assert "Decision: declined" in text and "- register says dissolved" in text


async def test_traced_llm_call_runs_with_tracking_disabled(monkeypatch):
    # llm_span is a no-op tracer span when no exporter is installed, so unit tests pass
    # straight through the instrumented function.
    reply = json.dumps({"community_benefit": 4, "feasibility": 4, "value_for_money": 3, "rationale": "solid"})
    response = SimpleNamespace(
        model="stub", usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
    )

    async def create(**_):
        return response

    stub = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "client", lambda: stub)
    assert (await llm.score_with_llm(ORCHARD)).total == 11
