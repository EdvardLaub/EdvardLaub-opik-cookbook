import { StringOutputParser } from "@langchain/core/output_parsers";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { ChatOllama, OllamaEmbeddings } from "@langchain/ollama";
import { loadChunks } from "./loader.js";
import { VectorStore, type Hit } from "./store.js";

export const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
export const CHAT_MODEL = "llama3.2:1b";
export const EMBED_MODEL = "nomic-embed-text";
export const TOP_K = 2;

export const prompt = ChatPromptTemplate.fromMessages([
  [
    "system",
    "You are the helper for the Marrow Lane Community Garden. Answer the question using only the " +
      "garden notes below. If the notes do not cover it, say so. Answer in at most three sentences.\n\n{context}",
  ],
  ["human", "{question}"],
]);

/** Paste the retrieved chunks into one context block. */
export function formatContext(hits: Hit[]): string {
  return hits.map((h) => h.chunk.text).join("\n\n---\n\n");
}

export async function buildStore(docsDir: string): Promise<VectorStore> {
  const embeddings = new OllamaEmbeddings({ model: EMBED_MODEL, baseUrl: OLLAMA_URL });
  return VectorStore.build(await loadChunks(docsDir), embeddings);
}

export class GardenAssistant {
  private readonly llm = new ChatOllama({
    model: CHAT_MODEL,
    baseUrl: OLLAMA_URL,
    temperature: 0,
    numPredict: 200, // cap the answer length: this runs on CPU
  });

  constructor(private readonly store: VectorStore) {}

  /** Retrieval step: the question in, the TOP_K best-matching rulebook sections out. */
  async retrieve(question: string): Promise<Hit[]> {
    return this.store.search(question, TOP_K);
  }

  async ask(question: string): Promise<string> {
    const hits = await this.retrieve(question);
    const chain = prompt.pipe(this.llm).pipe(new StringOutputParser());
    return chain.invoke({ context: formatContext(hits), question });
  }
}
