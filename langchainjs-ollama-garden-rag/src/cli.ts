import { fileURLToPath } from "node:url";
import { GardenAssistant, buildStore, CHAT_MODEL, OLLAMA_URL } from "./chain.js";

const DOCS_DIR = fileURLToPath(new URL("../docs", import.meta.url));

export const DEMO_QUESTIONS = [
  "Can I use a hose to water my plot?",
  "When is it safe to plant out tomatoes?",
  "What can't go in the compost bins?",
];

async function ensureOllama(): Promise<void> {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/tags`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch {
    throw new Error(
      `Ollama is not reachable at ${OLLAMA_URL}. Start it yourself and pull the models: ` +
        `ollama pull ${CHAT_MODEL} && ollama pull nomic-embed-text`,
    );
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2).filter((a) => a !== "--demo");
  const questions = args.length > 0 ? [args.join(" ")] : DEMO_QUESTIONS;

  await ensureOllama();
  const assistant = new GardenAssistant(await buildStore(DOCS_DIR));
  for (const question of questions) {
    console.log(`Q: ${question}\nA: ${await assistant.ask(question)}\n`);
  }
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
