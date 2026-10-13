# beeai-py-lab-equipment-triage

![Python](https://img.shields.io/badge/python-3.12%2B-3776ab?style=flat&logo=python&logoColor=white)
![BeeAI](https://img.shields.io/badge/beeai--framework-0.1.85-f5c518?style=flat)
![OpenInference](https://img.shields.io/badge/openinference--instrumentation--beeai-0.1.30-7b61ff?style=flat)
![Opik](https://img.shields.io/badge/Opik-OTLP%20ingestion-2f54eb?style=flat)

**A ReAct agent that reads a researcher's "the freezer is warm" message and decides how bad it is, what to do, and who to call, with every model call and tool call visible in Opik.**

When an agent answers `SEVERITY: critical, call Facilities`, the answer alone tells you nothing about whether it looked at the instrument's log, checked the calibration dates, or just guessed. This example puts a small [BeeAI Framework](https://github.com/i-am-bee/beeai-framework) agent in front of the instruments of a made-up university lab (a floor centrifuge, an autoclave, a -80C freezer, a UV spectrophotometer). BeeAI emits OpenInference spans, so a few lines of OpenTelemetry setup send the whole run to Opik with no Opik SDK calls in the app.

## What you'll build

One `ReActAgent` on `gpt-4o-mini` with three read-only tools over JSON files in `data/`:

- `lookup_instrument_log` returns the instrument's model, room, owner and maintenance history.
- `check_calibration_schedule` returns the interval and the next due date (the fictional "today" is 2026-10-13).
- `find_service_contact` returns the person or vendor to call, and how fast they respond.

`python main.py` (via `uv run`) feeds it three scripted problem reports and prints the decision for each:

1. The -80C freezer reads -71C after the door was left open overnight.
2. The centrifuge shook at 4200 rpm and the imbalance sensor stopped it, for the second time in a week.
3. The spectrophotometer looks "a bit noisy", and its calibration is one day overdue.

## See it in Opik

Open the project **beeai-py-lab-equipment-triage**. One run of `uv run main.py` produces **3 traces**, each named `ReAct`, with their Input and Output columns filled: the input is the instructions plus the report, the output is the three-line decision.

Open the spectrophotometer trace (8 spans). It is a root `ReAct` span with seven children: four `OpenAIChatModel` spans (type `llm`, model `gpt-4o-mini`) and three tool spans, `lookup_instrument_log`, `check_calibration_schedule` and `find_service_contact`. Click a tool span and you see the arguments the model chose (`{"instrument_id": "SP-07"}`, then `{"instrument_type": "spectrophotometer"}`) and the JSON the tool returned, including the contact line "Tomas Lindqvist, ext. 5-0207". The calibration span returns `next_due: 2026-10-12`, which is why the final answer talks about calibration.

The traces differ because the model decides how many tools to call:

| Report | Spans | Shape | Trace tokens |
|---|---|---|---|
| Spectrophotometer | 8 | 4 LLM calls, 3 tool calls | 2578 |
| Centrifuge | 4 | 2 LLM calls, only the log lookup | 2380 |
| Freezer | 7 | 3 LLM calls, 1 tool call, plus an `error` and a `retry` span | 3576 |

The freezer trace is the most useful one to open. The `error` span holds a BeeAI parser error (the model's text did not fit the ReAct format), the `retry` span says `iteration: 1`, and the next LLM call is the recovery. Without tracing you would only see a slightly slower answer.

Some honest limits of what lands in Opik:

- **No "iteration" spans.** The Python instrumentor does not wrap each ReAct turn. The tree is flat: LLM and tool spans are siblings under `ReAct`, in the order they ran. Read the order to follow the loop.
- **Tool spans are type `general`**, not `tool`.
- **Cost stays empty.** Spans carry token counts (the trace totals above are summed from them) but Opik did not compute a dollar cost for these spans.
- **Some LLM spans show 0 tokens.** In the spectrophotometer trace the two middle LLM calls (the ones that produced tool calls) report zero usage, while the first and last report real numbers. That is how the streamed BeeAI calls were reported, so the trace totals undercount slightly.
- **Runs vary.** The model is not deterministic, so span counts change between runs.

## Run it yourself

1. Install [uv](https://docs.astral.sh/uv/) and have a local Opik running (or an Opik Cloud key).
2. `cp .env.example .env` and set `OPENAI_API_KEY` (a `.env` in a parent folder also works).
3. `uv run main.py`
4. Open the `beeai-py-lab-equipment-triage` project in Opik at http://localhost:5173 and click the newest trace.

A run takes about 15 to 25 seconds and costs a fraction of a cent. For Opik Cloud, set `OPIK_OTLP_ENDPOINT=https://www.comet.com/opik/api/v1/private/otel` and `OPIK_API_KEY`.

## Poke around

- Reword report 3 to say the readings are drifting and the lamp keeps cutting out. The log says the lamp has 1950 of 2000 hours; see whether the agent finds that in the `lookup_instrument_log` output and whether severity changes.
- Add an autoclave report ("cycle 4 failed with E-31 again") and compare which tools the agent chooses against the centrifuge case.
- Set `max_iterations` to 2 in `main.py` and watch the spectrophotometer trace get cut off before `find_service_contact` can run.
- In `tracing.py`, make `DropTokenSpans` keep everything. BeeAI streams, and the instrumentor then emits one `new_token` span per chunk, hundreds per trace.

## Gotchas we hit

- **The trace is buried in hundreds of `new_token` spans.** BeeAI streams the model's answer, and the instrumentor turns every event it has no dedicated handler for into a child span named after the event, so each streamed chunk becomes a `new_token` leaf. Subclass the OTLP exporter and drop them before export: `kept = [s for s in spans if s.name != "new_token"]` in `DropTokenSpans.export` (see `tracing.py`).
- **You look for per-iteration spans and find none.** The Python instrumentor records the current ReAct iteration as metadata on the `ReAct` root span (`metadata.iteration`, `metadata.iterations.N.*`) and only creates child spans for LLM calls, tools, `error` and `retry`. Follow the loop by the order of the sibling spans.
- **Traces land in the wrong project, or nowhere.** The project comes from the `projectName` OTLP header and the workspace from `Comet-Workspace`; the exporter must also point at `<endpoint>/v1/traces`. For local Opik no `Authorization` header is sent; add it only when `OPIK_API_KEY` is set. `tests/test_tracing.py` pins this config.
- **Cost is empty and some LLM spans show 0 tokens.** You can see this in the traces above: the OpenInference spans carry usage but no model-price mapping Opik uses for cost, and the tool-call turns of streamed calls report zero usage. Treat trace token totals as a lower bound.

## How it's put together

- `main.py` loads env, sets up tracing before importing the agent, runs the three reports, flushes and shuts the tracer provider down.
- `tracing.py` is the only tracing code: a tracer provider, an OTLP exporter aimed at Opik (headers `Comet-Workspace` and `projectName`), `BeeAIInstrumentor`, and an exporter subclass that drops per-token spans.
- `tools.py` holds the three tools.
- `tests/test_tools.py` runs the three tools against `data/` (lookups, case handling, unknown ids, overdue calibration).
- `tests/test_tracing.py` checks the OTLP config (endpoint, `Comet-Workspace`, `projectName`, no `Authorization` locally) and that `DropTokenSpans` drops `new_token` spans, using fake spans.
- `data/instruments.json`, `data/calibration.json`, `data/contacts.json` are the fictional lab records.
- `pyproject.toml` pins `beeai-framework`, the instrumentor, and `opik`, plus `pytest` as a dev dependency.

Run the offline tests (no model, no Opik, no network) with `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`. The app calls no Opik SDK function, so there is no tracking switch to flip; the unset keys are just a guard.

---

*built with Opik · inspired by Opik's examples and documentation*
