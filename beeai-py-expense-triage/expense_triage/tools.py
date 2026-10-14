"""The agent's three tools. Each has a plain function (easy to unit test) and a BeeAI wrapper."""

import json

from beeai_framework.tools import StringToolOutput, tool

from expense_triage import data


def lookup_expense_policy_data(category: str) -> dict:
    pol = data.policy()
    rule = pol["categories"].get(category)
    if rule is None:
        return {"error": f"unknown category '{category}'", "known": sorted(pol["categories"])}
    return {
        "category": category,
        "rule": rule["rule"],
        "receipt_required_over_usd": pol["receipt_required_over_usd"],
        "pre_approval_over_usd": rule["pre_approval_over_usd"],
    }


def check_per_diem_data(city: str, category: str, amount_usd: float, days: int = 1) -> dict:
    table = data.per_diems().get(city)
    if table is None:
        return {"error": f"no per-diem table for '{city}'", "known": sorted(data.per_diems())}
    key = {"meals": "meals_per_day", "lodging": "lodging_per_night"}.get(category)
    if key is None:
        return {"city": city, "category": category, "note": "no per-diem applies to this category"}
    limit = round(table[key] * max(days, 1), 2)
    return {
        "city": city,
        "category": category,
        "limit_usd": limit,
        "claimed_usd": amount_usd,
        "within_limit": amount_usd <= limit,
        "over_by_usd": round(max(amount_usd - limit, 0), 2),
    }


def get_prior_claims_data(employee_id: str) -> dict:
    claims = data.prior_claims().get(employee_id)
    if claims is None:
        return {"error": f"unknown employee '{employee_id}'"}
    return {"employee_id": employee_id, "claims": claims}


@tool(name="lookup_expense_policy")
def lookup_expense_policy(category: str) -> StringToolOutput:
    """Look up the company expense policy for one category (meals, lodging, ground_transport,
    software, client_entertainment): the reimbursement rule, receipt threshold and pre-approval limit."""
    return StringToolOutput(json.dumps(lookup_expense_policy_data(category)))


@tool(name="check_per_diem")
def check_per_diem(city: str, category: str, amount_usd: float, days: int = 1) -> StringToolOutput:
    """Compare a claimed amount with the per-diem limit for a city. Only meals and lodging have a
    per-diem; days is the number of days (meals) or nights (lodging) the amount covers."""
    return StringToolOutput(json.dumps(check_per_diem_data(city, category, amount_usd, days)))


@tool(name="get_prior_claims")
def get_prior_claims(employee_id: str) -> StringToolOutput:
    """Fetch the employee's previously paid claims (date, category, city, amount, description),
    for example to spot a duplicate of the claim under review."""
    return StringToolOutput(json.dumps(get_prior_claims_data(employee_id)))


TOOLS = [lookup_expense_policy, check_per_diem, get_prior_claims]
