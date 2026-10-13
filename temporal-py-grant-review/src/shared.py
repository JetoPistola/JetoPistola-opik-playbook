"""Constants and plain-data types shared by the starter, the workflow and the worker."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

TASK_QUEUE = "grant-review"
TEMPORAL_PORT = 7243
TEMPORAL_ADDRESS = f"localhost:{TEMPORAL_PORT}"
PROJECT_NAME = "temporal-py-grant-review"
MODEL = "gpt-4o-mini"

ROOT = Path(__file__).resolve().parent.parent

# Fictional fund: ZIP codes it serves and what is left in each category this quarter.
ELIGIBLE_ZIPS = {"94110", "94103", "94112"}
BUDGET_LEFT_USD = {"community-space": 6000, "youth": 3000, "green-space": 5000}
MAX_GRANT_USD = 5000


def load_env() -> None:
    """Load .env from this folder or the nearest parent, then pin the Opik project."""
    for folder in [ROOT, *ROOT.parents]:
        if (folder / ".env").exists():
            load_dotenv(folder / ".env")
            break
    # Both processes read OPIK_PROJECT_NAME, so client and worker spans land in one project.
    os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME


def load_applications() -> list[dict]:
    return json.loads((ROOT / "data" / "applications.json").read_text())


@dataclass
class ReviewInput:
    application: dict
    # Opik distributed-trace headers, carried as a plain dict (the workflow sandbox
    # never touches Opik; only activities do).
    trace_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ReviewResult:
    application_id: str
    decision: str
    reason: str
    score: int | None = None
    attempts_budget_check: int | None = None
