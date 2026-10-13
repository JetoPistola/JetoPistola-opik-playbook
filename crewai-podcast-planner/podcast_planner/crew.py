from pathlib import Path

from crewai import Crew, Process
from opik.integrations.crewai import track_crewai

from .agents import build_agents
from .tasks import build_tasks

DEFAULT_NOTES = Path(__file__).resolve().parent.parent / "data" / "episode_notes.md"

PROJECT_NAME = "crewai-podcast-planner"


def build_crew() -> Crew:
    agents = build_agents()
    crew = Crew(
        agents=list(agents),
        tasks=build_tasks(*agents),
        process=Process.sequential,
        verbose=False,
    )
    # track_crewai instruments the crew: each kickoff becomes ONE trace in PROJECT_NAME, with a
    # "Task: ..." span per task and an llm span (tokens + cost) for each agent's model call.
    # Without it the crew runs but nothing is recorded.
    track_crewai(project_name=PROJECT_NAME, crew=crew)
    return crew


def plan_episode(brief: str, notes_path: Path = DEFAULT_NOTES) -> str:
    crew = build_crew()
    result = crew.kickoff(inputs={"brief": brief, "notes": notes_path.read_text()})
    return str(result)
