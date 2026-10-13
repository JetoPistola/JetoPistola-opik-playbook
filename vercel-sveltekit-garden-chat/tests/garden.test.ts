import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { PROJECT_NAME, SYSTEM_PROMPT } from "../src/lib/server/garden";

describe("system prompt", () => {
  it("pastes the whole calendar and care notes from data/", () => {
    for (const file of ["planting-calendar.md", "plant-care.md"]) {
      expect(SYSTEM_PROMPT).toContain(readFileSync(`data/${file}`, "utf8").trim());
    }
  });

  it("keeps the persona and the do-not-guess rule", () => {
    expect(SYSTEM_PROMPT).toContain("You are Sprout");
    expect(SYSTEM_PROMPT).toContain("say so plainly instead of guessing");
  });

  it("pins the Opik project name the README and rule use", () => {
    expect(PROJECT_NAME).toBe("vercel-sveltekit-garden-chat");
  });
});
