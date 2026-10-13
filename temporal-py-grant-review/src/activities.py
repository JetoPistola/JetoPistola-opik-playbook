"""Activities: the only place that talks to Opik and OpenAI.

Each activity receives the client's distributed-trace headers and hands them to
`@opik.track` through the `opik_distributed_trace_headers` keyword, so the span
becomes a child of the span that started the workflow in another process.
"""

from __future__ import annotations

import json

import opik
from openai import AsyncOpenAI
from opik.integrations.openai import track_openai
from temporalio import activity

from shared import BUDGET_LEFT_USD, ELIGIBLE_ZIPS, MAX_GRANT_USD, MODEL

# track_openai wraps the client: each completion becomes an llm span with token usage and cost,
# nested under the activity's span. project_name=None leaves the project to OPIK_PROJECT_NAME.
_client = track_openai(AsyncOpenAI(), project_name=None)


@activity.defn
async def check_eligibility(application: dict, trace_headers: dict[str, str]) -> dict:
    # Passing the client's headers makes this span a child of the client's root span,
    # so it lands in the same trace instead of starting a new one in the worker.
    return await _check_eligibility(application, opik_distributed_trace_headers=trace_headers)


# @opik.track opens a "tool" span named check_eligibility.
@opik.track(name="check_eligibility", type="tool")
async def _check_eligibility(application: dict) -> dict:
    problems = []
    if application["zip"] not in ELIGIBLE_ZIPS:
        problems.append(f"ZIP {application['zip']} is outside the fund's service area")
    if application["requested_usd"] > MAX_GRANT_USD:
        problems.append(f"request exceeds the ${MAX_GRANT_USD} cap")
    return {"eligible": not problems, "problems": problems}


@activity.defn
async def score_application(application: dict, trace_headers: dict[str, str]) -> dict:
    return await _score_application(application, opik_distributed_trace_headers=trace_headers)


# A "general" span; the OpenAI call inside nests under it as an llm span.
@opik.track(name="score_application", type="general")
async def _score_application(application: dict) -> dict:
    response = await _client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You review community grant applications for a neighborhood fund. "
                    "Score 1-10 on clarity, community impact and budget realism combined. "
                    'Reply as JSON: {"score": int, "rationale": "one sentence"}.'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Applicant: {application['applicant']}\n"
                    f"Category: {application['category']}\n"
                    f"Requested: ${application['requested_usd']}\n"
                    f"Summary: {application['summary']}"
                ),
            },
        ],
    )
    return json.loads(response.choices[0].message.content)


@activity.defn
async def check_budget_remaining(application: dict, trace_headers: dict[str, str]) -> dict:
    attempt = activity.info().attempt
    # Same header hand-off as above, so every retry attempt joins the client's trace.
    return await _check_budget(
        application, attempt, opik_distributed_trace_headers=trace_headers
    )


# Each Temporal attempt is its own span; the raised ConnectionError is recorded as
# error info on the failed attempt's span, and the retry shows up as a second, clean span.
@opik.track(name="check_budget_remaining", type="tool")
async def _check_budget(application: dict, attempt: int) -> dict:
    # The ledger service is "down" on every first attempt; Temporal retries it.
    if attempt == 1:
        raise ConnectionError("ledger service unavailable (HTTP 503)")
    left = BUDGET_LEFT_USD[application["category"]]
    return {
        "attempt": attempt,
        "category_budget_left_usd": left,
        "fits": application["requested_usd"] <= left,
    }
