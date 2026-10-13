"""Import main.py offline.

main.py runs the whole flow at import time (upload, optimize, save). These fixtures
swap the Opik client and the optimizer for fakes, so importing it needs no Opik,
no provider key and no runtime change to main.py.
"""

import contextlib
import importlib.util
import io
import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

APP_DIR = pathlib.Path(__file__).resolve().parent.parent


class FakeOptimizer:
    """Stands in for MetaPromptOptimizer: records its arguments, returns a canned winner."""

    last = None

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.call_kwargs = None
        FakeOptimizer.last = self

    def optimize_prompt(self, **kwargs):
        from opik_optimizer import ChatPrompt

        self.call_kwargs = kwargs
        winner = ChatPrompt(system="Reply with the label only.", user="{review}", model="openai/gpt-4o-mini")
        return SimpleNamespace(
            initial_score=0.75,
            score=1.0,
            details={"trials_completed": 4},
            llm_cost_total=None,
            optimization_id="opt-123",
            prompt=winner,
        )


@pytest.fixture(scope="session")
def app():
    """Returns SimpleNamespace(module=main, client=fake client, optimizer=FakeOptimizer, stdout=str)."""
    import dotenv
    import opik
    import opik_optimizer

    client = MagicMock(name="opik.Opik()")
    client.rest_client.optimizations.get_optimization_by_id.return_value = SimpleNamespace(project_id="proj-456")
    client.config.url_override = "http://localhost:5173/api"
    client.config.workspace = "default"

    mp = pytest.MonkeyPatch()
    mp.setattr(opik, "Opik", lambda *a, **k: client)
    mp.setattr(opik, "flush_tracker", lambda *a, **k: None)
    mp.setattr(opik_optimizer, "MetaPromptOptimizer", FakeOptimizer)
    mp.setattr(dotenv, "load_dotenv", lambda *a, **k: False)  # never read a real .env in tests
    mp.setenv("OPIK_PROJECT_NAME", "placeholder")  # main.py overwrites it; this restores it afterwards

    buf = io.StringIO()
    spec = importlib.util.spec_from_file_location("review_intents_main", APP_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    try:
        with contextlib.redirect_stdout(buf):
            spec.loader.exec_module(module)
    finally:
        mp.undo()
    return SimpleNamespace(module=module, client=client, optimizer=FakeOptimizer, stdout=buf.getvalue())
