# Reading-Level Router

**`litellm-reading-level-router`**: one rewrite job, two providers, and a cost-and-latency table that Opik and your terminal agree on.

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LiteLLM](https://img.shields.io/badge/litellm-1.79%2B-1C7ED6?style=flat)
![Opik](https://img.shields.io/badge/Opik-2.2.99-2f54eb?style=flat)

Suppose you publish explainers and want each one rewritten for a child, a teenager and a general adult audience. Two models can do it, so which should you route to? "Cheaper" and "faster" are claims you can only make with numbers measured on your own prompts. This example sends three short fictional passages through three reading levels (nine prompts) to `gpt-4o-mini` and `claude-haiku-4-5` via LiteLLM, logs every call to Opik, and prints a per-model summary that you can check against Opik's table.

## What you'll build

A single script, `main.py`. It reads `data/passages.json` (a tide-pool explainer, a bridge-restoration news item, a sourdough primer) and, for each model, asks for a rewrite aimed at an 8-year-old, a 12-year-old and an adult. LiteLLM makes the provider a plain string. Tracing is Opik's `OpikLogger` callback added to `litellm.callbacks`. Each call is tagged with the model, the reading level and the passage id. At the end the script prints totals per model plus mean words-per-sentence by level, a cheap readability signal.

## See it in Opik

Open the **`litellm-reading-level-router`** project on the Traces tab. One run leaves 18 traces, each holding a single `llm` span (no orphans, no nesting). Filter by the tag `gpt-4o-mini-2024-07-18` or `claude-haiku-4-5-20251001`, or add the provider/model columns, and compare:

| Model (as Opik reports it) | Calls | Tokens | Total estimated cost | Mean latency |
|---|---|---|---|---|
| gpt-4o-mini-2024-07-18 | 9 | 1792 | $0.000581 | 1.62 s |
| claude-haiku-4-5-20251001 | 9 | 2044 | $0.005312 | 1.44 s |

Those numbers are each span's `total_estimated_cost` summed per model, and they match the table the script prints. Haiku cost about 9x more on this workload yet was slightly faster. Open a Haiku trace for the age-8 rewrite and you will notice it often starts with a markdown `# Heading` that the OpenAI output does not have, a quirk invisible in an aggregate but obvious one click away.

## Run it yourself

1. Have Opik reachable (`opik configure`, or a local self-hosted instance).
2. `cp .env.example .env` and add `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.
3. `uv sync`
4. `uv run main.py` (about 45 seconds, well under a cent)
5. Open the project above in Opik and filter the Traces table by model.
6. Optional offline tests (no keys, no Opik): `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- Add `"Reply with plain text, no headings"` to the prompt and see whether Haiku's token count and cost drop.
- Sort Traces by duration, then by cost. The two rankings disagree here.
- Add a third model string to `MODELS` (any LiteLLM-supported one) and re-run; the new model appears as another row group with no other code change.
- Edit `data/passages.json` with your own paragraphs, or add a fourth level to `LEVELS`.

## Gotchas we hit

**A `RuntimeWarning: coroutine 'CustomBatchLogger.periodic_flush' was never awaited` prints at startup.** `OpikLogger.__init__` tries `asyncio.create_task(self.periodic_flush())`; in a plain synchronous script there is no running event loop, so the task is never created. Seen with litellm 1.105.0 and opik 2.2.99. It is harmless: traces still arrive, because the script ends with `opik.flush_tracker()`. Ignore it, or silence it with `warnings.filterwarnings("ignore", message=".*periodic_flush.*")` before constructing `OpikLogger()`.

## How it's put together

- `main.py`: the router loop, OpikLogger setup, and the summary table.
- `tests/test_router.py`: offline tests with `litellm.completion` monkeypatched; they cover passage loading, prompt and tag building, the zero-cost fallback and the summary table.
- `tests/conftest.py`: puts the example folder on the import path.
- `data/passages.json`: three fictional source passages.
- `pyproject.toml`: dependencies (LiteLLM, `opik==2.2.99`, python-dotenv), managed with uv.
- `.env.example`: the provider keys the script reads.

---

*built with Opik · inspired by Opik's examples and documentation*
