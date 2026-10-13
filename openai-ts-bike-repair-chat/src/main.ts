import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "dotenv";
import OpenAI from "openai";
import { Opik } from "opik";
import { SYSTEM_PROMPT, advise, buildFeedbackScores, conversations, type TurnRecord } from "./advisor.js";

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
// Load the repo-root .env (walk up from the app folder), then a local one if present.
for (let dir = appDir, i = 0; i < 4; i++, dir = dirname(dir)) {
  config({ path: resolve(dir, ".env"), quiet: true });
}

const PROJECT = "openai-ts-bike-repair-chat";

// Opik client: everything below lands in this project; URL and workspace come from OPIK_* env vars.
const client = new Opik({ projectName: PROJECT });
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function main() {
  if (!process.env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not set");
  const all: TurnRecord[] = [];
  for (const convo of conversations) {
    console.log(`\n=== ${convo.threadId} ===`);
    const history: OpenAI.Chat.ChatCompletionMessageParam[] = [{ role: "system", content: SYSTEM_PROMPT }];
    let n = 0;
    for (const text of convo.turns) {
      const rec = await advise(client, openai, convo.threadId, ++n, history, text);
      all.push(rec);
      console.log(`[turn ${n}] rider: ${text}\n         advisor: ${rec.reply}`);
      console.log(`         tokens in/out: ${rec.promptTokens}/${rec.completionTokens}`);
    }
  }

  // After the run: attach feedback scores to the traces we already sent.
  const scores = buildFeedbackScores(all);
  client.logTracesFeedbackScores(scores);

  // flush() waits for the batched traces, spans and scores to be delivered; a short script
  // would otherwise exit before they are sent and the project would look empty.
  await client.flush();
  console.log(`\nLogged ${all.length} traces in ${conversations.length} threads and ${scores.length} feedback scores to project "${PROJECT}".`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
