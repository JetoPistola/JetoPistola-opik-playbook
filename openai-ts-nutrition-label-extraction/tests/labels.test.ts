import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { LABELS, renderPng } from "../src/labels.js";

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const sha = (b: Buffer) => createHash("sha256").update(b).digest("hex");

describe("label rendering", () => {
  it("defines six labels with unique ids", () => {
    expect(LABELS).toHaveLength(6);
    expect(new Set(LABELS.map((l) => l.id)).size).toBe(6);
  });

  it("renders every label to a PNG larger than the lowered attachment threshold", () => {
    for (const label of LABELS) {
      const png = renderPng(label);
      expect(png.subarray(0, 8).equals(PNG_MAGIC)).toBe(true);
      // main.ts sets the attachment threshold to 10,000 characters of base64.
      expect(png.toString("base64").length).toBeGreaterThan(10_000);
    }
  });

  it("renders identical bytes on repeated calls", () => {
    for (const label of LABELS) {
      expect(sha(renderPng(label))).toBe(sha(renderPng(label)));
    }
  });

  it("keeps the sodium-less label honest: the ground truth is null", () => {
    const label = LABELS.find((l) => l.id === "no-sodium-line");
    expect(label?.truth.sodium_mg).toBeNull();
    expect(label?.svg.toLowerCase()).not.toContain("sodium");
  });
});
