import { describe, expect, it, vi } from "vitest";
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";
import { GenAIMappingExporter, mapVoltAgentToGenAI } from "../src/telemetry/genaiMapper.ts";

// A span is just an attribute bag as far as the mapper cares.
const span = (attributes: Record<string, unknown>) => ({ attributes }) as unknown as ReadableSpan;

describe("mapVoltAgentToGenAI", () => {
  it("maps an llm span to gen_ai usage, model and system", () => {
    const s = span({
      "span.type": "llm",
      "llm.model": "gpt-4o-mini",
      "llm.usage.prompt_tokens": 518,
      "llm.usage.completion_tokens": 51,
      "llm.usage.total_tokens": 569,
    });
    mapVoltAgentToGenAI(s);
    expect(s.attributes).toMatchObject({
      "gen_ai.request.model": "gpt-4o-mini",
      "gen_ai.response.model": "gpt-4o-mini",
      "gen_ai.system": "openai",
      "gen_ai.provider.name": "openai",
      "gen_ai.usage.input_tokens": 518,
      "gen_ai.usage.output_tokens": 51,
      "gen_ai.usage.total_tokens": 569,
    });
  });

  it("keeps a zero token count and skips counts that are absent", () => {
    const s = span({ "span.type": "llm", "llm.usage.prompt_tokens": 0 });
    mapVoltAgentToGenAI(s);
    expect(s.attributes["gen_ai.usage.input_tokens"]).toBe(0);
    expect(s.attributes).not.toHaveProperty("gen_ai.usage.output_tokens");
    expect(s.attributes).not.toHaveProperty("gen_ai.request.model");
    expect(s.attributes["gen_ai.system"]).toBe("openai");
  });

  it("moves tool input to gen_ai.tool.call.arguments and drops schema internals", () => {
    const s = span({ "span.type": "tool", input: '{"desk_id":"HD-02"}', "tool.parameters": "{...}" });
    mapVoltAgentToGenAI(s);
    expect(s.attributes["gen_ai.tool.call.arguments"]).toBe('{"desk_id":"HD-02"}');
    expect(s.attributes).not.toHaveProperty("input");
    expect(s.attributes).not.toHaveProperty("tool.parameters");
  });

  it("defaults missing tool arguments to an empty object", () => {
    const s = span({ "span.type": "tool" });
    mapVoltAgentToGenAI(s);
    expect(s.attributes["gen_ai.tool.call.arguments"]).toBe("{}");
  });

  it("leaves other span types untouched", () => {
    const s = span({ "span.type": "agent", input: "hello" });
    mapVoltAgentToGenAI(s);
    expect(s.attributes).toEqual({ "span.type": "agent", input: "hello" });
  });
});

describe("GenAIMappingExporter", () => {
  it("maps spans before delegating to the inner exporter", () => {
    const inner: SpanExporter = {
      export: vi.fn((spans, done) => {
        // The inner exporter must already see mapped attributes.
        expect(spans[0].attributes["gen_ai.usage.input_tokens"]).toBe(7);
        done({ code: 0 });
      }),
      shutdown: vi.fn(async () => {}),
      forceFlush: vi.fn(async () => {}),
    };
    const done = vi.fn();
    new GenAIMappingExporter(inner).export([span({ "span.type": "llm", "llm.usage.prompt_tokens": 7 })], done);
    expect(inner.export).toHaveBeenCalledOnce();
    expect(done).toHaveBeenCalledWith({ code: 0 });
  });

  it("forwards shutdown and forceFlush", async () => {
    const inner = { export: vi.fn(), shutdown: vi.fn(async () => {}) } as unknown as SpanExporter;
    const wrapper = new GenAIMappingExporter(inner);
    await wrapper.forceFlush(); // inner has no forceFlush: must still resolve
    await wrapper.shutdown();
    expect(inner.shutdown).toHaveBeenCalledOnce();
  });
});
