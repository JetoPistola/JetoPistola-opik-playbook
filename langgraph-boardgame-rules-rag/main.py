"""Rulebook referee: RAG over fictional board-game rulebooks, traced with Opik.

Graph: retrieve (embedding search over rule sections) -> generate (gpt-4o-mini).
Retrieval is a named @opik.track(type="tool") function so it always shows up
as its own span. After a few live questions, an Opik dataset and an
evaluate() run score the pipeline with Hallucination and ContextPrecision.
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
from opik.evaluation import evaluate
from opik.evaluation.metrics import ContextPrecision, Hallucination
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


# Explicit tool span: retrieval is tracked by hand so it always appears as "search_rulebooks"
# (type tool) inside the retrieve node, with the retrieved sections as its output.
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

# Questions with reference answers; inserted into an Opik dataset for the experiment below.
DATASET_ITEMS = [
    {"question": "How many coins does it cost to light a lantern in Lantern Harbor?",
     "expected_output": "5 coins."},
    {"question": "In Obsidian Crown, how many more cubes do I need to take a province another house holds?",
     "expected_output": "You must beat its cube count by at least 2."},
    {"question": "What does a spore token do in Moss & Mushroom?",
     "expected_output": "Spend 1 to swap a market tile for the top of the stack; unspent spores score 1 point each."},
    {"question": "What happens when two Clockwork Couriers automatons land on the same tile?",
     "expected_output": "Both lose their next command and stay put."},
    {"question": "How do you win Moss & Mushroom solo?",
     "expected_output": "Reach 40 points before the stack runs out."},
    {"question": "How many parcels can an automaton carry at once?",
     "expected_output": "At most 2 parcels."},
]


def rag_task(item: dict) -> dict:
    # Runs inside evaluate(): each call becomes an "evaluation_task" trace linked to the
    # experiment item. "context" is returned so ContextPrecision can score it.
    result = app.invoke({"question": item["question"]})
    return {"output": result["answer"], "context": result["context"]}


def main() -> None:
    for question in [
        "How many actions do I get per turn in Lantern Harbor?",
        "Can the crown holder use the Betray action in Obsidian Crown?",
        "How many players can play Clockwork Couriers?",
        "Is there a Lantern Harbor expansion with pirates?",  # not in the rulebooks
    ]:
        result = app.invoke({"question": question})
        print(f"Q: {question}\nA: {result['answer']}\n")

    client = opik.Opik()
    # Same name every run; the dataset shows under Datasets in Opik.
    dataset = client.get_or_create_dataset(name=PROJECT_NAME)
    dataset.insert(DATASET_ITEMS)

    # evaluate() runs rag_task per item and scores each output with the two LLM-judge metrics;
    # results appear under Experiments as "rules-baseline-k<K>", rows linked to their traces.
    # No project_name here: it is deprecated and the dataset's project is used.
    evaluation = evaluate(
        dataset=dataset,
        task=rag_task,
        scoring_metrics=[Hallucination(), ContextPrecision()],
        scoring_key_mapping={"input": "question"},
        experiment_name=f"rules-baseline-k{TOP_K}",
        task_threads=2,
    )
    agg = evaluation.aggregate_evaluation_scores().aggregated_scores
    print(f"Experiment scores (mean over {len(evaluation.test_results)} questions):")
    for name, stats in agg.items():
        print(f"  {name}: {stats.mean:.2f}")
    if evaluation.experiment_url:
        print(f"Experiment: {evaluation.experiment_url}")

    # Flush both senders: short scripts otherwise exit before traces and scores upload.
    tracer.flush()
    opik.flush_tracker()


if __name__ == "__main__":
    main()
