// Builds the VoltAgent observability instance that ships spans to Opik over OTLP.
import { VoltAgentObservability } from "@voltagent/core";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import type { SpanExporter } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { GenAIMappingExporter } from "./genaiMapper.ts";

export const PROJECT_NAME = process.env.OPIK_PROJECT_NAME ?? "voltagent-coworking-desk-agent";

export function buildObservability() {
  const endpoint = (process.env.OPIK_OTLP_ENDPOINT ?? "http://localhost:5173/api/v1/private/otel").replace(/\/+$/, "");
  // Opik reads the workspace and target project from these OTLP headers; without projectName
  // the spans land in the default project instead of this example's.
  const headers: Record<string, string> = {
    "Comet-Workspace": process.env.OPIK_WORKSPACE ?? "default",
    projectName: PROJECT_NAME,
  };
  // Local self-hosted Opik needs no key; Opik Cloud does.
  if (process.env.OPIK_API_KEY) headers.Authorization = process.env.OPIK_API_KEY;

  // Plain OTLP/HTTP exporter pointed at Opik's OTel ingestion endpoint (no Opik SDK involved).
  const otlp: SpanExporter = new OTLPTraceExporter({ url: `${endpoint}/v1/traces`, headers });
  // The mapper wrapper is the lesson: with SKIP_GENAI_MAPPER=1 the raw exporter is used and every
  // span arrives typed "general" with no usage or cost in Opik.
  const exporter = process.env.SKIP_GENAI_MAPPER === "1" ? otlp : new GenAIMappingExporter(otlp);

  // BatchSpanProcessor buffers spans; demo.ts must call observability.shutdown() or they never ship.
  return new VoltAgentObservability({
    serviceName: PROJECT_NAME,
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });
}
