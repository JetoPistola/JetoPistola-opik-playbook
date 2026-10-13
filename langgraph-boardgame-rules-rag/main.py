"""Rulebook referee: RAG over fictional board-game rulebooks.

Graph: retrieve (embedding search over rule sections) -> generate (gpt-4o-mini).
"""

import os
import pathlib

import dotenv

# Walk up from this folder to find a .env (repo root or local copy).
for parent in pathlib.Path(__file__).resolve().parents:
    if (parent / ".env").exists():
        dotenv.load_dotenv(parent / ".env")
        break

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

DOCS_DIR = pathlib.Path(__file__).parent / "docs"
TOP_K = int(os.environ.get("TOP_K", "3"))


def load_chunks() -> list[str]:
    """One chunk per '##' rule section, prefixed with the game title."""
    chunks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        title, *sections = path.read_text().split("\n## ")
        game = title.splitlines()[0].lstrip("# ").strip()
        for section in sections:
            chunks.append(f"[{game}]\n## {section.strip()}")
    return chunks


store = InMemoryVectorStore.from_texts(
    load_chunks(), OpenAIEmbeddings(model="text-embedding-3-small")
)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def search_rulebooks(question: str, k: int = TOP_K) -> list[str]:
    """Return the k rule sections closest to the question."""
    return [d.page_content for d in store.similarity_search(question, k=k)]


class State(TypedDict):
    question: str
    context: list[str]
    answer: str


def retrieve(state: State) -> dict:
    return {"context": search_rulebooks(state["question"])}


def generate(state: State) -> dict:
    context = "\n\n---\n\n".join(state["context"])
    reply = llm.invoke([
        ("system",
         "You are a friendly board-game referee. Answer using only the rulebook "
         "excerpts below. If they do not answer the question, say the rulebooks "
         "don't cover it. Be concise.\n\n" + context),
        ("user", state["question"]),
    ])
    return {"answer": reply.content}


builder = StateGraph(State)
builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

app = builder.compile()


def main() -> None:
    for question in [
        "How many actions do I get per turn in Lantern Harbor?",
        "Can the crown holder use the Betray action in Obsidian Crown?",
        "How many players can play Clockwork Couriers?",
        "Is there a Lantern Harbor expansion with pirates?",  # not in the rulebooks
    ]:
        result = app.invoke({"question": question})
        print(f"Q: {question}\nA: {result['answer']}\n")


if __name__ == "__main__":
    main()
