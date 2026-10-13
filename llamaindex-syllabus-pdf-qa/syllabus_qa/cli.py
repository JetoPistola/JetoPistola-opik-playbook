"""CLI: `build`, `ask "<question>"`, `suite`, or no subcommand to do all three."""

import argparse

import opik

from syllabus_qa import config  # noqa: F401  (sets project + env before opik loads)


def _cmd_build() -> None:
    from syllabus_qa.corpus import generate_syllabi
    paths = generate_syllabi(force=True)
    print(f"Wrote {len(paths)} syllabus PDFs:")
    for p in paths:
        print(f"  {p.relative_to(config.ROOT)}")


def _cmd_ask(question: str) -> None:
    from syllabus_qa.index import build_query_engine
    from syllabus_qa.qa import ask
    a = ask(build_query_engine(), question)
    print(f"Q: {a.question}\nA: {a.text}\n")


def _cmd_demo() -> None:
    from syllabus_qa.index import build_query_engine
    from syllabus_qa.qa import DEMO_QUESTIONS, ask
    engine = build_query_engine()
    for q in DEMO_QUESTIONS:
        a = ask(engine, q)
        print(f"Q: {a.question}\nA: {a.text}\n")


def _cmd_suite() -> None:
    from syllabus_qa.index import build_query_engine
    from syllabus_qa.suite import run_suite
    run_suite(build_query_engine())


def main() -> None:
    parser = argparse.ArgumentParser(prog="syllabus-qa")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("build", help="(re)generate the syllabus PDFs")
    ask_p = sub.add_parser("ask", help="ask one question")
    ask_p.add_argument("question")
    sub.add_parser("suite", help="run the clause-level test suite")
    args = parser.parse_args()

    try:
        if args.cmd == "build":
            _cmd_build()
        elif args.cmd == "ask":
            _cmd_ask(args.question)
        elif args.cmd == "suite":
            _cmd_suite()
        else:  # default: build + demo questions + suite
            _cmd_build()
            _cmd_demo()
            _cmd_suite()
    finally:
        # Traces are sent in the background; flush so a short-lived CLI run doesn't exit before they upload.
        opik.flush_tracker()
