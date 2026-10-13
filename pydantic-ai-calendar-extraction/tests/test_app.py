import pytest
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart

from calendar_extraction import tracing
from calendar_extraction.agent import agent, extract_event
from calendar_extraction.cases import CASES, GLOBAL_ASSERTIONS
from calendar_extraction.models import CalendarEvent


def fake_model(args: dict) -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(tool, args)])

    return FunctionModel(respond)


def test_event_defaults_are_empty():
    ev = CalendarEvent(title="Lunch")
    assert ev.date is None and ev.end_time is None and ev.attendees == []


def test_cases_keep_expected_values_out_of_item_data():
    assert len(CASES) == 7 and GLOBAL_ASSERTIONS
    for case in CASES:
        assert list(case["data"]) == ["message"]
        assert case["assertions"]


def test_extract_event_with_tracking_disabled():
    # @opik.track is a no-op here (OPIK_TRACK_DISABLE=true); the function behaves normally.
    with agent.override(model=fake_model({"title": "Sync", "date": "2026-03-05", "attendees": ["Ines"]})):
        out = extract_event(CASES[0]["data"]["message"])
    assert out["title"] == "Sync" and out["date"] == "2026-03-05"
    assert out["end_time"] is None and out["attendees"] == ["Ines"]


def test_extract_event_rejects_invalid_output():
    with agent.override(model=fake_model({"date": "2026-03-05"})):  # title missing
        with pytest.raises(Exception):
            extract_event("x")


def test_tracing_setup_builds_opik_otlp_config(monkeypatch):
    import logfire

    monkeypatch.setattr(logfire, "configure", lambda **kw: None)
    monkeypatch.setattr(logfire, "instrument_pydantic_ai", lambda: None)
    for k in ("OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_HEADERS", "OPIK_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OPIK_URL_OVERRIDE", "http://opik.test/api/")
    monkeypatch.setenv("OPIK_WORKSPACE", "ws1")
    tracing.setup()
    import os

    assert os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://opik.test/api/v1/private/otel"
    assert os.environ["OTEL_EXPORTER_OTLP_HEADERS"] == (
        "Comet-Workspace=ws1,projectName=pydantic-ai-calendar-extraction"
    )
