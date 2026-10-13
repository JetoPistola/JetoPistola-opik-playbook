import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Offline seam: replace the OTLP exporter, the batch processor and VoltAgentObservability with
// stubs, so buildObservability() can be inspected without starting any exporter or touching the network.
const captured: { processorArg?: unknown; otlpOpts?: { url: string; headers: Record<string, string> } } = {};

vi.mock("@opentelemetry/exporter-trace-otlp-http", () => ({
  OTLPTraceExporter: class {
    constructor(opts: { url: string; headers: Record<string, string> }) {
      captured.otlpOpts = opts;
    }
  },
}));
vi.mock("@opentelemetry/sdk-trace-base", () => ({
  BatchSpanProcessor: class {
    constructor(exporter: unknown) {
      captured.processorArg = exporter;
    }
  },
}));
vi.mock("@voltagent/core", () => ({ VoltAgentObservability: class {} }));

const ENV_KEYS = ["SKIP_GENAI_MAPPER", "OPIK_OTLP_ENDPOINT", "OPIK_WORKSPACE", "OPIK_API_KEY", "OPIK_PROJECT_NAME"];

describe("buildObservability", () => {
  beforeEach(() => {
    vi.resetModules();
    for (const k of ENV_KEYS) delete process.env[k];
    captured.processorArg = undefined;
    captured.otlpOpts = undefined;
  });
  afterEach(() => {
    for (const k of ENV_KEYS) delete process.env[k];
  });

  it("wraps the OTLP exporter in the gen_ai mapper by default", async () => {
    const { buildObservability } = await import("../src/telemetry/observability.ts");
    buildObservability();
    // Re-import the mapper after resetModules so the class identity matches the one observability.ts used.
    const { GenAIMappingExporter } = await import("../src/telemetry/genaiMapper.ts");
    expect(captured.processorArg).toBeInstanceOf(GenAIMappingExporter);
    expect(captured.otlpOpts?.url).toBe("http://localhost:5173/api/v1/private/otel/v1/traces");
    expect(captured.otlpOpts?.headers).toEqual({
      "Comet-Workspace": "default",
      projectName: "voltagent-coworking-desk-agent",
    });
  });

  it("SKIP_GENAI_MAPPER=1 sends the raw exporter, with no mapping", async () => {
    process.env.SKIP_GENAI_MAPPER = "1";
    const { buildObservability } = await import("../src/telemetry/observability.ts");
    buildObservability();
    const { GenAIMappingExporter } = await import("../src/telemetry/genaiMapper.ts");
    expect(captured.processorArg).not.toBeInstanceOf(GenAIMappingExporter);
  });

  it("reads endpoint, workspace, project and key from the environment", async () => {
    process.env.OPIK_OTLP_ENDPOINT = "https://opik.example/api/v1/private/otel/";
    process.env.OPIK_WORKSPACE = "team";
    process.env.OPIK_PROJECT_NAME = "desk-unmapped";
    process.env.OPIK_API_KEY = "k";
    const { buildObservability } = await import("../src/telemetry/observability.ts");
    buildObservability();
    expect(captured.otlpOpts?.url).toBe("https://opik.example/api/v1/private/otel/v1/traces");
    expect(captured.otlpOpts?.headers).toEqual({ "Comet-Workspace": "team", projectName: "desk-unmapped", Authorization: "k" });
  });
});
