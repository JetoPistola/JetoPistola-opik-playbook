<div align="center">

# 📒 The Opik Playbook

**25 small, runnable LLM apps, each one built to make a single [Opik](https://github.com/comet-ml/opik) feature click.**

[![examples](https://img.shields.io/badge/examples-25-6c5ce7?style=flat)](#the-plays)
[![Python](https://img.shields.io/badge/Python-14-3776ab?style=flat&logo=python&logoColor=white)](#the-plays)
[![TypeScript](https://img.shields.io/badge/TypeScript-8-3178c6?style=flat&logo=typescript&logoColor=white)](#the-plays)
[![Java](https://img.shields.io/badge/Java-1-b07219?style=flat)](#the-plays)
[![low-code](https://img.shields.io/badge/low--code-2-ea4b71?style=flat)](#the-plays)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat)](LICENSE)

</div>

---

Docs tell you that Opik records threads, runs test suites, and attaches images to traces. A playbook shows you a bike-shop chatbot whose conversations land as threads, an espresso-machine manual bot whose citations fail a test suite, and nutrition labels sitting next to what a vision model claimed to read from them. Every folder here is a small, self-contained app with a fictional domain and its own offline data. Each one is set up so that the interesting thing, whether a cost gap, a hallucinated field, a retry or a leak, shows up where you can see it in Opik.

Nothing is staged. Every README describes the run that was actually traced, including the parts that went wrong: a 4/6 suite, a stuck sensor the agent missed, a span that has no cost because the integration never sent a model name.

## The plays

### 1 · See what happened: tracing and trace trees

| Example | Stack | What it shows |
|---|---|---|
| [langgraphjs-home-energy-agent](langgraphjs-home-energy-agent) | TypeScript · LangGraph.js + `opik-langchain` | Agent-loop trees with real tool spans, up to a 4-tool chain in one request |
| [crewai-podcast-planner](crewai-podcast-planner) | Python · CrewAI | One trace per crew kickoff, with tokens and dollars broken out per agent |
| [langgraph-postmortem-team](langgraph-postmortem-team) | Python · LangGraph | A planner → investigator loop → writer graph as one deep trace, rendered in the agent-graph view |
| [smolagents-weather-station-analyst](smolagents-weather-station-analyst) | Python · smolagents + OpenInference | The pandas code a CodeAgent wrote and its execution logs, step by step |
| [beeai-py-lab-equipment-triage](beeai-py-lab-equipment-triage) | Python · BeeAI + OpenInference | ReAct LLM and tool spans, including a parser error and the retry that recovered |
| [temporal-py-grant-review](temporal-py-grant-review) | Python · Temporal | One trace spanning two OS processes, with a failed activity attempt and its retry |
| [opik-py-redaction-pipeline](opik-py-redaction-pipeline) | Python · Opik SDK, by hand | Manual spans, hand-recorded usage, after-the-fact feedback scores, flush semantics |

### 2 · Follow a conversation: threads

| Example | Stack | What it shows |
|---|---|---|
| [openai-ts-bike-repair-chat](openai-ts-bike-repair-chat) | TypeScript · OpenAI + `opik-openai` | Three customers, ten turns, cost per turn, and a satisfaction score on each thread |
| [langchain-fastapi-library-chat](langchain-fastapi-library-chat) | Python · LangChain + FastAPI | String-in/string-out root runs, so the Threads view reads like a transcript |
| [vercel-sveltekit-garden-chat](vercel-sveltekit-garden-chat) | TypeScript · SvelteKit + Vercel AI SDK | Streaming spans, threads, and a live LLM-judge rule scoring every reply |
| [dify-gym-membership-assistant](dify-gym-membership-assistant) | Low-code · Dify | Tracing switched on in Dify's settings: one thread, prompt tokens climbing turn by turn |

### 3 · Prove it works: test suites, datasets, experiments

| Example | Stack | What it shows |
|---|---|---|
| [anthropic-ts-espresso-manual-qa](anthropic-ts-espresso-manual-qa) | TypeScript · Anthropic SDK | Plain-English citation assertions; a near-quote caught, 4/6 passing |
| [pydantic-ai-calendar-extraction](pydantic-ai-calendar-extraction) | Python · Pydantic AI (OTel) | A suite that catches invented values in typed extraction, 3/7 passing |
| [llamaindex-syllabus-pdf-qa](llamaindex-syllabus-pdf-qa) | Python · LlamaIndex | Retrieve/synthesize spans plus a clause-by-clause suite over PDFs |
| [langgraph-boardgame-rules-rag](langgraph-boardgame-rules-rag) | Python · LangGraph | A dataset and an experiment scored with Hallucination and ContextPrecision |

### 4 · Ship better prompts: the prompt library and optimization

| Example | Stack | What it shows |
|---|---|---|
| [opik-ts-changelog-prompts](opik-ts-changelog-prompts) | TypeScript · Opik SDK | Two immutable prompt versions; the same suite goes 0/5 → 5/5 |
| [optimizer-app-review-intents](optimizer-app-review-intents) | Python · Opik Agent Optimizer | A score curve from 0.75 to 1.00, with the winning prompt saved to the library |

### 5 · Know what it costs: cost and model comparison

| Example | Stack | What it shows |
|---|---|---|
| [litellm-reading-level-router](litellm-reading-level-router) | Python · LiteLLM | The same job on gpt-4o-mini and Claude Haiku: cost and latency side by side (~9× gap) |
| [voltagent-coworking-desk-agent](voltagent-coworking-desk-agent) | TypeScript · VoltAgent (OTel) | Why `gen_ai.*` attribute names decide whether usage and cost land at all |
| [quarkus-langchain4j-pharmacy-faq](quarkus-langchain4j-pharmacy-faq) | Java · Quarkus + LangChain4j (OTLP) | JVM spans over OTLP, with prompt text, completion, usage and cost on the LLM span |

### 6 · Keep the evidence: images and audio on traces

| Example | Stack | What it shows |
|---|---|---|
| [openai-ts-field-guide-plates](openai-ts-field-guide-plates) | TypeScript · OpenAI images | Generated PNGs attached to traces, and a v1 → v2 prompt brief with a diff |
| [openai-ts-nutrition-label-extraction](openai-ts-nutrition-label-extraction) | TypeScript · OpenAI vision | Label images next to the extracted fields, plus a suite with an honest miss |
| [whisper-vet-voicemail-triage](whisper-vet-voicemail-triage) | Python · OpenAI TTS + Whisper | A playable MP3 on every trace; judge flakiness absorbed by an execution policy |

### 7 · Trace what you didn't write: local and no-code

| Example | Stack | What it shows |
|---|---|---|
| [ollama-astronomy-log-rag](ollama-astronomy-log-rag) | Python · Ollama + LangChain | Full tracing with zero cloud LLM calls and no API key |
| [n8n-foodbank-volunteer-screening](n8n-foodbank-volunteer-screening) | Low-code · n8n | Hook-based tracing with no workflow nodes added; IF branches visible per run |

## Running one

Every example is standalone. Pick a folder and follow its README; the short version is:

1. **Have an Opik to send to.** The quickest is a local one: `git clone https://github.com/comet-ml/opik && cd opik && ./opik.sh` gives you the UI and API on `http://localhost:5173`. Opik Cloud works too; set `OPIK_URL_OVERRIDE`, `OPIK_API_KEY` and `OPIK_WORKSPACE`.
2. **Fill in the shared keys once.** `cp .env.example .env` at the repo root and add `OPENAI_API_KEY` (plus `ANTHROPIC_API_KEY` for the two examples that use Claude). Each example finds this file by walking up from its own folder.
3. **Run the command in the README.** Python examples use [uv](https://docs.astral.sh/uv/), usually `uv run main.py`. TypeScript examples use `npm install && npm run demo`. The Java one uses `./run.sh`, and the two low-code ones use `./setup.sh && ./demo.sh` with Docker.
4. **Open the project in Opik.** Each example logs to a project named exactly after its folder.
5. **Run the tests without any keys.** Every Python and TypeScript example ships a handful of offline tests (`uv run pytest` or `npm test`) that stub the model and run with Opik tracking switched off, so they pass in seconds with no provider key and no Opik server. Each README shows the exact command.

A full run of any single example costs well under a dollar in model calls; most cost a fraction of a cent.

## What's in a folder

Every example has the same anatomy, so once you've read one you can find your way around the rest:

- `README.md`: the problem; what to open in Opik and what you'll see there, with the real numbers from a traced run; exact run commands; experiments to try; and a **Gotchas** section. Each gotcha gives the symptom you'd hit (an empty column, a null cost, a cryptic error), its cause, and the fix, for the versions pinned in that folder.
- The app itself, small enough to read in one sitting: `pyproject.toml` or `package.json` (Python ≥ 3.12, strict TypeScript), plus `pom.xml` for Java or Docker files for the low-code stacks. Every place the code touches Opik (configuring it, wrapping a client, opening a span, logging usage, scores, attachments or prompts, flushing) has a short comment saying what it produces in Opik and what breaks without it.
- `tests/`: offline tests for the app's own logic, plus at least one traced call made with tracking disabled. That shows the Opik layer doesn't get in the way of unit tests. Java and low-code examples have none.
- `.env.example`: only the variables that example reads, each with a link to where to get it.
- `data/` or `docs/`: a fictional, offline corpus (manuals, catalogs, logs, CSVs). Media the app generates, such as images and audio, is produced at run time and never committed.

## Read the history

Each example landed in its own short series of commits, so `git log -- <folder>` reads like a small tutorial. Typically the first commit is the plain app with no Opik at all, the next adds tracing, and the last adds the evaluation, prompt-library or feedback layer the example is about. Where a real problem came up while building, its fix is a separate commit with the matching gotcha. `git diff` between the first and last commit of a folder is exactly the change it takes to make that app observable.

## License

[Apache 2.0](LICENSE).

---

<sub>inspired by Opik's examples and documentation · [github.com/comet-ml/opik](https://github.com/comet-ml/opik) · [comet.com/docs/opik](https://www.comet.com/docs/opik/)</sub>
