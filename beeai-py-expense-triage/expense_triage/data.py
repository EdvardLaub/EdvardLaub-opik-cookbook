"""Loads the fictional company data from data/ (policy, per-diems, prior claims, reports)."""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DECISIONS = ("approve", "needs-receipt", "escalate")


@lru_cache
def _load(name: str):
    return json.loads((DATA_DIR / name).read_text())


def policy() -> dict:
    return _load("policy.json")


def per_diems() -> dict:
    return _load("per_diem.json")


def prior_claims() -> dict:
    return _load("claims.json")


def reports() -> list[dict]:
    return _load("reports.json")


def format_report(report: dict) -> str:
    """The text the agent sees. The `expected` label is deliberately left out."""
    receipt = "attached" if report["has_receipt"] else "NOT attached"
    return (
        f"Expense report {report['id']}\n"
        f"Employee: {report['employee']} ({report['employee_id']})\n"
        f"Expense date: {report['date']}\n"
        f"City: {report['city']}\n"
        f"Category: {report['category']}\n"
        f"Amount: {report['amount_usd']:.2f} USD over {report['days']} day(s)/night(s)\n"
        f"Description: {report['description']}\n"
        f"Receipt: {receipt}"
    )
