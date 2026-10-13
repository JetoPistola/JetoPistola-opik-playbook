// The lesson of this example lives here. VoltAgent emits OpenTelemetry spans
// with its own attribute names (llm.usage.prompt_tokens, llm.model, ...).
// Opik reads the OpenTelemetry GenAI conventions (gen_ai.*). This exporter
// wrapper copies VoltAgent's attributes to the names Opik understands, just
// before the spans are sent.
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";

type Attrs = Record<string, unknown>;

export function mapVoltAgentToGenAI(span: ReadableSpan): void {
  const attrs = span.attributes as Attrs;
  const type = attrs["span.type"];

  if (type === "llm") {
    const model = attrs["llm.model"];
    if (model) {
      attrs["gen_ai.request.model"] = model;
      attrs["gen_ai.response.model"] = model;
    }
    // gen_ai.request.model / gen_ai.response.model: Opik shows the model and uses it for pricing.
    // A recognised provider is what lets Opik price the call.
    attrs["gen_ai.system"] = "openai";
    attrs["gen_ai.provider.name"] = "openai";
    const prompt = attrs["llm.usage.prompt_tokens"];
    const completion = attrs["llm.usage.completion_tokens"];
    const total = attrs["llm.usage.total_tokens"];
    // gen_ai.usage.*: these fill the span's Usage column; cost is estimated from them plus model/provider.
    if (prompt !== undefined) attrs["gen_ai.usage.input_tokens"] = prompt;
    if (completion !== undefined) attrs["gen_ai.usage.output_tokens"] = completion;
    if (total !== undefined) attrs["gen_ai.usage.total_tokens"] = total;
  } else if (type === "tool") {
    // gen_ai.* attributes make Opik type this span "tool" with clean arguments as its input.
    // Tool arguments become the span input; drop schema internals.
    attrs["gen_ai.tool.call.arguments"] = attrs["input"] ?? "{}";
    delete attrs["input"];
    delete attrs["tool.parameters"];
  }
}

// Wrapper exporter: mutates each finished span's attributes, then hands it to the real OTLP exporter.
export class GenAIMappingExporter implements SpanExporter {
  constructor(private readonly inner: SpanExporter) {}

  export(spans: ReadableSpan[], done: Parameters<SpanExporter["export"]>[1]): void {
    spans.forEach(mapVoltAgentToGenAI);
    this.inner.export(spans, done);
  }
  shutdown(): Promise<void> {
    return this.inner.shutdown();
  }
  forceFlush(): Promise<void> {
    return this.inner.forceFlush?.() ?? Promise.resolve();
  }
}
