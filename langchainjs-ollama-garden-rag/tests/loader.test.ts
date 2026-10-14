import { describe, expect, it } from "vitest";
import { chunkMarkdown, loadChunks } from "../src/loader.js";
import { DOCS_DIR } from "./helpers.js";

describe("chunkMarkdown", () => {
  it("makes one chunk per ## section and prefixes the file title", () => {
    const chunks = chunkMarkdown("demo", "# Demo Title\n\n## First rule\nDo A.\n\n## Second rule\nDo B.\n");
    expect(chunks.map((c) => c.id)).toEqual(["demo#first-rule", "demo#second-rule"]);
    expect(chunks[0]?.text).toBe("Demo Title\n## First rule\nDo A.");
  });
});

describe("loadChunks", () => {
  it("chunks the whole rulebook with unique ids", async () => {
    const chunks = await loadChunks(DOCS_DIR);
    expect(chunks.length).toBeGreaterThanOrEqual(15);
    expect(new Set(chunks.map((c) => c.id)).size).toBe(chunks.length);
    expect(new Set(chunks.map((c) => c.source))).toEqual(
      new Set(["composting", "planting-calendar", "plot-rules", "watering-rota"]),
    );
  });
});
