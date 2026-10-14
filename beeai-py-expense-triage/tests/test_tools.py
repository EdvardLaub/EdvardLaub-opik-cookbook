import asyncio
import json

from expense_triage import tools


def test_policy_lookup_known_and_unknown_category():
    ok = tools.lookup_expense_policy_data("client_entertainment")
    assert ok["pre_approval_over_usd"] == 200 and ok["receipt_required_over_usd"] == 25
    assert "known" in tools.lookup_expense_policy_data("yachts")


def test_per_diem_flags_overage_and_scales_with_days():
    over = tools.check_per_diem_data("Boston", "meals", 142.0)
    assert over["within_limit"] is False and over["over_by_usd"] == 62.0
    two_nights = tools.check_per_diem_data("Denver", "lodging", 372.0, days=2)
    assert two_nights["limit_usd"] == 380.0 and two_nights["within_limit"] is True


def test_per_diem_edge_cases():
    assert "no per-diem" in tools.check_per_diem_data("Austin", "software", 10)["note"]
    assert "error" in tools.check_per_diem_data("Atlantis", "meals", 10)


def test_prior_claims_lookup():
    assert len(tools.get_prior_claims_data("E-2050")["claims"]) == 2
    assert "error" in tools.get_prior_claims_data("E-0000")


def test_beeai_tool_wrapper_returns_json_text():
    # The @tool wrapper is what the ReAct agent calls (and what Opik records as a tool-named span).
    async def call():  # Tool.run() returns an awaitable Run object, not a coroutine
        return await tools.check_per_diem.run({"city": "Boston", "category": "meals", "amount_usd": 142.0, "days": 1})

    out = asyncio.run(call())
    assert json.loads(out.get_text_content())["within_limit"] is False
