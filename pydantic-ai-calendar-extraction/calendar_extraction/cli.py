"""CLI: `uv run calendar-extraction`."""

from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    # Walk up from the package to find a .env (repo root or this folder).
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env").exists():
            load_dotenv(parent / ".env")
            break

    from .agent import MODEL, extract_event
    from .cases import CASES

    print(f"Extracting {len(CASES)} messages with {MODEL}...\n")
    for case in CASES:
        msg = case["data"]["message"]
        print(f"  {msg[:60]!r}...\n    -> {extract_event(msg)}\n")
