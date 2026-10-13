# ollama-astronomy-log-rag

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/ollama-llama3.2%3A1b-grey?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2.99-2f54eb?style=flat)](https://github.com/comet-ml/opik)

**A logbook assistant for a stargazing club that runs entirely on your laptop, with every step visible in Opik and no cloud LLM calls.**

A 1-billion-parameter model is cheap and private, but it gets things wrong, and you only find that out if you can see what it was shown and what it said. This example answers questions about the fictional Marlowe Ridge Astronomy Club's observing logs (dates, targets, seeing, equipment, sky-quality readings) using Ollama through LangChain. No API key is needed anywhere. Opik records each question as a trace so you can check the model's answer against the exact excerpts it was handed.

## What you'll build

A small Python package, `astrolog/`, with a CLI:

- `ingest` lists the log entries that will be embedded (one chunk per session entry, 8 in total across `docs/`).
- `ask "<question>"` answers one question.
- `demo` runs four scripted questions, one of which the model gets wrong.

Embeddings come from `nomic-embed-text`, answers from `llama3.2:1b`, and vectors live in an in-memory store. Retrieval is wrapped in a function decorated with `@opik.track(type="tool")`, so it always appears as its own named tool span. Local models report no token usage through LangChain, so Opik shows no tokens or cost here. The lesson is tracing, not spend.

## See it in Opik

Open the project **ollama-astronomy-log-rag**. After one `demo` run it holds **4 traces**, all named `ask_the_logbook`. Open any one:

- The tree has 7 spans: `RunnableParallel<context,question>`, `RunnablePassthrough`, two spans called `search_observing_logs`, `ChatPromptTemplate`, `ChatOllama` (type `llm`) and `StrOutputParser`.
- Pick the `search_observing_logs` span of type **tool**. Its input is the question. Its metadata lists the two log entries that were retrieved (e.g. `2026-07-18 - Milky Way and Sagittarius`) and `k: 2`. Its output is the full text handed to the model. The second `search_observing_logs` span, type general, is LangChain's own wrapper around the same call.
- The `ChatOllama` span holds the final prompt and the answer. Usage and cost columns are empty, as explained above.

Where the small model slips: for "What equipment did Jonas Okafor use at Cedar Hollow, and which filter?" retrieval was fine. The excerpt says *10-inch Dobsonian ... OIII filter*, yet the model replied "an 8-inch telescope ... but I do not know what filter he was using". The mistake is in the model, not the retrieval, and the tool span versus the `ChatOllama` span makes that obvious. The Saturn answer also embellishes slightly: it adds "minimal light pollution" to the seeing score of 5/5. The Perseid answer is right on the count (47) but garbles the sentence. The "darkest sky" question is answered correctly (2026-07-18, 21.8 mag/arcsec^2).

## Run it yourself

Needs Python 3.12+, [uv](https://docs.astral.sh/uv/), a running Ollama with the two models, and an Opik instance configured for the Python SDK (`~/.opik.config` or `OPIK_URL_OVERRIDE` / `OPIK_WORKSPACE`).

1. `ollama pull llama3.2:1b && ollama pull nomic-embed-text`
2. `cd ollama-astronomy-log-rag`
3. Optional: `cp .env.example .env` (set `OLLAMA_BASE_URL` if Ollama is not on `localhost:11434`).
4. `uv run astrolog ingest`
5. `uv run astrolog demo` (about 25 seconds on the machine used here)
6. `uv run astrolog ask "Who attended the Perseid watch?"`
7. Offline tests (no Ollama, no Opik, no keys): `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- Change `TOP_K` in `astrolog/config.py` to 1 or 4 and compare the retrieved `entries` metadata across traces.
- Ask something the logs do not cover ("What did Priya see on Mars?") and see whether the model admits it.
- Swap `CHAT_MODEL` for a larger local model and rerun the Jonas question.
- Remove the `@opik.track` line in `retrieve.py` and see what the tree looks like without the dedicated tool span.

## Gotchas we hit

- **Usage and cost columns are empty on the `ChatOllama` span.** Opik's LangChain integration only has usage extractors for OpenAI, Anthropic, Google, Vertex, Groq and Bedrock (checked in opik 2.2.99), and Ollama through LangChain reports none of those shapes, so there are no tokens and no cost. That is expected for a local model; nothing to fix.
- **`search_observing_logs` shows up twice in the tree.** The decorated function is put into a LangChain chain, which wraps it as a runnable: one span is your `tool` span (with the `entries` and `k` metadata), the other is LangChain's `general` wrapper. Open the one typed `tool`.
- **`ChatPromptTemplate` is typed `tool`.** The tracer maps LangChain's `prompt` run type to a `tool` span (`get_span_type` in `opik/integrations/langchain/run_parse_helpers.py`), so filtering the project by span type `tool` also returns the prompt step. Filter by the name `search_observing_logs` instead.

## How it's put together

- `astrolog/config.py`: project name, model names, Ollama URL, top-k.
- `astrolog/ingest.py`: splits each markdown log into one document per `##` entry.
- `astrolog/store.py`: builds the in-memory vector store with `OllamaEmbeddings`.
- `astrolog/retrieve.py`: the `@opik.track(type="tool")` retrieval function.
- `astrolog/answer.py`: prompt, `ChatOllama` and the LangChain chain.
- `astrolog/cli.py`: `ingest`, `ask`, `demo`; attaches `OpikTracer` and flushes.
- `tests/conftest.py`: fake embeddings and a fake chat model, swapped in by monkeypatch so Ollama is never called.
- `tests/test_astrolog.py`: chunking of `docs/`, the traced retrieval function with tracking disabled, the chain with fakes, CLI parsing and `OLLAMA_BASE_URL`.
- `docs/`: fictional club logs and equipment roster.

*built with Opik · inspired by Opik's examples and documentation*
