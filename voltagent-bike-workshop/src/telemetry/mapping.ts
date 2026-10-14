// Pure attribute-mapping layer: VoltAgent's span attributes in, the OTel
// GenAI (`gen_ai.*`) names Opik understands out. No SDK imports, so it is
// unit-testable without exporting anything.
export type Attrs = Record<string, unknown>;

// Opik prices a span from a recognized provider plus the model name, so the
// provider has to be spelled out: VoltAgent only records it on the root span.
export function inferProvider(model: string): string | undefined {
  if (/^(gpt-|o\d|chatgpt)/i.test(model)) return "openai";
  if (/^claude/i.test(model)) return "anthropic";
  if (/^gemini/i.test(model)) return "google";
  return undefined;
}

// VoltAgent's llm.messages is AI-SDK shaped ({role, content: string | parts[]});
// Opik reads `gen_ai.input.messages` in the OTel GenAI shape ({role, parts[]}).
export function toGenAIMessages(raw: unknown): string | undefined {
  if (typeof raw !== "string") return undefined;
  try {
    const messages = JSON.parse(raw) as { role: string; content: unknown }[];
    return JSON.stringify(
      messages.map((m) => ({
        role: m.role,
        parts:
          typeof m.content === "string"
            ? [{ type: "text", content: m.content }]
            : (m.content as { type: string; text?: string }[]).map((p) => ({ type: p.type, content: p.text ?? "" })),
      })),
    );
  } catch {
    return undefined;
  }
}

// Opik dumps every attribute it does not recognise into the span's input
// field, so after mapping we keep only the names it understands.
const OPIK_READS = /^(gen_ai\.|input\.|output\.)/;

export function mapSpanAttributes(attrs: Attrs): Attrs {
  const out: Attrs = { ...attrs };

  if (attrs["span.type"] === "llm") {
    const model = attrs["llm.model"];
    if (typeof model === "string") {
      out["gen_ai.request.model"] = model;
      const provider = inferProvider(model);
      if (provider) out["gen_ai.provider.name"] = provider;
    }
    // llm.usage.* -> gen_ai.usage.* is what makes Opik record token usage.
    for (const key of ["prompt_tokens", "completion_tokens", "total_tokens"]) {
      const value = attrs[`llm.usage.${key}`];
      if (value !== undefined) out[`gen_ai.usage.${key}`] = value;
    }
    const messages = toGenAIMessages(attrs["llm.messages"]);
    if (messages) out["gen_ai.input.messages"] = messages;
    // llm.output is filled in by AgentRunAggregator (the llm span has none).
    if (typeof attrs["llm.output"] === "string") {
      out["gen_ai.output.messages"] = JSON.stringify([
        { role: "assistant", parts: [{ type: "text", content: attrs["llm.output"] }] },
      ]);
    }
  } else if (attrs["span.type"] === "tool") {
    // gen_ai.tool.* makes Opik type the span as a tool call, with the
    // arguments as its input and the tool's return value as its output.
    out["gen_ai.tool.name"] = attrs["tool.name"];
    out["gen_ai.tool.call.arguments"] = attrs["input"] ?? "{}";
    if (attrs["output"] !== undefined) out["gen_ai.tool.call.result"] = attrs["output"];
  } else if (attrs["entity.type"] === "agent" && attrs["span.type"] === undefined) {
    // The agent run (root span): input.value / output.value become the trace's
    // input and output columns instead of an attribute dump.
    if (attrs["input"] !== undefined) out["input.value"] = attrs["input"];
    if (attrs["output"] !== undefined) out["output.value"] = attrs["output"];
  }
  return Object.fromEntries(Object.entries(out).filter(([key]) => OPIK_READS.test(key)));
}
