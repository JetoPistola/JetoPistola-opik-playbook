# Library Chat Widget with FastAPI and LangChain

**`langchain-fastapi-library-chat`** — a book-recommendation chat API whose conversations read like transcripts in Opik.

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat&logo=fastapi&logoColor=white)
![Opik](https://img.shields.io/badge/opik-2.2.99-2f54eb?style=flat)

A chat widget talks to your backend one HTTP request at a time. Without a conversation key, a patron's four-question chat is four unrelated rows in your tracing tool. This example is the backend for the (fictional) Maple Street Public Library's "Ask Dewey" widget: patrons describe what they feel like reading and Dewey recommends books from a small catalog, honestly reporting what is checked out.

## What you'll build

A FastAPI app with `POST /chat` taking `{message, conversation_id}`. Each request runs a LangChain chain: a step that searches `data/catalog.json` (14 invented books), a prompt that includes the matches plus the conversation so far, `gpt-4o-mini`, and a string parser. The chain takes a plain string and returns a plain string, so each trace's input is literally what the patron typed and its output is what Dewey said. An `OpikTracer(thread_id=conversation_id)` is created per request. The catalog search is a function decorated with `@opik.track(type="tool")` so it always shows up as its own span.

`uv run main.py` boots the server on `127.0.0.1:5302`, plays four scripted patrons (11 turns) over real HTTP, stops the server and flushes traces. Nothing keeps running afterwards.

## See it in Opik

Open the project **`langchain-fastapi-library-chat`**. The **Threads** tab lists four threads: `patron-cozy-mystery` (3 turns), `patron-sci-fi-crew` (3), `patron-nature-walks` (3) and `patron-kids-and-cooking` (2). Open one and you get a chat transcript: patron message, Dewey's reply, next message. Try `patron-cozy-mystery`: Dewey recommends *The Lantern Keeper's Daughter* (3 copies), confirms it is on the shelf, then offers a hold on *Salt and Cipher* because every copy is checked out. In `patron-sci-fi-crew`, the last question ("anything on dragons?") gets an honest "not in the excerpts" rather than an invented title.

In the **Traces** tab there are 11 traces named `library-chat-turn`, one per turn. Their input is the patron's text and their output is the reply, with no chain internals dumped into the columns. Open one: you see `prepare-context` containing a `search_catalog` tool span (the retrieved books), then `ChatPromptTemplate`, `ChatOpenAI` (an `llm` span with tokens and cost) and `StrOutputParser`. The whole run cost about $0.00075 in total, from `total_estimated_cost`.

## Run it yourself

1. `cd langchain-fastapi-library-chat`
2. `cp .env.example .env` and set `OPENAI_API_KEY` (a repo-root `.env` also works). For local Opik set `OPIK_URL_OVERRIDE=http://localhost:5173/api/`; for Cloud set `OPIK_API_KEY`.
3. `uv run main.py`
4. `uv run python verify.py` prints trace, span and thread counts from Opik.
5. Offline tests (no keys, no Opik): `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`. `OPIK_TRACK_DISABLE=true` makes `@opik.track` and `OpikTracer` send nothing.
6. Interactive use: `uv run uvicorn library_chat.server:app --port 5302`, then
   `curl -s localhost:5302/chat -H 'content-type: application/json' -d '{"message":"cozy mystery please","conversation_id":"me-1"}'`

## Poke around

- Reuse a `conversation_id` across two curl calls, then use a new id: the first becomes one thread, the second a fresh one with no memory.
- Remove `@opik.track` from `search_catalog` and compare the trace tree: is the retrieval still visible?
- Ask for something absent ("a book about dragons") and read the `search_catalog` output next to the reply to see what Dewey was actually given.
- Change `chain.invoke(req.message, ...)` to pass a dict and look at what the Threads transcript becomes.

## Gotchas to watch for

**The `ChatPromptTemplate` span shows up with type `tool`, next to `search_catalog`.** With `opik==2.2.99` the LangChain integration maps LangChain's `prompt` runs to the `tool` span type (see `get_span_type` in `opik/integrations/langchain/run_parse_helpers.py`), so a filter on type `tool` returns two spans per turn, not one. Nothing to fix: filter on the name `search_catalog` when you only want the retrieval, and expect the prompt span to carry the formatted messages.

**The root run is a bare string, and LangChain hands the tracer `{'input': ...}` / `{'output': ...}`.** A chain that takes a plain string and returns a plain string reaches `OpikTracer` as `{'input': 'cozy mystery please'}` and `{'output': '...'}` (checked by overriding `_finalize_trace`). Keep the chain string-in, string-out, as `chain.invoke(req.message, ...)` does here, so the only thing in those one-key payloads is the patron's text and Dewey's reply. Passing a multi-key dict instead puts every key into that payload (see the last "Poke around" item).

## How it's put together

- `main.py` — entry point for the scripted run.
- `library_chat/server.py` — FastAPI app, chain, per-conversation memory, per-request `OpikTracer`.
- `library_chat/catalog.py` — keyword retriever with the `@opik.track(type="tool")` span.
- `library_chat/demo.py` — starts uvicorn on 5302, plays the conversations, shuts down, flushes.
- `tests/conftest.py` — offline setup: fake key, tracking disabled, the chat model swapped for a recording stub.
- `tests/test_catalog.py` — retrieval ranking, empty results and availability formatting (calls the traced `search_catalog` with tracking off).
- `tests/test_chat.py` — string-in/string-out chain and the `/chat` endpoint through FastAPI's `TestClient`.
- `data/catalog.json` — the invented catalog.
- `verify.py` — queries Opik for traces, spans and threads.

---

*built with Opik · inspired by Opik's examples and documentation*
