# temporal-py-grant-review

*One Opik trace, two operating-system processes, and a retry you can see.*

Temporal keeps long-running work alive across crashes and flaky services. The price is that one logical job now runs in two places: a starter that submits the workflow, and a worker (often on another machine) that executes it. Ordinary tracing gives you two unrelated fragments, and the interesting part, the failed attempt Temporal quietly retried, sits in the worker's half with no link back to the request that caused it.

This example reviews grant applications for a made-up neighborhood fund (the Larkspur Neighborhood Fund) and uses Opik's distributed tracing to stitch both halves into one trace.

## What you'll build

A `GrantReviewWorkflow` that runs three activities per application:

1. `check_eligibility`: ZIP code in the service area? Request under the $5,000 cap? Ineligible applications are rejected right there.
2. `score_application`: `gpt-4o-mini` scores the pitch from 1 to 10 (traced with `track_openai`).
3. `check_budget_remaining`: looks up what is left in the application's category. Its "ledger service" fails with a 503 on **every first attempt** and succeeds on retry.

`python src/demo.py` starts a Temporal dev server in-process, launches `src/worker.py` as a **separate OS process**, reviews the three applications in `data/applications.json`, then sends the worker SIGTERM so it flushes its Opik spans.

The glue is small. The starter calls `opik_context.get_distributed_trace_headers()` inside its tracked function and puts the resulting plain dict in the workflow input. Activities pass it to `@opik.track` as `opik_distributed_trace_headers=`, which makes each activity span a child of the starter's span. The workflow itself never imports Opik, which keeps Temporal's sandbox happy.

## See it in Opik

Open the `temporal-py-grant-review` project and the **Traces** tab. After a clean run there are 3 traces, named `grant-review:APP-201`, `grant-review:APP-202`, `grant-review:APP-203`.

- **grant-review:APP-201** (approved, score 9) has 6 spans: root `review_grant_application`, then `check_eligibility`, `score_application` with a nested `chat_completion_create` LLM span (162 tokens), and finally **two** `check_budget_remaining` spans. The first carries error info, `ConnectionError: ledger service unavailable (HTTP 503)`; the second is clean. The trace total is about $0.00004.
- Open both `check_budget_remaining` spans side by side: the first shows the `ConnectionError` in its error section, the second has no error and returns `"attempt": 2`. Every span in the trace, including the ones the worker process created, hangs under the client's `review_grant_application` root.
- **grant-review:APP-202** (waitlisted: score 4, and only $3,000 left in the youth category) has the same shape and a trace cost of about $0.00004.
- **grant-review:APP-203** (rejected, ZIP 94901 is out of area) has just 2 spans, root plus `check_eligibility`, and no LLM cost. The workflow ended before spending a token.

In my run the whole demo took about 16 seconds and cost roughly $0.00008 in total.

## Run it yourself

1. `cp .env.example .env` and set `OPENAI_API_KEY` (a `.env` in any parent folder also works). For local Opik, run `opik configure` once; for Opik Cloud, also set `OPIK_API_KEY` and `OPIK_WORKSPACE`.
2. `uv sync`
3. `uv run python src/demo.py`
4. Open the `temporal-py-grant-review` project in Opik.

Tests need no keys, no Opik and no Temporal server (tracking is switched off with `OPIK_TRACK_DISABLE=true`):

`env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

The first run downloads the Temporal dev server binary. It listens on `localhost:7243`. You will see Python tracebacks from the worker log: those are Temporal reporting the deliberate 503 before it retries.

## Poke around

- In `src/activities.py`, change `attempt == 1` to `attempt <= 3` and the budget check shows three red spans before the green one (the retry policy allows four attempts).
- Remove `opik_distributed_trace_headers=` from one activity wrapper and watch that span fall out of the trace into an orphan trace of its own.
- Raise `BUDGET_LEFT_USD["youth"]` in `src/shared.py` and see APP-202 move from waitlisted to a decision based on its score.
- Edit the scoring prompt and compare the `chat_completion_create` input and output across the two scored applications.

## Gotchas we hit

**1. `RestrictedWorkflowAccessError: Cannot access urllib.request.Request.__mro_entries__ from inside a workflow`** appears as soon as a workflow module imports `opik` (directly or through `activities.py`) without a pass-through. Temporal runs workflow code in a sandbox that restricts modules like `urllib.request`, and Opik imports them. Keep all Opik calls in activities, and let the workflow carry the trace headers as a plain `dict[str, str]` in its input. `workflows.py` imports the activity functions only inside `workflow.unsafe.imports_passed_through()`.

**2. The worker's spans are missing in Opik, but the client's are there.** Opik sends spans from a background queue. When the worker is stopped with SIGTERM and has no handler, Python exits without running its exit hooks, and whatever was still queued is lost. Install a SIGTERM handler that lets the worker finish, then call the flush before exiting:

```python
asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)
...
opik.flush_tracker()
```

**3. `TypeError: _check_eligibility() got an unexpected keyword argument 'opik_distributed_trace_headers'`** once you set `OPIK_TRACK_DISABLE=true`. With tracking disabled `@opik.track` passes keyword arguments through untouched instead of consuming the header argument. Do not disable tracking on a worker that forwards headers this way. In tests, `tests/conftest.py` replaces each tracked function with its undecorated body (`func.__wrapped__`) that ignores the keyword.

**4. `AttributeError: 'ErrorInfoPublic' object has no attribute 'get'`** (and `TypeError: 'ErrorInfoPublic' object is not subscriptable` on `error_info["message"]`) when you read spans back with `client.search_spans(...)`. The spans that come back from the REST layer carry `error_info` as an object with `.exception_type`, `.message` and `.traceback`, not a dict. Use `span.error_info.exception_type` and guard with `if span.error_info:`.

## How it's put together

- `src/demo.py`: dev server, worker subprocess, client loop, clean shutdown; creates the root span and distributed headers.
- `src/worker.py`: the worker process; flushes Opik on SIGTERM.
- `src/workflows.py`: the durable workflow and its retry policy.
- `src/activities.py`: the three activities, the traced OpenAI client and the transient failure.
- `src/shared.py`: constants, fund rules, input/result types, `.env` loading.
- `data/applications.json`: three fictional applications.
- `tests/conftest.py`: switches Opik tracking off, sets a dummy OpenAI key and unwraps the tracked functions for tests.
- `tests/test_activities.py`: eligibility rules, budget failure on attempt 1 and success on attempt 2, scoring with a stubbed OpenAI client.
- `tests/test_headers.py`: trace headers survive JSON and reach every tracked activity; the tracked functions run with tracking disabled.

---

*built with Opik · inspired by Opik's examples and documentation*
