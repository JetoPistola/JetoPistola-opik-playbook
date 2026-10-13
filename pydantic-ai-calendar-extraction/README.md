<div align="center">

# Calendar Events, Caught Lying

**`pydantic-ai-calendar-extraction`**

*An agent that fills in the blanks politely. A test suite that notices.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![Pydantic AI](https://img.shields.io/badge/pydantic--ai-2.x-E92063?style=flat)
![Opik](https://img.shields.io/badge/Opik-2.2.99-2f54eb?style=flat)

</div>

---

Ask a model to turn "dinner with the Okonkwos next Friday at 7pm?" into a calendar
entry and you get a tidy typed record back. The danger is the fields the message
never filled in: a restaurant nobody picked, an end time nobody mentioned, guests
nobody named. A confident-looking `CalendarEvent` hides all of that. This project
extracts events with a Pydantic AI agent, ships every call to Opik over
OpenTelemetry, and then runs a test suite whose assertions are specifically about
**not inventing values**.

## What you'll build

- A `CalendarEvent` model (title, date, start/end time, timezone, location, attendees)
  with almost everything optional.
- A Pydantic AI agent on `gpt-4o-mini` that fills it from seven fictional messages: a
  formal invite, a casual chat, a voicemail, an offsite reminder, a vague "lunch
  sometime", a forwarded invite with a TBD duration, and a book-club change.
- Tracing through logfire's OTel instrumentation, with Opik's `OpikSpanProcessor`
  nesting the agent's spans under one `extract_event` span.
- An Opik test suite: three global assertions (no invented fields, valid formats)
  plus two or three per-message assertions, judged by an LLM, 3 runs per message,
  an item passes if 2 of 3 runs pass.

## See it in Opik

Open the **`pydantic-ai-calendar-extraction`** project. The **Traces** tab holds 28
traces from one run: 7 named `extract_event` (the plain extraction pass) and 21
named `evaluation_task` (7 messages x 3 suite runs). Expand an `extract_event`
trace: the input is the raw message, the output is the typed record, and below it
sit an `invoke_agent agent` span and a `chat gpt-4o-mini` span. The chat spans carry
token usage (including reasoning tokens) and an estimated cost, about $0.00008 each.

Then go to **Experiments** and open `calendar-agent-gpt-4o-mini`. The suite result
from this run was **3 of 7 items passed (43%)**. The failures are the point:

- *Book club moved...* The message says "same crowd as always". The agent returned
  `attendees: ['Same crowd as always']`, treating a phrase as a person. The
  "attendees are empty" assertion passed 0 of 3 runs.
- *Team lunch sometime this week* The agent produced `date: 2026-03-05` out of
  "sometime this week". The "all fields null" assertion passed 0 of 3 runs.
- *Dinner with the Okonkwos* The expected date and time check failed in all 3 runs,
  and the voicemail failed intermittently (the end-time/location check passed 2 of 3).

The global "every non-null value is derivable from the message" assertion passed
only 13 of 21 runs, which is the honest headline number for this prompt. Your own
numbers will move a little between runs: the judge is an LLM too.

## Run it yourself

1. Add `OPENAI_API_KEY` to a `.env` here or in any parent folder (`cp .env.example .env`).
2. Start Opik locally (default `http://localhost:5173`); for a hosted workspace set
   `OPIK_API_KEY` and `OPIK_URL_OVERRIDE`/`OPIK_WORKSPACE`.
3. `uv sync`
4. `uv run main.py` (same as `uv run calendar-extraction`; add `--skip-suite` to only extract).
5. Open the project named above; the experiment URL is printed at the end. A run
   takes about a minute and cost about $0.01 in gpt-4o-mini calls (app plus judge).

## Run the tests

`env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest` (no keys, no Opik, a few seconds).

## Poke around

- Delete "Never guess a duration or end time" from the system prompt in
  `agent.py` and compare the next experiment.
- Swap `MODEL` for `openai:gpt-4.1-mini` and see whether the "same crowd" item changes.
- Change `runs_per_item` / `pass_threshold` in `suite.py` and watch the pass rate shift.
- Add a message to `cases.py` with a deliberately unresolvable detail and write the
  assertion that should catch the model guessing it.

## Gotchas we hit

- **Nothing shows up in Opik, or traces land in the wrong project.** Pydantic AI is traced
  through logfire/OTel, not `@opik.track`, so the OTLP exporter needs its own settings.
  Set `OTEL_EXPORTER_OTLP_ENDPOINT=<opik url>/v1/private/otel` and
  `OTEL_EXPORTER_OTLP_HEADERS=Comet-Workspace=<workspace>,projectName=<project>` (plus
  `Authorization=<key>` on a hosted workspace) before `logfire.configure(...)`, and call
  `tracing.setup()` before importing the agent module.
- **`client.get_experiments_by_name(...)` raises `ExperimentNotFound` for an experiment whose URL
  was just printed.** To check a run programmatically, list by dataset instead:
  `client.rest_client.experiments.find_experiments(dataset_id=...)`.
- **Importing the agent fails with a missing-API-key error in tests.** `Agent("openai:...")`
  builds the provider client at construction, so the import needs `OPENAI_API_KEY` set even
  when no call is made. `tests/conftest.py` sets a placeholder before the app is imported and
  tests swap in a `FunctionModel` with `agent.override(model=...)`, so no network call happens.
- **The suite pass rate wobbles between runs.** The judge is an LLM. Use
  `global_execution_policy={"runs_per_item": 3, "pass_threshold": 2}` as `suite.py` does.

## How it's put together

- `main.py` thin entry point, calls the CLI.
- `calendar_extraction/cli.py` runs the extractions, then the suite, then flushes.
- `calendar_extraction/tracing.py` points logfire/OTel at Opik's OTLP endpoint.
- `calendar_extraction/models.py` the `CalendarEvent` schema.
- `calendar_extraction/agent.py` the Pydantic AI agent and the tracked `extract_event`.
- `calendar_extraction/cases.py` the messages plus global and per-message assertions.
- `calendar_extraction/suite.py` builds the Opik test suite and runs it.
- `tests/test_app.py` offline tests: model defaults, case shape, a `@track`ed extraction against a
  `FunctionModel`, and the OTLP endpoint/headers built by `tracing.setup()`.

---

*built with Opik · inspired by Opik's examples and documentation*
