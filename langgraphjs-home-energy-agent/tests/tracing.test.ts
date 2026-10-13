import { AIMessage, type BaseMessage } from "@langchain/core/messages";
import { BaseChatModel } from "@langchain/core/language_models/chat_models";
import type { ChatResult } from "@langchain/core/outputs";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { OpikCallbackHandler } from "opik-langchain";
import { describe, expect, it } from "vitest";
import { tools } from "../src/tools.js";

// Scripted model: first turn asks for read_meter, second turn answers. No provider key needed.
class ScriptedModel extends BaseChatModel {
  _llmType() { return "scripted"; }
  bindTools() { return this as any; }
  async _generate(messages: BaseMessage[]): Promise<ChatResult> {
    const sawTool = messages.some((m) => m.getType() === "tool");
    const message = sawTool
      ? new AIMessage("11.5 kWh")
      : new AIMessage({ content: "", tool_calls: [{ id: "c1", name: "read_meter", args: { from_hour: 17, to_hour: 21 } }] });
    return { generations: [{ text: String(message.content), message }] };
  }
}

describe("agent loop with the Opik callback handler", () => {
  it("runs the tool loop with tracking disabled (OPIK_TRACK_DISABLE=true)", async () => {
    // Guard so the test never talks to Opik, even if run without the documented env var.
    process.env.OPIK_TRACK_DISABLE = "true";
    const agent = createReactAgent({ llm: new ScriptedModel({}), tools });
    const handler = new OpikCallbackHandler({ projectName: "offline-test" });
    const result = await agent.invoke(
      { messages: [{ role: "user", content: "usage 5-9pm?" }] },
      { callbacks: [handler], runName: "energy-request-test" },
    );
    await handler.flushAsync();
    const toolMsg = result.messages.find((m: BaseMessage) => m.getType() === "tool");
    expect(JSON.parse(String(toolMsg!.content)).total_kwh).toBe(11.5);
    expect(result.messages.at(-1)!.content).toBe("11.5 kWh");
  });
});
