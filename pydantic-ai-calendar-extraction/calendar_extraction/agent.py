"""The extraction agent."""

from typing import Any

from pydantic_ai import Agent

from .models import CalendarEvent

MODEL = "openai:gpt-4o-mini"

# Messages are dated relative to this fictional "today" (a Monday).
TODAY = "2026-03-02"

agent = Agent(
    MODEL,
    output_type=CalendarEvent,
    # Resolve the provider lazily so importing the module (and tests) needs no API key.
    defer_model_check=True,
    system_prompt=(
        "You turn messy emails, chat messages and voicemail notes into one "
        f"calendar event. Today is Monday {TODAY}; resolve relative days from it. "
        "Fill in a field only if the message supports it. If a time, location "
        "or attendee list is not given, leave it null/empty. Never guess a "
        "duration or end time."
    ),
)


def extract_event(message: str) -> dict[str, Any]:
    """One extraction: messy message in, typed event out."""
    return agent.run_sync(message).output.model_dump()
