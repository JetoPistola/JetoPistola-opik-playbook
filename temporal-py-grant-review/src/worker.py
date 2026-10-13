"""Worker process: runs workflows and activities, exports Opik spans, flushes on SIGTERM."""

from __future__ import annotations

import asyncio
import signal

import opik
from temporalio.client import Client
from temporalio.worker import Worker

from shared import TASK_QUEUE, TEMPORAL_ADDRESS, load_env


async def main() -> None:
    load_env()
    from activities import check_budget_remaining, check_eligibility, score_application
    from workflows import GrantReviewWorkflow

    client = await Client.connect(TEMPORAL_ADDRESS)
    stop = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)
    asyncio.get_running_loop().add_signal_handler(signal.SIGINT, stop.set)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GrantReviewWorkflow],
        activities=[check_eligibility, score_application, check_budget_remaining],
    ):
        print("worker: ready", flush=True)
        await stop.wait()
    # The demo stops this worker with SIGTERM; flush here so spans still queued in
    # this process reach Opik before it exits, otherwise the worker half of the trace is lost.
    opik.flush_tracker()
    print("worker: flushed Opik and exiting", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
