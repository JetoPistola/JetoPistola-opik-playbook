// The whole Opik integration for the server: an OpenTelemetry NodeSDK whose
// trace exporter is OpikExporter, plus the AI SDK v7 registerTelemetry call.
import { config } from "dotenv";
import path from "node:path";
import { NodeSDK } from "@opentelemetry/sdk-node";
import { registerTelemetry } from "ai";
import { OpenTelemetry } from "@ai-sdk/otel";
import { Opik } from "opik";
import { OpikExporter } from "opik-vercel";
import { PROJECT_NAME } from "./garden";

// Secrets live in one repo-root .env; this folder's .env wins if present.
// Neither overrides variables already set in the shell.
config({ path: path.resolve(process.cwd(), ".env"), quiet: true });
config({ path: path.resolve(process.cwd(), "../.env"), quiet: true });

let started = false;

export function startTelemetry() {
  if (started) return;
  started = true;

  // NodeSDK installs the OpenTelemetry tracer provider that the AI SDK emits spans into.
  const sdk = new NodeSDK({
    serviceName: PROJECT_NAME,
    // OpikExporter turns each AI SDK call into an Opik trace with llm/general spans, token
    // usage and cost. Note: OPIK_TRACK_DISABLE does not stop this exporter from sending.
    traceExporter: new OpikExporter({
      // Pin the Opik project; URL / workspace come from OPIK_* env vars.
      client: new Opik({ projectName: PROJECT_NAME }),
      tags: ["sveltekit", "streaming"],
    }),
  });
  sdk.start();

  // AI SDK v7 only emits spans once an integration is registered globally; without this
  // the exporter above receives nothing. usage:true records token counts for cost.
  registerTelemetry(
    new OpenTelemetry({
      usage: true,
      // The route passes threadId / traceName through runtimeContext; turn them into the
      // span attributes OpikExporter reads (thread id and trace name in Opik).
      enrichSpan: ({ runtimeContext }) => {
        const attributes: Record<string, string> = {};
        if (runtimeContext?.threadId != null)
          attributes["ai.telemetry.metadata.threadId"] = String(runtimeContext.threadId);
        if (runtimeContext?.traceName != null)
          attributes["ai.telemetry.metadata.traceName"] = String(runtimeContext.traceName);
        return attributes;
      },
    }),
  );

  // Flush batched spans when the server is told to stop; a killed process loses the last
  // traces still in the batch queue.
  const stop = async () => {
    await sdk.shutdown().catch(() => {});
    process.exit(0);
  };
  process.once("SIGTERM", stop);
  process.once("SIGINT", stop);
}
