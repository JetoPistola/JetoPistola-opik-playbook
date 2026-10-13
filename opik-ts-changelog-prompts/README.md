# opik-ts-changelog-prompts

![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)
![Node](https://img.shields.io/badge/node-20%2B-339933?style=flat&logo=nodedotjs&logoColor=white)
![Opik SDK](https://img.shields.io/badge/opik-2.2.99-2f54eb?style=flat)

**Turn commit notes into release notes, then prove which prompt wording is better.**

Developers write commit notes like `PEB-412: fix NPE in SyncQueue.flush() when offline edits exceed 50 items (a3f9c21)`. Users want to read "Fixed a sync issue that caused crashes when offline edits exceeded 50 items." An LLM can bridge that gap, but only if the prompt is firm about the output, and prompts are usually edited in place with no record of what changed or whether it helped.

This example keeps the prompt in Opik's prompt library, ships two immutable versions of it, and runs one test suite against each so the improvement shows up as a number.

## What you'll build

A small TypeScript script for a fictional note-taking app called Pebble. It uses only the Opik TypeScript SDK plus the OpenAI SDK wrapped with `opik-openai` (model `gpt-4o-mini`).

- The system prompt is registered as `changelog-rewriter`. **v1** says "turn the commit note into a changelog entry". **v2** adds hard rules: start with Added/Fixed/Improved/Removed, one sentence of at most 18 words, plain language, no ticket IDs, hashes, file paths or code identifiers.
- Registration is idempotent: a version is only created if its exact text is not already in the prompt's history, so re-running never produces a v3.
- A test suite holds five commit notes and three plain-English assertions judged by an LLM. Each item runs 3 times and must pass 2 of them, which smooths over model and judge randomness.
- The suite runs once per prompt version, producing two experiments.

## See it in Opik

**Prompt library.** Open the Prompts page and find `changelog-rewriter`. It has exactly two versions, v1 and v2; the version comparison shows v2 adding the bulleted rules. Neither version can be edited after the fact.

**Experiments.** Open the experiments `changelog-rewriter-v1` and `changelog-rewriter-v2` in the `opik-ts-changelog-prompts` project, each linked to the prompt version it tested. In the run behind this README, v1 passed 0 of 5 items (0%) and v2 passed 5 of 5 (100%). The v1 replies read like pasted release-note drafts: markdown headings, bullet lists, backticked names such as `SyncQueue.flush()`, and several sentences. The v2 replies are single lines such as "Fixed a bug that caused the app to crash when syncing more than 50 offline edits."

**Traces.** The project holds 31 traces: 1 named `rewrite_commit_note` (the warm-up call with the latest prompt) and 30 named `evaluation_task` (5 notes x 3 runs x 2 versions). Open an `evaluation_task` trace to see nested spans: `llm_task` containing `rewrite_commit_note` (its metadata carries `prompt_name`, `prompt_version` and `prompt_commit`) and, under it, a `rewrite-llm` span from `opik-openai` with model `gpt-4o-mini-2024-07-18`, token usage and an estimated cost of about $0.00003. The judge's calls appear as `model.generateText` `llm` spans (30 of them, all with a cost). Total estimated cost for the whole run is about $0.006.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY` (a repo-root `.env` is also picked up).
2. Point the SDK at your Opik: `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default` (for Opik Cloud, set `OPIK_API_KEY` and drop the URL override).
3. `npm install`
4. `npm run demo` (about 25 seconds)
5. Open the `opik-ts-changelog-prompts` project and the Prompts page.
6. Optional offline tests, no keys and no Opik needed: `npm test`. The script sets `OPIK_TRACK_DISABLE=true`, the SDK's switch that turns `track` into a plain call-through.

## Poke around

- Edit `PROMPT_V2` (for example, change 18 words to 10) and re-run. The library gains a v3 because the text changed; an unchanged run adds nothing.
- Delete the "no ticket IDs" rule from v2 and see which assertion starts failing, and for which notes.
- Add a sixth commit note that mentions a user-visible removal, plus an item-level assertion (`assertions: [...]` on that item) that the line starts with "Removed".
- Raise `passThreshold` to 3 in `globalExecutionPolicy` and see how a strict policy changes the pass rate.

## Gotchas we hit

**Traces show up under "Default Project" instead of your project.** `track()` uses a default client that reads `OPIK_PROJECT_NAME` when the SDK loads, so a static `import { track } from "opik"` runs before your code can set it. Set the variable first and import dynamically:

```ts
process.env.OPIK_PROJECT_NAME = PROJECT;
const { Opik, runTests, track } = await import("opik");
```

**You filter spans by type `llm` and the model call is missing.** The `opik-openai` span (`rewrite-llm` here) has type `general`, even though it carries the model, token usage and cost. Look it up by name or model; only the judge's `model.generateText` spans are typed `llm`.

**`TypeError` or `undefined` when reading `version.template`.** Items returned by `getVersions()` are `PromptVersion` objects, which expose the text as `.prompt`. The `.template` alias exists only on the `Prompt` object from `getPrompt`. Compare `h.prompt === text`.

**A new prompt version appears even though the text was already registered.** `createPrompt` only compares your text with the latest version, so registering v1's text again after v2 exists makes a new version. The app checks the full `getVersions()` history first and skips text it has already stored.

**The change description you pass never shows up on the version.** `createPrompt({ ..., changeDescription })` accepts the field, but with opik 2.2.99 the SDK does not forward it, so both versions in the library have an empty description. Until that is fixed, put the reason for a change in the template history itself (or in your commit message), not in `changeDescription`.

## How it's put together

- `src/main.ts`: prompt versions, idempotent registration, the traced `rewrite` function, the test suite, and the per-version `runTests` loop.
- `tests/main.test.ts`: vitest suite that imports `src/main.ts` with fake OpenAI, Opik client and suite runner, and checks version registration, idempotence, the prompt sent to the model and the per-version experiments; `track` stays real with tracking disabled.
- `package.json`, `tsconfig.json`: strict TypeScript; `overrides` keeps `opik-openai` on the same `opik` release.
- `.env.example`: the provider key and Opik settings.

---

*built with Opik · inspired by Opik's examples and documentation*
