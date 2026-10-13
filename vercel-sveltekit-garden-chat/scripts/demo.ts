// One command: build + boot the SvelteKit server on 5301, play two scripted
// multi-turn streaming conversations over HTTP, then shut the server down.
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { setTimeout as sleep } from "node:timers/promises";
import { config } from "dotenv";
import path from "node:path";

config({ path: path.resolve(process.cwd(), ".env"), quiet: true });
config({ path: path.resolve(process.cwd(), "../.env"), quiet: true });

const PORT = "5301";
const BASE = `http://127.0.0.1:${PORT}`;

if (!process.env.OPENAI_API_KEY) {
  console.error("Missing OPENAI_API_KEY. Copy .env.example to .env (or use the repo-root .env).");
  process.exit(1);
}

const conversations = [
  {
    title: "Tomatoes and the late frost",
    turns: [
      "I started my Sungold tomatoes indoors. When can I safely plant them outside?",
      "The leaves on top are going yellow. What's wrong?",
      "Can I use slug pellets around them?",
    ],
  },
  {
    title: "Garlic and carrots",
    turns: [
      "When do I plant garlic here, and how deep?",
      "And how do I keep carrot fly off my carrots?",
    ],
  },
];

async function chatTurn(chatId: string, messages: unknown[]): Promise<string> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: chatId, messages }),
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  let text = "";
  let buffer = "";
  const decoder = new TextDecoder();
  // The AI SDK UI-message stream is SSE; print text deltas as they arrive.
  for await (const chunk of res.body as unknown as AsyncIterable<Uint8Array>) {
    buffer += decoder.decode(chunk, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === "text-delta" && event.delta) {
          text += event.delta;
          process.stdout.write(event.delta);
        }
      } catch {
        /* ignore keepalives */
      }
    }
  }
  process.stdout.write("\n");
  return text;
}

const message = (role: "user" | "assistant", text: string) => ({
  id: randomUUID(),
  role,
  parts: [{ type: "text", text }],
});

// 1. Build and boot the server.
console.log("Building SvelteKit app...");
const build = spawnSync("npx", ["vite", "build"], { stdio: ["ignore", "ignore", "inherit"] });
if (build.status !== 0) process.exit(build.status ?? 1);

const server: ChildProcess = spawn("node", ["build"], {
  env: { ...process.env, PORT, HOST: "127.0.0.1" },
  stdio: ["ignore", "inherit", "inherit"],
});

async function waitForServer() {
  for (let i = 0; i < 120; i++) {
    try {
      if ((await fetch(BASE, { signal: AbortSignal.timeout(2000) })).ok) return;
    } catch {
      /* not up yet */
    }
    await sleep(500);
  }
  throw new Error("Server did not become ready");
}

try {
  await waitForServer();
  console.log(`Server ready on ${BASE}\n`);
  for (const conv of conversations) {
    const chatId = randomUUID();
    console.log(`=== ${conv.title} (thread ${chatId.slice(0, 8)}) ===`);
    const history: ReturnType<typeof message>[] = [];
    for (const turn of conv.turns) {
      console.log(`\nYou: ${turn}\nSprout: `);
      history.push(message("user", turn));
      history.push(message("assistant", await chatTurn(chatId, history)));
    }
    console.log();
  }
} finally {
  // 2. Stop the server.
  server.kill("SIGTERM");
  await Promise.race([once(server, "exit"), sleep(15_000)]);
  if (server.exitCode === null) server.kill("SIGKILL");
  console.log("Server stopped.");
}

console.log("Done.");
