import { config } from "dotenv";
import { fileURLToPath } from "node:url";
import OpenAI from "openai";
import { Opik } from "opik";
import { MuseumGuide } from "./guide.js";

// Load this folder's .env, then the repo-root .env. dotenv never overrides variables already set.
const here = fileURLToPath(new URL(".", import.meta.url));
config({ path: [`${here}../.env`, `${here}../../.env`], quiet: true });

export const PROJECT = "openai-ts-museum-guide-chat";

// Two scripted visitors, so the demo needs no typing.
const CONVERSATIONS: Record<string, string[]> = {
  "family-saturday-visit": [
    "Hi! We're two adults and two kids (aged 6 and 9) coming on Saturday. What will tickets cost?",
    "What time do you open on Saturdays, and which exhibit should the kids not miss?",
    "Is the touch tank open all day?",
  ],
  "wheelchair-and-quiet-hour": [
    "I use a wheelchair. Is the museum step-free?",
    "My son is sensitive to noise. Is there a calmer time to visit?",
    "Great. Do you have a vegan menu in the cafe?", // not in the guide's facts: it should say it isn't sure
  ],
};

async function main(): Promise<void> {
  const openai = new OpenAI();
  // The Opik client owns the project name: every trace below lands in this project.
  const opik = new Opik({ projectName: PROJECT });

  const turns: { thread: string; traceId: string }[] = [];
  for (const [threadId, userTurns] of Object.entries(CONVERSATIONS)) {
    console.log(`\n=== Conversation: ${threadId} ===`);
    const guide = new MuseumGuide(openai, opik, threadId);
    for (const message of userTurns) {
      const turn = await guide.ask(message);
      turns.push({ thread: threadId, traceId: turn.traceId });
      console.log(`\nVisitor: ${message}\nGuide:   ${turn.reply}`);
    }
  }

  // The family visitor clicks thumbs-up on the last answer of their conversation. The score is
  // attached to an existing trace by id, after the run, so it shows in the Feedback scores column.
  // Traces must reach the server first, so flush before scoring.
  await opik.flush();
  const liked = turns.filter((t) => t.thread === "family-saturday-visit").at(-1);
  if (!liked) throw new Error("no turns recorded");
  opik.logTracesFeedbackScores([
    { id: liked.traceId, name: "visitor-satisfaction", value: 1.0, reason: "Visitor tapped thumbs-up on the touch-tank answer." },
  ]); // returns void: the score is queued and sent on the next flush
  await opik.flush(); // without this the process can exit before the score is sent
  console.log(`\nLogged visitor-satisfaction=1.0 on trace ${liked.traceId}`);

  // Read the traces back to print what each turn cost (computed by Opik from the llm span's usage).
  const traces = await opik.searchTraces({ projectName: PROJECT, waitForAtLeast: turns.length, waitForTimeout: 30 });
  console.log("\nCost per turn (from Opik):");
  for (const t of traces.sort((a, b) => +new Date(a.startTime ?? 0) - +new Date(b.startTime ?? 0))) {
    console.log(`  ${(t.threadId ?? "-").padEnd(26)} $${(t.totalEstimatedCost ?? 0).toFixed(6)}  ${t.id}`);
  }
  const total = traces.reduce((s, t) => s + (t.totalEstimatedCost ?? 0), 0);
  console.log(`  total over ${traces.length} turns: $${total.toFixed(6)}`);
}

main()
  .catch((err) => {
    console.error(err);
    process.exitCode = 1;
  });
