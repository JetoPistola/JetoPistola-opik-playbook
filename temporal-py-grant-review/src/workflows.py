from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import check_budget_remaining, check_eligibility, score_application
    from shared import ReviewInput, ReviewResult

OPTS = dict(
    start_to_close_timeout=timedelta(seconds=60),
    retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=4),
)


@workflow.defn
class GrantReviewWorkflow:
    @workflow.run
    async def run(self, inp: ReviewInput) -> ReviewResult:
        app = inp.application

        elig = await workflow.execute_activity(check_eligibility, app, **OPTS)
        if not elig["eligible"]:
            return ReviewResult(app["id"], "rejected", "; ".join(elig["problems"]))

        scored = await workflow.execute_activity(score_application, app, **OPTS)
        budget = await workflow.execute_activity(check_budget_remaining, app, **OPTS)

        if not budget["fits"]:
            return ReviewResult(
                app["id"], "waitlisted",
                f"only ${budget['category_budget_left_usd']} left in {app['category']}",
                scored["score"], budget["attempt"],
            )
        decision = "approved" if scored["score"] >= 7 else "needs-revision"
        return ReviewResult(app["id"], decision, scored["rationale"], scored["score"], budget["attempt"])
