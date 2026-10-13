from types import SimpleNamespace

import pytest
from opentelemetry.sdk.trace.export import SpanExportResult

import tracing


@pytest.fixture
def captured(monkeypatch):
    """Build the provider without touching global OTel state or instrumenting BeeAI."""
    seen = {}
    real = tracing.DropTokenSpans

    def spy(**kwargs):
        seen.update(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(tracing, "DropTokenSpans", spy)
    monkeypatch.setattr(tracing.trace, "set_tracer_provider", lambda p: None)
    monkeypatch.setattr(tracing, "BeeAIInstrumentor", lambda: SimpleNamespace(instrument=lambda **kw: None))
    for var in ("OPIK_OTLP_ENDPOINT", "OPIK_WORKSPACE", "OPIK_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    return seen


def test_local_config(captured):
    tracing.setup_tracing()
    assert captured["endpoint"] == "http://localhost:5173/api/v1/private/otel/v1/traces"
    assert captured["headers"] == {"Comet-Workspace": "default", "projectName": "beeai-py-lab-equipment-triage"}
    assert "Authorization" not in captured["headers"]


def test_cloud_config(captured, monkeypatch):
    monkeypatch.setenv("OPIK_OTLP_ENDPOINT", "https://example.test/opik/api/v1/private/otel/")
    monkeypatch.setenv("OPIK_WORKSPACE", "team")
    monkeypatch.setenv("OPIK_API_KEY", "key-123")
    tracing.setup_tracing()
    assert captured["endpoint"] == "https://example.test/opik/api/v1/private/otel/v1/traces"
    assert captured["headers"]["Comet-Workspace"] == "team"
    assert captured["headers"]["Authorization"] == "key-123"


def test_drop_token_spans_filters_new_token(monkeypatch):
    forwarded = []
    monkeypatch.setattr(
        tracing.OTLPSpanExporter, "export", lambda self, spans: forwarded.append([s.name for s in spans]) or SpanExportResult.SUCCESS
    )
    exporter = tracing.DropTokenSpans(endpoint="http://localhost:1/v1/traces")
    fake = [SimpleNamespace(name=n) for n in ("ReAct", "new_token", "OpenAIChatModel", "new_token")]
    assert exporter.export(fake) == SpanExportResult.SUCCESS
    assert forwarded == [["ReAct", "OpenAIChatModel"]]

    # A batch of only token spans is swallowed without calling the network exporter.
    assert exporter.export([SimpleNamespace(name="new_token")]) == SpanExportResult.SUCCESS
    assert len(forwarded) == 1
