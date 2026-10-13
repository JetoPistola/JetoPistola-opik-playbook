// Tiny REST helpers for the Opik API (project lookup, online-rule setup, score polling).
import { config } from "dotenv";
import path from "node:path";

config({ path: path.resolve(process.cwd(), ".env"), quiet: true });
config({ path: path.resolve(process.cwd(), "../.env"), quiet: true });

export const PROJECT_NAME = "vercel-sveltekit-garden-chat";
export const RULE_NAME = "garden_answer_relevance";

const base = (process.env.OPIK_URL_OVERRIDE ?? "http://localhost:5173/api/").replace(/\/+$/, "");

function headers(): Record<string, string> {
  const h: Record<string, string> = {
    "Content-Type": "application/json",
    "Comet-Workspace": process.env.OPIK_WORKSPACE ?? "default",
  };
  if (process.env.OPIK_API_KEY) h.Authorization = process.env.OPIK_API_KEY;
  return h;
}

export async function opik(method: string, route: string, body?: unknown): Promise<Response> {
  return fetch(`${base}${route}`, {
    method,
    headers: headers(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function ensureProjectId(): Promise<string> {
  const find = async () => {
    const res = await opik("GET", `/v1/private/projects?name=${encodeURIComponent(PROJECT_NAME)}&size=20`);
    const page = (await res.json()) as { content: { id: string; name: string }[] };
    return page.content.find((p) => p.name === PROJECT_NAME)?.id;
  };
  let id = await find();
  if (!id) {
    // A rule is attached to a project id, so the project must exist before the rule, and the
    // rule before the first trace; otherwise early traces go unscored. Create it up front.
    await opik("POST", "/v1/private/projects", { name: PROJECT_NAME });
    id = await find();
  }
  if (!id) throw new Error("Could not find or create the Opik project");
  return id;
}

const JUDGE_PROMPT = `You are grading a home-gardening chat assistant.
Question and conversation so far (JSON):
{{input}}

Assistant's reply:
{{output}}

Does the reply directly address what the user asked (even if it honestly says the notes do not cover it)?
Score 1.0 if it is fully on topic and responsive, 0.5 if partly responsive, 0.0 if off topic or evasive.`;

/**
 * Create the live LLM-as-judge rule for this project unless it already exists.
 * The online-rule REST payload is not documented; this shape (type llm_as_judge,
 * variables mapping, DOUBLE schema) comes from the Python SDK's rest_api types.
 * The judge writes its score back to the trace as feedback score `answer_relevance`.
 */
export async function ensureOnlineRule(): Promise<string> {
  const projectId = await ensureProjectId();
  const res = await opik(
    "GET",
    `/v1/private/automations/evaluators?project_id=${projectId}&name=${encodeURIComponent(RULE_NAME)}&size=50`,
  );
  const page = (await res.json()) as { content: { id: string; name: string }[] };
  const existing = page.content.find((r) => r.name === RULE_NAME);
  if (existing) return `already present (${existing.id})`;

  const create = await opik("POST", "/v1/private/automations/evaluators", {
    type: "llm_as_judge",
    name: RULE_NAME,
    project_ids: [projectId],
    action: "evaluator",
    enabled: true,
    sampling_rate: 1.0,
    code: {
      model: { name: "gpt-4o-mini", temperature: 0.0 },
      messages: [
        { role: "SYSTEM", content: "You are a strict but fair grader. Reply only with the requested score." },
        { role: "USER", content: JUDGE_PROMPT },
      ],
      variables: { input: "input", output: "output" },
      schema: [
        { name: "answer_relevance", type: "DOUBLE", description: "0.0 to 1.0: does the reply address the question" },
      ],
    },
  });
  if (!create.ok) throw new Error(`Rule creation failed: ${create.status} ${await create.text()}`);
  return "created";
}

export interface TraceRow {
  id: string;
  name: string;
  thread_id?: string;
  feedback_scores?: { name: string; value: number }[];
}

export async function listTraces(): Promise<TraceRow[]> {
  const res = await opik(
    "GET",
    `/v1/private/traces?project_name=${encodeURIComponent(PROJECT_NAME)}&size=100`,
  );
  return ((await res.json()) as { content: TraceRow[] }).content;
}
