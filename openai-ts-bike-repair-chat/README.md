# Bike Repair Advisor: Conversations, Cost, Feedback

**`openai-ts-bike-repair-chat`** — three riders, ten chat turns, and one Opik project that reads like a service desk instead of a pile of API calls.

![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)
![openai](https://img.shields.io/badge/openai-6.x-412991?style=flat&logo=openai&logoColor=white)
![Opik](https://img.shields.io/badge/opik-2.2.99-2f54eb?style=flat)

Chat features log one request per message, but nobody thinks in requests. A rider who asks about a flat tire, then a thorn, then a final price has had *one* conversation, and the shop owner wants to know what it cost and whether the rider left happy. This example is the advisor bot for "Wobbly Spoke Cycle Works" (an invented shop). It quotes prices only from a small price list in `data/parts.json`, and it uses Opik to group turns into threads, price each turn, and attach scores to traces after the run.

## What you'll build

A Node script on the plain OpenAI TypeScript SDK. For each turn it opens an Opik trace tagged with a `threadId`, hands that trace to `trackOpenAI` as the parent, and lets the wrapped client record the model call with tokens and cost. After all three conversations finish, it logs two kinds of feedback score: `price-accuracy` (a deterministic check that every dollar figure in the reply can be built from the price list) and `user-satisfaction` (a simulated thumbs up or down on each conversation's last turn).

## See it in Opik

Open the `openai-ts-bike-repair-chat` project.

- **Threads tab:** three threads, `rider-maya-flat-tire` (3 turns), `rider-omar-brake-squeal` (4 turns) and `rider-lena-ghost-shifting` (3 turns). Open one and the turns read top to bottom as a chat.
- **Traces tab:** 10 traces named `advise-turn`, each with one child span, `advisor-llm`, holding the full message array sent to the model. Add the *Estimated cost* column: in the verified run costs were about $0.0001 per turn, rising within a thread as history is re-sent (Maya: $0.000100, $0.000107, $0.000115; prompt tokens 400, 491, 564). Omar's third turn, at 559 prompt tokens, is his most expensive at $0.000128; his fourth, at 652 tokens, costs $0.000121 because the reply is short.
- **Feedback scores columns:** `price-accuracy` is 1.0 on all 10 traces. `user-satisfaction` appears on the last turn of each thread: 1.0 for Maya and Omar, 0.0 for Lena. Filter on `user-satisfaction < 1` to jump straight to the unhappy conversation, then read its thread to see why.

One honest detail: with this integration the child span shows up with type `general` rather than `llm`, though model usage and cost are still captured on it.

## Run it yourself

1. `cd openai-ts-bike-repair-chat`
2. `cp .env.example .env` and set `OPENAI_API_KEY` (a `.env` in any parent folder is also picked up).
3. Point at your Opik server: `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default` (for Opik Cloud, set `OPIK_API_KEY` and `OPIK_WORKSPACE` instead).
4. `npm install`
5. `npm run demo`
6. Optional: `npm test` runs the offline tests (no key, no Opik).

The run takes about 30 seconds and costs about a tenth of a cent on `gpt-4o-mini`.

## Poke around

- Add a fourth conversation to `conversations` in `src/main.ts` and watch a new thread appear.
- Delete the `threadId` line from `client.trace(...)` and compare the Threads tab: the turns fall apart again.
- Raise the system prompt size (add parts to `data/parts.json`) and see how the per-turn cost curve steepens.
- Make `priceAccuracy` stricter, or ask for a part that is not on the list, and look for traces that score below 1.0.

## Gotchas we hit

- **Symptom: every turn is its own conversation; the Threads tab is empty.** `trackOpenAI` accepts `client`, `generationName`, `parent` and `traceMetadata`, but no `threadId`. Fix: create the trace yourself and hand it over: `const trace = client.trace({ name: "advise-turn", threadId }); const tracked = trackOpenAI(openai, { client, parent: trace });`, then call `trace.end()` when the turn is done.
- **Symptom: `npm install` fails with `ERESOLVE unable to resolve dependency tree` (`peer opik@"^1.8.61" from opik-openai@2.2.99`).** `opik-openai@2.2.99` still declares a peer range for the 1.x `opik` package. Fix: add an npm override that points it at your installed `opik`: `"overrides": { "opik-openai": { "opik": "$opik" } }`.
- **Symptom: the model call shows up with span type `general` instead of `llm`.** That is what the wrapper produces when it is given a `parent` trace. Usage and *Estimated cost* are still recorded on the span, so nothing is lost beyond the label.
- **Symptom: `trace.id` is `undefined` when logging feedback scores.** The TypeScript `Trace` object keeps its id under `.data.id`; pass `rec.trace.data.id` to `logTracesFeedbackScores`. Also note `opik-openai` needs `openai@^6`.

## How it's put together

- `src/main.ts` — loads `.env`, creates the Opik client, runs the three conversations, logs the feedback scores and flushes.
- `src/advisor.ts` — price list and system prompt, conversations, `advise` (trace-per-turn with `threadId`, `trackOpenAI` wiring), `priceAccuracy`, `buildFeedbackScores`.
- `tests/advisor.test.ts` — offline vitest tests with a stubbed OpenAI client: price check, prompt contents, a traced `advise` call and the feedback-score builder.
- `data/parts.json` — fictional parts, labor rate and service times that the prompt quotes from.
- `package.json`, `tsconfig.json` — strict TypeScript; `npm run demo` runs it with `tsx`, `npm run typecheck` checks types, `npm test` runs vitest with `OPIK_TRACK_DISABLE=true` (the Opik TS SDK's documented switch, also readable as `track_disable` in `~/.opik.config`), so tracing becomes a no-op and nothing is sent.
- `package.json` `overrides` — `opik-openai` still declares a peer range of `opik@^1.8`, so the block pins it to the installed `opik`.
- `.env.example` — the variables the example reads.

---
*built with Opik · inspired by Opik's examples and documentation*
