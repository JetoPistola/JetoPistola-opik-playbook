"""Offline test setup: no provider key, no repo-root .env, and no real OTLP export."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from opentelemetry.exporter.otlp.proto.http import trace_exporter  # noqa: E402
from opentelemetry.sdk.trace.export import SpanExportResult  # noqa: E402


class RecordingExporter(trace_exporter.OTLPSpanExporter):
    """The real exporter (it reads endpoint and headers from the env), but export() keeps spans in memory."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.exported = []

    def export(self, spans):
        self.exported.extend(spans)
        return SpanExportResult.SUCCESS


@pytest.fixture
def load_main(monkeypatch):
    """Import a fresh `main` with a clean Opik/OpenAI environment; returns a loader taking env overrides."""
    import dotenv
    from openinference.instrumentation.smolagents import SmolagentsInstrumentor

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)  # ignore any real .env
    monkeypatch.setattr(trace_exporter, "OTLPSpanExporter", RecordingExporter)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")  # the OpenAI client wants one at construction
    for var in ("OPIK_API_KEY", "OPIK_OTEL_ENDPOINT", "OPIK_WORKSPACE", "OPENAI_BASE_URL"):
        monkeypatch.delenv(var, raising=False)

    def loader(**env):
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        SmolagentsInstrumentor().uninstrument()  # each load instruments its own tracer provider
        sys.modules.pop("main", None)
        return importlib.import_module("main")

    yield loader
    SmolagentsInstrumentor().uninstrument()
    sys.modules.pop("main", None)
