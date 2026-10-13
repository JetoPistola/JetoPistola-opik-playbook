/**
 * Nutrition-label extraction with image attachments and a test suite.
 *
 * Six fictional labels are rendered to PNG at run time. gpt-4o-mini reads each
 * one with a zod-defined structured output; opik-openai traces the call, and
 * the label image (sent as a base64 data URL) is stored by Opik as an
 * attachment. A test suite then pins the ground truth for every label and an
 * LLM judge grades each extraction.
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

// Opik reads its settings from env vars at import time, so everything Opik-related
// is configured above the dynamic imports below.
const PROJECT = "openai-ts-nutrition-label-extraction";
// Names the project every trace lands in; the default track() client reads it at import time.
process.env.OPIK_PROJECT_NAME = PROJECT;
// Opik only lifts inline base64 images into trace attachments above 256 KB of encoded
// text by default. Our label PNGs are 30-90 KB, so lower the bar to 10 KB; without
// this most labels would have no image in the Attachments tab.
process.env.OPIK_MIN_BASE64_EMBEDDED_ATTACHMENT_SIZE ??= "10000";
(globalThis as Record<string, unknown>).AI_SDK_LOG_WARNINGS = false;

const { default: OpenAI } = await import("openai");
const { zodResponseFormat } = await import("openai/helpers/zod");
// Opik is imported dynamically so the env vars above are already set when it loads.
const { Opik, track, runTests, getTrackContext } = await import("opik");
const { trackOpenAI } = await import("opik-openai");
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

// Explicit client so the traces and the test suite both go to the same project.
const opik = new Opik({ projectName: PROJECT });
const rawOpenAI = new OpenAI();

/** One extraction: image in, validated fields out. The data URL in the message
 *  is what Opik turns into a trace attachment. */
// track() makes this function the parent span (type general) named extract_label, so
// each model call below nests under it, whether called directly or from the suite.
const extractLabel = track(
  { name: "extract_label", type: "general" },
  async (labelId: string): Promise<NutritionLabel> => {
    const label = LABELS.find((l) => l.id === labelId);
    if (!label) throw new Error(`unknown label ${labelId}`);
    const dataUrl = `data:image/png;base64,${renderPng(label).toString("base64")}`;
    // trackOpenAI logs the completion as a span (typed general, not llm) with usage and the
    // image in Attachments. Without parent: the active span it would open its own trace.
    const openai = trackOpenAI(rawOpenAI, {
      client: opik,
      generationName: "read-label",
      parent: getTrackContext()?.span,
    });
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
  },
);

const fmt = (v: unknown) => (v === null ? "none printed" : JSON.stringify(v));

function assertionsFor(t: (typeof LABELS)[number]["truth"]): string[] {
  const allergens = t.allergens.length ? t.allergens.join(", ") : "none (empty list)";
  return [
    `calories is ${fmt(t.calories)}, total_fat_g is ${fmt(t.total_fat_g)} and total_carbs_g is ${fmt(t.total_carbs_g)}`,
    `sodium_mg is ${fmt(t.sodium_mg)}${t.sodium_mg === null ? " (null; the label has no sodium line, so any number is invented)" : ""} and protein_g is ${fmt(t.protein_g)}`,
    `serving_size is "${t.serving_size}", product_name is "${t.product_name}" and the allergens list is: ${allergens}`,
  ];
}

async function main() {
  // 1. A quick look at one label.
  const first = LABELS[0];
  console.log(`Reading ${first.id}...`);
  console.log(await extractLabel(first.id), "\n");

  // 2. Build the suite (it shows up in Opik under Test suites): item data = which label,
  //    plus the challenge note. The suite-level assertions apply to every item; each
  //    item pins its own truth.
  const suite = await opik.getOrCreateTestSuite({
    name: PROJECT,
    projectName: PROJECT,
    description: "Ground truth for six fictional nutrition labels",
    globalAssertions: [
      "The response is a JSON object with every field present: product_name, serving_size, calories, total_fat_g, sodium_mg, total_carbs_g, protein_g, allergens",
      "The numeric fields (calories, total_fat_g, sodium_mg, total_carbs_g, protein_g) are plain numbers or null, never strings with units",
    ],
    globalExecutionPolicy: { runsPerItem: 1, passThreshold: 1 },
  });
  await suite.insert(
    LABELS.map((l) => ({
      data: { label_id: l.id, challenge: l.challenge },
      description: l.challenge,
      assertions: assertionsFor(l.truth),
    })),
  );

  // 3. runTests runs the task per item and the LLM judge grades each assertion; the
  //    result is an experiment in Opik with one trace per label (evaluation_task).
  const result = await runTests({
    testSuite: suite,
    projectName: PROJECT,
    model: MODEL,
    taskThreads: 3,
    task: async (item) => {
      const extraction = await extractLabel(String(item.label_id));
      return { input: item, output: extraction };
    },
  });

  // 4. Report honestly.
  const rate = result.passRate === undefined ? "n/a" : `${Math.round(result.passRate * 100)}%`;
  console.log(`Pass rate: ${rate} (${result.itemsPassed}/${result.itemsTotal} labels passed)`);
  for (const item of result.itemResults.values()) {
    const input = item.testResults[0].testCase.taskOutput["input"] as { label_id: string };
    console.log(`  [${item.passed ? "PASS" : "FAIL"}] ${input.label_id}`);
    if (!item.passed) {
      for (const run of item.testResults) {
        console.log(`         output: ${JSON.stringify(run.testCase.taskOutput["output"])}`);
        for (const s of run.scoreResults) {
          if (s.scoringFailed || s.value !== 1) console.log(`         failed: ${s.name} - ${s.reason}`);
        }
      }
    }
  }
  if (result.experimentUrl) console.log(`\nView the run: ${result.experimentUrl}`);

  // The script exits right after this; flush sends the batched traces and attachments first.
  await opik.flush();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
