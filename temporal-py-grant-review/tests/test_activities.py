import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from temporalio.testing import ActivityEnvironment

import activities
from shared import load_applications

APPS = {a["id"]: a for a in load_applications()}


def run_activity(fn, *args, attempt=1):
    env = ActivityEnvironment()
    env.info = replace(env.info, attempt=attempt)
    return asyncio.run(env.run(fn, *args))


def test_eligible_application_passes():
    result = run_activity(activities.check_eligibility, APPS["APP-201"], {})
    assert result == {"eligible": True, "problems": []}


def test_out_of_area_zip_is_rejected():
    result = run_activity(activities.check_eligibility, APPS["APP-203"], {})
    assert result["eligible"] is False
    assert "94901" in result["problems"][0]


def test_request_over_cap_is_rejected():
    big = {**APPS["APP-201"], "requested_usd": 9000}
    result = run_activity(activities.check_eligibility, big, {})
    assert result["eligible"] is False
    assert "cap" in result["problems"][0]


def test_budget_check_fails_on_first_attempt():
    with pytest.raises(ConnectionError, match="503"):
        run_activity(activities.check_budget_remaining, APPS["APP-201"], {}, attempt=1)


def test_budget_check_succeeds_on_retry():
    ok = run_activity(activities.check_budget_remaining, APPS["APP-201"], {}, attempt=2)
    assert ok == {"attempt": 2, "category_budget_left_usd": 6000, "fits": True}
    short = run_activity(activities.check_budget_remaining, APPS["APP-202"], {}, attempt=2)
    assert short["fits"] is False  # youth: $4,200 requested, $3,000 left


def test_scoring_uses_stubbed_openai_client(monkeypatch):
    seen = {}

    async def create(**kwargs):
        seen.update(kwargs)
        content = json.dumps({"score": 8, "rationale": "Clear and realistic."})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    stub = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(activities, "_client", stub)

    # The real @opik.track-decorated function runs here with tracking disabled.
    result = run_activity(activities.score_application, APPS["APP-201"], {})
    assert result == {"score": 8, "rationale": "Clear and realistic."}
    assert seen["model"] == "gpt-4o-mini"
    assert "Linden Street Tool Library" in seen["messages"][1]["content"]
