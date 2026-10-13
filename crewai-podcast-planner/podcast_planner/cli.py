import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_BRIEF = "An episode on why the Northern Reach's foghorns fell silent, built around a retired keeper's story."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="podcast-planner", description=__doc__)
    parser.add_argument("brief", nargs="?", default=DEFAULT_BRIEF, help="the episode brief")
    parser.add_argument("--notes", type=Path, default=None, help="path to a notes markdown file")
    return parser


def main() -> None:
    # Load the nearest .env walking up from here (repo root in the playbook).
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            load_dotenv(parent / ".env")
            break
    # Turns off CrewAI's own telemetry so only Opik receives trace data from this run.
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "false")

    args = build_parser().parse_args()

    import opik

    from .crew import DEFAULT_NOTES, plan_episode

    result = plan_episode(args.brief, args.notes or DEFAULT_NOTES)
    print("\n=== EPISODE PACKAGE ===\n")
    print(result)
    # The tracker sends in the background; flush so the trace is delivered before the process exits.
    opik.flush_tracker()


if __name__ == "__main__":
    main()
