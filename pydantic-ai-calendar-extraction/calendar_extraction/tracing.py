"""Send Pydantic AI's OpenTelemetry spans (via logfire) to Opik.

Must be imported and `setup()` called BEFORE the agent module is imported.
No keys are written anywhere: a local Opik needs none, and a hosted one can
supply OPIK_API_KEY from the environment.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from . import PROJECT_NAME


def setup() -> None:
    # Walk up from the package to find a .env (repo root or this folder).
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            load_dotenv(parent / ".env")
            break

    os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
    base = os.environ.get("OPIK_URL_OVERRIDE", "http://localhost:5173/api/").rstrip("/")
    workspace = os.environ.get("OPIK_WORKSPACE", "default")
    # Comet-Workspace and projectName route the OTLP spans to this workspace and project;
    # without them nothing shows up (or it lands in the Default Project).
    headers = f"Comet-Workspace={workspace},projectName={PROJECT_NAME}"
    if os.environ.get("OPIK_API_KEY"):
        headers = f"Authorization={os.environ['OPIK_API_KEY']},{headers}"
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", f"{base}/v1/private/otel")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_HEADERS", headers)
    os.environ["OTEL_METRICS_EXPORTER"] = "none"

    import logfire
    from opik.integrations.otel import OpikSpanProcessor

    # OpikSpanProcessor forwards every OTel span to Opik (nesting them under the active @track trace);
    # instrument_pydantic_ai emits "invoke_agent" and "chat <model>" spans with token usage.
    logfire.configure(send_to_logfire=False, additional_span_processors=[OpikSpanProcessor()])
    logfire.instrument_pydantic_ai()
