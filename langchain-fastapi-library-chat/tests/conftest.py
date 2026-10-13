"""Offline test setup: no provider key, no Opik. The chat model is swapped for a stub."""
import os

# Must be set before library_chat.server is imported: ChatOpenAI wants a key at construction,
# and the tests never call it. Tracking is off so OpikTracer / @opik.track send nothing.
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ["OPIK_TRACK_DISABLE"] = "true"

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from library_chat import server


@pytest.fixture
def prompts():
    """Replace the ChatOpenAI step (index 1 of the chain's middle steps) with a recording stub."""
    seen: list[str] = []

    def fake_model(prompt_value):
        text = "\n".join(m.content for m in prompt_value.to_messages())
        seen.append(text)
        return AIMessage(f"stub reply #{len(seen)}")

    real_model = server.chain.middle[1]
    server.chain.middle[1] = RunnableLambda(fake_model)
    server.HISTORY.clear()
    yield seen
    server.chain.middle[1] = real_model
    server.HISTORY.clear()


@pytest.fixture
def client(prompts):
    return TestClient(server.app)
