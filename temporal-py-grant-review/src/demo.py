"""One command: dev server + separate worker process + client, then clean shutdown."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path

import opik
from opik import opik_context
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

from shared import (
    TASK_QUEUE, TEMPORAL_PORT, ReviewInput, ReviewResult, load_applications, load_env,
)

load_env()
from workflows import GrantReviewWorkflow  # noqa: E402


# Root span of the trace, created in the client process.
@opik.track(name="review_grant_application", type="general")
async def review(client: Client, application: dict) -> ReviewResult:
    """Client-side root of the trace. Its headers travel to the worker process."""
    # Names the whole trace (grant-review:APP-201) and tags it, so traces are easy to find in the list.
    opik_context.update_current_trace(
        name=f"grant-review:{application['id']}",
        tags=["temporal", application["category"]],
        metadata={"applicant": application["applicant"]},
    )
    # Serialises this span's identity into a plain dict; the worker process reads it back
    # to attach its spans to this trace.
    headers = opik_context.get_distributed_trace_headers()
    return await client.execute_workflow(
        GrantReviewWorkflow.run,
        ReviewInput(application=application, trace_headers=dict(headers)),
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
            # The client process is short-lived: flush so its root spans are sent before exit.
            opik.flush_tracker()
        finally:
            worker.send_signal(signal.SIGTERM)
            try:
                print(worker.communicate(timeout=60)[0].strip())
            except subprocess.TimeoutExpired:
                worker.kill()


if __name__ == "__main__":
    asyncio.run(main())
