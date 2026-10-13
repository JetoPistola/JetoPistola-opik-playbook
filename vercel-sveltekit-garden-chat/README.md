# vercel-sveltekit-garden-chat

*A streaming SvelteKit chat about vegetable gardening, where every reply becomes an Opik trace, every conversation a thread, and every trace gets graded by a judge you never call yourself.*

![TypeScript](https://img.shields.io/badge/typescript-6-3178C6?style=flat&logo=typescript&logoColor=white)
![SvelteKit](https://img.shields.io/badge/sveltekit-2-FF3E00?style=flat&logo=svelte&logoColor=white)
![Vercel AI SDK](https://img.shields.io/badge/ai%20sdk-7-000000?style=flat&logo=vercel&logoColor=white)
![opik-vercel](https://img.shields.io/badge/opik--vercel-2.2.99-2f54eb?style=flat)

A chat reply is a stream. There is no single return value to log, the browser re-sends the whole history on every turn, and "did the bot actually answer the question?" is something nobody checks until a user complains. This example is **Sprout**, the helper for a fictional allotment called Fernhollow. It shows three things working together: the AI SDK's streaming spans exported to Opik through `opik-vercel`, a thread id that stitches turns into conversations, and a live LLM-as-judge rule that scores each trace the moment it lands.

## What you'll build

A SvelteKit app with one page and one endpoint. The page uses the `Chat` class from `@ai-sdk/svelte` (the Svelte counterpart of `useChat`). The endpoint, `src/routes/api/chat/+server.ts`, calls `streamText` with `gpt-4o-mini`. The system prompt contains the whole fictional planting calendar and plant-care notes from `data/`, so answers are grounded in them.

The Opik side lives in `src/lib/server/telemetry.ts`: an OpenTelemetry `NodeSDK` whose trace exporter is `OpikExporter`, pinned to the project `vercel-sveltekit-garden-chat`, plus the AI SDK v7 `registerTelemetry` call. An `enrichSpan` hook copies the chat id (sent by the `Chat` class on every request) into the span attributes so it becomes the Opik thread id.

`npm run demo` does everything unattended:

1. creates the online-evaluation rule `garden_answer_relevance` through the Opik REST API (skipped if it already exists), so it is in place before any trace arrives;
2. builds the app and boots it on `127.0.0.1:5301`;
3. plays two scripted conversations over HTTP, reading the streamed replies (3 turns about tomatoes and slugs, 2 turns about garlic and carrots);
4. stops the server (SIGTERM, which flushes the span batch);
5. polls Opik until the judge's scores show up and prints them.

## See it in Opik

Open the project **vercel-sveltekit-garden-chat**. After one demo run the Traces tab holds 10 rows, in two kinds:

- **5 traces named `garden-chat-turn`**: one per streamed reply. Each has two spans: an `llm` span called `chat gpt-4o-mini` carrying the model name, token usage and estimated cost, and a `general` span called `step 1`. The input shows the full message array (the long system prompt with the allotment notes, then the history); the output is the final assembled reply even though it left the server as a stream. In the verified run the `llm` spans used 657, 711 and 771 tokens across the three turns of the tomato conversation: the history is re-sent each turn, so input grows. Cost per turn was about $0.0001 (0.00011 to 0.00014 USD).
- **5 traces named `online_evaluation`**: the judge's own runs. Opik logs the rule's LLM call into the same project (an `llm_call` span of roughly 950 to 1,090 tokens each), which is why the count doubles. Filter by name if you only want the chat turns.

On the Threads tab, the 5 chat traces collapse into **2 threads**: one with 3 turns (tomatoes, yellow leaves, slug pellets) and one with 2 (garlic, carrot fly). Click a thread to read it as a transcript.

Back on the Traces tab, scroll to the feedback-scores column: every `garden-chat-turn` trace carries `answer_relevance` with the value 1.0 in the verified run (all 5). The scores arrive a few seconds after the trace, written by the backend, not by your code. Open Automation / Online evaluation for the project to see the rule `garden_answer_relevance`, 100% sampling, using `gpt-4o-mini`. Total spend for a full run, chat plus judge, came to about $0.0014.

## Run it yourself

Requires Node 20+ and an OpenAI key. The Opik project needs an OpenAI key configured as a provider (workspace settings, AI providers) so the judge can run.

1. `cp .env.example .env` and fill in `OPENAI_API_KEY` and the Opik settings (a repo-root `.env` one level up is also read).
2. `npm install`, then optionally `npm test`
3. `npm run demo`
4. Open the `vercel-sveltekit-garden-chat` project in Opik: Traces, then Threads. Give the judge up to a minute for the scores.

For interactive chatting: `npm run dev`, then visit http://127.0.0.1:5301. Each page load is one conversation, hence one Opik thread. Create the rule first by running `npm run demo` once, or the traces from your own chat will go unscored.

## Offline tests

`npm test` runs vitest in well under a second with no OpenAI key and no Opik. It sets `OPIK_TRACK_DISABLE=true`, the Opik SDK's documented switch for turning tracking off. That switch only reaches the SDK's own tracing paths (decorators and wrappers), not the OpenTelemetry exporter used here, so the tests also never start the real telemetry: `telemetry.ts` is tested with the exporter, `NodeSDK` and `registerTelemetry` replaced by recorders, and the endpoint test stubs `streamText`.

## Poke around

- Ask something the notes do not cover ("how do I prune an apple tree?") in `npm run dev` and see whether `answer_relevance` rewards an honest "the notes don't say".
- Edit the judge prompt in `scripts/opik-rest.ts`, delete the rule in the Opik UI, run the demo again, and compare the scores.
- Remove `threadId` from `runtimeContext` in the endpoint and watch the Threads tab lose its transcripts.
- Switch the model in `+server.ts` to `gpt-4.1-mini` and compare per-turn cost and tokens.

## Gotchas we hit

**1. The Opik project stays empty even though `experimental_telemetry` is on.** AI SDK v7 emits no spans until an integration is registered globally. We checked with an in-memory exporter and a mock model: `isEnabled: true` alone produced zero spans, adding `registerTelemetry(new OpenTelemetry({ usage: true }))` produced `chat`, `step 1` and `invoke_agent` spans. Fix: call it once at startup, as `telemetry.ts` does, and start it from `hooks.server.ts`.

**2. Traces arrive but the Threads tab is empty.** Passing `runtimeContext: { threadId }` and `includeRuntimeContext` is not enough: with the same mock setup no thread attribute reached the spans. `OpikExporter` reads `ai.telemetry.metadata.threadId`, so copy it yourself in `enrichSpan`:

```ts
enrichSpan: ({ runtimeContext }) =>
  runtimeContext?.threadId != null
    ? { "ai.telemetry.metadata.threadId": String(runtimeContext.threadId) }
    : {},
```

**3. `OPIK_TRACK_DISABLE=true` does not silence the exporter.** We pointed an `Opik` client at a fake URL with the variable set and still saw a POST to `/v1/private/traces/batch` on flush; the flag is only consulted by the SDK's decorators and wrappers. In tests, never start the real `NodeSDK` and `OpikExporter` (or set `isEnabled: false` in the telemetry settings).

**4. `useChat` is not there.** `@ai-sdk/svelte` exports a `Chat` class (plus `Completion` and `StructuredObject`), not a hook. Use `new Chat({ transport: new DefaultChatTransport({ api: "/api/chat" }) })` and read `chat.messages` and `chat.status`.

**5. SvelteKit 3 does not support the Node 20 this example targets.** `@sveltejs/kit@3` declares `engines.node >=22.17` (checked with `npm view @sveltejs/kit@3 engines`). Stay on SvelteKit 2 with `adapter-node` 5, as `package.json` does; the AI SDK v7 packages also print an engine warning on Node 20, which did not affect the verified run.

## How it's put together

- `src/routes/+page.svelte`: the chat UI built on the `Chat` class.
- `src/routes/api/chat/+server.ts`: `streamText` plus the telemetry settings and thread id.
- `src/lib/server/telemetry.ts`: `NodeSDK` + `OpikExporter` + `registerTelemetry`, flushed on SIGTERM.
- `src/lib/server/garden.ts`: loads `data/` into the system prompt.
- `src/hooks.server.ts`: starts telemetry when the server boots.
- `scripts/opik-rest.ts`: REST helpers: create the online rule, list traces and scores.
- `scripts/demo.ts`: the one-command orchestration described above.
- `data/`: the fictional planting calendar and care notes.
- `vitest.config.ts`: plain vitest setup with the `$lib` alias.
- `tests/garden.test.ts`: the system prompt contains the data files, the persona and the no-guessing rule.
- `tests/online-rule.test.ts`: the rule payload (`llm_as_judge`, variables, DOUBLE schema), project-first creation and no duplicate rule, against a fake REST API.
- `tests/telemetry.test.ts`: `startTelemetry` pins the project and tags, and `enrichSpan` maps `runtimeContext` to span attributes.
- `tests/chat-endpoint.test.ts`: the endpoint, with tracking disabled and `streamText` stubbed, sends the chat id as thread id and the trace name.

---

*built with Opik · inspired by Opik's examples and documentation*
