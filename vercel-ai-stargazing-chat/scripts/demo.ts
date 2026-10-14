// `npm run demo`: set up the online rule, boot the Next.js app, play the scripted
// conversations over HTTP, wait for the judge's scores, and shut the server down.
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "dotenv";
import { PROJECT_NAME } from "../src/lib/config";
import { ensureProject, ensureRule, opikApi, RULE_NAME, SCORE_NAME } from "../src/lib/online-rule";
import { conversations } from "./conversations";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
config({ path: path.join(root, ".env"), quiet: true });
config({ path: path.join(root, "..", ".env"), quiet: true });
process.env.OPIK_URL_OVERRIDE ??= "http://localhost:5173/api/";
process.env.OPIK_WORKSPACE ??= "default";

const PORT = process.env.DEMO_PORT ?? "4220";
const BASE = `http://localhost:${PORT}`;

if (!process.env.OPENAI_API_KEY) {
  console.error("Missing OPENAI_API_KEY. Copy .env.example to .env and fill it in.");
  process.exit(1);
}

// 1. The online-evaluation rule must exist BEFORE traffic: it only scores traces
//    that arrive after it is enabled. Idempotent, so re-runs reuse it.
const projectId = await ensureProject(PROJECT_NAME);
const rule = await ensureRule(projectId);
console.log(`Online rule "${RULE_NAME}" ${rule.created ? "created" : "already present"} (${rule.id}).`);

// 2. Boot the app (its own process group, so Next and its workers die together).
console.log(`Starting Next.js on port ${PORT}...`);
const next = spawn(path.join(root, "node_modules", ".bin", "next"), ["dev", "-p", PORT], {
  cwd: root,
  env: { ...process.env },
  stdio: ["ignore", "pipe", "pipe"],
  detached: true,
});
next.stdout?.on("data", () => {});
next.stderr?.on("data", (d: Buffer) => {
  if (/error/i.test(d.toString())) process.stderr.write(d);
});

async function waitForServer(timeoutMs = 90_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(BASE, { signal: AbortSignal.timeout(2000) })).ok) return;
    } catch {
      /* not up yet */
    }
    await sleep(500);
  }
  throw new Error("Next.js did not become ready in time");
}

type Msg = { id: string; role: "user" | "assistant"; parts: { type: "text"; text: string }[] };
const msg = (role: Msg["role"], text: string): Msg => ({ id: randomUUID(), role, parts: [{ type: "text", text }] });

/** POST the whole history like useChat does and read the SSE stream back. */
async function chatTurn(chatId: string, messages: Msg[]): Promise<string> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: chatId, messages }),
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  let text = "";
  let buffer = "";
  const decoder = new TextDecoder();
  for await (const chunk of res.body as unknown as AsyncIterable<Uint8Array>) {
    buffer += decoder.decode(chunk, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
      try {
        const ev = JSON.parse(line.slice(6));
        if (ev.type === "text-delta" && ev.delta) {
          text += ev.delta;
          process.stdout.write(ev.delta);
        }
      } catch {
        /* ignore keepalives */
      }
    }
  }
  process.stdout.write("\n");
  return text;
}

interface TraceRow {
  id: string;
  name: string;
  thread_id?: string;
  feedback_scores?: { name: string; value: number; reason?: string }[];
}

async function fetchTraces(): Promise<TraceRow[]> {
  const res = await opikApi(`/v1/private/traces?project_name=${encodeURIComponent(PROJECT_NAME)}&size=100`);
  return ((await res.json()) as { content: TraceRow[] }).content;
}

try {
  await waitForServer();
  console.log("Server ready.\n");

  // 3. Scripted traffic. One chat id per conversation becomes one Opik thread.
  for (const conversation of conversations) {
    const chatId = `stargazing-${randomUUID().slice(0, 8)}`;
    console.log(`=== ${conversation.title} (thread ${chatId}) ===`);
    const history: Msg[] = [];
    for (const turn of conversation.turns) {
      console.log(`\nYou: ${turn}\nNova: `);
      history.push(msg("user", turn));
      history.push(msg("assistant", await chatTurn(chatId, history)));
    }
    console.log();
  }

  // 4. The exporter batches; the judge runs server-side a little later. Poll for scores.
  const expected = conversations.reduce((n, c) => n + c.turns.length, 0);
  console.log(`Waiting for ${expected} traces and their "${SCORE_NAME}" scores...`);
  let rows: TraceRow[] = [];
  for (let i = 0; i < 40; i++) {
    await sleep(3000);
    rows = (await fetchTraces()).filter((t) => t.thread_id?.startsWith("stargazing-"));
    const scored = rows.filter((t) => t.feedback_scores?.some((s) => s.name === SCORE_NAME));
    if (rows.length >= expected && scored.length >= expected) break;
  }
  console.log("\nthread            trace           score");
  for (const t of rows.sort((a, b) => (a.thread_id ?? "").localeCompare(b.thread_id ?? ""))) {
    const s = t.feedback_scores?.find((x) => x.name === SCORE_NAME);
    console.log(`${t.thread_id?.padEnd(17)} ${t.id.slice(0, 13)}  ${s ? s.value : "pending"}`);
  }
  console.log(`\nDone. Open project "${PROJECT_NAME}" in Opik: Traces, Threads, and the Online evaluation tab.`);
} finally {
  try {
    process.kill(-(next.pid as number), "SIGTERM");
  } catch {
    /* already gone */
  }
}
