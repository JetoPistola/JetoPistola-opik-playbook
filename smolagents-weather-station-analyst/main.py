"""Weather-station analyst: a smolagents CodeAgent whose pandas code shows up in Opik spans."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT = "smolagents-weather-station-analyst"
CSV = Path(__file__).parent / "data" / "readings.csv"

for p in Path(__file__).resolve().parents:  # walk up to a repo-root .env
    if (p / ".env").exists():
        load_dotenv(p / ".env")
        break
os.environ.pop("OPENAI_BASE_URL", None)

# Opik ingests OpenTelemetry at /api/v1/private/otel: no Opik SDK needed, spans arrive over OTLP/HTTP.
endpoint = os.getenv("OPIK_OTEL_ENDPOINT", "http://localhost:5173/api/v1/private/otel")
# Comet-Workspace picks the workspace, projectName the Opik project the traces land in.
headers = f"Comet-Workspace={os.getenv('OPIK_WORKSPACE', 'default')},projectName={PROJECT}"
if os.getenv("OPIK_API_KEY"):  # Authorization is only needed for Opik Cloud; local Opik takes none
    headers = f"Authorization={os.environ['OPIK_API_KEY']}," + headers
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = endpoint
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = headers

from openinference.instrumentation.smolagents import SmolagentsInstrumentor  # noqa: E402
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: E402

# The batch processor ships spans in the background, so they must be flushed before exit (see main()).
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
# The instrumentor hooks CodeAgent.run, each step and each model call: the generated pandas code lands in
# the generate spans' output and the execution logs in the Step spans' output, with token usage on LLM spans.
SmolagentsInstrumentor().instrument(tracer_provider=provider)

from smolagents import CodeAgent, OpenAIServerModel  # noqa: E402

agent = CodeAgent(
    tools=[],
    model=OpenAIServerModel(model_id="gpt-4o-mini"),
    additional_authorized_imports=["pandas"],
    max_steps=6,
)

BRIEFING = f"""You analyse readings from the Larkspur Hill community weather station.
Hourly data, 2-15 March 2026, is in the CSV at: {CSV}
Columns: timestamp (YYYY-MM-DD HH:MM), temp_c, humidity_pct, wind_kmh, rain_mm (rain in that hour).
Load it with pandas, inspect it, and answer with concrete numbers. If something in the data
looks wrong or untrustworthy, say so plainly in your answer. Reply in two or three sentences."""

QUESTIONS = [
    "How much rain fell in total over the fortnight, and which day was the wettest?",
    "What was the average wind speed per day, and which day was the calmest?",
    "What were the hottest and coldest readings of the fortnight, and when did they happen?",
]


def main() -> None:
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n=== Question {i}: {q}")
        print(f"Answer {i}:", agent.run(BRIEFING + "\n\nQuestion: " + q))
    # Without force_flush/shutdown the BatchSpanProcessor queue is dropped at exit and the project stays empty.
    provider.force_flush()
    provider.shutdown()
    print(f"\nDone. Open the '{PROJECT}' project in Opik.")


if __name__ == "__main__":
    main()
