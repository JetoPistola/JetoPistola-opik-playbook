# langgraph-postmortem-team

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/langgraph-1.x-1C3C3C?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2.99-2f54eb?style=flat)](https://github.com/comet-ml/opik)

*Three agents, one outage, one trace that shows who did what and what it cost.*

After an outage someone has to read logs, alerts, deploy history and a noisy chat
channel, then write it up without pointing fingers. This example hands that job to
a small LangGraph team for a made-up incident at a made-up company (Brightwharf
Ledger, card checkout returning 503s for about 30 minutes). The point is
observability: when a multi-agent run gives a questionable write-up, you want one
trace where the plan, each investigation pass and the draft are separate, costed steps.

## What you'll build

A graph with a **lead**, an **investigator** that loops, and a **writer**, all on `gpt-4o-mini`.

- The lead reads the incident brief and chooses which evidence files to examine, with a focus for each (structured output, capped at 4).
- The investigator takes one task per pass and reads one file from `data/`: `logs.md`, `alert-timeline.md`, `deploy-history.md`, `chat-transcript.md`. A conditional edge sends it around again until every task has notes.
- The writer drafts a blameless post-mortem: summary, timeline, root cause, contributing factors, action items.

The compiled graph is passed through `track_langgraph` with an `OpikTracer`, so the whole run is logged as a single trace and Opik can draw the agent graph.

## See it in Opik

Open the **langgraph-postmortem-team** project, Traces tab. A clean run leaves exactly one trace (named `LangGraph`, about 19 seconds, 4,320 tokens, about $0.00135). Open it:

- The span tree has 18 spans: 12 general spans (one per node pass, plus the router and the chain wrappers LangChain emits) and 6 `llm` spans. In order: `lead`, then four `investigator` passes (each followed by a `route` decision), then `writer`. Each node span contains its `ChatOpenAI` span with the exact prompt and completion.
- Switch to the graph view of the trace: the lead -> investigator self-loop -> writer structure is drawn from the graph the tracer was given.
- Cost by agent, summed from the LLM spans' estimated cost in my run: lead $0.00011 (368 tokens), four investigator passes $0.00073 (2,295 tokens), writer $0.00051 (1,657 tokens). Every LLM span has usage and a non-null estimated cost.

The write-up itself is a fair thing to inspect: in my run the writer misplaced a couple of timeline entries (it put the canary at 14:04 and the rollback completion at 14:35, which the evidence does not say). Click from the writer span back through the investigator notes to see where the drift started.

## Run it yourself

1. `cd langgraph-postmortem-team`
2. Put `OPENAI_API_KEY` in a `.env` (copy `.env.example`) in this folder or any parent folder.
3. Point the SDK at Opik: `opik configure` (local self-hosted needs no key; Cloud needs `OPIK_API_KEY` and `OPIK_WORKSPACE`).
4. `uv run main.py`

A run takes about 20 seconds and costs under a cent.

Offline tests (no keys, no Opik, a fake chat model; they cover evidence loading, the
`MAX_INVESTIGATIONS` cap, routing and a full graph run through the tracked graph):

```
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest
```

## Poke around

- Add a fifth file to `data/` and see whether the lead picks it up; raise `MAX_INVESTIGATIONS` and watch the loop grow and the cost split shift.
- Edit `deploy-history.md` to remove the line about the config default and see what the writer does with the missing root cause.
- Change the writer's model and compare its per-node cost in the trace.
- Drop `MAX_INVESTIGATIONS` to 2: the loop in the graph view shortens, two evidence files go unread, and you can check whether the post-mortem admits the gap or papers over it.

## Gotchas we hit

- **Symptom:** you look for a root span in the trace's span tree, or filter spans by `parent_span_id is None` expecting one row, and instead find six top-level spans (`lead`, four `investigator`, `writer`). **Cause:** the LangGraph tracer does not open a root span; each node span sits directly under the trace, and the trace itself (named `LangGraph`) is the root. **Fix:** treat the trace as the unit. Fetch spans with `client.search_spans(project_name=..., trace_id=trace.id)` and read the node spans as the top level; the `route` and `ChatOpenAI` spans are their children.

## How it's put together

- `main.py` - state, the three agents, router, graph wiring, tracer, entry point.
- `tests/conftest.py` - dummy key, tracking switched off, and a fake chat model swapped in for `main.llm`.
- `tests/test_postmortem.py` - evidence loading, the investigation cap, routing, and a full graph run with tracking disabled.
- `data/` - four fictional evidence files for incident INC-2291.
- `pyproject.toml` - dependencies (opik pinned to 2.2.99) and pytest as a dev dependency.
- `.env.example`, `.gitignore` - key template and ignores.

*built with Opik · inspired by Opik's examples and documentation*
