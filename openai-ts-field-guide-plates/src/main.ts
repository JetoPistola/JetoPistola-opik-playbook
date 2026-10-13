// Field-guide plate generator: renders the brief for every species in
// data/species.json and paints one plate per bird with gpt-image-1.
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import OpenAI from "openai";
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

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function generatePlate(bird: Species): Promise<string> {
  const imagePrompt = render(BRIEF, {
    ...bird,
    field_marks: bird.field_marks.join("; "),
  });
  const result = await openai.images.generate({
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
  return file;
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  for (const bird of species) {
    const file = await generatePlate(bird);
    console.log(`${bird.common_name} -> ${file}`);
  }
  console.log("\nDone. Plates are in output/.");
}

main().catch((e) => {
  console.error("Run failed:", e);
  process.exit(1);
});
