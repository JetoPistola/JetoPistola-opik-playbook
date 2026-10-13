/**
 * Prompt lifecycle with the Opik prompt library (TypeScript).
 *
 * The app rewrites raw developer commit notes for a fictional notes app, Pebble,
 * into one user-facing changelog line. The system prompt lives in the Opik
 * prompt library as "changelog-rewriter": v1 is a loose "summarize this" prompt,
 * v2 adds hard rules. The same test suite runs against each version.
 */
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "dotenv";
import OpenAI from "openai";
import type { Prompt } from "opik";

const here = dirname(fileURLToPath(import.meta.url));
// Load the repo-root .env by walking up from the app folder.
for (let dir = resolve(here, ".."), i = 0; i < 4; i++, dir = dirname(dir)) {
  config({ path: resolve(dir, ".env"), quiet: true });
}

const PROJECT = "opik-ts-changelog-prompts";
// Opik: `track` uses a default client that reads OPIK_PROJECT_NAME when the SDK loads. Set it before
// the dynamic import, or every trace lands in "Default Project" instead of this project.
process.env.OPIK_PROJECT_NAME = PROJECT;
const { Opik, runTests, track, getTrackContext } = await import("opik");
const { trackOpenAI } = await import("opik-openai");
const MODEL = "gpt-4o-mini";
const PROMPT_NAME = "changelog-rewriter";

const PROMPT_V1 = `You work on Pebble, a note-taking app. Turn the developer's commit
note into a changelog entry for the release page.`;

const PROMPT_V2 = `You work on Pebble, a note-taking app. Turn the developer's commit
note into ONE changelog line for end users, following these rules exactly:

- Start with one of these verbs: Added, Fixed, Improved, Removed.
- Write a single sentence of at most 18 words.
- Describe what changes for the user, in plain language.
- Never include ticket IDs, commit hashes, file paths, or code identifiers
  (function, class, or variable names).
Output only the line, nothing else.`;

const VERSIONS = [
  { template: PROMPT_V1, change: "Initial version: generic rewrite instruction." },
  {
    template: PROMPT_V2,
    change: "Add hard rules: leading verb, one short sentence, no ticket IDs/hashes/paths/identifiers.",
  },
];

const COMMIT_NOTES = [
  "PEB-412: fix NPE in SyncQueue.flush() when offline edits exceed 50 items (a3f9c21)",
  "PEB-455 refactor: swap markdown parser to remark, drops 40% of render time on notes >10k chars. see src/render/mdPipeline.ts",
  "PEB-478 add dark mode toggle to settings screen, persisted via ThemeStore.setPreference (commit 7be01d4)",
  "PEB-490: remove deprecated /v1/export endpoint usage; export to PDF now goes through ExportService.run()",
  "PEB-503 fix: pinned notes lost their order after app restart because pinIndex was never serialized in NoteRepo.save",
];

const ASSERTIONS = [
  "The reply starts with exactly one of the words Added, Fixed, Improved, or Removed",
  "The reply is a single sentence of 18 words or fewer",
  "The reply contains no ticket IDs (like PEB-123), commit hashes, file paths, or code identifiers such as function, class, or variable names",
];

// Opik client: talks to the prompt library, the test suite and the experiments, and is flushed at exit.
const client = new Opik({ projectName: PROJECT });
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

/**
 * Push both versions to the Opik prompt library. Only creates a version whose text is not already in
 * the history, so re-runs never add a v3 (createPrompt only compares against the latest version).
 */
async function ensureVersions(): Promise<void> {
  for (const v of VERSIONS) {
    const existing = await client.getPrompt({ name: PROMPT_NAME, projectName: PROJECT });
    if (existing) {
      const history = await existing.getVersions();
      if (history.some((h) => h.prompt === v.template)) continue;
    }
    // Each createPrompt call with new text becomes a new immutable version of "changelog-rewriter".
    await client.createPrompt({
      name: PROMPT_NAME,
      prompt: v.template,
      projectName: PROJECT,
      changeDescription: v.change,
    });
  }
}

/**
 * One rewrite. `track` opens a trace named rewrite_commit_note (or a child span when called inside a
 * test-suite run); opik-openai then logs the model call, with token usage and cost, as a child span.
 */
const rewrite = track(
  { name: "rewrite_commit_note", type: "general" },
  async (note: string, prompt: Prompt): Promise<string> => {
    const ctx = getTrackContext();
    // Span metadata: lets you filter traces in Opik by the exact prompt version that produced the line.
    ctx?.span.update({
      metadata: { prompt_name: prompt.name, prompt_version: prompt.version, prompt_commit: prompt.commit },
    });
    // trackOpenAI nests the completion under this span as "rewrite-llm", with model, usage and cost.
    // Its span type is "general" (not "llm"), so filter by name or model when looking for it.
    const tracked = trackOpenAI(openai, { client, parent: ctx?.span, generationName: "rewrite-llm" });
    const res = await tracked.chat.completions.create({
      model: MODEL,
      temperature: 0.7,
      messages: [
        { role: "system", content: prompt.prompt },
        { role: "user", content: note },
      ],
    });
    return res.choices[0]?.message?.content?.trim() ?? "";
  },
);

async function main() {
  if (!process.env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not set");

  // 1. Prompt library: v1 and v2 of the same prompt.
  await ensureVersions();

  // 2. A single call with the latest version, to see the output.
  const latest = (await client.getPrompt({ name: PROMPT_NAME, projectName: PROJECT }))!;
  console.log(`Note:  ${COMMIT_NOTES[0]}`);
  console.log(`Line (${latest.version}): ${await rewrite(COMMIT_NOTES[0], latest)}\n`);

  // 3. Opik test suite (a dataset plus LLM-judged assertions): 3 runs per item, 2 must pass, to absorb judge and model flakiness.
  const suite = await client.getOrCreateTestSuite({
    name: PROJECT,
    projectName: PROJECT,
    globalAssertions: ASSERTIONS,
    globalExecutionPolicy: { runsPerItem: 3, passThreshold: 2 },
  });
  await suite.insert(COMMIT_NOTES.map((note) => ({ data: { note } })));

  // 4. Same suite, once per prompt version -> two experiments.
  const rows: string[] = [];
  for (const version of ["v1", "v2"]) {
    const prompt = await client.getPrompt({ name: PROMPT_NAME, version, projectName: PROJECT });
    if (!prompt) throw new Error(`prompt version ${version} missing`);
    // runTests runs the task over every suite item and records one experiment per prompt version,
    // linked to that prompt version; evaluation_task traces and judge spans land in the project.
    const result = await runTests({
      testSuite: suite,
      projectName: PROJECT,
      experimentName: `${PROMPT_NAME}-${version}`,
      experimentConfig: { prompt_version: version, prompt_commit: prompt.commit, model: MODEL },
      prompts: [prompt],
      model: "gpt-4o-mini",
      taskThreads: 5,
      task: async (item) => ({ input: { note: item.note }, output: await rewrite(String(item.note), prompt) }),
    });
    rows.push(
      `${PROMPT_NAME} ${version}: ${Math.round((result.passRate ?? 0) * 100)}% pass rate (${result.itemsPassed}/${result.itemsTotal} items)`,
    );
  }

  console.log("=== Prompt version comparison ===");
  rows.forEach((r) => console.log(r));
  // Flush: traces and spans are batched in memory, so without this the process can exit before they upload.
  await client.flush();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
