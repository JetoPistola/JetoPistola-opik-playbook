import os
import time

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from smolagents import ChatMessage, MessageRole, Model

from conftest import RecordingExporter


def _exporter(main):
    return main.provider._active_span_processor._span_processors[0].span_exporter


def _headers(main):
    """The OTLP header string main.py hands to the exporter, as a dict."""
    return dict(kv.split("=", 1) for kv in os.environ["OTEL_EXPORTER_OTLP_HEADERS"].split(","))


def test_local_opik_exporter_config(load_main):
    main = load_main()
    assert _exporter(main)._endpoint == "http://localhost:5173/api/v1/private/otel/v1/traces"
    headers = _headers(main)
    assert headers == {"Comet-Workspace": "default", "projectName": "smolagents-weather-station-analyst"}
    assert "Authorization" not in headers  # local Opik needs no key


def test_cloud_config_adds_authorization(load_main):
    main = load_main(OPIK_API_KEY="k-123", OPIK_WORKSPACE="acme", OPIK_OTEL_ENDPOINT="https://example.test/otel")
    assert _exporter(main)._endpoint == "https://example.test/otel/v1/traces"
    headers = _headers(main)
    assert headers["Authorization"] == "k-123"
    assert headers["Comet-Workspace"] == "acme"
    assert headers["projectName"] == main.PROJECT


class StubModel(Model):
    """Returns one scripted reply: a code block that computes with pandas and calls final_answer."""

    def generate(self, messages, **kwargs):
        reply = (
            "Thought: load the file.\n<code>\nimport pandas as pd\n"
            "df = pd.read_csv(r'%s')\nprint(len(df))\nfinal_answer(int(len(df)))\n</code>"
        )
        return ChatMessage(role=MessageRole.ASSISTANT, content=reply % self.csv)


def test_agent_run_with_instrumentation_active_emits_execution_logs(load_main):
    main = load_main()
    model = StubModel(model_id="stub")
    model.csv = str(main.CSV)
    main.agent.model = model
    assert main.agent.run(main.BRIEFING + "\n\nQuestion: how many rows?") == 337  # the app still works traced
    main.provider.force_flush()
    spans = {s.name: s for s in _exporter(main).exported}
    assert spans["CodeAgent.run"].attributes["output.value"] == "337"
    step = next(s for n, s in spans.items() if n.startswith("Step"))
    assert "Execution logs:\n337" in step.attributes["output.value"]  # execution log is on the Step span


def test_batch_processor_holds_spans_until_flush():
    """Why main() flushes: the batch processor queues spans and exports on a timer (5s by default)."""
    exporter = RecordingExporter()
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    with provider.get_tracer("t").start_as_current_span("s"):
        pass
    time.sleep(0.2)
    assert exporter.exported == []  # still queued; a process exiting here would lose it
    provider.force_flush()
    assert [s.name for s in exporter.exported] == ["s"]
    provider.shutdown()
