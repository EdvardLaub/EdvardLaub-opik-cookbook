import { describe, expect, it } from "vitest";
import type { ReadableSpan, SpanProcessor } from "@opentelemetry/sdk-trace-base";
import { AgentRunAggregator, applyRunTotals } from "../src/telemetry/aggregate.ts";
import { mapSpanAttributes } from "../src/telemetry/mapping.ts";

const llm = () => ({ "operation.id": "r1", "span.type": "llm", "llm.model": "gpt-4o-mini", "llm.usage.total_tokens": 506 });
const root = () => ({
  "operation.id": "r1",
  "entity.type": "agent",
  "usage.prompt_tokens": 816,
  "usage.completion_tokens": 75,
  "usage.total_tokens": 891,
  output: "Ready for pickup.",
});

describe("run-total aggregation", () => {
  it("replaces last-step usage with the run totals and adds the answer as output", () => {
    const span = llm() as Record<string, unknown>;
    applyRunTotals([span], root());
    expect(span["llm.usage.total_tokens"]).toBe(891);
    const mapped = mapSpanAttributes(span);
    expect(mapped["gen_ai.usage.total_tokens"]).toBe(891);
    expect(JSON.parse(mapped["gen_ai.output.messages"] as string)[0].parts[0].content).toBe("Ready for pickup.");
  });

  it("leaves usage alone when a run has several llm spans", () => {
    const a = llm() as Record<string, unknown>;
    const b = llm() as Record<string, unknown>;
    applyRunTotals([a, b], root());
    expect(a["llm.usage.total_tokens"]).toBe(506);
  });

  it("holds llm spans until the root ends and releases them on shutdown otherwise", async () => {
    const seen: string[] = [];
    const next = {
      onStart: () => {},
      onEnd: (s: ReadableSpan) => seen.push(String((s.attributes as Record<string, unknown>)["span.type"] ?? "root")),
      forceFlush: async () => {},
      shutdown: async () => {},
    } as SpanProcessor;
    const agg = new AgentRunAggregator(next);
    const span = (attributes: object) => ({ attributes }) as unknown as ReadableSpan;

    agg.onEnd(span(llm()));
    agg.onEnd(span({ "operation.id": "r1", "span.type": "tool" }));
    expect(seen).toEqual(["tool"]); // llm span is still held
    agg.onEnd(span(root()));
    expect(seen).toEqual(["tool", "llm", "root"]);

    agg.onEnd(span({ ...llm(), "operation.id": "r2" })); // a run whose root never ends
    await agg.shutdown();
    expect(seen).toEqual(["tool", "llm", "root", "llm"]);
  });
});
