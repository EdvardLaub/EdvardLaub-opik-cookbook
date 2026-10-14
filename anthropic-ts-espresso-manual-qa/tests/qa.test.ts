import { describe, expect, it, vi } from "vitest";
import { checkQuotes, extractQuotes } from "../src/quotes.js";

// Tracing off for the whole file: track()-wrapped functions then just run.
process.env.OPIK_TRACK_DISABLE = "true";

const manual = `Descale every 3 months
if you use tap water. Never use vinegar.`;

describe("quote checking", () => {
  it("extracts quotes and normalises whitespace", () => {
    const answer = "Yes. <quote>Descale every 3 months\n   if you use tap water.</quote>";
    expect(extractQuotes(answer)).toEqual(["Descale every 3 months if you use tap water."]);
  });

  it("accepts verbatim quotes even across manual line wraps", () => {
    const answer = "<quote>Descale every 3 months if you use tap water.</quote> <quote>Never use vinegar.</quote>";
    expect(checkQuotes(answer, manual).allVerbatim).toBe(true);
  });

  it("flags paraphrased quotes", () => {
    const answer = "<quote>Descale every three months.</quote>";
    const result = checkQuotes(answer, manual);
    expect(result.allVerbatim).toBe(false);
    expect(result.missing).toEqual(["Descale every three months."]);
  });

  it("treats an answer with no quotes as not verified", () => {
    expect(checkQuotes("No idea.", manual).allVerbatim).toBe(false);
  });

  it("is case sensitive: a quote re-capitalised by the model is flagged", () => {
    expect(checkQuotes("<quote>never use Vinegar.</quote>", manual).allVerbatim).toBe(false);
  });
});

describe("traced answerQuestion with tracking disabled", () => {
  it("still returns the model text", async () => {
    const { MANUAL } = await import("../src/qa.js");
    const { setClient } = await import("../src/qa.js");
    const quote = MANUAL.split("\n").find((l) => l.startsWith("Backflush"))!.trim();
    const create = vi.fn().mockResolvedValue({
      model: "claude-haiku-4-5",
      content: [{ type: "text", text: `Weekly. <quote>${quote}</quote>` }],
      usage: { input_tokens: 10, output_tokens: 5 },
    });
    setClient({ messages: { create } } as never);
    const { answerQuestion } = await import("../src/qa.js");
    const answer = await answerQuestion("How often do I backflush?");
    expect(answer).toContain("<quote>Backflush");
    expect(checkQuotes(answer, MANUAL).allVerbatim).toBe(true);
  });
});
