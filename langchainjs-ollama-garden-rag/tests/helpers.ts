import { FakeListChatModel } from "@langchain/core/utils/testing";
import { fileURLToPath } from "node:url";
import { GardenAssistant } from "../src/chain.js";
import { loadChunks } from "../src/loader.js";
import { VectorStore, type Embedder } from "../src/store.js";

export const DOCS_DIR = fileURLToPath(new URL("../docs", import.meta.url));

const KEYWORDS = ["hose", "tomato", "compost", "frost", "fee", "dog"];
const vec = (text: string): number[] => KEYWORDS.map((w) => text.toLowerCase().split(w).length - 1);

/** Bag-of-keywords embedder: deterministic, no Ollama needed. */
export const keywordEmbedder: Embedder = {
  embedDocuments: async (texts) => texts.map(vec),
  embedQuery: async (text) => vec(text),
};

export async function offlineAssistant(reply = "stub answer"): Promise<GardenAssistant> {
  const store = await VectorStore.build(await loadChunks(DOCS_DIR), keywordEmbedder);
  return new GardenAssistant(store, new FakeListChatModel({ responses: [reply] }));
}
