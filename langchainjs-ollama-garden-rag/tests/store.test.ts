import { describe, expect, it } from "vitest";
import { loadChunks } from "../src/loader.js";
import { VectorStore, cosine } from "../src/store.js";
import { DOCS_DIR, keywordEmbedder } from "./helpers.js";

describe("cosine", () => {
  it("is 1 for parallel vectors, 0 for orthogonal ones and for zero vectors", () => {
    expect(cosine([1, 2], [2, 4])).toBeCloseTo(1);
    expect(cosine([1, 0], [0, 1])).toBe(0);
    expect(cosine([0, 0], [1, 1])).toBe(0);
  });
});

describe("VectorStore", () => {
  it("returns the best-scoring chunks first, at most k of them", async () => {
    const store = await VectorStore.build(await loadChunks(DOCS_DIR), keywordEmbedder);
    const hits = await store.search("Can I use a hose on my plot?", 2);
    expect(hits).toHaveLength(2);
    expect(hits.map((h) => h.chunk.id)).toContain("watering-rota#hose-ban-and-sprinklers");
    expect(hits[0]!.score).toBeGreaterThanOrEqual(hits[1]!.score);
  });
});
