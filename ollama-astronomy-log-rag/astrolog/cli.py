"""astrolog CLI: ingest | ask "<question>" | demo"""
import argparse

from dotenv import load_dotenv

load_dotenv()

from .answer import build_chain  # noqa: E402
from .config import DOCS_DIR  # noqa: E402
from .ingest import load_chunks  # noqa: E402
from .store import build_store  # noqa: E402

DEMO_QUESTIONS = [
    "What equipment did Jonas Okafor use at Cedar Hollow, and which filter?",
    "How many meteors did Lena count during the Perseid watch?",
    "What was the seeing during the Saturn session, and which moons were seen?",
    "Which session had the darkest sky overall, and what was its SQM reading?",
]


def _ask(chain, question: str) -> str:
    return chain.invoke(question)


def cmd_ingest(_args) -> None:
    for c in load_chunks(DOCS_DIR):
        print(f"{c.metadata['source']:28} {c.metadata['entry']}")


def _run(questions: list[str]) -> None:
    store = build_store()
    chain = build_chain(store)
    for q in questions:
        print(f"Q: {q}\nA: {_ask(chain, q)}\n")


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
