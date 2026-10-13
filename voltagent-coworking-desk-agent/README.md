# voltagent-coworking-desk-agent

*A coworking desk-booking agent that proves why OpenTelemetry attribute names matter: same traces, with and without token counts and cost.*

You can wire any OpenTelemetry-emitting framework to Opik in five minutes and still end up with a dashboard where every LLM call shows no tokens and no cost. That is what happens with VoltAgent out of the box: it writes `llm.usage.prompt_tokens` and `llm.model`, while Opik reads the GenAI conventions, `gen_ai.usage.input_tokens`, `gen_ai.request.model` and a provider. The spans arrive, but as anonymous "general" spans. This example is a small desk-booking assistant for a fictional space, Driftwood Cowork, with one module whose only job is to translate the names, so you can see the difference.

## What you'll build

An in-process VoltAgent `Agent` on `gpt-4o-mini` (no HTTP server) with four tools over JSON files in `data/`: `check_desk_availability`, `book_desk`, `list_amenities` and `cancel_booking`. The project is split by responsibility: `src/agent/` holds the agent, `src/tools/` has one file per tool plus a shared in-memory store, `src/telemetry/` holds the OTLP exporter and the attribute mapper, and `src/demo.ts` plays three scripted member requests, one of which chains two tools (check availability, then book).

## See it in Opik

Open the project `voltagent-coworking-desk-agent` (workspace `default`). After one run there are 3 traces, one per request, each named `driftwood-desk-assistant`.

Open the second trace (the booking). Its tree is a root agent span, an `llm:generateText` span typed **llm**, and two spans typed **tool**: `tool.execution:check_desk_availability` and `tool.execution:book_desk`. On the llm span you will see model `gpt-4o-mini`, provider `openai`, usage of 518 prompt and 51 completion tokens, and an estimated cost of about $0.00011. The tool spans show clean arguments (for example `{"desk_id": "HD-02", "date": "2026-11-03", "member": "Priya Natarajan"}`) and the tool's reply, including booking id `BK-3101`. The traces table has populated Input, Output, Usage and Estimated cost columns; the three traces cost $0.00027 in total.

Now the contrast. Running with `SKIP_GENAI_MAPPER=1` (the exporter wrapper switched off) gave the same 3 traces and the same tool outputs, but every span, llm and tool alike, was typed **general**, usage was empty and estimated cost was empty. Nothing errors; the data just silently goes missing.

Two honest caveats from the run: the trace Input column shows VoltAgent's whole attribute bag (the member's sentence is under its `input` key, next to the system prompt and operation ids), and the llm span's own Output is empty because VoltAgent puts the final answer on the root span only.

## Run it yourself

1. Have a reachable Opik. The default endpoint is a local self-hosted one, `http://localhost:5173/api/v1/private/otel`, workspace `default`, no key needed. For Opik Cloud set `OPIK_OTLP_ENDPOINT`, `OPIK_API_KEY` and `OPIK_WORKSPACE` (see `.env.example`).
2. `cp .env.example .env` and set `OPENAI_API_KEY`. (A `.env` in a parent folder is also picked up.)
3. `npm install`
4. `npm run demo`
5. Open the project `voltagent-coworking-desk-agent` in Opik and click the second trace.
6. Optional, offline: `npm test` runs the vitest suite. It needs no OpenAI key and no Opik. This example uses no Opik SDK: export happens only if `buildObservability()` constructs the OTLP exporter, and the tests never do (they test the mapper as a pure function and stub the exporter classes), so nothing is exported and nothing touches the network.

## Poke around

- Run `SKIP_GENAI_MAPPER=1 OPIK_PROJECT_NAME=desk-unmapped npm run demo` and compare the two projects: span types, usage and cost columns.
- In `src/telemetry/genaiMapper.ts`, delete the two provider lines (`gen_ai.system`, `gen_ai.provider.name`) and rerun, then check whether the cost column still fills in; Opik needs a recognised provider to price a call.
- Ask for a booked desk: edit request 2 to use `2026-11-04` in the Harbor Loft and read the check_desk_availability span to see how the agent handles a fully booked day.
- Add a fifth tool in `src/tools/`, export it from `index.ts`, add it to the agent, and see it appear as a typed tool span with no tracing code.

## Gotchas we hit

- **Spans arrive in Opik but every one is typed `general`, with empty Usage and no cost.** VoltAgent writes its own attribute names (`llm.model`, `llm.usage.prompt_tokens`, `span.type`) and emits no `gen_ai.*` attributes at all (checked in the installed `@voltagent/core` 2.x source). Opik prices and types spans from the GenAI conventions. Fix: wrap the OTLP exporter so each span is mapped before it is sent, as in `src/telemetry/observability.ts`: `new BatchSpanProcessor(new GenAIMappingExporter(otlp))`. Setting `gen_ai.system` and `gen_ai.response.model` as well as the usage counts is what lets the cost estimate fill in.
- **The llm span's Output is empty.** VoltAgent sets no `llm.output` attribute on the llm span (not present in the installed source), so there is nothing to map. The final answer lives on the root agent span; read it there, or on the trace's Output column.
- **A warning on every model call: "System messages in the prompt or messages fields...".** VoltAgent puts its system prompt in the messages array, and the AI SDK it uses (the `ai` package) warns each time. It is harmless; `src/demo.ts` filters that single message by matching `"System messages in the prompt"` on `console.warn`.

## How it's put together

- `src/demo.ts` loads env, wires the agent and observability, runs three requests, shuts the exporter down to flush.
- `src/agent/deskAgent.ts` the agent: instructions, model, tools.
- `src/tools/*.ts` one file per tool; `store.ts` loads `data/` into memory so bookings persist within a run (the JSON files are never modified).
- `src/telemetry/genaiMapper.ts` the span rename to `gen_ai.*`, as an exporter wrapper.
- `src/telemetry/observability.ts` the OTLP exporter aimed at Opik, headers `Comet-Workspace` and `projectName`.
- `tests/genaiMapper.test.ts` the mapper as a pure function (usage, model, system, tool arguments) plus the exporter wrapper.
- `tests/observability.test.ts` the `SKIP_GENAI_MAPPER` toggle and env-driven OTLP settings, with the exporter classes stubbed.
- `tests/tools.test.ts` the four tools against `data/*.json`.
- `vitest.config.ts` points vitest at `tests/`.
- `data/` the fictional desks, amenities and starting bookings.

---

*built with Opik · inspired by Opik's examples and documentation*
