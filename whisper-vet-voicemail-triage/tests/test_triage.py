"""Offline tests: no provider keys, no Opik. Run with
`env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`.
"""

import json
import os
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")  # client needs *a* value to construct
os.environ["OPIK_TRACK_DISABLE"] = "true"

import triage
from triage import build_callback_list, parse_triage
from voicemails import VOICEMAILS


def test_parse_triage_normalizes_fields():
    raw = json.dumps(
        {"urgency": "Same Day", "reason": " limp ", "caller": "Tomasz", "pet": "Juno",
         "phone": "555-0128", "callback_within": "2 hours"}
    )
    out = parse_triage(raw)
    assert out["urgency"] == "same-day"
    assert out["phone"] == "5550128"
    assert out["reason"] == "limp"


def test_unknown_urgency_escalates_to_emergency():
    assert parse_triage(json.dumps({"urgency": "urgent!!"}))["urgency"] == "emergency"
    assert parse_triage("{}")["phone"] is None


def test_callback_list_most_urgent_first_and_stable():
    rows = [
        {"id": "a", "urgency": "routine"},
        {"id": "b", "urgency": "same-day"},
        {"id": "c", "urgency": "emergency"},
        {"id": "d", "urgency": "emergency"},
    ]
    assert [r["id"] for r in build_callback_list(rows)] == ["c", "d", "b", "a"]


def test_voicemail_fixtures_cover_every_level():
    assert {v["expected"] for v in VOICEMAILS} == set(triage.URGENCY_ORDER)


def test_traced_classify_runs_with_tracking_disabled(monkeypatch):
    """@opik.track and track_openai must not get in the way of a stubbed call."""
    reply = json.dumps({"urgency": "routine", "reason": "refill", "caller": "Grace",
                        "pet": "Otis", "phone": "5550166", "callback_within": "3 days"})
    fake = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])))
    )
    monkeypatch.setattr(triage, "_client", fake)
    assert triage.classify("hello")["urgency"] == "routine"
