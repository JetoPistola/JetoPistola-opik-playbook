// Scripted conversation: three requests, one of which chains several tools.
import { config } from "dotenv";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// Load .env from this folder, or walk up to the repo-root .env.
let dir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
for (let i = 0; i < 4; i++, dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) config({ path: join(dir, ".env"), quiet: true });
}
delete process.env.OPENAI_BASE_URL;

// VoltAgent puts the system prompt in the messages array, which makes the AI SDK
// warn on every call. Filter that single known warning.
const realWarn = console.warn.bind(console);
console.warn = (...a: unknown[]) => {
  if (typeof a[0] === "string" && a[0].includes("System messages in the prompt")) return;
  realWarn(...a);
};

if (!process.env.OPENAI_API_KEY) {
  console.error("Missing OPENAI_API_KEY. Copy .env.example to .env and fill it in.");
  process.exit(1);
}

// Import after env is loaded: the exporter reads it on construction.
const { VoltAgent } = await import("@voltagent/core");
const { buildObservability, PROJECT_NAME } = await import("./telemetry/observability.ts");
const { deskAgent } = await import("./agent/deskAgent.ts");

const observability = buildObservability();
// Registering the observability instance makes VoltAgent emit its spans to the Opik exporter.
new VoltAgent({ agents: { deskAgent }, observability }); // no server option: stays in-process

const REQUESTS = [
  "What does the Quiet Room offer? I need somewhere without phone calls.",
  "I'm Priya Natarajan. Find me a desk with a monitor on 2026-11-03 in the Harbor Loft and book it.",
  "Actually something came up. Please cancel booking BK-3002.",
];

for (const [i, q] of REQUESTS.entries()) {
  console.log(`\n=== Request ${i + 1} ===\nMember:    ${q}`);
  const r = await deskAgent.generateText(q);
  console.log(`Assistant: ${r.text}`);
}

// shutdown() flushes the batch exporter; without it the process exits before the spans reach Opik.
await observability.shutdown(); // flush the batch exporter
console.log(`\nDone. Open the "${PROJECT_NAME}" project in Opik.`);
process.exit(0);
