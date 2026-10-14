// Runs the real agent and tools against a stubbed model, with tracking
// disabled: the observability wiring must not get in the way of unit tests.
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { MockLanguageModelV3 } from "ai/test";
import { VoltAgent } from "@voltagent/core";
import { createWorkshopAssistant } from "../src/agent.ts";
import { createObservability, trackingDisabled } from "../src/telemetry/index.ts";

const usage = {
  inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
  outputTokens: { total: 5, text: 5, reasoning: 0 },
};

describe("agent with tracking disabled", () => {
  beforeAll(() => {
    process.env.OPIK_TRACK_DISABLE = "true";
  });
  afterAll(() => {
    delete process.env.OPIK_TRACK_DISABLE;
  });

  it("answers through a stubbed model while observability is a no-op", async () => {
    expect(trackingDisabled()).toBe(true);
    const model = new MockLanguageModelV3({
      doGenerate: async () => ({
        content: [{ type: "text", text: "Ticket WS-2042 is ready for pickup." }],
        finishReason: { unified: "stop", raw: "stop" },
        usage,
        warnings: [],
      }),
    });
    const agent = createWorkshopAssistant(model);
    new VoltAgent({ agents: { agent }, observability: createObservability() });
    const result = await agent.generateText("Status of WS-2042?");
    expect(result.text).toContain("ready for pickup");
  });
});
