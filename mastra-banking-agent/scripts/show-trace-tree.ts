// Prints the agent-loop tree of the newest traces in the Opik project, read back over the REST API.
// Usage: npm run tree [-- <number of traces>]. Opik-internal noise spans (model_chunk, processor_run)
// are hidden so the interesting part, the chat -> execute_tool loop, reads at a glance.
import { config } from "dotenv";
import { fileURLToPath } from "node:url";

config({ path: [fileURLToPath(new URL("../.env", import.meta.url)), fileURLToPath(new URL("../../.env", import.meta.url))], quiet: true });

const base = `${(process.env.OPIK_URL_OVERRIDE ?? "http://localhost:5173/api").replace(/\/+$/, "")}/v1/private`;
const headers: Record<string, string> = {
  "Comet-Workspace": process.env.OPIK_WORKSPACE ?? "default",
  ...(process.env.OPIK_API_KEY ? { Authorization: process.env.OPIK_API_KEY } : {}),
};
const project = process.env.OPIK_PROJECT_NAME ?? "mastra-banking-agent";
const limit = Number(process.argv[2] ?? 4);

const get = async (path: string) => {
  const res = await fetch(base + path, { headers });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as any;
};

const NOISE = new Set(["model_chunk", "processor_run", "model_generation"]);
const proj = (await get(`/projects?name=${encodeURIComponent(project)}`)).content?.[0];
if (!proj) throw new Error(`No Opik project named ${project} yet. Run npm run demo first.`);
const traces = (await get(`/traces?project_id=${proj.id}&size=${limit}`)).content as any[];
console.log(`${project}: ${traces.length} newest trace(s)\n`);

for (const t of traces.reverse()) {
  const text = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v ?? ""));
  console.log(`TRACE ${t.id}\n  input : ${text(t.input?.["input"] ?? t.input).slice(0, 90)}\n  output: ${text(t.output?.["output"] ?? t.output).slice(0, 90) || "(empty)"}\n  tokens: ${t.usage?.total_tokens ?? "-"}  cost: ${t.total_estimated_cost ?? "null"}`);
  const spans = ((await get(`/spans?project_id=${proj.id}&trace_id=${t.id}&size=200`)).content as any[]).sort((a, b) =>
    a.start_time.localeCompare(b.start_time));
  const byId = new Map(spans.map((s) => [s.id, s]));
  const visible = spans.filter((s) => !NOISE.has(s.name.split(" ")[0]));
  const depth = (s: any): number => {
    let d = 0;
    for (let p = byId.get(s.parent_span_id); p; p = byId.get(p.parent_span_id)) if (!NOISE.has(p.name.split(" ")[0])) d++;
    return d;
  };
  for (const s of visible) {
    let detail = "";
    if (s.type === "tool") detail = `  args=${JSON.stringify(s.input?.["gen_ai.tool.call.arguments"] ?? "")}`;
    if (s.type === "llm") detail = `  tokens=${s.usage?.total_tokens ?? "-"} cost=${s.total_estimated_cost ?? "null"}`;
    console.log(`  ${"  ".repeat(depth(s))}[${s.type}] ${s.name}${detail}`);
  }
  console.log();
}
