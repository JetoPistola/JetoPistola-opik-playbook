import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type OpenAI from "openai";
import type { Opik, Trace } from "opik";
import { trackOpenAI } from "opik-openai";

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export const MODEL = "gpt-4o-mini";

export interface Catalog {
  shop: string;
  labor_rate_per_hour_usd: number;
  parts: { sku: string; name: string; price_usd: number }[];
  services: { name: string; hours: number }[];
}
export const catalog: Catalog = JSON.parse(readFileSync(resolve(appDir, "data/parts.json"), "utf8"));

const priceList = [
  ...catalog.parts.map((p) => `- ${p.name} [${p.sku}]: $${p.price_usd.toFixed(2)}`),
  ...catalog.services.map(
    (s) => `- ${s.name}: ${s.hours} h x $${catalog.labor_rate_per_hour_usd}/h = $${(s.hours * catalog.labor_rate_per_hour_usd).toFixed(2)}`,
  ),
].join("\n");

export const SYSTEM_PROMPT = `You are the repair advisor for ${catalog.shop}, a small bike shop.
Diagnose problems from the rider's description, say what to do, and quote costs ONLY from this price list.
If something is not on the list, say a mechanic must inspect it. Keep replies under 90 words.

Price list:
${priceList}`;

// Three fictional riders, each a multi-turn conversation. `happy` is the thumbs-up we log afterwards.
export const conversations = [
  {
    threadId: "rider-maya-flat-tire",
    happy: true,
    turns: [
      "My commuter bike's rear tire goes soft every two days. 700x28 tires. What's going on?",
      "I found a tiny thorn in the tread. Can you just swap the tube?",
      "What would that cost in total with labor?",
    ],
  },
  {
    threadId: "rider-omar-brake-squeal",
    happy: true,
    turns: [
      "My disc brakes squeal loudly when I stop in the rain.",
      "The pads look glazed and shiny. Replace them on both wheels?",
      "Give me the full price for both wheels, parts and labor.",
      "Can you also true my wheels for free while I'm there?",
    ],
  },
  {
    threadId: "rider-lena-ghost-shifting",
    happy: false,
    turns: [
      "My 11-speed bike skips gears under load and the chain looks rusty.",
      "It has about 6000 km on it. Is a new chain enough?",
      "What if I replace the cassette too? Total with labor please.",
    ],
  },
];

export interface TurnRecord {
  threadId: string;
  turn: number;
  trace: Trace;
  reply: string;
  promptTokens: number;
  completionTokens: number;
}

export async function advise(
  client: Opik,
  openai: OpenAI,
  threadId: string,
  turn: number,
  history: OpenAI.Chat.ChatCompletionMessageParam[],
  userText: string,
): Promise<TurnRecord> {
  history.push({ role: "user", content: userText });
  // One trace per turn; sharing a threadId is what makes Opik show the turns as one conversation
  // in the Threads tab. trackOpenAI has no threadId option, so we own the trace and pass it as parent.
  const trace = client.trace({
    name: "advise-turn",
    threadId,
    input: { message: userText, turn },
    metadata: { turn, shop: catalog.shop },
  });
  // Wrapping with parent: trace nests the model call under this trace as a child span named
  // advisor-llm, carrying the message array, token usage and cost (the span type is `general`, not `llm`).
  const tracked = trackOpenAI(openai, { client, parent: trace, generationName: "advisor-llm" });
  const res = await tracked.chat.completions.create({
    model: MODEL,
    temperature: 0.2,
    messages: history,
  });
  const reply = res.choices[0]?.message?.content ?? "";
  history.push({ role: "assistant", content: reply });
  // Record the reply as the trace output and close it; without end() the trace has no end time.
  trace.update({ output: { reply } });
  trace.end();
  return {
    threadId,
    turn,
    trace,
    reply,
    promptTokens: res.usage?.prompt_tokens ?? 0,
    completionTokens: res.usage?.completion_tokens ?? 0,
  };
}

// Cheap deterministic check: every dollar amount in the reply should be derivable from the price list.
export function priceAccuracy(reply: string): number {
  const known = new Set<number>([
    ...catalog.parts.map((p) => p.price_usd),
    ...catalog.services.map((s) => s.hours * catalog.labor_rate_per_hour_usd),
  ]);
  const amounts = [...reply.matchAll(/\$(\d+(?:\.\d+)?)/g)].map((m) => Number(m[1]));
  if (amounts.length === 0) return 1;
  // Totals are sums of items, so accept any sum of up to 4 known values (with repetition).
  const sums = new Set<number>(known);
  for (let k = 0; k < 3; k++) for (const s of [...sums]) for (const v of known) sums.add(Math.round((s + v) * 100) / 100);
  const ok = amounts.filter((a) => sums.has(Math.round(a * 100) / 100)).length;
  return Number((ok / amounts.length).toFixed(2));
}

type FeedbackScores = Parameters<Opik["logTracesFeedbackScores"]>[0];

// Builds the post-run feedback: price-accuracy on every turn's trace, user-satisfaction on each
// conversation's last turn. These become the Feedback scores columns in the Traces tab.
export function buildFeedbackScores(all: TurnRecord[]): FeedbackScores {
  const scores: FeedbackScores = [];
  for (const rec of all) {
    scores.push({
      id: rec.trace.data.id,
      name: "price-accuracy",
      value: priceAccuracy(rec.reply),
      reason: "share of quoted dollar amounts that match the price list",
    });
  }
  for (const convo of conversations) {
    const last = [...all].reverse().find((r) => r.threadId === convo.threadId)!;
    scores.push({
      id: last.trace.data.id,
      name: "user-satisfaction",
      value: convo.happy ? 1 : 0,
      reason: convo.happy ? "rider clicked thumbs-up" : "rider clicked thumbs-down: total felt too high",
    });
  }
  return scores;
}
