# Fornello Manual Q&A: quote it or fail it

**`anthropic-ts-espresso-manual-qa`** · a TypeScript bot that answers from a product manual, plus an Opik test suite that audits every quote it gives.

![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?style=flat&logo=typescript&logoColor=white)
![Node](https://img.shields.io/badge/node-20%2B-339933?style=flat&logo=nodedotjs&logoColor=white)
![Anthropic SDK](https://img.shields.io/badge/@anthropic--ai/sdk-0.70-191919?style=flat)
![Opik](https://img.shields.io/badge/opik-2.2.99-2f54eb?style=flat)

A support bot that answers from a manual is only useful while its answers are really *in* the manual. The failure that hurts is the quiet one: a quote that is almost right, with a word dropped or a sentence stitched together, sitting next to a claim it does not quite support. Nobody notices until a customer descales a boiler with vinegar.

This example asks Claude Haiku to answer questions about a fictional home espresso machine (the Fornello Piccolo F-200) and to wrap every supporting excerpt in `<quote>` tags. Then it turns "are the quotes honest?" into an Opik **test suite**: three plain-English assertions applied to every answer, a few extra assertions attached to individual questions, and a hard pass or fail per question.

## What you'll build

- `src/qa.ts` and `src/main.ts`, about 200 lines together. They call Claude Haiku 4.5 through the official `@anthropic-ai/sdk`.
- **Hand-written tracing.** Opik's TypeScript SDK has no first-party Anthropic integration (there is one for OpenAI, Vercel AI, LangChain and Gemini), so each model call is logged as an `llm` span you create yourself, carrying the model, the provider `anthropic`, and token usage. With those fields set, Opik computes cost for you.
- A test suite with **three suite-level assertions** (every quote is verbatim; quotes support the claims; the question was answered) and **item-level assertions** on two questions: the descaling answer must say "3 months / 6 weeks" and forbid vinegar, and the 110V question, which the manual never covers, must admit that instead of inventing an answer.
- An execution policy of **3 runs per question, passing at 2 of 3**, so one flaky generation or judge call does not decide a verdict.

## See it in Opik

Open the local Opik UI and pick the project **anthropic-ts-espresso-manual-qa**.

**Traces tab.** After one run there are 19 traces: one named `answer_question` (the warm-up question about descaling) and 18 named `evaluation_task` (6 questions x 3 runs). Open `answer_question`: it holds a single `llm` child span, `anthropic.messages.create`, with model `claude-haiku-4-5-20251001`, provider `anthropic`, about 1,100 prompt tokens (the whole manual rides in the system prompt), around 100 completion tokens, and an estimated cost of roughly $0.0015. The output is the answer with its `<quote>` blocks. Across the project, all 37 `llm` spans have non-zero cost; the app's own Claude calls sum to about $0.029, and the judge calls add about $0.066.

**Test suites.** Open the suite named `anthropic-ts-espresso-manual-qa` (6 items) and its latest run. In my verified run Opik showed **18 samples, pass rate 100%, 6 of 6 items passed**:

- Passed 3/3 runs: warranty, red blinking light, double-shot time and dose, descaling and vinegar.
- Passed 2/3 runs: "How do I steam milk safely?" and the 110V question, which the manual never covers. In one run each, the judge was stricter than in the others (for 110V, whether an honest "not covered" counts as answering the question). The execution policy absorbed that: an item needs 2 of 3 runs, so one strict verdict does not fail it.

Your numbers will differ: model and judge are not deterministic, and an item can land on 2/3 or fail outright on another run. That variance is why the policy runs each item three times. Click any run's row to read each assertion's reason and jump to the trace that produced the answer.

## Run it yourself

1. Start from this folder: `cd anthropic-ts-espresso-manual-qa && npm install`
2. Provide a key: `cp .env.example .env` and set `ANTHROPIC_API_KEY` (the app also picks up a `.env` from any parent directory).
3. Point at Opik. Local self-hosted example:
   `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default`
   For Opik Cloud set `OPIK_API_KEY` and `OPIK_WORKSPACE` instead.
4. `npm run demo` (about 35 seconds, roughly $0.10 in Haiku calls).
5. Optional: `npm run typecheck`, and `npm test` for the offline tests (no keys, no Opik).

The script prints the warm-up answer, a pass/fail line per question with failure reasons, and a link to the run.

## Poke around

- Edit the system prompt in `src/main.ts` to drop the "copied character-for-character" rule, re-run, and watch the verbatim assertion start failing.
- Change `passThreshold` from 2 to 3 (or `runsPerItem` to 1) and see how much stricter or noisier the verdicts get.
- Reword the 110V assertion so that "the manual does not cover this" counts as a valid answer, and re-run.
- Add a question whose answer needs two distant passages (for example filter life versus watery espresso) and see whether the quotes still hold up.

## Gotchas we hit

**Cost is empty on the model call, or the call is missing from the trace.** Opik's TypeScript SDK has no Anthropic wrapper, so nothing logs the call for you. Cause: only your own spans exist. Fix: inside a `track()`-ed function, open a child span with `getTrackContext()?.span.span({ type: "llm", ... })`, then `update` it with `model`, `provider: "anthropic"` and `usage` (`prompt_tokens`, `completion_tokens`, `total_tokens`) before `end()`. Opik prices the span from those fields.

**Every judge call prints an AI SDK warning.** The suite's LLM judge runs on the Vercel AI SDK, which logs a warning per call and buries your results. Fix, before the first judge call: `globalThis.AI_SDK_LOG_WARNINGS = false`.

**Tests send traces to Opik, or fail without a server.** Fix: disable tracking with the SDK's `OPIK_TRACK_DISABLE=true` environment variable (config key `trackDisable`; `setTracingActive(false)` does the same at runtime). `npm test` sets it for you, and with it on `getTrackContext()` is undefined, which is why the span calls use `?.`.

## How it's put together

- `src/qa.ts`: system prompt, the Claude call with its hand-logged `llm` span, quote extraction, and the question/assertion definitions.
- `src/main.ts`: env and project setup, the warm-up trace, the suite definition, `runTests`, and the summary printout.
- `tests/qa.test.ts`: offline vitest tests with a stubbed Anthropic client (prompt, quotes, span-logging path, `track()` with tracking disabled).
- `docs/manual.md`: the fictional owner's manual used as the only source of truth.
- `package.json` / `package-lock.json` / `tsconfig.json`: pinned `opik` 2.2.99, vitest, strict TypeScript, `demo` and `test` scripts.
- `.env.example`: the variables you need; no secrets are committed.

*built with Opik · inspired by Opik's examples and documentation*
