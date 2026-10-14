import type { Chunk } from "./loader.js";

/** The two methods of LangChain's Embeddings interface that the store needs. */
export interface Embedder {
  embedDocuments(texts: string[]): Promise<number[][]>;
  embedQuery(text: string): Promise<number[]>;
}

export interface Hit {
  chunk: Chunk;
  score: number;
}

export function cosine(a: number[], b: number[]): number {
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < a.length; i++) {
    const x = a[i] ?? 0;
    const y = b[i] ?? 0;
    dot += x * y;
    na += x * x;
    nb += y * y;
  }
  return na === 0 || nb === 0 ? 0 : dot / Math.sqrt(na * nb);
}

/** A tiny in-memory vector store: embed every chunk once, rank by cosine similarity per query. */
export class VectorStore {
  private constructor(
    private readonly entries: { chunk: Chunk; vector: number[] }[],
    private readonly embedder: Embedder,
  ) {}

  static async build(chunks: Chunk[], embedder: Embedder): Promise<VectorStore> {
    const vectors = await embedder.embedDocuments(chunks.map((c) => c.text));
    return new VectorStore(
      chunks.map((chunk, i) => ({ chunk, vector: vectors[i] ?? [] })),
      embedder,
    );
  }

  get size(): number {
    return this.entries.length;
  }

  async search(query: string, k: number): Promise<Hit[]> {
    const q = await this.embedder.embedQuery(query);
    return this.entries
      .map(({ chunk, vector }) => ({ chunk, score: cosine(q, vector) }))
      .sort((a, b) => b.score - a.score)
      .slice(0, k);
  }
}
