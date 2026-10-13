import { openai } from "@ai-sdk/openai";
import { convertToModelMessages, streamText, type UIMessage } from "ai";
import { SYSTEM_PROMPT } from "$lib/server/garden";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request }) => {
  // The Chat class posts its id and the full history on every turn.
  const { messages }: { id: string; messages: UIMessage[] } = await request.json();

  const result = streamText({
    model: openai("gpt-4o-mini"),
    system: SYSTEM_PROMPT,
    messages: await convertToModelMessages(messages),
  });

  return result.toUIMessageStreamResponse();
};
