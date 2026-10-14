import { describe, expect, it } from "vitest";
import { buildRulePayload, JUDGE_PROMPT, SCORE_NAME } from "../src/lib/online-rule";
import { opikSpanAttributes, telemetrySettings } from "../src/lib/telemetry";

describe("telemetry helpers", () => {
  it("maps runtimeContext to the attributes opik-vercel reads", () => {
    expect(opikSpanAttributes({ threadId: "t1", traceName: "n" })).toEqual({
      "ai.telemetry.metadata.threadId": "t1",
      "ai.telemetry.metadata.traceName": "n",
    });
    expect(opikSpanAttributes(undefined)).toEqual({});
  });

  // OpikExporter.getSettings is the integration wrapper; it must be callable
  // (and harmless) with tracking disabled, as in these offline tests.
  it("builds telemetry settings with tracking disabled", () => {
    const s = telemetrySettings();
    expect(s.isEnabled).toBe(true);
    expect(s.metadata?.traceName).toBe("observing-chat-turn");
    expect(s.includeRuntimeContext).toEqual({ threadId: true, traceName: true });
  });
});

describe("online rule payload", () => {
  it("targets the project and scores a boolean", () => {
    const p = buildRulePayload("proj-1");
    expect(p.project_ids).toEqual(["proj-1"]);
    expect(p.code.schema[0]?.name).toBe(SCORE_NAME);
    expect(p.code.schema[0]?.type).toBe("BOOLEAN");
    expect(JUDGE_PROMPT).toContain("{{input}}");
    expect(JUDGE_PROMPT).toContain("{{output}}");
  });
});
