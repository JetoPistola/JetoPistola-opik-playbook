"""The extraction agent and its traced entry point."""

from typing import Any

import opik
from pydantic_ai import Agent

from . import PROJECT_NAME
from .models import CalendarEvent

MODEL = "openai:gpt-4o-mini"

# Messages are dated relative to this fictional "today" (a Monday).
TODAY = "2026-03-02"

agent = Agent(
    MODEL,
    output_type=CalendarEvent,
    system_prompt=(
        "You turn messy emails, chat messages and voicemail notes into one "
        f"calendar event. Today is Monday {TODAY}; resolve relative days from it. "
        "Fill in a field only if the message supports it. If a time, location "
        "or attendee list is not given, leave it null/empty. Never guess a "
        "duration or end time."
    ),
)


# opik.track makes each call one trace named "extract_event" (input = message, output = typed record);
# the Pydantic AI spans from the OTel bridge nest under it. Without it they arrive as separate traces.
@opik.track(project_name=PROJECT_NAME, name="extract_event")
def extract_event(message: str) -> dict[str, Any]:
    """One traced extraction: messy message in, typed event out."""
    return agent.run_sync(message).output.model_dump()
