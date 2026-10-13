import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "dotenv";
import OpenAI from "openai";
import { SYSTEM_PROMPT, advise, conversations, priceAccuracy } from "./advisor.js";

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
// Load the repo-root .env (walk up from the app folder), then a local one if present.
for (let dir = appDir, i = 0; i < 4; i++, dir = dirname(dir)) {
  config({ path: resolve(dir, ".env"), quiet: true });
}

async function main() {
  if (!process.env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not set");
  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  let turns = 0;
  for (const convo of conversations) {
    console.log(`\n=== ${convo.threadId} ===`);
    const history: OpenAI.Chat.ChatCompletionMessageParam[] = [{ role: "system", content: SYSTEM_PROMPT }];
    let n = 0;
    for (const text of convo.turns) {
      const rec = await advise(openai, convo.threadId, ++n, history, text);
      turns++;
      console.log(`[turn ${n}] rider: ${text}\n         advisor: ${rec.reply}`);
      console.log(`         tokens in/out: ${rec.promptTokens}/${rec.completionTokens}`);
      console.log(`         price accuracy: ${priceAccuracy(rec.reply)}`);
    }
  }
  console.log(`\nAnswered ${turns} turns in ${conversations.length} conversations.`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
