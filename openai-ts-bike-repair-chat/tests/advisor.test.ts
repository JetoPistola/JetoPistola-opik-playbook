import { describe, expect, it } from "vitest";
import { Opik } from "opik";
import type OpenAI from "openai";
import { SYSTEM_PROMPT, advise, buildFeedbackScores, catalog, conversations, priceAccuracy, type TurnRecord } from "../src/advisor.js";

// Stub model client: no network, no key. Returns a canned reply with usage numbers.
function stubOpenAI(reply: string): OpenAI {
  const create = async () => ({
    id: "chatcmpl-stub",
    object: "chat.completion",
    created: 0,
    model: "gpt-4o-mini",
    choices: [{ index: 0, finish_reason: "stop", message: { role: "assistant", content: reply } }],
    usage: { prompt_tokens: 12, completion_tokens: 5, total_tokens: 17 },
  });
  return { chat: { completions: { create } } } as unknown as OpenAI;
}

describe("priceAccuracy", () => {
  it("scores 1 for replies with no dollar amounts", () => {
    expect(priceAccuracy("A mechanic must inspect that.")).toBe(1);
  });

  it("accepts single prices and sums of listed prices", () => {
    const tube = catalog.parts.find((p) => p.sku === "TUBE-700x28")!.price_usd;
    const labor = catalog.services[0]!.hours * catalog.labor_rate_per_hour_usd;
    expect(priceAccuracy(`The tube is $${tube}.`)).toBe(1);
    expect(priceAccuracy(`Total: $${(tube + labor).toFixed(2)}.`)).toBe(1);
  });

  it("penalises amounts that are not on the price list", () => {
    expect(priceAccuracy("That is $7.50 plus $999.")).toBe(0.5);
  });
});

describe("prompt and conversations", () => {
  it("puts every part and service into the system prompt", () => {
    for (const p of catalog.parts) expect(SYSTEM_PROMPT).toContain(p.sku);
    for (const s of catalog.services) expect(SYSTEM_PROMPT).toContain(s.name);
  });

  it("defines three conversations with unique thread ids", () => {
    expect(conversations).toHaveLength(3);
    expect(new Set(conversations.map((c) => c.threadId)).size).toBe(3);
  });
});

// Run with OPIK_TRACK_DISABLE=true (npm test sets it): the Opik trace and the trackOpenAI wrapper
// become no-ops, so the traced code path runs against a stub with nothing sent to a server.
describe("advise with tracking disabled", () => {
  it("returns the reply, appends to history and records usage", async () => {
    const client = new Opik({ projectName: "offline-tests" });
    const history: OpenAI.Chat.ChatCompletionMessageParam[] = [{ role: "system", content: SYSTEM_PROMPT }];
    const rec = await advise(client, stubOpenAI("Swap the tube for $7.50."), "t-1", 1, history, "Flat tire?");
    expect(rec.reply).toBe("Swap the tube for $7.50.");
    expect(rec.promptTokens).toBe(12);
    expect(rec.completionTokens).toBe(5);
    expect(history.map((m) => m.role)).toEqual(["system", "user", "assistant"]);
  });

  it("builds price-accuracy for every turn and satisfaction on each last turn", async () => {
    const client = new Opik({ projectName: "offline-tests" });
    const records: TurnRecord[] = [];
    for (const convo of conversations) {
      const history: OpenAI.Chat.ChatCompletionMessageParam[] = [];
      let n = 0;
      for (const text of convo.turns) records.push(await advise(client, stubOpenAI("Fine."), convo.threadId, ++n, history, text));
    }
    const scores = buildFeedbackScores(records);
    expect(scores.filter((s) => s.name === "price-accuracy")).toHaveLength(records.length);
    const sat = scores.filter((s) => s.name === "user-satisfaction");
    expect(sat.map((s) => s.value)).toEqual([1, 1, 0]);
  });
});
