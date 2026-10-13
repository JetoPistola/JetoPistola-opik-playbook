# smolagents-weather-station-analyst

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![smolagents](https://img.shields.io/badge/smolagents-CodeAgent-FFD21E?style=flat)
![Opik](https://img.shields.io/badge/Opik-OTLP-2f54eb?style=flat)

*Ask a code-writing agent about messy sensor data, then read the pandas it actually ran.*

A code agent that answers with a number is only as good as the code behind the number. Real sensor logs have stuck
sensors, sentinel values and duplicated rows, and an agent can compute straight through all of them and sound sure of
itself. This example puts a smolagents `CodeAgent` in front of two weeks of hourly readings from a fictional
community weather station (Larkspur Hill) and traces every step into Opik, so you can check each answer against the
code and the execution output that produced it.

## What you'll build

- `data/readings.csv`: 337 hourly rows (2-15 March 2026) with `temp_c`, `humidity_pct`, `wind_kmh`, `rain_mm`. Three
  faults are planted: one `-99.9` temperature dropout, a 30-hour stretch where the wind sensor is stuck at `0.0`, and
  one rainy hour (5 March, 06:00) that appears twice.
- `main.py`: a `CodeAgent` on `gpt-4o-mini` (pandas is the only extra import, `max_steps=6`) asked three questions:
  total and wettest-day rain, average wind per day and the calmest day, and the hottest and coldest readings.
- Tracing via `openinference-instrumentation-smolagents` and a plain OTLP/HTTP exporter pointed at Opik. No
  decorators in the agent code.

## See it in Opik

Open the **smolagents-weather-station-analyst** project. It holds 3 traces, all named `CodeAgent.run`, with the full
prompt as input and the agent's final answer as output.

- **Trace 1 (rain)** has 6 spans: two `Step` spans, two `OpenAIModel.generate` spans and `FinalAnswerTool`, under the
  root. Click the first `generate` span: its output contains the model's thought and a `<code>` block with the real
  `pd.read_csv` / `groupby` code. Click `Step 1`: the output is the execution log, starting with the
  `describe()` table whose `min` for `temp_c` reads `-99.9`. The answer reads "34.00 mm, wettest day March 5th
  (18.6 mm)" and flags the temperature as faulty.
- **Trace 2 (wind)** has 14 spans across 6 steps. The final answer says the calmest day was 9 March at 0.94 km/h and
  calls the data trustworthy. It isn't: that is the stuck sensor, and the agent never questioned it.
- **Trace 3 (temperature)** also has 14 spans. Step 2's log prints `-99.9` at 7 March 15:00; step 3 checks it; step 4
  fails with a pandas `KeyError` (visible in the log) and step 5 recovers, ending with "coldest valid reading 3.2 C".

Honest findings from this run, which the traces let you verify:

- The duplicated hour was missed. The true total is 32.5 mm (34.0 mm with the duplicate) and the wettest day is 17.1 mm, not
  18.6 mm. The pandas in trace 1 has no `drop_duplicates`, and you can see that.
- The stuck wind sensor was missed too: the agent reported a calmest day of 0.94 km/h and called the wind data
  trustworthy, even though the sensor read 0.0 for 30 straight hours.
- Of the three planted faults, only the -99.9 temperature dropout was caught (it was flagged in two of the three
  traces). In trace 3 you can watch a `KeyError` at step 4 and the agent's recovery at step 5.
- LLM spans carry token usage (first span of trace 1: 2,125 prompt / 239 completion tokens, model `gpt-4o-mini`), and the
  trace totals roll up (10,714 tokens for trace 1). No cost appears: Opik's `total_estimated_cost` is empty for these
  OTLP spans. The root `CodeAgent.run` span is typed `llm` by the instrumentation, which is a quirk of the
  OpenInference mapping.

Your numbers will drift between runs because the model is not deterministic.

## Run it yourself

1. Start Opik (this example targets a local instance at `http://localhost:5173`; for Opik Cloud, set
   `OPIK_OTEL_ENDPOINT`, `OPIK_API_KEY` and `OPIK_WORKSPACE`).
2. `cp .env.example .env` and fill in `OPENAI_API_KEY` (a `.env` in any parent folder also works).
3. `uv sync`
4. `uv run main.py` (about a minute, a few cents).
5. Open the project above in Opik.
6. Optional, offline: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest` (a few seconds, no keys, no
   network; the tests swap the OTLP exporter for an in-memory one, so `OPIK_TRACK_DISABLE` is belt and braces here).

## Poke around

- Add a fourth question: "Are any of these readings untrustworthy?" and see whether it finds the stuck wind sensor.
- Tell the briefing to "check for duplicated timestamps first" and re-run; compare the rain total and the code in the
  first `generate` span.
- Swap in `gpt-4.1-mini` and compare step counts and token usage across traces.
- Run `uv run make_data.py` to regenerate the CSV, move the faults around, and see which ones the agent catches.

## Gotchas we hit

- **The project stays empty, or the last trace is missing, even though the script exited 0.** The OpenTelemetry
  `BatchSpanProcessor` queues finished spans and exports them on a timer (5 s by default), so a script that ends first
  drops them. Call `provider.force_flush()` and `provider.shutdown()` at the end of `main()`, as this example does.
  `tests/test_tracing.py` shows the queue holding spans until the flush.
- **Token usage is there but cost is empty.** Spans arriving over OTLP from OpenInference carry `llm.token_count.*`
  and the model name, yet Opik's `total_estimated_cost` stayed empty for `gpt-4o-mini` in this run. Don't wait for a
  cost column: compute cost yourself from the usage on the `generate` spans, or use an SDK-based integration when
  you need Opik's cost estimates.
- **The root `CodeAgent.run` span shows up typed `llm`.** OpenInference marks that span as an agent
  (`openinference.span.kind=AGENT`, visible in `tests/test_tracing.py`'s spans), but Opik's mapping of
  OpenInference attributes typed it `llm` in this run, so filtering by type `llm` returns the three roots as well as
  the `generate` spans. Filter by span name (`OpenAIModel.generate`) when you want only model calls.

## How it's put together

- `main.py`: OTLP setup, instrumentation, the agent and the three questions; flushes the tracer provider on exit.
- `make_data.py`: deterministic generator for the committed CSV.
- `data/readings.csv`: the fictional readings with planted faults.
- `tests/conftest.py`: offline setup: fake OpenAI key, no `.env`, and an in-memory stand-in for the OTLP exporter.
- `tests/test_data.py`: the generator reproduces the committed CSV; the three planted faults are there.
- `tests/test_tracing.py`: endpoint and headers (workspace, project name, no `Authorization` locally), a stubbed
  agent run under instrumentation, and why the flush matters.
- `pyproject.toml`: dependencies, with `opik` pinned for tooling parity. The trace path itself uses OpenTelemetry only.
- `.env.example`, `.gitignore`: config template and ignores.

*built with Opik · inspired by Opik's examples and documentation*
