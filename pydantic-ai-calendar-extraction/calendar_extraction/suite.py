"""Opik test suite: run the agent over CASES and let an LLM judge the assertions."""

from typing import Any

import opik

from . import PROJECT_NAME
from .cases import CASES, GLOBAL_ASSERTIONS


def run_suite(extract, experiment_name: str):
    client = opik.Opik()
    # A test suite stores the items and assertions in Opik; an LLM judge scores each assertion.
    # Each item runs 3 times and passes if 2 pass, which absorbs judge flakiness.
    suite = client.get_or_create_test_suite(
        name=PROJECT_NAME,
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )
    suite.insert(CASES)

    def task(item: dict[str, Any]) -> dict[str, Any]:
        return {"input": item, "output": extract(item["message"])}

    # run_tests runs the task per item and logs an experiment with one evaluation_task trace per run.
    result = opik.run_tests(
        test_suite=suite,
        task=task,
        experiment_name=experiment_name,
        worker_threads=4,
        generate_report=False,
    )
    return client, result
