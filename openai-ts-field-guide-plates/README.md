# openai-ts-field-guide-plates

![Node](https://img.shields.io/badge/node-20%2B-5FA04E?style=flat&logo=node.js&logoColor=white)
![openai](https://img.shields.io/badge/openai-6.x-412991?style=flat)
![opik](https://img.shields.io/badge/opik-2.2.99-2f54eb?style=flat)

*Paint two fictional birds under two versions of a brief, and see each plate sitting on its own trace.*

You can't diff a picture. When an illustration pipeline drifts, the only record of what produced a given plate is whatever text someone typed into the image model, and that text usually lives in a chat thread. This app is a tiny plate generator for an imaginary regional bird field guide. It keeps the brief in the Opik prompt library, renders it for each species, calls the OpenAI Images API through a tracked client, and attaches every PNG to the trace that made it. Brief version, rendered prompt and finished picture end up in one place.

## What you'll build

- `data/species.json` holds two invented birds, the Emberbreast Wren and the Tidewatch Plover, each with a habitat, a pose note and three field marks.
- The brief template `field-guide-plate-brief` is registered in the Opik prompt library as two Mustache versions. v1 only describes the bird. v2 adds house plate conventions: plain neutral background, strict side profile, gouache style, and a leader line from each field mark to a printed label.
- Each version is rendered for each species and sent to `gpt-image-1` (quality `low`, 1024x1024), giving 4 images and 4 traces.
- The OpenAI client is wrapped with `trackOpenAI` from `opik-openai`. After the call, the base64 image goes into the trace output and the Opik SDK uploads it as a real attachment.

## See it in Opik

Open the `openai-ts-field-guide-plates` project. The Traces tab lists four `generate-plate` traces, tagged with `v1` or `v2` and the species id. Each trace has metadata with `prompt_name`, `prompt_version` and `prompt_id`, so a plate can always be traced back to the brief that made it. Open any trace: the input shows the species and the fully rendered prompt, and the attachments panel holds one PNG (1.3 to 1.6 MB each). Under it is a single `images.generate` span with model `gpt-image-1` and usage of 63 to 113 prompt tokens and 272 image output tokens. In our run each trace took 10 to 12 seconds.

Cost caveat: Opik did estimate a cost for these spans (between $0.0003 and $0.0006 each), computed from token counts. That is almost certainly below what OpenAI actually bills for a low-quality image, so use your OpenAI usage page for real spend. The span type is `general`, not `llm`.

Then open Prompts and find `field-guide-plate-brief`: exactly two versions. Open the commit/diff view and v2 shows seven added lines (the "Plate conventions" block) and a reworded first line.

What we saw in the pictures, honestly: v1 already produced a cream background and a captioned name plate, but in a three-quarter pose with scenery props (heather sprig). v2 delivered a side profile and drew leader lines to labels, which is exactly what the brief asked for. The label text, however, is garbled ("Siogle black rack conlier", "Fub bill have"). The model follows the layout instructions but cannot spell on a low-quality render. Your images will differ run to run, which is the reason to keep the version beside the picture.

## Run it yourself

1. `cd openai-ts-field-guide-plates && npm install`
2. `cp .env.example .env`, set `OPENAI_API_KEY`, and point Opik at your instance. For Opik Cloud use `OPIK_API_KEY` and `OPIK_WORKSPACE`; for a local install keep the `OPIK_URL_OVERRIDE` and `OPIK_WORKSPACE` lines from the example. A `.env` in a parent folder is also picked up.
3. `npm run demo`
4. Open the project and the prompt library as described above. PNGs are also written to `output/` (git-ignored). A full run takes about 45 seconds.

Re-running is safe: the app only creates a prompt version when no stored version has that exact text, so the library stays at two versions. New traces are added each run.

## Poke around

- Add a v3 to `src/briefs.ts` that asks for "labels in capital letters, three words maximum" and see whether the garbled lettering improves. Remember to add it to the `ensureVersion` calls and generate with it.
- Add a third species to `data/species.json` and compare the v1 and v2 plates for it.
- Change `quality: "low"` to `"medium"` in `src/main.ts` and compare label legibility and the usage numbers on the span.
- Filter traces by the `v2` tag and look at the attachments side by side with the `v1` ones.

## Gotchas we hit

**Both runs are tagged `v1`, or the library ends up with a duplicate version.** `opik.getPrompt({ name })` without a version is not a reliable "latest": it goes through the client's prompt cache and can hand back an older version, so a v2 you just created may come back as v1. The same lookup used as a dedupe check then misses the newer text and creates it again. Fix: fetch each brief by name, `opik.getPrompt({ name, version: "v2" })`, and make the dedupe check look at every stored version, `(await existing.getVersions()).some((v) => v.prompt === template)`, as `ensureVersion` in `src/main.ts` does.

**`npm install` fails with `ERESOLVE ... peer opik@"^1.8.61" from opik-openai@2.2.99`.** `opik-openai@2.2.99` still declares a peer range of `opik@^1.8.61`, which excludes the 2.x `opik` it ships alongside. Pin both at the same version and add an npm override so they share one copy:

```json
"overrides": { "opik-openai": { "opik": "$opik" } }
```

**The image span shows type `general` and a tiny cost.** `trackOpenAI` records `images.generate` as a `general` span, not an `llm` span, so LLM-type filters will not list it. Opik's cost for it is estimated from token counts (a few hundredths of a cent here), far below what OpenAI bills for a `gpt-image-1` render. Use the OpenAI usage page for real spend.

## Tests

`npm test` runs vitest offline: no `OPENAI_API_KEY`, no Opik. Tracking is disabled with Opik's `OPIK_TRACK_DISABLE=true`, which `vitest.config.ts` sets for you. The OpenAI images client is a stub.

## How it's put together

- `src/main.ts` registers brief versions, renders them, generates and traces the plates, and flushes.
- `src/briefs.ts` holds the two Mustache templates and their change descriptions.
- `data/species.json` is the fictional bird corpus.
- `tests/briefs.test.ts` renders both brief versions from the species data.
- `tests/run.test.ts` runs `main.ts` against stubbed `opik`, `opik-openai` and `openai`: version registration and dedupe on re-runs, rendered prompts, trace tags and the attached PNG.
- `tests/traced-call.test.ts` makes one call through the real `trackOpenAI` wrapper with tracking disabled.
- `tests/helpers.ts` renders Mustache the way Opik's `Prompt.format` does.
- `vitest.config.ts` sets `OPIK_TRACK_DISABLE=true` and runs tests in forked processes.
- `package.json` pins `opik` and `opik-openai` at 2.2.99 and overrides the stale peer range so they share one `opik`.
- `.env.example` lists the variables to set.

---

*built with Opik · inspired by Opik's examples and documentation*
