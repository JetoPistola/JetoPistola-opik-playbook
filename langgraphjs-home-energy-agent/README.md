# langgraphjs-home-energy-agent

![Node](https://img.shields.io/badge/node-20%2B-339933?style=flat&logo=node.js&logoColor=white)
![LangGraph.js](https://img.shields.io/badge/LangGraph.js-ReAct%20agent-1c3c3c?style=flat)
![Opik](https://img.shields.io/badge/Opik-opik--langchain%202.2.99-2f54eb?style=flat)

*A smart-home energy assistant whose every tool call shows up as a real tool span in Opik.*

## The problem

An agent that answers "what would the dishwasher cost at 2am?" is only trustworthy if its numbers came from somewhere. The chat transcript can't tell you whether the model called the tariff tool, with which hour, or just made up a figure. In an agent loop (model, tool, model, tool, model) you need the whole tree: what the model asked for, what the tool actually returned, and what each model turn cost.

## What you'll build

A [LangGraph.js](https://langchain-ai.github.io/langgraphjs/) ReAct agent ("Voltie") on `gpt-4o-mini` for a fictional household. Four tools read local JSON in `data/home.json`: `read_meter` (yesterday's usage by hour), `list_appliances`, `estimate_cost` (time-of-use tariff table) and `schedule_appliance`. Tracing is one callback: `OpikCallbackHandler` from `opik-langchain` is passed to `agent.invoke`.

`npm run demo` sends three requests, each its own trace. The third needs a four-step chain: list appliances, price 6pm and 2am, schedule the cheaper slot, then answer.

## See it in Opik

Open the project `langgraphjs-home-energy-agent`. It holds 3 traces named `energy-request-1` to `-3`; each has populated input and output.

- `energy-request-1` has 13 spans: an `llm` span (`ChatOpenAI`, `gpt-4o-mini`, 370 tokens) that decides to call a tool, then a `tool` span `read_meter` with input `from_hour: 17, to_hour: 21`, then a second `llm` span (442 tokens) that writes the answer (11.5 kWh, which matches the meter data).
- `energy-request-3` is the interesting one, with 28 spans and four `llm` spans in a loop: `list_appliances`, then two `estimate_cost` calls (hour 18 and hour 2), then `schedule_appliance` with `appliance_id: dishwasher, start_hour: 2`, then the final answer. Click a tool span to see the exact arguments and the JSON it returned.
- Between the llm and tool spans you will also see LangGraph's own plumbing as `general` spans (`agent`, `prompt`, `RunnableSequence`, `Branch<agent,tools,__end__>`, `tools`). They are noise for most debugging; collapse them.
- The `llm` spans carry token usage and an estimated cost (for example 0.0001665 USD on the last turn of request 2). Whole-trace totals from my run: request 1 about 812 tokens / $0.00014, request 2 1,230 tokens / $0.00027, request 3 2,396 tokens / $0.00043. The full run cost under a tenth of a cent.

Honest limits: the trace-level input and output are the raw LangGraph state (`{messages: [...]}`), not a clean question/answer pair, and the trace-level usage is summed from the llm spans.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY` (or keep it in a parent folder's `.env`; the app walks up to find one).
2. For a self-hosted Opik, keep `OPIK_URL_OVERRIDE` and `OPIK_WORKSPACE` from `.env.example`; for Opik Cloud add `OPIK_API_KEY` and drop the override.
3. `npm install`
4. `npm run demo` (about 10 seconds).
5. Open the project in Opik and click the newest trace.
6. Offline tests (no key, no Opik): `OPIK_TRACK_DISABLE=true npm test`. `OPIK_TRACK_DISABLE` is the Opik SDK's switch for turning tracking off.

## Poke around

- Change the third request to ask for the EV charger; the 4 kW-hour cycle and 7.4 kW draw make the tariff gap much bigger.
- Ask to schedule the heat pump. `schedule_appliance` returns an error object; see how the agent explains it and how the error appears in the tool span.
- Edit the tariff bands in `data/home.json` and check that the numbers in the answer move with them.
- Remove "Never guess numbers" from the system prompt in `src/main.ts` and see whether the model starts skipping tool calls.

## Gotchas we hit

- **`npm install` fails with `ERESOLVE ... peer opik@"^1.8.75" from opik-langchain@2.2.99`.** `opik-langchain` 2.2.99 still declares a peer range for the 1.x `opik` SDK, while you need `opik` 2.2.99 next to it. Pin both and tell npm to use your top-level `opik` for the integration, in `package.json`: `"overrides": { "opik-langchain": { "opik": "$opik" } }`.
- **The trace's input and output columns show `{messages: [...]}` instead of a question and an answer.** The callback handler records the raw LangGraph state for the root run. Read the last message in the list for the answer, or click into the `llm` spans for clean prompts and completions; there is no handler option that reshapes it.

## How it's put together

- `src/main.ts`: loads env, builds the `createReactAgent` graph, runs the three requests with `OpikCallbackHandler`, flushes.
- `src/tools.ts`: the four zod-typed tools over the local data.
- `tests/tools.test.ts`: calls the four tools directly against `data/home.json` (meter sums, tariff pricing, midnight wrap, scheduling rules).
- `tests/tracing.test.ts`: runs the agent loop with a scripted model and an `OpikCallbackHandler` while tracking is disabled, so no key or server is needed.
- `data/home.json`: appliances, tariff bands and yesterday's hourly meter readings (all fictional).
- `package.json`: pins opik 2.2.99, adds vitest and the `npm test` script, and overrides `opik-langchain`'s stale peer range on `opik`.

*built with Opik · inspired by Opik's examples and documentation*
