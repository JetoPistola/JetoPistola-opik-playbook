"""One command: dev server + separate worker process + client, then clean shutdown."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

from shared import (
    TASK_QUEUE, TEMPORAL_PORT, ReviewInput, ReviewResult, load_applications, load_env,
)

load_env()
from workflows import GrantReviewWorkflow  # noqa: E402


async def review(client: Client, application: dict) -> ReviewResult:
    """Start the workflow from the client process and wait for the result."""
    return await client.execute_workflow(
        GrantReviewWorkflow.run,
        ReviewInput(application=application),
        id=f"grant-{application['id']}-{uuid.uuid4().hex[:6]}",
        task_queue=TASK_QUEUE,
    )


async def main() -> None:
    src = Path(__file__).parent
    async with await WorkflowEnvironment.start_local(port=TEMPORAL_PORT, ui=False) as env:
        worker = subprocess.Popen(
            [sys.executable, str(src / "worker.py")],
            cwd=src, env=os.environ.copy(), stdout=subprocess.PIPE, text=True,
        )
        try:
            assert worker.stdout and "ready" in worker.stdout.readline()
            print(f"client pid {os.getpid()} / worker pid {worker.pid}", flush=True)
            for app in load_applications():
                r = await review(env.client, app)
                print(f"{r.application_id}: {r.decision} (score={r.score}, "
                      f"budget-check attempt={r.attempts_budget_check}) - {r.reason}", flush=True)
        finally:
            worker.send_signal(signal.SIGTERM)
            try:
                print(worker.communicate(timeout=60)[0].strip())
            except subprocess.TimeoutExpired:
                worker.kill()


if __name__ == "__main__":
    asyncio.run(main())
