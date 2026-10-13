import { beforeEach, describe, expect, it, vi } from "vitest";

// main.ts runs on import, so these tests import it with the OpenAI client, the Opik client and the
// suite runner replaced by in-memory fakes. `track` and `getTrackContext` stay real: with
// OPIK_TRACK_DISABLE=true (set by `npm test`) the traced `rewrite` just calls through.
const h = vi.hoisted(() => {
  const state = {
    store: [] as { prompt: string; change: string }[],
    openaiCalls: [] as { system: string; user: string }[],
    runs: [] as { experimentName: string; promptText: string; items: number }[],
    suite: undefined as any,
    inserted: [] as any[],
    createCalls: 0,
    done: undefined as undefined | (() => void),
  };
  const versionObj = (i: number) => ({
    name: "changelog-rewriter",
    version: `v${i + 1}`,
    commit: `c${i + 1}`,
    prompt: state.store[i].prompt,
  });
  return { state, versionObj };
});

vi.mock("openai", () => ({
  default: class {
    chat = {
      completions: {
        create: async ({ messages }: any) => {
          h.state.openaiCalls.push({ system: messages[0].content, user: messages[1].content });
          return { choices: [{ message: { content: "  Fixed a sync crash.  " } }] };
        },
      },
    };
  },
}));

vi.mock("opik-openai", () => ({ trackOpenAI: (c: unknown) => c }));

vi.mock("opik", async (importOriginal) => {
  const real = await importOriginal<typeof import("opik")>();
  class FakeOpik {
    async getPrompt({ version }: { version?: string }) {
      const { store } = h.state;
      if (store.length === 0) return null;
      const i = version ? Number(version.slice(1)) - 1 : store.length - 1;
      return {
        ...h.versionObj(i),
        getVersions: async () => store.map((_, k) => h.versionObj(k)),
      };
    }
    async createPrompt({ prompt, changeDescription }: any) {
      h.state.createCalls++;
      h.state.store.push({ prompt, change: changeDescription });
    }
    async getOrCreateTestSuite(opts: any) {
      h.state.suite = opts;
      return { insert: async (items: any[]) => void h.state.inserted.push(...items) };
    }
    async flush() {
      h.state.done?.();
    }
  }
  return {
    ...real,
    Opik: FakeOpik,
    runTests: async (opts: any) => {
      const items = h.state.inserted.slice(-5);
      for (const data of items) await opts.task(data.data);
      h.state.runs.push({
        experimentName: opts.experimentName,
        promptText: opts.prompts[0].prompt,
        items: items.length,
      });
      return { passRate: 1, itemsPassed: items.length, itemsTotal: items.length };
    },
  };
});

async function runMain(): Promise<string[]> {
  const lines: string[] = [];
  vi.spyOn(console, "log").mockImplementation((...a) => void lines.push(a.join(" ")));
  const finished = new Promise<void>((resolve) => (h.state.done = resolve));
  vi.resetModules();
  await import("../src/main.ts");
  await finished;
  return lines;
}

beforeEach(() => {
  vi.stubEnv("OPENAI_API_KEY", "test-key");
  vi.stubEnv("OPIK_TRACK_DISABLE", "true");
  Object.assign(h.state, { openaiCalls: [], runs: [], inserted: [], createCalls: 0, suite: undefined });
});

describe("changelog rewriter", () => {
  it("registers v1 and v2 once, and re-running adds no v3", async () => {
    h.state.store = [];
    await runMain();
    expect(h.state.store).toHaveLength(2);
    expect(h.state.store[0].prompt).toContain("changelog entry");
    expect(h.state.store[1].prompt).toContain("at most 18 words");
    expect(h.state.createCalls).toBe(2);
    await runMain();
    expect(h.state.store).toHaveLength(2);
    expect(h.state.createCalls).toBe(2);
  });

  it("runs the same suite once per prompt version through the traced rewrite", async () => {
    h.state.store = [];
    const lines = await runMain();
    expect(h.state.suite.globalAssertions).toHaveLength(3);
    expect(h.state.suite.globalExecutionPolicy).toEqual({ runsPerItem: 3, passThreshold: 2 });
    expect(h.state.runs.map((r) => r.experimentName)).toEqual([
      "changelog-rewriter-v1",
      "changelog-rewriter-v2",
    ]);
    // The model is called with each version's text as the system prompt, and the trimmed reply is returned.
    const systems = new Set(h.state.openaiCalls.map((c) => c.system));
    expect(systems).toEqual(new Set(h.state.store.map((s) => s.prompt)));
    expect(lines.some((l) => l.includes("Line (v2): Fixed a sync crash."))).toBe(true);
    expect(lines).toContain("changelog-rewriter v1: 100% pass rate (5/5 items)");
  });
});
