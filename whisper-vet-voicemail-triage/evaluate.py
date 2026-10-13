"""Test suite over the triage step, tolerant of LLM-judge flakiness.

Reads the transcripts cached by main.py (out/triage.json), re-runs the
triage step on each, and has an LLM judge check three assertions. Each item
runs 3 times and must pass at least 2.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
PROJECT = "whisper-vet-voicemail-triage"
# set before importing opik so the suite and its traces use this project
os.environ["OPIK_PROJECT_NAME"] = PROJECT
os.environ.pop("OPENAI_BASE_URL", None)

import opik

from main import triage

ASSERTIONS = [
    "The urgency level is justified by the transcript: anything suggesting "
    "toxin ingestion, bloat, breathing trouble, seizures or trauma is "
    "'emergency'; a non-life-threatening injury is 'same-day'; bookings and "
    "refills are 'routine'.",
    "The callback entry's owner name and pet name match the transcript, and "
    "the callback number contains the same digits the caller gave.",
    "Nothing in the output is invented: no symptoms, times or numbers that "
    "the caller did not mention.",
]


def task(item: dict) -> dict:
    out = triage(item["transcript"])
    return {"input": {"transcript": item["transcript"]}, "output": out}


if __name__ == "__main__":
    path = HERE / "out" / "triage.json"
    if not path.exists():
        raise SystemExit("Run `uv run main.py` first.")
    client = opik.Opik()
    # runs_per_item=3 / pass_threshold=2: each item runs 3 times and passes with 2 judge passes,
    # so one odd LLM-judge verdict does not fail the suite
    suite = client.get_or_create_test_suite(
        name="vet-voicemail-triage-suite",
        project_name=PROJECT,
        global_assertions=ASSERTIONS,
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )
    have = {i["data"]["voicemail_id"] for i in suite.get_items()}
    for rec in json.loads(path.read_text()):
        if rec["id"] not in have:
            suite.insert([{"data": {"voicemail_id": rec["id"], "transcript": rec["transcript"]}}])
    # run_tests creates an experiment: one evaluation_task trace per run with per-assertion results
    result = opik.run_tests(test_suite=suite, task=task)
    print(f"\nPass rate: {result.pass_rate:.0%}")
    # flush so the last traces and results are sent before exit
    opik.flush_tracker()
