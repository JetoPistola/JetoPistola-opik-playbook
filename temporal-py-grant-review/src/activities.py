"""Activities: eligibility check, OpenAI scoring and a flaky budget lookup."""

from __future__ import annotations

import json

from openai import AsyncOpenAI
from temporalio import activity

from shared import BUDGET_LEFT_USD, ELIGIBLE_ZIPS, MAX_GRANT_USD, MODEL

_client = AsyncOpenAI()


@activity.defn
async def check_eligibility(application: dict) -> dict:
    problems = []
    if application["zip"] not in ELIGIBLE_ZIPS:
        problems.append(f"ZIP {application['zip']} is outside the fund's service area")
    if application["requested_usd"] > MAX_GRANT_USD:
        problems.append(f"request exceeds the ${MAX_GRANT_USD} cap")
    return {"eligible": not problems, "problems": problems}


@activity.defn
async def score_application(application: dict) -> dict:
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
async def check_budget_remaining(application: dict) -> dict:
    attempt = activity.info().attempt
    # The ledger service is "down" on every first attempt; Temporal retries it.
    if attempt == 1:
        raise ConnectionError("ledger service unavailable (HTTP 503)")
    left = BUDGET_LEFT_USD[application["category"]]
    return {
        "attempt": attempt,
        "category_budget_left_usd": left,
        "fits": application["requested_usd"] <= left,
    }
