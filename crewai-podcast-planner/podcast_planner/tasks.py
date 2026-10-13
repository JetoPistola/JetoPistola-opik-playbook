from crewai import Agent, Task


def build_tasks(researcher: Agent, outliner: Agent, editor: Agent) -> list[Task]:
    research = Task(
        name="Research the topic",
        description=(
            "Episode brief: {brief}\n\nUsing ONLY the notes below, list the facts, "
            "guests, listener-data insights, and known gaps relevant to the brief. "
            "Do not invent anything.\n\nNOTES:\n\n{notes}"
        ),
        expected_output="6-8 bullets, each citing a number or name from the notes, plus a 'Gaps' line.",
        agent=researcher,
    )
    outline = Task(
        name="Draft the outline",
        description=(
            "Write a timed outline (about 30 minutes) for the episode brief: {brief}. "
            "Use the research. Respect the listener-data insights about drop-off and openings."
        ),
        expected_output="5-6 segments, each with a start minute, a title, and one line of content.",
        agent=outliner,
        context=[research],
    )
    notes = Task(
        name="Write the show notes",
        description=(
            "Produce the final package for the episode brief: {brief}, from the research and outline."
        ),
        expected_output=(
            "A title, a two-sentence episode description, a 'Guests' list, and three "
            "bullet 'In this episode' highlights. Under 200 words."
        ),
        agent=editor,
        context=[research, outline],
    )
    return [research, outline, notes]
