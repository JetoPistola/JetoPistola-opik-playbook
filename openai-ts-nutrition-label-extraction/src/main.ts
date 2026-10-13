/**
 * Nutrition-label extraction with a vision model.
 *
 * Six fictional labels are rendered to PNG at run time. gpt-4o-mini reads each
 * one with a zod-defined structured output, and the script compares every
 * extraction with the ground truth printed next to the label definition.
 */
import path from "node:path";
import process from "node:process";
import { z } from "zod";

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

const PROJECT = "openai-ts-nutrition-label-extraction";

const { default: OpenAI } = await import("openai");
const { zodResponseFormat } = await import("openai/helpers/zod");
const { LABELS, renderPng } = await import("./labels.js");

const MODEL = "gpt-4o-mini";

const NutritionLabel = z.object({
  product_name: z.string(),
  serving_size: z.string().describe("Exactly as printed, e.g. '1 bar (40 g)'"),
  calories: z.number().nullable(),
  total_fat_g: z.number().nullable(),
  sodium_mg: z.number().nullable(),
  total_carbs_g: z.number().nullable(),
  protein_g: z.number().nullable(),
  allergens: z.array(z.string()).describe("Lower-case allergens the label says it contains"),
});
type NutritionLabel = z.infer<typeof NutritionLabel>;

const SYSTEM = `You read photographed nutrition-facts labels and return the fields as JSON.
- Use the values for ONE serving as defined by the serving size.
- If a field is not printed on the label, return null for it. Never guess.
- List only allergens the label says the product contains.`;

const openai = new OpenAI();

/** One extraction: image in, validated fields out. */
async function extractLabel(labelId: string): Promise<NutritionLabel> {
  const label = LABELS.find((l) => l.id === labelId);
  if (!label) throw new Error(`unknown label ${labelId}`);
  const dataUrl = `data:image/png;base64,${renderPng(label).toString("base64")}`;
  const res = await openai.chat.completions.create({
    model: MODEL,
    temperature: 0,
    response_format: zodResponseFormat(NutritionLabel, "nutrition_label"),
    messages: [
      { role: "system", content: SYSTEM },
      {
        role: "user",
        content: [
          { type: "text", text: "Extract the label fields." },
          { type: "image_url", image_url: { url: dataUrl, detail: "high" } },
        ],
      },
    ],
  });
  return NutritionLabel.parse(JSON.parse(res.choices[0].message.content ?? "{}"));
}

async function main() {
  console.log(`${PROJECT}: reading ${LABELS.length} labels with ${MODEL}\n`);
  let passed = 0;
  for (const label of LABELS) {
    const got = await extractLabel(label.id);
    const wrong = (Object.keys(label.truth) as (keyof NutritionLabel)[]).filter(
      (k) => JSON.stringify(got[k]) !== JSON.stringify(label.truth[k]),
    );
    if (wrong.length === 0) passed++;
    console.log(`[${wrong.length === 0 ? "PASS" : "FAIL"}] ${label.id} (${label.challenge})`);
    for (const k of wrong) {
      console.log(`         ${k}: expected ${JSON.stringify(label.truth[k])}, got ${JSON.stringify(got[k])}`);
    }
  }
  console.log(`\n${passed}/${LABELS.length} labels matched the ground truth exactly`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
