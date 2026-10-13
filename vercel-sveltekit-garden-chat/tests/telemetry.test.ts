import { describe, expect, it, vi } from "vitest";

// Never start a real OpikExporter in tests: OPIK_TRACK_DISABLE does not stop it from
// sending, so the whole OTel/Opik layer is replaced by recorders.
const captured: { integration?: { enrichSpan: Function; usage: boolean }; sdkOptions?: any } = {};
vi.mock("@opentelemetry/sdk-node", () => ({
  NodeSDK: class {
    constructor(o: unknown) {
      captured.sdkOptions = o;
    }
    start() {}
    shutdown = async () => {};
  },
}));
vi.mock("opik-vercel", () => ({ OpikExporter: class { constructor(public opts: unknown) {} } }));
vi.mock("opik", () => ({ Opik: class { constructor(public opts: unknown) {} } }));
vi.mock("@ai-sdk/otel", () => ({
  OpenTelemetry: class {
    constructor(o: { enrichSpan: Function; usage: boolean }) {
      captured.integration = o;
    }
  },
}));
vi.mock("ai", () => ({ registerTelemetry: vi.fn() }));

import { startTelemetry } from "../src/lib/server/telemetry";

describe("startTelemetry", () => {
  startTelemetry();
  startTelemetry(); // second call must be a no-op

  it("pins the exporter to the project and tags the traces", () => {
    const exporter = captured.sdkOptions.traceExporter;
    expect(exporter.opts.client.opts).toEqual({ projectName: "vercel-sveltekit-garden-chat" });
    expect(exporter.opts.tags).toEqual(["sveltekit", "streaming"]);
  });

  it("maps runtimeContext to the span attributes OpikExporter reads", () => {
    const { enrichSpan, usage } = captured.integration!;
    expect(usage).toBe(true);
    expect(enrichSpan({ runtimeContext: { threadId: "abc", traceName: "garden-chat-turn" } })).toEqual({
      "ai.telemetry.metadata.threadId": "abc",
      "ai.telemetry.metadata.traceName": "garden-chat-turn",
    });
    expect(enrichSpan({ runtimeContext: undefined })).toEqual({});
  });
});
