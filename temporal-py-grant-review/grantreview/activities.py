"""Temporal activities: the side-effecting steps of a review."""

from temporalio import activity

from grantreview.data import LARKFIELD_PREFIXES, MAX_GRANT, REGISTER
from grantreview.llm import letter_with_llm, score_with_llm
from grantreview.models import Application, Eligibility, Score


def eligibility_problems(app: Application, register_status: str) -> list[str]:
    """Pure rule check, separated from the register lookup so it can be unit-tested."""
    problems = []
    if register_status != "registered":
        problems.append(f"the charity register lists {app.applicant} as '{register_status}'")
    if not app.postcode.upper().startswith(LARKFIELD_PREFIXES):
        problems.append(f"postcode {app.postcode} is outside the Larkfield area")
    if app.amount_requested > MAX_GRANT:
        problems.append(f"GBP {app.amount_requested} is above the GBP {MAX_GRANT} limit")
    return problems


async def lookup_register(applicant: str) -> str:
    """Stand-in for the national charity register, which times out on the first call."""
    if activity.info().attempt == 1:
        raise ConnectionError("Charity register timed out (503 from registry.example.org)")
    return REGISTER.get(applicant, "unknown")


@activity.defn
async def check_eligibility(app: Application) -> Eligibility:
    status = await lookup_register(app.applicant)
    problems = eligibility_problems(app, status)
    return Eligibility(eligible=not problems, reasons=problems)


@activity.defn
async def score_application(app: Application) -> Score:
    return await score_with_llm(app)


@activity.defn
async def draft_letter(app: Application, decision: str, reasons: list[str]) -> str:
    return await letter_with_llm(app, decision, reasons)
