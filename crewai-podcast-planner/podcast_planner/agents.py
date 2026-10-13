from crewai import Agent

MODEL = "gpt-4o-mini"


def build_agents() -> tuple[Agent, Agent, Agent]:
    researcher = Agent(
        role="Topic Researcher",
        goal="Pull the facts, people, and gaps for an episode out of raw show notes.",
        backstory="A fact-checker who only states what the notes support, with the number attached.",
        llm=MODEL,
    )
    outliner = Agent(
        role="Outline Writer",
        goal="Shape research into a timed episode outline that holds listeners past minute 22.",
        backstory="A veteran audio producer who thinks in segments, cold opens, and pacing.",
        llm=MODEL,
    )
    editor = Agent(
        role="Show-Notes Editor",
        goal="Write publishable show notes and a punchy episode description from the outline.",
        backstory="A copy editor who cuts every filler word and never invents a claim.",
        llm=MODEL,
    )
    return researcher, outliner, editor
