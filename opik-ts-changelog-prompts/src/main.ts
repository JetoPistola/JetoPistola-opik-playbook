/**
 * Changelog-line rewriter for Pebble, a fictional note-taking app.
 *
 * Takes raw developer commit notes and rewrites each one into a single
 * user-facing changelog line with an LLM. The system prompt is hard-coded.
 */
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "dotenv";
import OpenAI from "openai";

const here = dirname(fileURLToPath(import.meta.url));
// Load the repo-root .env by walking up from the app folder.
for (let dir = resolve(here, ".."), i = 0; i < 4; i++, dir = dirname(dir)) {
  config({ path: resolve(dir, ".env"), quiet: true });
}

const MODEL = "gpt-4o-mini";

const SYSTEM_PROMPT = `You work on Pebble, a note-taking app. Turn the developer's commit
note into ONE changelog line for end users, following these rules exactly:

- Start with one of these verbs: Added, Fixed, Improved, Removed.
- Write a single sentence of at most 18 words.
- Describe what changes for the user, in plain language.
- Never include ticket IDs, commit hashes, file paths, or code identifiers
  (function, class, or variable names).
Output only the line, nothing else.`;

const COMMIT_NOTES = [
  "PEB-412: fix NPE in SyncQueue.flush() when offline edits exceed 50 items (a3f9c21)",
  "PEB-455 refactor: swap markdown parser to remark, drops 40% of render time on notes >10k chars. see src/render/mdPipeline.ts",
  "PEB-478 add dark mode toggle to settings screen, persisted via ThemeStore.setPreference (commit 7be01d4)",
  "PEB-490: remove deprecated /v1/export endpoint usage; export to PDF now goes through ExportService.run()",
  "PEB-503 fix: pinned notes lost their order after app restart because pinIndex was never serialized in NoteRepo.save",
];

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function rewrite(note: string): Promise<string> {
  const res = await openai.chat.completions.create({
    model: MODEL,
    temperature: 0.7,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: note },
    ],
  });
  return res.choices[0]?.message?.content?.trim() ?? "";
}

async function main() {
  if (!process.env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not set");
  for (const note of COMMIT_NOTES) {
    console.log(`Note:  ${note}`);
    console.log(`Line:  ${await rewrite(note)}\n`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
