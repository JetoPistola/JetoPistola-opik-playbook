import { describe, expect, it, vi } from "vitest";

// The model is stubbed: streamText just records its arguments. opik-vercel is the real
// package, but telemetry is never started, so nothing is exported.
const streamText = vi.hoisted(() =>
  vi.fn((_args: unknown) => ({ toUIMessageStreamResponse: () => new Response("ok") })),
);
vi.mock("ai", async (orig) => ({ ...(await orig<typeof import("ai")>()), streamText }));
vi.mock("@ai-sdk/openai", () => ({ openai: (model: string) => ({ stub: model }) }));

import { POST } from "../src/routes/api/chat/+server";

describe("POST /api/chat", () => {
  it("sends the chat id as thread id and names the trace, with tracking disabled", async () => {
    expect(process.env.OPIK_TRACK_DISABLE).toBe("true");
    const request = new Request("http://x/api/chat", {
      method: "POST",
      body: JSON.stringify({
        id: "chat-123",
        messages: [{ id: "m1", role: "user", parts: [{ type: "text", text: "When do I plant garlic?" }] }],
      }),
    });
    const res = await POST({ request } as Parameters<typeof POST>[0]);
    expect(await res.text()).toBe("ok");

    const args = streamText.mock.calls[0][0] as any;
    expect(args.model).toEqual({ stub: "gpt-4o-mini" });
    expect(args.system).toContain("You are Sprout");
    expect(args.messages).toEqual([{ role: "user", content: [{ type: "text", text: "When do I plant garlic?" }] }]);
    expect(args.runtimeContext).toEqual({ threadId: "chat-123", traceName: "garden-chat-turn" });
    expect(args.experimental_telemetry).toMatchObject({
      isEnabled: true,
      metadata: { traceName: "garden-chat-turn" },
      includeRuntimeContext: { threadId: true, traceName: true },
    });
  });
});
