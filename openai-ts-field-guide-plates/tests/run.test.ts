// Runs the real main.ts end to end with `opik`, `opik-openai` and `openai`
// replaced by in-memory stubs: no network, no keys, no Opik.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { renderBrief } from "./helpers.js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const h = vi.hoisted(() => ({
  versions: [] as any[],
  created: [] as any[],
  traces: [] as any[],
  prompts: [] as string[],
  flushed: false,
}));

vi.mock("opik", async (importActual) => {
  const actual = await importActual<typeof import("opik")>();
  const toPrompt = (v: any) => ({
    id: "prompt-1",
    version: v.version,
    format: (vars: any) => renderBrief(v.prompt, vars),
    getVersions: async () => h.versions,
  });
  class FakeOpik {
    async getPrompt({ version }: { name: string; version?: string }) {
      if (h.versions.length === 0) return null;
      // Without a version, return the OLDEST: the "getPrompt() is not latest" trap.
      const found = version
        ? h.versions.find((v) => v.version === version)
        : h.versions[0];
      return found ? toPrompt(found) : null;
    }
    async createPrompt(args: any) {
      h.created.push(args);
      const v = {
        prompt: args.prompt,
        version: `v${h.versions.length + 1}`,
        compareTo: () => "",
      };
      h.versions.push(v);
    }
    trace(args: any) {
      const t = { args, output: undefined as any, ended: false,
        update(u: any) { t.output = u.output; }, end() { t.ended = true; } };
      h.traces.push(t);
      return t;
    }
    async flush() { h.flushed = true; }
  }
  return { ...actual, Opik: FakeOpik };
});

vi.mock("opik-openai", () => ({ trackOpenAI: (client: any) => client }));

vi.mock("openai", () => ({
  default: class {
    images = {
      generate: async (req: any) => {
        h.prompts.push(req.prompt);
        return { data: [{ b64_json: Buffer.from("fake-png").toString("base64") }] };
      },
    };
  },
}));

const root = process.cwd();
let tmp: string;

async function runMain() {
  vi.resetModules();
  h.flushed = false;
  h.created.length = h.traces.length = h.prompts.length = 0;
  await import("../src/main.js");
  await vi.waitFor(() => expect(h.flushed).toBe(true));
}

beforeEach(() => {
  h.versions.length = 0;
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), "plates-"));
  fs.mkdirSync(path.join(tmp, "data"));
  fs.copyFileSync(path.join(root, "data/species.json"), path.join(tmp, "data/species.json"));
  process.chdir(tmp);
  process.env.OPENAI_API_KEY = "test-key";
  vi.spyOn(console, "log").mockImplementation(() => {});
});
afterEach(() => {
  process.chdir(root);
  vi.restoreAllMocks();
});

describe("plate run", () => {
  it("registers v1 and v2, then paints 4 plates with rendered prompts", async () => {
    await runMain();
    expect(h.created.map((c) => c.changeDescription)).toHaveLength(2);
    expect(h.versions.map((v) => v.version)).toEqual(["v1", "v2"]);

    expect(h.prompts).toHaveLength(4);
    expect(h.prompts[0]).toContain("Emberbreast Wren");
    expect(h.prompts[0]).not.toContain("Plate conventions"); // v1
    expect(h.prompts[3]).toContain("Tidewatch Plover");
    expect(h.prompts[3]).toContain("Plate conventions"); // v2
    expect(h.prompts[3]).toContain("single black neck collar; yellow orbital ring");

    expect(fs.readdirSync("output").sort()).toEqual([
      "v1-ember-wren.png", "v1-tidewatch-plover.png",
      "v2-ember-wren.png", "v2-tidewatch-plover.png",
    ]);
  });

  it("tags each trace with its brief version and attaches the PNG", async () => {
    await runMain();
    expect(h.traces).toHaveLength(4);
    const t = h.traces[3];
    expect(t.args.name).toBe("generate-plate");
    expect(t.args.tags).toEqual(["v2", "tidewatch-plover"]);
    expect(t.args.metadata.prompt_version).toBe("v2");
    expect(t.output.plate).toMatch(/^data:image\/png;base64,/);
    expect(h.traces.every((x) => x.ended)).toBe(true);
  });

  it("does not create a duplicate version on a re-run", async () => {
    await runMain(); // library now holds v1 and v2
    await runMain(); // getPrompt() without a version returns v1 here
    expect(h.created).toHaveLength(0);
    expect(h.versions).toHaveLength(2);
  });

  it("adds only the missing version when the library holds v1", async () => {
    await runMain();
    h.versions.pop(); // keep only v1
    await runMain();
    expect(h.created).toHaveLength(1);
    expect(h.versions.map((v) => v.version)).toEqual(["v1", "v2"]);
  });
});
