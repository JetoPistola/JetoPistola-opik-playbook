// Field-guide plate generator. One run:
//   1. registers the plate brief in the Opik prompt library (v1, then v2),
//   2. renders each version for every species in data/species.json,
//   3. generates one image per render with a tracked OpenAI client; the PNG
//      goes into the trace output so Opik stores it as an attachment.
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import OpenAI from "openai";
import { Opik, PromptType, type Prompt } from "opik";
import { trackOpenAI } from "opik-openai";
import { BRIEF_V1, BRIEF_V2, PROMPT_NAME, V1_CHANGE, V2_CHANGE } from "./briefs.js";

delete process.env.OPENAI_BASE_URL;

// Own .env first, then walk up to the repo root. Existing env vars win.
for (let dir = process.cwd(), i = 0; i < 4; i++, dir = path.dirname(dir)) {
  try {
    process.loadEnvFile(path.join(dir, ".env"));
  } catch {
    /* not here */
  }
}
if (!process.env.OPENAI_API_KEY) {
  console.error("OPENAI_API_KEY is not set. Add it to .env and re-run.");
  process.exit(1);
}

const PROJECT = "openai-ts-field-guide-plates";
const MODEL = "gpt-image-1";
const SIZE = "1024x1024";
const OUTPUT_DIR = "output";

interface Species {
  id: string;
  common_name: string;
  habitat: string;
  pose_note: string;
  field_marks: string[];
}
const species: Species[] = JSON.parse(
  fs.readFileSync(path.resolve("data/species.json"), "utf8"),
);

// projectName sends traces to this project and also scopes the prompt library
// entry below; without it everything lands in "Default Project".
const opik = new Opik({ projectName: PROJECT });
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// Opik prompt library: createPrompt does not dedupe by version, and getPrompt()
// without a version is not a reliable "latest", so check every stored version's
// text instead. A fresh library ends with exactly 2 versions (v1, v2) in the
// Prompts tab, and re-runs add nothing.
async function ensureVersion(template: string, change: string): Promise<void> {
  const existing = await opik.getPrompt({ name: PROMPT_NAME });
  if (existing) {
    const versions = await existing.getVersions();
    if (versions.some((v) => v.prompt === template)) return;
  }
  await opik.createPrompt({
    name: PROMPT_NAME,
    prompt: template,
    type: PromptType.MUSTACHE,
    changeDescription: change,
    tags: ["image-generation", "field-guide"],
    projectName: PROJECT,
  });
}

async function generatePlate(prompt: Prompt, bird: Species): Promise<string> {
  const imagePrompt = prompt.format({
    ...bird,
    field_marks: bird.field_marks.join("; "),
  });
  const version = prompt.version ?? "unknown";

  // One trace per plate. Tags and metadata tie it to the brief version, so the
  // Traces tab can filter by v1/v2 and the prompt can be found from the picture.
  const trace = opik.trace({
    name: "generate-plate",
    input: { species: bird.common_name, image_prompt: imagePrompt },
    tags: [version, bird.id],
    metadata: { prompt_name: PROMPT_NAME, prompt_version: version, prompt_id: prompt.id },
  });
  // trackOpenAI wraps the client: images.generate becomes a child span of `trace`
  // with model and token usage (typed "general", not "llm"; the cost is a
  // token-based estimate, far below real image pricing).
  const tracked = trackOpenAI(openai, {
    client: opik,
    parent: trace,
    generationName: "images.generate",
  });

  try {
    const result = await tracked.images.generate({
      model: MODEL,
      prompt: imagePrompt,
      n: 1,
      size: SIZE,
      quality: "low",
    });
    const b64 = result.data?.[0]?.b64_json;
    if (!b64) throw new Error("no image data returned");

    const file = path.join(OUTPUT_DIR, `${version}-${bird.id}.png`);
    fs.writeFileSync(file, Buffer.from(b64, "base64"));

    // A large base64 data URI in the trace output is uploaded by the Opik SDK as
    // a real attachment: the PNG shows in the trace's attachments panel.
    trace.update({
      output: { plate: `data:image/png;base64,${b64}`, model: MODEL, size: SIZE },
    });
    return file;
  } finally {
    // Ends the trace even when the image call throws.
    trace.end();
  }
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  await ensureVersion(BRIEF_V1, V1_CHANGE);
  await ensureVersion(BRIEF_V2, V2_CHANGE);

  const v1 = await opik.getPrompt({ name: PROMPT_NAME, version: "v1" });
  // Ask for versions by name: "latest" can lag right after createPrompt.
  const v2 = await opik.getPrompt({ name: PROMPT_NAME, version: "v2" });
  if (!v1 || !v2) throw new Error("brief versions missing from the library");

  // compareTo prints the v1 -> v2 text diff to the terminal; the same diff is in
  // the Prompts tab's commit view.
  const versions = await v2.getVersions();
  console.log(`"${PROMPT_NAME}" has ${versions.length} versions. Diff:`);
  if (versions.length >= 2) versions[0].compareTo(versions[versions.length - 1]);

  for (const prompt of [v1, v2]) {
    console.log(`\nBrief ${prompt.version}:`);
    for (const bird of species) {
      const file = await generatePlate(prompt, bird);
      console.log(`  ${bird.common_name} -> ${file}`);
    }
  }

  // The SDK batches sends in the background; flush before the process exits
  // or the last traces and attachments never reach Opik.
  await opik.flush();
  console.log(`\nDone. Open project "${PROJECT}" in Opik.`);
}

main().catch(async (e) => {
  console.error("Run failed:", e);
  await opik.flush();
  process.exit(1);
});
