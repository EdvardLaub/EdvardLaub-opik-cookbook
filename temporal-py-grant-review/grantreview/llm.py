"""The two OpenAI calls, kept apart from Temporal so they are easy to stub."""

import json
import os

from openai import AsyncOpenAI

from grantreview.data import FOUNDATION, MAX_GRANT
from grantreview.models import Application, Score

MODEL = os.getenv("GRANT_MODEL", "gpt-4o-mini")

SCORE_SYSTEM = f"""You are a grant panel reader for the {FOUNDATION}. Score the application on three
criteria, each an integer from 1 (weak) to 5 (excellent):
- community_benefit: how many neighbours gain, and how directly
- feasibility: is there a concrete plan, permission, partners and evidence it can be delivered
- value_for_money: is the amount (maximum grant GBP {MAX_GRANT}) justified by costed items
Be strict: vague plans, missing permissions and unsupported costs score low.
Reply with JSON only: {{"community_benefit": n, "feasibility": n, "value_for_money": n, "rationale": "two sentences"}}"""

LETTER_SYSTEM = f"""You write decision letters for the {FOUNDATION}. Warm, plain English, under 120
words, addressed to the applicant, signed 'The Grants Panel'. Say clearly whether the grant is approved or
declined and give the real reasons you are given. Never invent amounts, dates or conditions."""


def client() -> AsyncOpenAI:
    return AsyncOpenAI()


def parse_score(raw: str) -> Score:
    """Parse and clamp the model's JSON so a stray 7 or a string never reaches the workflow."""
    data = json.loads(raw)

    def clamp(key: str) -> int:
        return max(1, min(5, int(data[key])))

    return Score(
        community_benefit=clamp("community_benefit"),
        feasibility=clamp("feasibility"),
        value_for_money=clamp("value_for_money"),
        rationale=str(data.get("rationale", "")).strip(),
    )


def score_prompt(app: Application) -> str:
    return (
        f"Applicant: {app.applicant}\nProject: {app.title}\n"
        f"Amount requested: GBP {app.amount_requested}\n\n{app.summary}"
    )


def letter_prompt(app: Application, decision: str, reasons: list[str]) -> str:
    bullet = "\n".join(f"- {r}" for r in reasons) or "- (no further comment)"
    return (
        f"Applicant: {app.applicant}\nProject: {app.title}\nAmount requested: GBP {app.amount_requested}\n"
        f"Decision: {decision}\nReasons:\n{bullet}"
    )


async def score_with_llm(app: Application) -> Score:
    resp = await client().chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SCORE_SYSTEM},
            {"role": "user", "content": score_prompt(app)},
        ],
    )
    return parse_score(resp.choices[0].message.content or "{}")


async def letter_with_llm(app: Application, decision: str, reasons: list[str]) -> str:
    resp = await client().chat.completions.create(
        model=MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": LETTER_SYSTEM},
            {"role": "user", "content": letter_prompt(app, decision, reasons)},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
