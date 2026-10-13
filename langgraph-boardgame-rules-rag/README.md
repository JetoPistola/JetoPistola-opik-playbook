# langgraph-boardgame-rules-rag

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.x-1C3C3C?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2.99-2f54eb?style=flat)](https://github.com/comet-ml/opik)

**A rules referee for four invented board games, where you can see which rule it looked up and score whether it made one up.**

Everyone at a game night has met the confident person who "remembers" a rule that is not in the book. LLM rulebook assistants fail the same way, and a fluent answer tells you nothing about whether it came from the right page. This example answers questions over four fictional rulebooks (Lantern Harbor, Obsidian Crown, Moss & Mushroom, Clockwork Couriers) with a two-node LangGraph graph, traces every step in Opik, then runs an experiment that grades the pipeline.

## What you'll build

- `retrieve` node: embeds the question (`text-embedding-3-small`) and picks the top 3 rule sections from an in-memory vector store. The search itself is a named `@opik.track(type="tool")` function, `search_rulebooks`, so it is always visible as its own span.
- `generate` node: `gpt-4o-mini` answers using only those excerpts, or says the rulebooks do not cover it.
- `OpikTracer` attached once via `track_langgraph`, so every graph call becomes a trace.
- A 6-question dataset and an `evaluate()` run scored by `Hallucination` and `ContextPrecision`.

## See it in Opik

Open the `langgraph-boardgame-rules-rag` project. After one run it holds 10 traces: 4 live questions (each trace named `LangGraph`) and 6 `evaluation_task` traces from the experiment.

- **A trace.** Expand any one. You get `retrieve` containing a `search_rulebooks` tool span (its output is the three rule sections, each tagged like `[Obsidian Crown]`), followed by `generate` containing a `ChatOpenAI` LLM span with the full prompt, token usage and estimated cost. In my run, "Is there a Lantern Harbor expansion with pirates?" retrieved unrelated Lantern Harbor sections and the model replied that the rulebooks don't cover it.
- **The experiment.** Go to Experiments and open `rules-baseline-k3` (dataset `langgraph-boardgame-rules-rag`). All 6 items scored `hallucination_metric` 0.00 and `context_precision_metric` 1.00 in the final run. (An earlier run of the same code gave a 0.97 precision average, so judge scores wobble slightly between runs.) Clicking a row jumps to its trace.

Per run: about 94 spans, with 22 LLM-type spans carrying usage and cost; the judge metrics appear as extra `completion` spans.

## Run it yourself

1. Install [uv](https://docs.astral.sh/uv/) and make sure Opik is reachable (`opik configure`, local or cloud).
2. `cp .env.example .env` and add `OPENAI_API_KEY` (a `.env` further up the tree also works).
3. `uv run main.py`
4. Open the project above in Opik.

A run takes about a minute and costs a few cents. `uv run python verify.py` prints trace, span, dataset and experiment counts.

Offline tests (no provider keys, no Opik; fake embeddings and a fake chat model, `OPIK_TRACK_DISABLE=true`):

```
env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest
```

## Poke around

- Set `TOP_K=1` (`TOP_K=1 uv run main.py`) and compare experiment `rules-baseline-k1` with `k3`.
- Edit `docs/lantern-harbor.md` so the game ends on the 9th lantern; the answers repeat it and hallucination stays 0, because the judge checks against retrieved text, not truth.
- Add a question about a game that is not in `docs/`, and read the retrieved sections in the `search_rulebooks` span.
- Swap `gpt-4o-mini` for another model in `main.py` and compare cost per trace.

## Gotchas we hit

- **`ImportError: cosine_similarity requires numpy to be installed` on the first search.** `InMemoryVectorStore` ranks results with numpy, but `langchain-core` does not depend on it, so a clean install can lack it. Add it explicitly: `"numpy>=2.0"` in `pyproject.toml`.
- **A deprecation warning about `project_name` from `evaluate()`, and experiment traces landing in a different project than you passed.** In `opik==2.2.99` the parameter is deprecated; if the dataset has a project it is always used. Drop the argument and let the dataset's project decide (this example does not pass it).
- **`AttributeError: ... has no attribute 'retrieve_dataset_by_identifier'` when checking from a script.** The REST client method is `client.rest_client.datasets.get_dataset_by_identifier(dataset_name=...)`, as `verify.py` uses.

## How it's put together

- `main.py` - corpus loading, tracked search tool, graph, dataset, experiment.
- `docs/` - four short fictional rulebooks, split on `##` headings.
- `tests/conftest.py` - imports `main` with the OpenAI embeddings and chat classes replaced by fakes.
- `tests/test_rag.py` - chunking, the tracked search tool (tracking disabled), the graph, dataset items and the eval task.
- `verify.py` - queries Opik to confirm what the run produced.
- `pyproject.toml`, `.env.example`, `.gitignore` - setup.

---

*built with Opik · inspired by Opik's examples and documentation*
