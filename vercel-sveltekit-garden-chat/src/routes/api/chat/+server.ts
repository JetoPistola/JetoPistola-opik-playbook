import { openai } from "@ai-sdk/openai";
import { convertToModelMessages, streamText, type UIMessage } from "ai";
import { OpikExporter } from "opik-vercel";
import { SYSTEM_PROMPT } from "$lib/server/garden";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request }) => {
  // The Chat class posts its id and the full history on every turn.
  const { id, messages }: { id: string; messages: UIMessage[] } = await request.json();

  const result = streamText({
    model: openai("gpt-4o-mini"),
    system: SYSTEM_PROMPT,
    messages: await convertToModelMessages(messages),
    // The chat id becomes the Opik thread id (see telemetry.ts enrichSpan): without it each
    // turn is a lone trace and the Threads tab stays empty.
    runtimeContext: { threadId: id, traceName: "garden-chat-turn" },
    // Turns telemetry on for this call; getSettings sets the trace name to garden-chat-turn,
    // and includeRuntimeContext lets those two keys reach enrichSpan.
    experimental_telemetry: {
      ...OpikExporter.getSettings({ name: "garden-chat-turn" }),
      includeRuntimeContext: { threadId: true, traceName: true },
    },
  });

  return result.toUIMessageStreamResponse();
};
