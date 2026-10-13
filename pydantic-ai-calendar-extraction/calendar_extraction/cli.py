"""CLI: `uv run calendar-extraction [--skip-suite]`."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract calendar events and test them with Opik")
    parser.add_argument("--skip-suite", action="store_true", help="only run the extractions")
    parser.add_argument("--experiment", default="calendar-agent-gpt-4o-mini")
    args = parser.parse_args()

    from . import tracing

    # Wires logfire -> Opik OTLP; if the agent is imported first, its calls are not instrumented.
    tracing.setup()  # must precede importing the agent
    import logfire
    import opik

    from .agent import MODEL, extract_event
    from .cases import CASES

    print(f"Extracting {len(CASES)} messages with {MODEL}...\n")
    for case in CASES:
        msg = case["data"]["message"]
        print(f"  {msg[:60]!r}...\n    -> {extract_event(msg)}\n")

    client = None
    if not args.skip_suite:
        from .suite import run_suite

        client, result = run_suite(extract_event, args.experiment)
        print(f"\nPass rate: {result.pass_rate:.0%} ({result.items_passed}/{result.items_total} items)")
        for r in result.item_results.values():
            msg = r.test_results[0].test_case.task_output["input"]["message"]
            print(f"  [{'PASS' if r.passed else 'FAIL'}] {msg[:60]!r}...")
        print(f"\nExperiment: {result.experiment_name} ({result.experiment_url})")

    # Flush all three buffers before exit: OTel spans, the Opik client (suite/experiment), and
    # the @track queue. Without them the last traces never appear in Opik.
    logfire.force_flush()
    (client or opik.Opik()).flush()
    opik.flush_tracker()
