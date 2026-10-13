/**
 * Espresso-manual Q&A with verbatim citations, guarded by an Opik test suite.
 *
 * Claude Haiku answers questions about a fictional owner's manual and must
 * back every claim with a <quote> copied from the manual. The Opik TypeScript
 * SDK has no Anthropic wrapper, so each model call is logged by hand as an
 * `llm` span (model + provider + token usage, which is what lets Opik price it).
 * A test suite then states the quality bar in plain English and an LLM judge
 * decides pass/fail for every answer.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const here = path.dirname(fileURLToPath(import.meta.url));

// Load the nearest .env walking up from this folder (repo root in the playbook).
for (let dir = path.resolve(here, ".."); ; dir = path.dirname(dir)) {
  const candidate = path.join(dir, ".env");
  if (fs.existsSync(candidate)) {
    dotenv.config({ path: candidate });
    break;
  }
  if (path.dirname(dir) === dir) break;
}
// Talk to the real Anthropic API, not a dev proxy.
delete process.env.ANTHROPIC_BASE_URL;

// Opik's LLM judge runs on the Vercel AI SDK, which prints a warning on every
// judge call; this global flag silences it so the run output stays readable.
(globalThis as Record<string, unknown>).AI_SDK_LOG_WARNINGS = false;

const PROJECT_NAME = "anthropic-ts-espresso-manual-qa";
// Sets the Opik project: traces, spans, the test suite and its runs all land here.
// Must happen before the opik SDK is imported.
process.env.OPIK_PROJECT_NAME = PROJECT_NAME;

const { default: Anthropic } = await import("@anthropic-ai/sdk");
const { Opik, runTests } = await import("opik");
// Imported after OPIK_PROJECT_NAME is set so track() picks up the project.
const { CASES, GLOBAL_ASSERTIONS, MODEL, makeAnswerQuestion } = await import("./qa.js");

const MANUAL = fs.readFileSync(path.join(here, "..", "docs", "manual.md"), "utf8");

const anthropic = new Anthropic({ baseURL: "https://api.anthropic.com" });

const answerQuestion = makeAnswerQuestion(anthropic, MANUAL);

async function main(): Promise<void> {
  // Opik client: needed for the test suite API and for flushing at the end.
  const client = new Opik({ projectName: PROJECT_NAME });

  // 1. Tracing demo (one `answer_question` trace with an llm child span): one answered question.
  const demo = CASES[0].question;
  console.log(`Q: ${demo}`);
  console.log(`A: ${await answerQuestion(demo)}\n`);

  // 2. Build the suite. Items carry the question AND the manual (so the judge
  // can check quotes), but no expected answers. Each item runs 3 times and must
  // pass 2 of them, which absorbs judge and model flakiness.
  // getOrCreateTestSuite: the suite shows up under "Test suites" in Opik. Global
  // assertions apply to every item; the policy makes each item pass on 2 of 3 runs.
  const suite = await client.getOrCreateTestSuite({
    name: PROJECT_NAME,
    projectName: PROJECT_NAME,
    globalAssertions: GLOBAL_ASSERTIONS,
    globalExecutionPolicy: { runsPerItem: 3, passThreshold: 2 },
  });
  // Items hold the question and the manual, so the judge can check quotes verbatim.
  await suite.insert(
    CASES.map((c) => ({
      data: { question: c.question, context: MANUAL },
      ...(c.assertions ? { assertions: c.assertions } : {}),
    })),
  );

  // 3. Run: answer every question, judge every assertion (Claude judges too).
  // runTests: runs the task per item/run (each an `evaluation_task` trace), then an
  // LLM judge scores every assertion pass/fail with a reason, logged as an experiment.
  const result = await runTests({
    testSuite: suite,
    projectName: PROJECT_NAME,
    model: MODEL,
    taskThreads: 3,
    task: async (item) => {
      const question = String(item.question);
      return { input: item, output: await answerQuestion(question) };
    },
  });

  // 4. Summarize.
  const rate = result.passRate === undefined ? "n/a" : `${Math.round(result.passRate * 100)}%`;
  console.log(`Pass rate: ${rate} (${result.itemsPassed}/${result.itemsTotal} items passed)`);
  for (const item of result.itemResults.values()) {
    const question = (item.testResults[0].testCase.taskOutput["input"] as { question: string }).question;
    console.log(`  [${item.passed ? "PASS" : "FAIL"}] ${question}  (${item.runsPassed}/${item.runsTotal} runs)`);
    if (!item.passed) {
      for (const run of item.testResults) {
        for (const s of run.scoreResults) {
          if (s.scoringFailed || s.value !== 1) console.log(`         failed: ${s.name} - ${s.reason}`);
        }
      }
    }
  }
  if (result.experimentUrl) console.log(`\nView the run: ${result.experimentUrl}`);

  // Without flush() the batched traces may not be sent before the process exits.
  await client.flush();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
