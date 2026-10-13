"""The typed record the agent must produce."""

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    title: str = Field(description="Short event title")
    date: str | None = Field(None, description="Calendar date as YYYY-MM-DD, only if determinable")
    start_time: str | None = Field(None, description="Start time, 24h HH:MM, only if stated")
    end_time: str | None = Field(None, description="End time, 24h HH:MM, only if stated")
    timezone: str | None = Field(None, description="Timezone as written in the text, if any")
    location: str | None = Field(None, description="Room, address or video link, only if stated")
    attendees: list[str] = Field(default_factory=list, description="Names of people named as attending")
