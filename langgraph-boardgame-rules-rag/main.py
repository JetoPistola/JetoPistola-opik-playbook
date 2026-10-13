"""Rulebook referee: RAG over fictional board-game rulebooks, traced with Opik.

Graph: retrieve (embedding search over rule sections) -> generate (gpt-4o-mini).
Retrieval is a named @opik.track(type="tool") function so it always shows up
as its own span.
"""

import os
import pathlib

PROJECT_NAME = "langgraph-boardgame-rules-rag"
# Set before opik is imported so every trace lands in this project, not "Default Project".
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import dotenv

# Walk up from this folder to find a .env (repo root or local copy).
for parent in pathlib.Path(__file__).resolve().parents:
    if (parent / ".env").exists():
        dotenv.load_dotenv(parent / ".env")
        break

import opik
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from opik.integrations.langchain import OpikTracer, track_langgraph
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


# Explicit tool span: the OpikTracer can drop LangChain retriever runs, so retrieval is
# tracked by hand and always appears as "search_rulebooks" (type tool) inside the retrieve node.
@opik.track(name="search_rulebooks", type="tool")
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

# OpikTracer turns each graph call into a trace: one span per node, plus an llm span
# (prompt, token usage, cost) for the ChatOpenAI call inside generate.
tracer = OpikTracer(project_name=PROJECT_NAME, tags=["boardgame-rag"])
# track_langgraph attaches the tracer to the compiled graph so callers need no config.
app = track_langgraph(builder.compile(), tracer)


def main() -> None:
    for question in [
        "How many actions do I get per turn in Lantern Harbor?",
        "Can the crown holder use the Betray action in Obsidian Crown?",
        "How many players can play Clockwork Couriers?",
        "Is there a Lantern Harbor expansion with pirates?",  # not in the rulebooks
    ]:
        result = app.invoke({"question": question})
        print(f"Q: {question}\nA: {result['answer']}\n")

    # Traces are sent in the background; flush so a short script doesn't exit before they upload.
    tracer.flush()
    opik.flush_tracker()


if __name__ == "__main__":
    main()
