"""The client's trace headers travel as a plain dict and reach every tracked activity."""

import asyncio
import json
from dataclasses import asdict

import pytest
from temporalio.testing import ActivityEnvironment

import activities
from shared import ReviewInput, load_applications

ORIGINAL_ELIGIBILITY = activities._check_eligibility
HEADERS = {"opik_trace_id": "trace-123", "opik_parent_span_id": "span-456"}
APP = load_applications()[0]


def test_review_input_headers_survive_json_roundtrip():
    # Temporal serialises workflow input as JSON; headers must stay a plain dict of strings.
    payload = json.loads(json.dumps(asdict(ReviewInput(application=APP, trace_headers=HEADERS))))
    assert payload["trace_headers"] == HEADERS


@pytest.mark.parametrize(
    "activity_fn, tracked_name, extra_args",
    [
        (activities.check_eligibility, "_check_eligibility", ()),
        (activities.score_application, "_score_application", ()),
        (activities.check_budget_remaining, "_check_budget", (1,)),
    ],
)
def test_each_activity_forwards_headers_to_its_tracked_function(
    monkeypatch, activity_fn, tracked_name, extra_args
):
    calls = []

    async def fake(*args, **kwargs):
        calls.append(kwargs)
        return {}

    monkeypatch.setattr(activities, tracked_name, fake)
    asyncio.run(ActivityEnvironment().run(activity_fn, APP, HEADERS))
    assert calls == [{"opik_distributed_trace_headers": HEADERS}]


def test_traced_function_runs_with_tracking_disabled():
    # ORIGINAL_ELIGIBILITY is the real @opik.track wrapper, captured before the autouse
    # fixture swaps it out. With tracking disabled it is a pass-through for plain calls.
    result = asyncio.run(ORIGINAL_ELIGIBILITY(APP))
    assert result["eligible"] is True


def test_disabled_tracking_does_not_swallow_the_headers_keyword():
    # Why the fixture in conftest.py exists: the disabled decorator forwards the keyword
    # to the function body instead of dropping it.
    with pytest.raises(TypeError, match="opik_distributed_trace_headers"):
        asyncio.run(ORIGINAL_ELIGIBILITY(APP, opik_distributed_trace_headers=HEADERS))
