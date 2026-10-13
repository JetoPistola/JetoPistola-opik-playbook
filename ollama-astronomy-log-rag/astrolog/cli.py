"""astrolog CLI: ingest | ask "<question>" | demo"""
import argparse

from dotenv import load_dotenv

load_dotenv()

import opik  # noqa: E402
from opik.integrations.langchain import OpikTracer  # noqa: E402

from .answer import build_chain  # noqa: E402
from .config import PROJECT_NAME  # noqa: E402
from .ingest import load_chunks  # noqa: E402
from .config import DOCS_DIR  # noqa: E402
from .store import build_store  # noqa: E402

DEMO_QUESTIONS = [
    "What equipment did Jonas Okafor use at Cedar Hollow, and which filter?",
    "How many meteors did Lena count during the Perseid watch?",
    "What was the seeing during the Saturn session, and which moons were seen?",
    "Which session had the darkest sky overall, and what was its SQM reading?",
]


def _ask(chain, tracer, question: str) -> str:
    # The OpikTracer callback turns each chain run into one trace, with a child span per step.
    return chain.invoke(question, config={"callbacks": [tracer]})


def cmd_ingest(_args) -> None:
    for c in load_chunks(DOCS_DIR):
        print(f"{c.metadata['source']:28} {c.metadata['entry']}")


def _run(questions: list[str]) -> None:
    store = build_store()
    chain = build_chain(store)
    # One tracer for all questions: each invoke becomes its own trace in the project, tagged for filtering.
    tracer = OpikTracer(project_name=PROJECT_NAME, tags=["ollama", "local-rag"])
    for q in questions:
        print(f"Q: {q}\nA: {_ask(chain, tracer, q)}\n")
    # Spans are sent in the background; without a flush a short CLI run can exit before they arrive.
    opik.flush_tracker()
    print(f"Done. Open the '{PROJECT_NAME}' project in Opik.")


def main() -> None:
    p = argparse.ArgumentParser(prog="astrolog")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest", help="list the log entries that will be embedded")
    ask = sub.add_parser("ask", help="ask one question")
    ask.add_argument("question")
    sub.add_parser("demo", help="run the scripted questions")
    args = p.parse_args()
    if args.cmd == "ingest":
        cmd_ingest(args)
    elif args.cmd == "ask":
        _run([args.question])
    else:
        _run(DEMO_QUESTIONS)
