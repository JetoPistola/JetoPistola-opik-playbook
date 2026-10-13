import { afterEach, describe, expect, it, vi } from "vitest";
import { ensureOnlineRule, RULE_NAME } from "../scripts/opik-rest";

type Call = { method: string; url: string; body?: any };

// Fake Opik REST API: records every call; `existing` controls what the lookups return.
function stubOpik(opts: { project?: boolean; rule?: boolean }) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: { method: string; body?: string }) => {
      calls.push({ method: init.method, url, body: init.body ? JSON.parse(init.body) : undefined });
      const json = (data: unknown) => new Response(JSON.stringify(data), { status: 200 });
      if (url.includes("/projects") && init.method === "GET") {
        return json({ content: opts.project ? [{ id: "proj-1", name: "vercel-sveltekit-garden-chat" }] : [] });
      }
      if (url.includes("/automations/evaluators") && init.method === "GET") {
        return json({ content: opts.rule ? [{ id: "rule-1", name: RULE_NAME }] : [] });
      }
      return json({});
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe("ensureOnlineRule", () => {
  it("posts an llm_as_judge rule with input/output variables and a DOUBLE score", async () => {
    const calls = stubOpik({ project: true });
    expect(await ensureOnlineRule()).toBe("created");
    const post = calls.find((c) => c.method === "POST" && c.url.endsWith("/automations/evaluators"))!;
    expect(post.body).toMatchObject({
      type: "llm_as_judge",
      name: RULE_NAME,
      project_ids: ["proj-1"],
      enabled: true,
      sampling_rate: 1.0,
      code: {
        model: { name: "gpt-4o-mini" },
        variables: { input: "input", output: "output" },
        schema: [{ name: "answer_relevance", type: "DOUBLE" }],
      },
    });
    const prompt = post.body.code.messages.map((m: { content: string }) => m.content).join("\n");
    expect(prompt).toContain("{{input}}");
    expect(prompt).toContain("{{output}}");
  });

  it("creates the project first when it does not exist yet", async () => {
    const calls = stubOpik({ project: false });
    // The stub never "finds" the project even after creation, so the helper must give up loudly.
    await expect(ensureOnlineRule()).rejects.toThrow("Could not find or create the Opik project");
    expect(calls.some((c) => c.method === "POST" && c.url.endsWith("/projects"))).toBe(true);
  });

  it("does not create a second rule when one already exists", async () => {
    const calls = stubOpik({ project: true, rule: true });
    expect(await ensureOnlineRule()).toContain("already present");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });
});
