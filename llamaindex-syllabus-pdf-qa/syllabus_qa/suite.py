"""Clause-level test suite: every item asserts one specific syllabus clause."""

import opik

from syllabus_qa.config import PROJECT_NAME
from syllabus_qa.qa import ask

SUITE_NAME = "syllabus-clauses"

# (question, [clause assertions]) -- one clause per assertion.
ITEMS = [
    ("How are BIO 101 late assignments penalized?",
     ["The answer states that BIO 101 late work loses 10% per day, accepted for a maximum of 3 days"]),
    ("What happens to MAT 120 homework that is turned in a day late?",
     ["The answer states MAT 120 homework up to 48 hours late gets a flat 15% penalty"]),
    ("What is the late policy for essays in ENG 110?",
     ["The answer states ENG 110 gives one 72-hour penalty-free grace extension per semester",
      "The answer states that after the grace extension, essays lose 5% per day for up to 5 days"]),
    ("How much is the final exam worth in BIO 101?",
     ["The answer states the BIO 101 final exam is worth 30% of the grade"]),
    ("What are the MAT 120 grading weights?",
     ["The answer states homework 20%, two midterms 25% each, and the final 30%"]),
    ("When does Dr. Tanaka hold office hours?",
     ["The answer states Tuesdays and Thursdays from 2:00 pm to 4:00 pm in room S214"]),
    ("Can I see Prof. Brightwater in person during office hours?",
     ["The answer states ENG 110 office hours (Fridays 1-3 pm) are online only"]),
    ("Is there a placement-test route into MAT 120?",
     ["The answer states MAT 120 requires MAT 095 with a C or better and has no placement alternative"]),
    ("What are the prerequisites for BIO 101?",
     ["The answer states BIO 099 with a C or better, or a placement score of 70 or above"]),
]

GLOBAL_ASSERTIONS = [
    "Every figure, time, and room in the answer appears in the retrieved syllabus "
    "excerpts - the answer invents no policy",
]


def run_suite(query_engine) -> None:
    client = opik.Opik()
    # A test suite is an Opik dataset whose items carry their own assertions (one per clause).
    # The global assertion is judged on every item; each item runs 3 times and must pass 2 of them.
    suite = client.get_or_create_test_suite(
        name=SUITE_NAME,
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )
    # The items are stored in the suite's dataset, syllabus-clauses.
    suite.insert([{"data": {"question": q}, "assertions": a} for q, a in ITEMS])

    def task(item: dict) -> dict:
        ans = ask(query_engine, item["question"])
        return {"input": item, "output": {"answer": ans.text, "retrieved_excerpts": ans.excerpts}}

    # run_tests runs the task per item and has an LLM judge score every assertion. It creates one
    # experiment, with an evaluation_task trace per run (holding the query tree) and a per-clause pass count.
    result = opik.run_tests(test_suite=suite, task=task, worker_threads=3, generate_report=False)

    print(f"\nClause pass rate: {result.pass_rate:.0%} "
          f"({result.items_passed}/{result.items_total} items passed)")
    for r in result.item_results.values():
        q = r.test_results[0].test_case.task_output["input"]["question"]
        print(f"  [{'PASS' if r.passed else 'FAIL'}] {q}")
        if not r.passed:
            for run in r.test_results:
                for s in run.score_results:
                    if s.scoring_failed or s.value != 1:
                        print(f"       failed: {s.name} - {s.reason}")
    if result.experiment_url:
        print(f"\nView the run: {result.experiment_url}")
