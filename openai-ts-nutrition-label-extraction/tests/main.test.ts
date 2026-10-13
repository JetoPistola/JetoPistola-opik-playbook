// Imports src/main.ts with the OpenAI client, the Opik client and the judge-backed
// runTests stubbed, then checks what the script hands to each of them. Nothing here
// talks to OpenAI or Opik. OPIK_TRACK_DISABLE=true (also set below) makes the real
// track() wrapper a pass-through.
import { beforeAll, describe, expect, it, vi } from "vitest";
import { LABELS } from "../src/labels.js";

process.env.OPIK_TRACK_DISABLE = "true";
process.env.OPENAI_API_KEY = "test-key-not-real";

const calls = vi.hoisted(() => ({
  create: [] as any[],
  insert: [] as any[],
  suite: [] as any[],
}));

const EXTRACTION = {
  product_name: "Stub",
  serving_size: "1 stub",
  calories: 1,
  total_fat_g: null,
  sodium_mg: null,
  total_carbs_g: 2,
  protein_g: 3,
  allergens: [],
};

vi.mock("openai", () => ({
  default: class {
    chat = {
      completions: {
        create: async (args: unknown) => {
          calls.create.push(args);
          return { choices: [{ message: { content: JSON.stringify(EXTRACTION) } }] };
        },
      },
    };
  },
}));

// Real track()/getTrackContext, stubbed Opik client and runTests.
vi.mock("opik", async (importOriginal) => ({
  ...(await importOriginal<typeof import("opik")>()),
  Opik: class {
    async getOrCreateTestSuite(cfg: unknown) {
      calls.suite.push(cfg);
      return { insert: async (items: unknown) => void calls.insert.push(items) };
    }
    async flush() {}
  },
  runTests: async (args: any) => {
    const item = { label_id: LABELS[0].id };
    await args.task(item);
    return { passRate: 1, itemsPassed: 1, itemsTotal: 1, itemResults: new Map() };
  },
}));

// trackOpenAI would wrap the client in a proxy; hand back the stub unchanged.
vi.mock("opik-openai", () => ({ trackOpenAI: (client: unknown) => client }));

beforeAll(async () => {
  vi.spyOn(console, "log").mockImplementation(() => {});
  await import("../src/main.js");
  await vi.waitFor(() => expect(calls.insert.length).toBe(1));
});

describe("extraction request", () => {
  it("sends the label PNG as a base64 data URL with a strict zod-derived schema", () => {
    const req = calls.create[0];
    expect(req.model).toBe("gpt-4o-mini");
    const image = req.messages[1].content[1].image_url;
    expect(image.url.startsWith("data:image/png;base64,")).toBe(true);
    expect(image.detail).toBe("high");

    const schema = req.response_format.json_schema;
    expect(schema.strict).toBe(true);
    expect(Object.keys(schema.schema.properties)).toEqual([
      "product_name",
      "serving_size",
      "calories",
      "total_fat_g",
      "sodium_mg",
      "total_carbs_g",
      "protein_g",
      "allergens",
    ]);
    // Every field is required; numeric ones accept null for "not printed".
    expect(schema.schema.required).toHaveLength(8);
    expect(schema.schema.properties.sodium_mg).toMatchObject({ type: "number", nullable: true });
    expect(schema.schema.properties.allergens.items.type).toBe("string");
  });

  it("runs the traced extract_label function with tracking disabled", () => {
    // The quick look at the first label plus the stubbed suite item.
    expect(calls.create.length).toBeGreaterThanOrEqual(2);
  });
});

describe("test suite definition", () => {
  it("creates one suite named after the project with strict pass policy", () => {
    const cfg = calls.suite[0];
    expect(cfg.name).toBe("openai-ts-nutrition-label-extraction");
    expect(cfg.globalAssertions).toHaveLength(2);
    expect(cfg.globalExecutionPolicy).toEqual({ runsPerItem: 1, passThreshold: 1 });
  });

  it("inserts one item per label, each with three assertions carrying the truth", () => {
    const items = calls.insert[0];
    expect(items).toHaveLength(LABELS.length);
    items.forEach((item: any, i: number) => {
      const label = LABELS[i];
      expect(item.data).toEqual({ label_id: label.id, challenge: label.challenge });
      expect(item.assertions).toHaveLength(3);
      expect(item.assertions[2]).toContain(`product_name is "${label.truth.product_name}"`);
    });
  });

  it("tells the judge the missing sodium line must be null", () => {
    const item = calls.insert[0].find((it: any) => it.data.label_id === "no-sodium-line");
    expect(item.assertions[1]).toContain("sodium_mg is none printed (null; the label has no sodium line");
  });
});
