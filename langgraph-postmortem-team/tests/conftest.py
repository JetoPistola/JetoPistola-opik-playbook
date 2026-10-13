import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# main.py builds ChatOpenAI at import time, which wants a key to exist.
# The value is a dummy: the model is replaced by FakeLLM before any call.
os.environ.setdefault("OPENAI_API_KEY", "test-not-a-real-key")
# Tracking off: track_langgraph / OpikTracer stay in the graph but send nothing.
os.environ["OPIK_TRACK_DISABLE"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


class FakeLLM:
    """Stands in for ChatOpenAI: scripted plan for the lead, canned text otherwise."""

    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    def with_structured_output(self, schema):
        return SimpleNamespace(invoke=lambda msgs: self.plan)

    def invoke(self, messages):
        self.calls.append(messages)
        return SimpleNamespace(content=f"notes-{len(self.calls)}")


def make_plan(*sources):
    return main.InvestigationPlan(
        tasks=[main.Task(source=s, focus=f"focus on {s}") for s in sources]
    )


@pytest.fixture
def fake_llm(monkeypatch):
    def install(*sources):
        fake = FakeLLM(make_plan(*sources))
        monkeypatch.setattr(main, "llm", fake)
        return fake

    return install
