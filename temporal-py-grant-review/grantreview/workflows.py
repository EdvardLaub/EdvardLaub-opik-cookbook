"""The durable review workflow. Deterministic code only: all I/O lives in activities."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from grantreview.activities import check_eligibility, draft_letter, score_application
    from grantreview.data import PASS_MARK
    from grantreview.models import Application, Review

RETRY = RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=4)
TIMEOUT = timedelta(seconds=60)


def decide(total: int) -> str:
    return "approved" if total >= PASS_MARK else "declined"


@workflow.defn
class GrantReviewWorkflow:
    @workflow.run
    async def run(self, app: Application) -> Review:
        eligibility = await workflow.execute_activity(
            check_eligibility, app, start_to_close_timeout=TIMEOUT, retry_policy=RETRY
        )
        if not eligibility.eligible:
            letter = await workflow.execute_activity(
                draft_letter, args=[app, "declined", eligibility.reasons],
                start_to_close_timeout=TIMEOUT, retry_policy=RETRY,
            )
            return Review(app.id, "declined", letter, eligibility_reasons=eligibility.reasons)

        score = await workflow.execute_activity(
            score_application, app, start_to_close_timeout=TIMEOUT, retry_policy=RETRY
        )
        decision = decide(score.total)
        letter = await workflow.execute_activity(
            draft_letter, args=[app, decision, [score.rationale]],
            start_to_close_timeout=TIMEOUT, retry_policy=RETRY,
        )
        return Review(app.id, decision, letter, score=score)
