import fs from "node:fs";
import { describe, expect, it } from "vitest";
import { renderBrief } from "./helpers.js";
import { BRIEF_V1, BRIEF_V2, PROMPT_NAME } from "../src/briefs.js";

const species = JSON.parse(fs.readFileSync("data/species.json", "utf8"));

const vars = (bird: (typeof species)[number]) => ({
  ...bird,
  field_marks: bird.field_marks.join("; "),
});

describe("brief rendering", () => {
  it("fills every placeholder from the species data", () => {
    for (const bird of species) {
      for (const template of [BRIEF_V1, BRIEF_V2]) {
        const text = renderBrief(template, vars(bird));
        expect(text).not.toMatch(/\{\{/);
        expect(text).toContain(bird.common_name);
        expect(text).toContain(bird.habitat);
        expect(text).toContain(bird.pose_note);
        expect(text).toContain(bird.field_marks.join("; "));
      }
    }
  });

  it("v2 adds the plate conventions that v1 lacks", () => {
    const bird = vars(species[0]);
    expect(renderBrief(BRIEF_V1, bird)).not.toContain("Plate conventions");
    expect(renderBrief(BRIEF_V2, bird)).toContain("Strict side profile");
  });
});
