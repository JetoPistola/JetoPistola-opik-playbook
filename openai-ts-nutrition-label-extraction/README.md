# openai-ts-nutrition-label-extraction

*A vision model read the label. Opik keeps the label next to what it claimed to read.*

![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?style=flat&logo=typescript&logoColor=white)
![OpenAI](https://img.shields.io/badge/openai-6.x-412991?style=flat&logo=openai&logoColor=white)
![Opik](https://img.shields.io/badge/Opik-2.2.99-2f54eb?style=flat)

When a vision model returns `"sodium_mg": 0` for a food label, the number looks
perfectly plausible. You only find out it is wrong by looking at the picture. This
example extracts typed nutrition fields from six fictional label images with
`gpt-4o-mini` and a zod schema, traces every call with `opik-openai`, and gets
each label image stored in Opik as an attachment, so image, model call and output
sit in one trace. A test suite then pins the ground truth for each label and
reports the pass rate without softening it.

## What you'll build

- `src/labels.ts` draws six labels as SVG and rasterises them to PNG at run time
  with `@resvg/resvg-js` (nothing is downloaded, nothing is committed):
  a clean baseline, a two-column "per 100 g / per serving" trap, tiny print on
  a big canvas, a rotated and blurred label, a label whose sodium line was never
  printed, and a dense allergen paragraph with a "may contain" clause.
- `src/main.ts` sends each PNG as a base64 data URL with a zod structured output
  (`zodResponseFormat`), wrapped in an `extract_label` track with the
  `opik-openai` client nested underneath. It then builds a test suite (two
  suite-wide assertions plus three per-label assertions carrying the expected
  values) and runs it with `runTests`; an LLM judge grades every assertion.

## See it in Opik

Open the project **openai-ts-nutrition-label-extraction** (local workspace
`default`).

- **Traces** has 7 rows from one run: one standalone `extract_label` trace (the
  quick look at the first label) and six `evaluation_task` traces from the suite.
  Open any of them and you will find an `extract_label` span with a `read-label`
  span inside it, the model call, `gpt-4o-mini-2024-07-18`, about 25.8k tokens
  (high-detail images are expensive) and roughly $0.004 per label.
- Each of those spans has an image in its **Attachments**: the label PNG the model
  saw. Open the `no-sodium-line` trace and you can see the sodium row really is
  missing, next to `"sodium_mg": 0` in the output.
- **Test suites** (the dataset is named after the project) shows one experiment
  with a pass rate of 0.83, 5 of 6 labels passed. The failing item is
  `no-sodium-line`: the label has no sodium line and the right answer is `null`,
  but the model returned `0` in every run I did. The hard-looking cases (blurry,
  rotated, tiny print, per-100 g trap) all passed.
- The whole run costs about $0.02 and takes about 20 seconds.

One run-to-run caveat: on an earlier run the same label also had its serving size
misread as "1 strip (2 g)". That one is nondeterministic, the sodium fabrication is not.

## Run it yourself

1. `npm install` (Node 20+). Needs system fonts, which any desktop OS has.
2. Put `OPENAI_API_KEY` in a `.env` here or anywhere above this folder
   (see `.env.example`).
3. Point the SDK at your Opik, for a local stack:
   `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default`
4. `npm run demo`

`npm run typecheck` runs `tsc --noEmit`.

Offline tests (no OpenAI key, no Opik, a few seconds):
`OPIK_TRACK_DISABLE=true npm test`. `OPIK_TRACK_DISABLE=true` is the SDK's
documented switch that turns `track()` into a pass-through. The tests render
the labels, check the zod schema that is sent to the model, and check the suite
items, with OpenAI, the Opik client and `runTests` stubbed.

## Poke around

- Add an instruction "never answer 0 unless the label prints 0" to the system
  prompt and re-run: does `no-sodium-line` flip to a pass?
- Change `detail: "high"` to `"low"` and watch the token count, the cost, and the
  tiny-print label.
- Unset the `OPIK_MIN_BASE64_EMBEDDED_ATTACHMENT_SIZE` line in `main.ts`: only
  images larger than 256 KB of base64 get lifted into attachments by default, so
  most labels will lose theirs. (The blurry one is large enough to stay.)
- Raise the suite policy to `runsPerItem: 3, passThreshold: 2` and see which
  items are flaky versus consistently wrong.

## Gotchas we hit

1. **Only one of six traces has an image attachment.** Symptom: the label PNGs are
   30-90 KB, yet most `extract_label` spans have an empty Attachments tab. Cause:
   the TypeScript SDK only lifts inline base64 into attachments above 256 KB of
   encoded text (default `minBase64EmbeddedAttachmentSize` of 256000). Fix: set the
   env var before `opik` is imported, as `main.ts` does:
   `process.env.OPIK_MIN_BASE64_EMBEDDED_ATTACHMENT_SIZE ??= "10000";`
2. **The model-call spans are not `llm` spans.** Symptom: the `read-label` span
   shows type `general`, so a filter on type `llm` finds nothing. Cause:
   `opik-openai` 2.2.99 logs every completion with `type: general` (usage and model
   are still recorded). Fix: filter by span name (`read-label`) instead, or wrap
   the call yourself if you need the `llm` type.
3. **Every model call becomes a separate trace.** Symptom: next to the
   `extract_label` traces there are extra top-level `read-label` traces. Cause:
   `trackOpenAI` opens its own trace unless it is handed a parent. Fix: build the
   wrapper inside the tracked function and pass the active span:
   `trackOpenAI(client, { client: opik, parent: getTrackContext()?.span })`.
4. **`Cannot find namespace 'z'` from `tsc`.** Symptom: `z.infer<typeof Schema>`
   fails to type-check. Cause: `const { z } = await import("zod")` (the pattern
   used for `opik` above) yields a value without the `z` type namespace. Fix:
   import zod statically, `import { z } from "zod";`; it has no import-time
   configuration, so it does not need to wait for the env vars.

## How it's put together

- `src/labels.ts` - label SVGs, ground truth, PNG rendering.
- `src/main.ts` - extraction, tracing, test suite, report.
- `package.json` / `package-lock.json` - pinned `opik` and `opik-openai` 2.2.99,
  with an `overrides` entry so `opik-openai` uses the same `opik`.
- `tests/labels.test.ts` - PNG rendering is valid, deterministic and above the
  attachment threshold; the no-sodium label really has no sodium line.
- `tests/main.test.ts` - imports `main.ts` with stubbed OpenAI, Opik client and
  `runTests`; checks the request and zod schema and the suite item definitions.
- `vitest.config.ts` - test include pattern.
- `.env.example`, `.gitignore`, `tsconfig.json` - setup.

*built with Opik · inspired by Opik's examples and documentation*
