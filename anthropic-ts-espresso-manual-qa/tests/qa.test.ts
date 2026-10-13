import fs from "node:fs";
import { describe, expect, it } from "vitest";
import {
  CASES,
  GLOBAL_ASSERTIONS,
  MODEL,
  buildSystemPrompt,
  extractQuotes,
  makeAnswerQuestion,
  makeAskClaude,
  type MessagesClient,
} from "../src/qa.js";

const MANUAL = fs.readFileSync(new URL("../docs/manual.md", import.meta.url), "utf8");

function stubClient(text: string) {
  const calls: unknown[] = [];
  const client: MessagesClient = {
    messages: {
      create: async (params) => {
        calls.push(params);
        return {
          content: [{ type: "text", text }, { type: "tool_use" }],
          usage: { input_tokens: 1100, output_tokens: 100 },
        };
      },
    },
  };
  return { client, calls };
}

describe("prompt and cases", () => {
  it("embeds the whole manual and the citation rule", () => {
    const prompt = buildSystemPrompt(MANUAL);
    expect(prompt).toContain(MANUAL);
    expect(prompt).toContain("<quote>...</quote>");
  });

  it("defines three suite-level assertions and pins the descaling and 110V items", () => {
    expect(GLOBAL_ASSERTIONS).toHaveLength(3);
    expect(CASES.filter((c) => c.assertions)).toHaveLength(2);
  });
});

describe("extractQuotes", () => {
  it("returns every quoted excerpt, trimmed", () => {
    const answer = "Every 3 months. <quote> Descale every 3 months </quote> No vinegar. <quote>Never use vinegar.</quote>";
    expect(extractQuotes(answer)).toEqual(["Descale every 3 months", "Never use vinegar."]);
  });

  it("finds no quotes in a plain refusal", () => {
    expect(extractQuotes("The manual does not cover this.")).toEqual([]);
  });
});

describe("askClaude with a stubbed Anthropic client", () => {
  it("sends the manual as system prompt and joins text blocks only", async () => {
    const { client, calls } = stubClient("Answer <quote>Never use vinegar.</quote>");
    const answer = await makeAskClaude(client, MANUAL)("Can I use vinegar?");
    expect(answer).toBe("Answer <quote>Never use vinegar.</quote>");
    expect(calls[0]).toMatchObject({ model: MODEL, messages: [{ role: "user", content: "Can I use vinegar?" }] });
    expect((calls[0] as { system: string }).system).toContain(MANUAL);
  });

  it("works through track() with Opik tracking disabled (npm test sets OPIK_TRACK_DISABLE=true)", async () => {
    const { client } = stubClient("Plain answer");
    const answerQuestion = makeAnswerQuestion(client, MANUAL);
    await expect(answerQuestion("How do I steam milk safely?")).resolves.toBe("Plain answer");
  });
});
