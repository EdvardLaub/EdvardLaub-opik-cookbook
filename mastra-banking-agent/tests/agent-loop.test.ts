// Runs the real agent with a scripted stand-in for the model (no API key, no Opik) and checks the
// shape the Opik lesson is about: one agent run, two model calls, and a real execute_tool step in between.
import { describe, expect, it } from "vitest";
import { Agent } from "@mastra/core/agent";
import { RequestContext } from "@mastra/core/request-context";
import { getBalance } from "../src/tools.ts";

function scriptedModel() {
  let call = 0;
  const usage = { inputTokens: 10, outputTokens: 5, totalTokens: 15 };
  return {
    specificationVersion: "v2",
    provider: "stub",
    modelId: "stub-model",
    supportedUrls: {},
    // Step 1: ask for the getBalance tool. Step 2: answer from its result.
    doGenerate: async () => {
      call++;
      return call === 1
        ? { content: [{ type: "tool-call", toolCallId: "c1", toolName: "getBalance", input: JSON.stringify({ accountId: "ACC-7001" }) }], finishReason: "tool-calls", usage, warnings: [] }
        : { content: [{ type: "text", text: "Your balance is $2,431.18." }], finishReason: "stop", usage, warnings: [] };
    },
    doStream: async () => { throw new Error("generate only"); },
  } as any;
}

describe("agent loop with tracking disabled", () => {
  it("calls the tool with the model's arguments and answers from its result", async () => {
    const agent = new Agent({ id: "t", name: "t", instructions: "x", model: scriptedModel(), tools: { getBalance } });
    const res = await agent.generate("balance?", { maxSteps: 4, requestContext: new RequestContext([["customerId", "CUS-3001"]]) });
    expect(res.steps).toHaveLength(2); // step 1 = tool call, step 2 = final answer
    const results = res.steps.flatMap((st: any) => st.toolResults).map((r: any) => r.payload ?? r);
    expect(results).toHaveLength(1);
    expect(results[0].toolName).toBe("getBalance");
    expect(results[0].result).toMatchObject({ accountId: "ACC-7001", balance: 2431.18 });
    expect(res.text).toContain("2,431.18");
  });
});
