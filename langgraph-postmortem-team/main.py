"""Incident post-mortem team: lead -> investigators (loop) -> writer.

The lead reads the incident brief and decides which evidence files to examine.
An investigator agent loops over that work list (bounded at MAX_INVESTIGATIONS),
reading one evidence file per pass. The writer drafts a blameless post-mortem.
"""

import pathlib

import dotenv

# Walk up from this folder to find a .env (own folder first, then repo root).
for parent in pathlib.Path(__file__).resolve().parents:
    if (parent / ".env").exists():
        dotenv.load_dotenv(parent / ".env")
        break

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

DATA_DIR = pathlib.Path(__file__).parent / "data"
MAX_INVESTIGATIONS = 4
EVIDENCE = {p.name: p.read_text() for p in sorted(DATA_DIR.glob("*.md"))}

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class Finding(TypedDict):
    source: str
    focus: str
    notes: str


class TeamState(TypedDict):
    incident: str
    tasks: list[dict]
    findings: list[Finding]
    postmortem: str


# --- Agent 1: the lead decides which evidence to examine ----------------------

class Task(BaseModel):
    source: str = Field(description="Exact evidence file name to examine")
    focus: str = Field(description="What the investigator should look for in it")


class InvestigationPlan(BaseModel):
    tasks: list[Task] = Field(description="One task per evidence file, at most 4")


def lead(state: TeamState) -> dict:
    """Choose evidence files and a focus for each."""
    plan = llm.with_structured_output(InvestigationPlan).invoke([
        ("system",
         "You lead an incident review. Available evidence files: "
         + ", ".join(EVIDENCE)
         + ". Pick the files worth examining (max 4, each file at most once) "
         "and give each a specific focus: the timeline, the trigger, the "
         "detection gaps, and how people responded."),
        ("user", state["incident"]),
    ])
    tasks = [t.model_dump() for t in plan.tasks if t.source in EVIDENCE]
    return {"tasks": tasks[:MAX_INVESTIGATIONS], "findings": []}


# --- Agent 2: the investigator reads one evidence file per pass ---------------

def investigator(state: TeamState) -> dict:
    """Examine the next open task's evidence file."""
    task = state["tasks"][len(state["findings"])]
    reply = llm.invoke([
        ("system",
         "You are an incident investigator. Read the evidence and report "
         "concrete facts relevant to the focus: timestamps, numbers, config "
         "values. Describe systems and processes, not people's faults. "
         "Bullet points, under 150 words.\n\n"
         f"[{task['source']}]\n{EVIDENCE[task['source']]}"),
        ("user", task["focus"]),
    ])
    finding: Finding = {
        "source": task["source"], "focus": task["focus"], "notes": reply.content,
    }
    return {"findings": state["findings"] + [finding]}


def route(state: TeamState) -> str:
    """Loop until every task has a finding (the lead capped the list)."""
    return "investigator" if len(state["findings"]) < len(state["tasks"]) else "writer"


# --- Agent 3: the writer drafts the blameless post-mortem ---------------------

def writer(state: TeamState) -> dict:
    notes = "\n\n".join(
        f"### {f['focus']} ({f['source']})\n{f['notes']}" for f in state["findings"]
    )
    reply = llm.invoke([
        ("system",
         "You write blameless post-mortems in markdown: Summary, Impact, "
         "Timeline, Root cause, Contributing factors, What went well, Action "
         "items. Blame systems and process, never individuals. Use only the "
         "notes; keep times and numbers exact. Under 450 words.\n\n" + notes),
        ("user", state["incident"]),
    ])
    return {"postmortem": reply.content}


graph = StateGraph(TeamState)
graph.add_node("lead", lead)
graph.add_node("investigator", investigator)
graph.add_node("writer", writer)
graph.add_edge(START, "lead")
graph.add_edge("lead", "investigator")
graph.add_conditional_edges(
    "investigator", route, {"investigator": "investigator", "writer": "writer"}
)
graph.add_edge("writer", END)

app = graph.compile()


def main() -> None:
    incident = (
        "INC-2291: on 2026-03-12 around 14:07 UTC, card checkout at Brightwharf "
        "Ledger started returning 503s for roughly 30 minutes. Write the "
        "blameless post-mortem."
    )
    print(f"Incident: {incident}\n")
    result = app.invoke({"incident": incident})
    print("Lead's work list:")
    for t in result["tasks"]:
        print(f"  - {t['source']}: {t['focus']}")
    print(f"\n{len(result['findings'])} investigations done. Post-mortem:\n")
    print(result["postmortem"])


if __name__ == "__main__":
    main()
