"""Constants and plain-data types shared by the starter, the workflow and the worker."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

TASK_QUEUE = "grant-review"
TEMPORAL_PORT = 7243
TEMPORAL_ADDRESS = f"localhost:{TEMPORAL_PORT}"
MODEL = "gpt-4o-mini"

ROOT = Path(__file__).resolve().parent.parent

# Fictional fund: ZIP codes it serves and what is left in each category this quarter.
ELIGIBLE_ZIPS = {"94110", "94103", "94112"}
BUDGET_LEFT_USD = {"community-space": 6000, "youth": 3000, "green-space": 5000}
MAX_GRANT_USD = 5000


def load_env() -> None:
    """Load .env from this folder or the nearest parent."""
    for folder in [ROOT, *ROOT.parents]:
        if (folder / ".env").exists():
            load_dotenv(folder / ".env")
            break


def load_applications() -> list[dict]:
    return json.loads((ROOT / "data" / "applications.json").read_text())


@dataclass
class ReviewInput:
    application: dict


@dataclass
class ReviewResult:
    application_id: str
    decision: str
    reason: str
    score: int | None = None
    attempts_budget_check: int | None = None
