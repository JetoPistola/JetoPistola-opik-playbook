import { startTelemetry } from "$lib/server/telemetry";

// Runs once when the server module loads, before the first request. Without this call
// no AI SDK span is ever exported and the Opik project stays empty.
startTelemetry();
