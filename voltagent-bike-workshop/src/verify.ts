// Reads the project back from Opik's REST API and reports whether usage,
// cost and span types landed. Run after `npm run demo`: `npm run verify`.
import "./env.ts";

const base = (process.env.OPIK_URL_OVERRIDE ?? "https://www.comet.com/opik/api").replace(/\/+$/, "");
const project = process.env.OPIK_PROJECT_NAME ?? "voltagent-bike-workshop";
const headers: Record<string, string> = {
  "Comet-Workspace": process.env.OPIK_WORKSPACE ?? process.env.OPIK_WORKSPACE_NAME ?? "default",
};
if (process.env.OPIK_API_KEY) headers.Authorization = process.env.OPIK_API_KEY;

async function get(path: string, params: Record<string, string>) {
  const res = await fetch(`${base}${path}?${new URLSearchParams(params)}`, { headers });
  if (!res.ok) throw new Error(`${path} -> ${res.status} ${await res.text()}`);
  return (await res.json()) as { content: any[] };
}

const traces = (await get("/v1/private/traces", { project_name: project, size: "50" })).content;
console.log(`project ${project}: ${traces.length} traces`);
let missing = 0;
for (const t of traces.reverse()) {
  const spans = (await get("/v1/private/spans", { project_name: project, trace_id: t.id, size: "50" })).content;
  const llm = spans.filter((s) => s.type === "llm");
  const tools = spans.filter((s) => s.type === "tool");
  console.log(`- trace ${t.id.slice(-6)} in/out: ${Boolean(t.input)}/${Boolean(t.output)} spans: ${spans.length}`);
  for (const s of llm) {
    const cost = s.total_estimated_cost;
    console.log(`    llm  ${s.model} tokens=${JSON.stringify(s.usage?.total_tokens)} cost=$${cost}`);
    console.log(`         output: ${JSON.stringify(s.output ?? null).slice(0, 70)}`);
    if (!s.usage?.total_tokens || !cost || !s.output) missing++;
  }
  console.log(`    tool ${tools.map((s) => s.name).join(", ") || "(none)"}`);
}
if (traces.length === 0 || missing > 0) {
  console.error("FAIL: no traces, or an llm span without usage, cost or output");
  process.exit(1);
}
console.log("OK: every llm span has token usage, an estimated cost and an output");
