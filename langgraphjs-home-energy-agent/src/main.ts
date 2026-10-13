import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "dotenv";
import { ChatOpenAI } from "@langchain/openai";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { OpikCallbackHandler } from "opik-langchain";
import { tools } from "./tools.js";

const here = dirname(fileURLToPath(import.meta.url));
// Load the repo-root .env (walk up from the app folder), then a local one if present.
for (let dir = resolve(here, ".."), i = 0; i < 4; i++, dir = dirname(dir)) {
  config({ path: resolve(dir, ".env"), quiet: true });
}

// Spans land in this Opik project; the handler below is told to use it explicitly.
const PROJECT = "langgraphjs-home-energy-agent";
const llm = new ChatOpenAI({ model: "gpt-4o-mini", temperature: 0 });

const agent = createReactAgent({
  llm,
  tools,
  prompt:
    "You are Voltie, the energy assistant for the Okonkwo-Lindgren household. Never guess numbers: " +
    "read the meter, list appliances, and estimate costs with the tools before answering. " +
    "Only schedule an appliance when the user asks you to. Be brief.",
});

const requests = [
  "How much electricity did we use yesterday between 5pm and 9pm?",
  "Which of our appliances can be shifted, and what would the dishwasher cost if I start it at 6pm versus 2am?",
  "Schedule tomorrow's dishwasher run at whichever of 6pm or 2am is cheaper, then confirm it and tell me how much I save.",
];

// One callback turns the whole agent loop into a trace tree: llm spans (tokens + cost), tool spans
// (args + returned JSON) and LangGraph plumbing as general spans. Without it Opik shows nothing.
const handler = new OpikCallbackHandler({ projectName: PROJECT });

for (const [i, question] of requests.entries()) {
  console.log(`\n[${i + 1}] ${question}`);
  // Passing the handler per invoke makes each request its own trace; runName becomes the trace name
  // (energy-request-N) and metadata is searchable on the trace.
  const result = await agent.invoke(
    { messages: [{ role: "user", content: question }] },
    { callbacks: [handler], runName: `energy-request-${i + 1}`, metadata: { request_index: i + 1 } },
  );
  const last = result.messages[result.messages.length - 1];
  console.log(`    -> ${typeof last.content === "string" ? last.content : JSON.stringify(last.content)}`);
}

// Flush before exit: spans are batched, and a short script would otherwise end with traces unsent.
await handler.flushAsync();
console.log("\nDone. Open the project", PROJECT, "in Opik.");
