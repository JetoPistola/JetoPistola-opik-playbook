import { getTrackContext, track } from "opik";

export const MODEL = "claude-haiku-4-5-20251001";

/** The slice of the Anthropic client this app uses (lets tests pass a stub). */
export interface MessagesClient {
  messages: {
    create(params: {
      model: string;
      max_tokens: number;
      system: string;
      messages: { role: "user"; content: string }[];
    }): Promise<{
      content: { type: string; text?: string }[];
      usage: { input_tokens: number; output_tokens: number };
    }>;
  };
}

export function buildSystemPrompt(manual: string): string {
  return `You answer questions about the Fornello Piccolo F-200 \
Owner's Manual, reproduced in full below.

Rules:
- Answer only from the manual. If the manual does not cover the question, say \
so plainly instead of guessing.
- Every factual claim must be backed by a citation: a verbatim excerpt from the \
manual wrapped in <quote>...</quote> tags, copied character-for-character.
- Keep answers short: the answer first, then the supporting quote(s).

<manual>
${manual}
</manual>`;
}

/** Pull every <quote>...</quote> excerpt out of an answer. */
export function extractQuotes(answer: string): string[] {
  return [...answer.matchAll(/<quote>([\s\S]*?)<\/quote>/g)].map((m) => m[1].trim());
}

/**
 * One Claude call, logged as a child `llm` span of whatever @track context is
 * active. This is the manual stand-in for an integration like track_anthropic.
 */
export function makeAskClaude(client: MessagesClient, manual: string) {
  const system = buildSystemPrompt(manual);
  return async function askClaude(question: string): Promise<string> {
    // Inside track() this is the current trace/span; it is undefined when
    // tracking is disabled, so every span call below is optional-chained.
    const ctx = getTrackContext();
    // A child span of type "llm": it shows up under the answer_question trace.
    const span = ctx?.span.span({
      name: "anthropic.messages.create",
      type: "llm",
      input: { system: "(manual Q&A system prompt)", question },
      metadata: { model: MODEL, provider: "anthropic", max_tokens: 1024 },
    });
    try {
      const response = await client.messages.create({
        model: MODEL,
        max_tokens: 1024,
        system,
        messages: [{ role: "user", content: question }],
      });
      const text = response.content
        .map((block) => (block.type === "text" ? (block.text ?? "") : ""))
        .join("");
      const { input_tokens, output_tokens } = response.usage;
      // model + provider + usage are what let Opik compute cost; without them
      // the span's cost column stays empty.
      span?.update({
        model: MODEL,
        provider: "anthropic",
        output: { text },
        usage: {
          prompt_tokens: input_tokens,
          completion_tokens: output_tokens,
          total_tokens: input_tokens + output_tokens,
        },
      });
      return text;
    } finally {
      // Close the span even if the API call throws.
      span?.end();
    }
  };
}

/** Wrap the asker in track(): creates the trace/span context askClaude hangs its llm span on. */
export function makeAnswerQuestion(client: MessagesClient, manual: string) {
  return track({ name: "answer_question", type: "general" }, makeAskClaude(client, manual));
}

// Suite-level assertions: the quality bar every answer must clear.
export const GLOBAL_ASSERTIONS = [
  "Every excerpt wrapped in <quote> tags in the response appears verbatim, " +
    "character for character, in the provided manual context",
  "The quoted excerpts genuinely support the factual claims made in the answer",
  "The response answers the question that was asked",
];

export interface Case {
  question: string;
  assertions?: string[];
}

export const CASES: Case[] = [
  {
    question: "How often should I descale, and can I use vinegar?",
    // Item-level: pins the one factually correct answer.
    assertions: [
      "The response says to descale every 3 months, or every 6 weeks in hard-water areas",
      "The response says vinegar must not be used",
    ],
  },
  { question: "How long should a double shot take and how much coffee do I use?" },
  { question: "My machine has a red blinking light. What should I do?" },
  { question: "What does the warranty not cover, and for how long does it last?" },
  { question: "How do I steam milk safely?" },
  {
    // The manual is silent here: the right answer is an honest "not covered".
    question: "Can I plug the F-200 into a 110V outlet when travelling in the US?",
    assertions: [
      "The response states that the manual does not cover this question rather than inventing an answer",
    ],
  },
];

