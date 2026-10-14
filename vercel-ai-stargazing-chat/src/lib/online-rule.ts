// Online evaluation: a rule that lives on the Opik project and scores each new
// trace with an LLM judge. This module creates it through REST, idempotently.
// (The TypeScript SDK has no helper for rules, and creation answers 201 with the
// id only in the Location header, so plain fetch is the simplest route.)

export const RULE_NAME = "grounded_answer";
export const SCORE_NAME = "grounded_answer";

export const JUDGE_PROMPT = `You are a strict fact-checker for a stargazing assistant of a fictional astronomy club.
The INPUT is the full prompt the assistant received: its instructions, the club's reference
material, and the conversation. The OUTPUT is its reply to the member's latest message.

Check every concrete detail in the reply (numbers, durations, times, names of equipment,
rules, dates) against the reference material in the INPUT. Return true only if the reply
addresses the latest question AND every concrete detail is supported by the material, or
the reply honestly says the guide does not cover it. Return false if any detail is wrong,
invented, or applied to the wrong thing (for example a duration or a time that the
material states differently), or if the reply is off-topic.

INPUT:
{{input}}

OUTPUT:
{{output}}`;

export function buildRulePayload(projectId: string, name = RULE_NAME) {
  return {
    type: "llm_as_judge",
    action: "evaluator",
    name,
    project_ids: [projectId],
    sampling_rate: 1, // score every trace; lower this for real traffic
    enabled: true,
    code: {
      model: { name: "gpt-4o-mini", temperature: 0 },
      messages: [{ role: "USER", content: JUDGE_PROMPT }],
      // Maps the template variables to fields of the trace.
      variables: { input: "input", output: "output" },
      schema: [
        { name: SCORE_NAME, type: "BOOLEAN", description: "True when the reply is relevant and grounded in the guide." },
      ],
    },
  };
}

export function opikBase(): string {
  return (process.env.OPIK_URL_OVERRIDE ?? "http://localhost:5173/api/").replace(/\/+$/, "");
}

export async function opikApi(path: string, init: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Comet-Workspace": process.env.OPIK_WORKSPACE ?? "default",
    ...(process.env.OPIK_API_KEY ? { Authorization: process.env.OPIK_API_KEY } : {}),
  };
  return fetch(`${opikBase()}${path}`, { ...init, headers: { ...headers, ...(init.headers as object) } });
}

async function json<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) throw new Error(`${what} failed: HTTP ${res.status} ${await res.text()}`);
  return (await res.json()) as T;
}

export async function ensureProject(name: string): Promise<string> {
  const found = await json<{ content: { id: string; name: string }[] }>(
    await opikApi(`/v1/private/projects?name=${encodeURIComponent(name)}&size=50`),
    "list projects",
  );
  const hit = found.content.find((p) => p.name === name);
  if (hit) return hit.id;
  const res = await opikApi("/v1/private/projects", { method: "POST", body: JSON.stringify({ name }) });
  if (!res.ok) throw new Error(`create project failed: HTTP ${res.status} ${await res.text()}`);
  const id = res.headers.get("location")?.split("/").filter(Boolean).pop();
  if (!id) throw new Error("create project returned no Location header");
  return id;
}

export interface RuleSummary {
  id: string;
  name: string;
  enabled: boolean;
  project_ids?: string[];
}

export async function listRules(projectId: string): Promise<RuleSummary[]> {
  const page = await json<{ content: RuleSummary[] }>(
    await opikApi(`/v1/private/automations/evaluators?project_id=${projectId}&size=100`),
    "list rules",
  );
  return page.content;
}

/**
 * Idempotent: reuse the rule if it exists, create it otherwise, and delete any
 * duplicates an earlier run left behind. Must run BEFORE traffic: a rule only
 * scores traces that arrive after it exists and is enabled.
 */
export async function ensureRule(projectId: string): Promise<{ id: string; created: boolean; removed: number }> {
  const same = (await listRules(projectId)).filter((r) => r.name === RULE_NAME);
  const [keep, ...dupes] = same;
  if (dupes.length) {
    const res = await opikApi("/v1/private/automations/evaluators/delete", {
      method: "POST",
      body: JSON.stringify({ ids: dupes.map((d) => d.id) }),
    });
    if (!res.ok) throw new Error(`delete duplicate rules failed: HTTP ${res.status}`);
  }
  if (keep) {
    // Re-apply the definition so an edited judge prompt reaches an existing rule
    // (and a disabled rule, which would silently score nothing, is re-enabled).
    const res = await opikApi(`/v1/private/automations/evaluators/${keep.id}`, {
      method: "PATCH",
      body: JSON.stringify(buildRulePayload(projectId)),
    });
    if (!res.ok) throw new Error(`update rule failed: HTTP ${res.status} ${await res.text()}`);
    return { id: keep.id, created: false, removed: dupes.length };
  }
  const res = await opikApi("/v1/private/automations/evaluators/", {
    method: "POST",
    body: JSON.stringify(buildRulePayload(projectId)),
  });
  if (res.status !== 201) throw new Error(`create rule failed: HTTP ${res.status} ${await res.text()}`);
  const id = res.headers.get("location")?.split("/").filter(Boolean).pop() ?? "";
  return { id, created: true, removed: 0 };
}
