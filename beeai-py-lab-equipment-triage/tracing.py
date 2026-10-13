"""Send BeeAI's OpenInference spans to Opik over OTLP. The only file that knows about tracing."""
import os

from openinference.instrumentation.beeai import BeeAIInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult

PROJECT = "beeai-py-lab-equipment-triage"


# Exporter subclass = the one filter between BeeAI and Opik. Without it every streamed chunk
# arrives in Opik as its own `new_token` span, burying the LLM and tool spans.
class DropTokenSpans(OTLPSpanExporter):
    """BeeAI streams the answer, and the instrumentor emits one `new_token` span per chunk
    (hundreds per trace). Drop those leaf spans so the tree shows iterations, LLM calls and tools."""

    def export(self, spans):
        kept = [s for s in spans if s.name != "new_token"]
        return super().export(kept) if kept else SpanExportResult.SUCCESS


def setup_tracing() -> TracerProvider:
    # Opik's OTLP endpoint; local self-hosted by default, Opik Cloud via OPIK_OTLP_ENDPOINT.
    endpoint = os.getenv("OPIK_OTLP_ENDPOINT", "http://localhost:5173/api/v1/private/otel")
    # Comet-Workspace picks the workspace; projectName picks the Opik project the traces land in
    # (without it they go to "Default Project").
    headers = {"Comet-Workspace": os.getenv("OPIK_WORKSPACE", "default"), "projectName": PROJECT}
    # Authorization is sent only for Opik Cloud; local Opik needs no auth header.
    if os.getenv("OPIK_API_KEY"):
        headers["Authorization"] = os.environ["OPIK_API_KEY"]
    exporter = DropTokenSpans(endpoint=endpoint.rstrip("/") + "/v1/traces", headers=headers)
    provider = TracerProvider(resource=Resource.create({"service.name": PROJECT}))
    # Batch export over OTLP/HTTP: spans reach Opik only after a flush (main.py flushes at exit).
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    # Instrumentor turns every ReAct run into an OpenInference trace: `ReAct` root, `llm` spans
    # with usage, tool spans, and `error`/`retry` spans. Must run before agents are created.
    BeeAIInstrumentor().instrument(tracer_provider=provider)
    return provider
