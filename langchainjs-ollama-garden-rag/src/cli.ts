import { config } from "dotenv";
import { fileURLToPath } from "node:url";
import { createHandler, PROJECT } from "./tracing.js";
import { GardenAssistant, buildStore, CHAT_MODEL, OLLAMA_URL } from "./chain.js";

// Load this folder's .env, then the repo-root .env. dotenv never overrides variables already set.
// Opik reads OPIK_URL_OVERRIDE / OPIK_WORKSPACE (and OPIK_API_KEY for Opik Cloud) from the environment.
const here = fileURLToPath(new URL(".", import.meta.url));
config({ path: [`${here}../.env`, `${here}../../.env`], quiet: true });

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
  const handler = createHandler();
  for (const question of questions) {
    console.log(`Q: ${question}\nA: ${await assistant.ask(question, [handler])}\n`);
  }
  // The SDK batches traces in the background; without this flush a short script can exit before they are sent.
  await handler.flushAsync();
  console.log(`Done. Open the "${PROJECT}" project in Opik.`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
