"""Ask one question; return the answer plus the excerpts retrieval fetched."""

from dataclasses import dataclass

SYSTEM_HINT = (
    "You answer student questions about course syllabi at Larkspur Community College. "
    "Answer only from the retrieved syllabus excerpts. Name the course, and quote the "
    "governing figure exactly (percentages, days, times, rooms). If the excerpts do not "
    "cover the question, say so."
)

DEMO_QUESTIONS = [
    "In BIO 101, how much is a lab report that is two days late penalized?",
    "What are the grading weights in MAT 120?",
    "When and where are Prof. Brightwater's office hours?",
    "What do I need to have completed before taking BIO 101?",
]


@dataclass
class Answer:
    question: str
    text: str
    excerpts: list[str]


def ask(query_engine, question: str) -> Answer:
    response = query_engine.query(f"{SYSTEM_HINT}\n\nQuestion: {question}")
    return Answer(question, str(response), [n.text for n in response.source_nodes])
