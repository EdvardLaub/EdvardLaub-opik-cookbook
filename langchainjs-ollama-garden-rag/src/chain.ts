import type { BaseCallbackHandler } from "@langchain/core/callbacks/base";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { RunnableLambda } from "@langchain/core/runnables";
import { tool } from "@langchain/core/tools";
import { ChatOllama, OllamaEmbeddings } from "@langchain/ollama";
import { z } from "zod";
import { loadChunks } from "./loader.js";
import { VectorStore, type Hit } from "./store.js";

export const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
export const CHAT_MODEL = "llama3.2:1b";
export const EMBED_MODEL = "nomic-embed-text";
export const TOP_K = 2;
export const SEARCH_STEP = "search_garden_docs";

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

export function defaultLlm(): ChatOllama {
  return new ChatOllama({
    model: CHAT_MODEL,
    baseUrl: OLLAMA_URL,
    temperature: 0,
    numPredict: 200, // cap the answer length: this runs on CPU
  });
}

export class GardenAssistant {
  /**
   * Retrieval as a named LangChain tool. Our vector store is plain TypeScript, not a LangChain
   * retriever, so the callback handler never sees a search on its own. Running it as a tool makes
   * the callback fire: Opik gets a span of type "tool" named search_garden_docs.
   */
  private readonly searchTool = tool(
    async ({ question }) => formatContext(await this.store.search(question, TOP_K)),
    {
      name: SEARCH_STEP,
      description: "Find the garden rulebook sections that best match a question.",
      schema: z.object({ question: z.string() }),
    },
  );

  constructor(
    private readonly store: VectorStore,
    private readonly llm: BaseChatModel = defaultLlm(),
  ) {}

  /** Retrieval step on its own: the question in, the TOP_K best-matching rulebook sections out. */
  async retrieve(question: string): Promise<Hit[]> {
    return this.store.search(question, TOP_K);
  }

  /** Pass callbacks (e.g. the Opik handler) to trace the run; omit them and nothing is logged. */
  async ask(question: string, callbacks: BaseCallbackHandler[] = []): Promise<string> {
    const answer = prompt.pipe(this.llm).pipe(new StringOutputParser());
    // The outer runnable is the trace root, so the search tool span and the model call nest under
    // one trace named ask_the_garden; the config it receives carries the parent run into both.
    const run = RunnableLambda.from(async (q: string, config) => {
      const context = await this.searchTool.invoke({ question: q }, config);
      return answer.invoke({ context, question: q }, config);
    }).withConfig({ runName: "ask_the_garden" });
    return run.invoke(question, { callbacks });
  }
}
