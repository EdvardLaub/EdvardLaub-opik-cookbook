import { describe, expect, it } from "vitest";
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";
import { GenAIMappingExporter } from "../src/telemetry/exporter.ts";
import { inferProvider, mapSpanAttributes } from "../src/telemetry/mapping.ts";

const llmAttrs = {
  "span.type": "llm",
  "llm.model": "gpt-4o-mini",
  "llm.usage.prompt_tokens": 456,
  "llm.usage.completion_tokens": 50,
  "llm.usage.total_tokens": 506,
};

describe("gen_ai attribute mapping", () => {
  it("maps llm usage, model and provider", () => {
    const out = mapSpanAttributes(llmAttrs);
    expect(out["gen_ai.usage.prompt_tokens"]).toBe(456);
    expect(out["gen_ai.usage.completion_tokens"]).toBe(50);
    expect(out["gen_ai.request.model"]).toBe("gpt-4o-mini");
    expect(out["gen_ai.provider.name"]).toBe("openai");
  });

  it("maps tool input, output and name, and drops the schema dump", () => {
    const out = mapSpanAttributes({ "span.type": "tool", "tool.name": "check_parts_stock", input: '{"sku":"CHN-12S"}', "tool.parameters": "{...}" });
    expect(out["gen_ai.tool.call.arguments"]).toBe('{"sku":"CHN-12S"}');
    expect(out["gen_ai.tool.name"]).toBe("check_parts_stock");
    expect(out).not.toHaveProperty("input");
    expect(out).not.toHaveProperty("tool.parameters");
  });

  it("maps the agent run to input.value / output.value and llm messages to the GenAI shape", () => {
    const root = mapSpanAttributes({ "entity.type": "agent", input: "hi", output: "hello" });
    expect(root["input.value"]).toBe("hi");
    expect(root["output.value"]).toBe("hello");
    const llm = mapSpanAttributes({
      "span.type": "llm",
      "llm.messages": JSON.stringify([{ role: "user", content: [{ type: "text", text: "status?" }] }]),
    });
    expect(JSON.parse(llm["gen_ai.input.messages"] as string)[0].parts[0]).toEqual({ type: "text", content: "status?" });
  });

  it("infers providers from model names", () => {
    expect(inferProvider("claude-haiku-4-5")).toBe("anthropic");
    expect(inferProvider("mystery-model")).toBeUndefined();
  });

  it("rewrites span attributes before the inner exporter sees them", () => {
    let seen: Record<string, unknown> | undefined;
    const inner: SpanExporter = {
      export: (spans, done) => {
        seen = spans[0]!.attributes as Record<string, unknown>;
        done({ code: 0 });
      },
      shutdown: async () => {},
    };
    const span = { attributes: { ...llmAttrs } } as unknown as ReadableSpan;
    new GenAIMappingExporter(inner).export([span], () => {});
    expect(seen?.["gen_ai.usage.total_tokens"]).toBe(506);
  });
});
