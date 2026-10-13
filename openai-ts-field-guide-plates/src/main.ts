// Field-guide plate generator: renders the brief for every species in
// data/species.json and paints one plate per bird with gpt-image-1. Each plate
// is traced in Opik with the PNG attached to its trace.
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import OpenAI from "openai";
import { Opik } from "opik";
import { trackOpenAI } from "opik-openai";
import { BRIEF, render } from "./briefs.js";

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

// The client sends traces to the Opik project named here; without a project
// name they would land in "Default Project".
const opik = new Opik({ projectName: PROJECT });
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function generatePlate(bird: Species): Promise<string> {
  const imagePrompt = render(BRIEF, {
    ...bird,
    field_marks: bird.field_marks.join("; "),
  });

  // A manual trace per plate: its input holds the rendered prompt, and it is the
  // parent that groups the image span and the PNG attachment.
  const trace = opik.trace({
    name: "generate-plate",
    input: { species: bird.common_name, image_prompt: imagePrompt },
    tags: [bird.id],
  });
  // trackOpenAI wraps the client: images.generate becomes a span under `trace`
  // (typed "general", not "llm") with model and token usage.
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

    const file = path.join(OUTPUT_DIR, `${bird.id}.png`);
    fs.writeFileSync(file, Buffer.from(b64, "base64"));

    // A large base64 data URI in the trace output is uploaded by the Opik SDK
    // as a real attachment: the PNG shows in the trace's attachments panel.
    trace.update({
      output: { plate: `data:image/png;base64,${b64}`, model: MODEL, size: SIZE },
    });
    return file;
  } finally {
    // Ends the trace; skipping it would leave the trace without an end time.
    trace.end();
  }
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  for (const bird of species) {
    const file = await generatePlate(bird);
    console.log(`${bird.common_name} -> ${file}`);
  }
  // The SDK batches sends in the background; flush before the process exits
  // or the last traces and attachments never reach Opik.
  await opik.flush();
  console.log(`\nDone. Plates are in output/; open project "${PROJECT}" in Opik.`);
}

main().catch(async (e) => {
  console.error("Run failed:", e);
  await opik.flush();
  process.exit(1);
});
