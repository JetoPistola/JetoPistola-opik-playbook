# llamaindex-syllabus-pdf-qa

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-callback%20integration-6a4c93?style=flat)
![Opik](https://img.shields.io/badge/Opik-2.2.99-2f54eb?style=flat)

*Ask three course syllabi about late work, then prove each clause with a test suite.*

Students ask the same questions every term: how much is the final worth, what happens if I hand it in a day late, when are office hours. Policies differ by course, so a chatbot that grabs the wrong syllabus gives a confident wrong answer ("10% per day" when this course says a flat 15%). This project answers those questions over three generated syllabus PDFs from a fictional Larkspur Community College, and uses Opik to show both how each answer was made and whether each clause is stated correctly.

## What you'll build

A small Python package (`syllabus_qa`) with a CLI. It writes three syllabus PDFs (BIO 101, MAT 120, ENG 110), indexes them with LlamaIndex using `text-embedding-3-small`, and answers with `gpt-4o-mini`. Tracing is one line, `set_global_handler("opik")`. Then it runs a clause-level Opik test suite: nine questions, each asserting a specific policy ("BIO 101 late work loses 10% per day, accepted for a maximum of 3 days"), plus one global assertion that the answer invents nothing outside the retrieved excerpts. Every item runs 3 times and must pass at least 2.

## See it in Opik

Open the project `llamaindex-syllabus-pdf-qa`. In my run it held 33 traces:

- **4 `query` traces** from the demo questions. Open one and expand it: a `retrieve` span containing an `embedding` span (the question vectorized, with the three syllabus chunks fetched as output), and a `synthesize` span containing `chunking`, `templating` and an `llm` span. The `llm` span (`gpt-4o-mini`) shows the prompt with the retrieved clauses stitched in, the answer, token usage and an estimated cost. If an answer is wrong, this tree tells you whether retrieval grabbed the wrong syllabus or the model misread the right one.
- **27 `evaluation_task` traces**: 9 suite items x 3 runs, each holding the same `query` tree plus the judge's work.
- **2 `index_construction` traces** for building the vector index (the default command builds it once for the demo and once for the suite).

All 58 `llm` spans carry usage and a non-null estimated cost; the whole run cost about $0.010 (31 `gpt-4o-mini` calls plus 27 judge calls on `gpt-5-nano`).

Then open Experiments, dataset `syllabus-clauses`. There is one experiment: 9 of 9 items passed (pass rate 100%, 27 runs). The per-assertion table shows each clause with its own pass count, for example "ENG 110 gives one 72-hour penalty-free grace extension per semester: 3/3". The suite is the useful part: when you change a syllabus or the retriever, the assertion that breaks names the clause, not just "answer quality dropped". A judge is an LLM and can wobble, which is what the 3-runs-pass-2 execution policy absorbs.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY` (or rely on a repo-root `.env`). For local Opik no other keys are needed; otherwise run `opik configure`.
2. `uv sync`
3. `uv run syllabus-qa` does everything (rebuild PDFs, four demo questions, the suite). Or step by step:
   - `uv run syllabus-qa build` regenerate the PDFs in `data/syllabi/`
   - `uv run syllabus-qa ask "How late can I submit ENG 110 essays?"`
   - `uv run syllabus-qa suite`
4. Open the project in Opik and click the newest `query` trace.
5. Offline tests (no keys, no Opik): `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`. `OPIK_TRACK_DISABLE=true` is the SDK's switch for turning tracking off.

The PDFs are committed (about 2.5 KB each) and also regenerated on demand if missing.

## Poke around

- Ask something no syllabus covers ("Is there a dress code in the lab?") and read the retrieved chunks in the trace; the answer should say it doesn't know.
- Change `TOP_K` in `syllabus_qa/config.py` from 3 to 1 and run `suite`: questions that need the right course's chunk are the first to fail.
- Edit the BIO 101 late-work clause in `corpus.py` (say, 15% per day), run `build`, then `suite`: only the assertions pinned to the old number should fail.
- Add an assertion to `ITEMS` in `suite.py`; it costs one sentence.

## Gotchas we hit

**Two `index_construction` traces after one run.** The default `uv run syllabus-qa` command shows 2 `index_construction` traces next to the `query` ones. Cause: the demo step and the suite step each call `build_query_engine()`, and every call re-embeds the PDFs, so the global handler records a build each time. Fix: that is expected for the default command; if you want a single build, run `ask` or `suite` on its own, or build the engine once and pass it to both steps (`build_query_engine(index)` accepts an existing index).

## How it's put together

- `syllabus_qa/config.py` - project name, paths, `.env` loading, Opik handler and model setup.
- `syllabus_qa/corpus.py` - generates the three syllabus PDFs with reportlab.
- `syllabus_qa/index.py` - loads PDFs and builds the LlamaIndex vector index and query engine.
- `syllabus_qa/qa.py` - the prompt, demo questions, and `ask()` returning answer plus excerpts.
- `syllabus_qa/suite.py` - the clause-level test suite and its run.
- `syllabus_qa/cli.py` - `build`, `ask`, `suite`, or all three by default.
- `tests/conftest.py` - turns Opik tracking off before anything imports it.
- `tests/test_corpus.py` - the PDFs are present, valid and state the four policies.
- `tests/test_cli.py` - subcommand parsing and dispatch.
- `tests/test_suite_items.py` - shape and coverage of the nine clause items and the global assertion.
- `tests/test_qa.py` - `ask()` over a mock LLM and mock embeddings, including a query with the Opik handler installed and tracking disabled.
- `data/syllabi/` - the generated PDF corpus.

---

*built with Opik · inspired by Opik's examples and documentation*
