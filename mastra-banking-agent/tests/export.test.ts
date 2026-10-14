import { describe, expect, it } from "vitest";
import { tidyAttributes } from "../src/opik-export.ts";

describe("tidyAttributes", () => {
  it("copies the customer message and the final answer onto the root span's input/output", () => {
    const out = tidyAttributes({
      "mastra.span.type": "agent_run",
      "mastra.agent_run.input": "What's my balance?",
      "mastra.agent_run.output": JSON.stringify({ text: "$2,431.18", files: [] }),
    });
    expect(out["input"]).toBe("What's my balance?");
    expect(out["output"]).toBe("$2,431.18");
  });

  it("leaves tool spans untouched", () => {
    const attrs = { "mastra.span.type": "tool_call", "gen_ai.tool.name": "getBalance" };
    expect(tidyAttributes(attrs)).toBe(attrs);
  });
});
