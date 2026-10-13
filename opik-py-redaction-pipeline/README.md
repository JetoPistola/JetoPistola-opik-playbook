# opik-py-redaction-pipeline

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![Opik](https://img.shields.io/badge/opik-2.2.99-2f54eb?style=flat)
![OpenAI](https://img.shields.io/badge/model-gpt--4o--mini-412991?style=flat&logo=openai&logoColor=white)

*A redaction pipeline that scrubs four fictional documents, traced with nothing but the low-level Opik client, and a verifier that happily passes documents that still leak.*

## The problem

Redacting personal data is a pipeline: a cheap regex pass, an LLM for the contextual stuff, a redactor, and a check at the end. When it leaks, you need to know which stage was blind, and "the verifier said pass" is not an answer. This app builds exactly that pipeline for a volunteer roster, a rental inquiry, a clinic phone note and a facilities email, and instruments it without `@opik.track` and without `track_openai`. Every trace, span, usage block and feedback score is one explicit call on `opik.Opik()`, so you see precisely what the decorators and wrappers normally do for you.

## What you'll build

For each file in `data/`, one `redact-document` trace:

```
redact-document                       trace
  ├─ regex-detector                   guardrail   emails, 555-xxxx phones, ID numbers
  ├─ contextual-detector              general
  │    └─ chat gpt-4o-mini            llm         model, provider, tokens recorded by hand
  ├─ redactor                         tool        swaps findings for [NAME], [ADDRESS], ...
  └─ verifier                         guardrail   re-runs the regexes on the output
```

After redaction, the script compares each output to `data/ground_truth.json` and logs two feedback scores per trace with `client.log_traces_feedback_scores(...)`: `redaction_recall` and `leaked_pii_count`. The scores arrive after the traces, which is the whole point: they come from knowledge the pipeline itself does not have.

## See it in Opik

Open the `opik-py-redaction-pipeline` project. The Traces tab lists four `redact-document` traces (one per file), each with two feedback-score columns. In the run described here:

| file | recall | leaked |
|---|---|---|
| `appointment_note.txt` | 0.86 | `five five five, oh one four two` (a phone number spelled out in words; the regex wants digits, the LLM prompt excluded phones) |
| `rental_inquiry.txt` | 0.83 | `Ellis Thackeray` (a manager's name, buried mid-sentence) |
| `volunteer_roster.txt` | 0.92 | `KRT-4471` (a licence plate; neither detector has a category for it) |
| `incident_email.txt` | 1.00 | nothing to leak, and nothing wrongly removed |

Click any trace and look at the **verifier** span: it says `passed: true` on all four, including the three that leak. It only re-runs the regexes, so it confirms the shapes it knows about are gone and is blind to the rest. The feedback scores are what expose it.

Expand a trace. Each has five spans in the shape above, with `chat gpt-4o-mini` nested under `contextual-detector` (the parent link is explicit, not inferred). The llm span shows model `gpt-4o-mini-2024-07-18`, provider `openai`, and token usage (for example 241 prompt and 120 completion tokens on the clinic note), and the span has a non-null `total_estimated_cost` that Opik computed server-side: $0.000108 for the clinic note, $0.000033 for the clean email, $0.000104 for the rental inquiry, $0.000149 for the roster. All four documents together cost about $0.0004. The `redactor` span's output is the redacted text, so you can read the leak in context.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY` (or use a repo-root `.env`, which the script finds by walking up). Point the SDK at your Opik with `opik configure`, or set `OPIK_URL_OVERRIDE` / `OPIK_API_KEY` / `OPIK_WORKSPACE`.
2. `uv sync`
3. `uv run main.py` (about 12 seconds)
4. Open the `opik-py-redaction-pipeline` project in Opik.
5. Optional, no keys and no Opik needed: `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- **Lose the batch.** `uv run main.py --no-flush` skips `client.flush()` and hard-exits. In my test only 3 of the 4 traces reached Opik (the SDK's background sender ships batches on its own schedule, so the loss is partial and timing-dependent) and none of the feedback scores did. A short-lived script that never flushes is a gamble; the app flushes before logging scores, then again after.
- **Leave spans open.** `uv run main.py --no-end` sends spans and traces without an `end_time`. They still arrive, but every duration is blank (`None`) in the trace list and the spans never read as finished. This is what a crash between "start" and `end()` looks like.
- **Close the gap.** Add a `plate` entry to the `PATTERNS` regexes or add "licence plate" to the system prompt, rerun, and watch `KRT-4471` drop out of the leaked list and the roster recall reach 1.00. Note that the verifier still says nothing different.
- **Break the usage block.** Remove `model=`/`provider=`/`usage=` from the llm span and the cost column goes empty: Opik computes cost from those three fields alone.

## Gotchas we hit

- **Symptom: a log full of "Calling ... shortly after creation with batching enabled may cause data loss".** Cause: creating a span and then calling `update()` or `end()` on it milliseconds later races the SDK's batching queue (the warning text is in `opik/logging_messages.py` of the pinned 2.2.99). Fix: do the work first, then create each span once, complete, with `start_time`, `end_time`, output and usage in the same `trace.span(...)` call. Generate ids up front with `opik.id_helpers.generate_id()` so `parent_span_id` and `id=` still link the tree.
- **Symptom: only 3 of 4 traces show up and no feedback scores.** Cause: the SDK ships data from a background thread, and a script that exits without `client.flush()` abandons whatever is still queued (reproduce it with `--no-flush`; how many survive is timing-dependent). Scores also need their traces to exist first. Fix: `client.flush()`, then `client.log_traces_feedback_scores(...)`, then flush again.
- **Symptom: spans are in Opik but the duration column is blank.** Cause: no `end_time` was sent (reproduce with `--no-end`; a crash between start and `end()` looks the same). Fix: pass `end_time=` when you create the span or trace.
- **Symptom: you set `OPIK_TRACK_DISABLE=true` and expected nothing to be sent.** Cause: in 2.2.99 that flag is read by the tracing runtime used by `@opik.track`, integrations and `opik_context`; `opik.Opik().trace(...)` and `.span(...)` never consult it, so hand-made traces would still be sent. Fix: the tests replace `main.client` with a recording spy, so they send nothing whatever the flag says; in your own code, guard the calls yourself if you need an off switch.

## How it's put together

- `main.py`: the whole app. Pipeline stages, every hand-written trace/span call, the ground-truth scoring and the flush.
- `data/*.txt`: four fictional documents.
- `data/ground_truth.json`: the PII each document actually contains, used only for scoring.
- `tests/conftest.py`: sets a dummy `OPENAI_API_KEY` and `OPIK_TRACK_DISABLE=true` before `main` is imported (it builds both clients at import).
- `tests/test_pipeline.py`: offline tests with a stubbed OpenAI client: regex detector, redactor, the verifier's blind spot, recall/leak scoring against `data/ground_truth.json`, and the span tree (types, parenting, usage) captured by a spy in place of the Opik client.
- `pyproject.toml`, `.env.example`, `.gitignore`: dependencies (opik 2.2.99, openai, python-dotenv; pytest as a dev group) and config.

A note on structure: spans are created once, complete, after their work finishes (with `start_time`, `end_time`, output and usage in the same call), and parent ids are generated up front. Creating a span and then calling `update()` / `end()` on it milliseconds later makes the SDK warn that batching may drop data, so this version avoids that pattern.

*built with Opik · inspired by Opik's examples and documentation*
