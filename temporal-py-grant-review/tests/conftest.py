"""Offline test setup: no OpenAI key, no Opik, no Temporal server."""

import os
import sys
from pathlib import Path

# Opik tracking off: @opik.track and track_openai become pass-throughs.
os.environ["OPIK_TRACK_DISABLE"] = "true"
# activities.py builds its OpenAI client at import time; a dummy key lets it import.
# Tests replace the client with a stub, so nothing ever calls OpenAI.
os.environ["OPENAI_API_KEY"] = "test-key-not-used"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def untraced_activities(monkeypatch):
    """Swap each @opik.track function for its undecorated body that ignores trace headers.

    With OPIK_TRACK_DISABLE=true the decorator passes keyword arguments straight through,
    so `opik_distributed_trace_headers=` would reach the function body and raise a
    TypeError. The tests call the plain bodies instead; test_headers.py checks the
    header hand-off separately by recording the keyword.
    """
    import activities

    for name in ("_check_eligibility", "_score_application", "_check_budget"):
        body = getattr(activities, name).__wrapped__

        async def call(*args, opik_distributed_trace_headers=None, _body=body, **kwargs):
            return await _body(*args, **kwargs)

        monkeypatch.setattr(activities, name, call)
