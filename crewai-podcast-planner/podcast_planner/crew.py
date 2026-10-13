from pathlib import Path

from crewai import Crew, Process

from .agents import build_agents
from .tasks import build_tasks

DEFAULT_NOTES = Path(__file__).resolve().parent.parent / "data" / "episode_notes.md"


def build_crew() -> Crew:
    agents = build_agents()
    crew = Crew(
        agents=list(agents),
        tasks=build_tasks(*agents),
        process=Process.sequential,
        verbose=False,
    )
    return crew


def plan_episode(brief: str, notes_path: Path = DEFAULT_NOTES) -> str:
    crew = build_crew()
    result = crew.kickoff(inputs={"brief": brief, "notes": notes_path.read_text()})
    return str(result)
