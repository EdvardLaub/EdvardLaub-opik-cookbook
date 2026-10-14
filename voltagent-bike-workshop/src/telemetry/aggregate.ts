// VoltAgent opens ONE llm span per generateText call, however many model
// steps the call takes (tool call -> tool result -> final answer). That span
// carries the token usage of the last step only, and no output. The totals
// and the final answer sit on the agent's root span, which ends last. This
// processor holds each run's llm span until the root span ends, copies the
// run totals onto it, and then releases everything to the real processor.
import type { ReadableSpan, SpanProcessor } from "@opentelemetry/sdk-trace-base";
import type { Attrs } from "./mapping.ts";

const USAGE_KEYS = ["prompt_tokens", "completion_tokens", "total_tokens"];

export const isLlmSpan = (a: Attrs) => a["span.type"] === "llm";
export const isAgentRoot = (a: Attrs) => a["entity.type"] === "agent" && a["span.type"] === undefined;

// Pure part, unit-tested: overwrite the llm span's usage with the run totals
// and give it the run's answer as output. Only done when the run has exactly
// one llm span, because the totals cannot be split across several.
export function applyRunTotals(llmSpans: Attrs[], root: Attrs): void {
  if (llmSpans.length !== 1) return;
  const llm = llmSpans[0]!;
  for (const key of USAGE_KEYS) {
    const total = root[`usage.${key}`];
    if (typeof total === "number") llm[`llm.usage.${key}`] = total;
  }
  if (typeof root["output"] === "string") llm["llm.output"] = root["output"];
}

export class AgentRunAggregator implements SpanProcessor {
  private held = new Map<string, ReadableSpan[]>();

  constructor(private readonly next: SpanProcessor) {}

  onStart(...args: Parameters<SpanProcessor["onStart"]>): void {
    this.next.onStart(...args);
  }

  onEnd(span: ReadableSpan): void {
    const attrs = span.attributes as Attrs;
    const run = attrs["operation.id"];
    if (typeof run === "string" && isLlmSpan(attrs)) {
      this.held.set(run, [...(this.held.get(run) ?? []), span]);
      return;
    }
    if (typeof run === "string" && isAgentRoot(attrs)) {
      const llmSpans = this.held.get(run) ?? [];
      this.held.delete(run);
      applyRunTotals(llmSpans.map((s) => s.attributes as Attrs), attrs);
      for (const s of llmSpans) this.next.onEnd(s);
    }
    this.next.onEnd(span);
  }

  // Never lose spans on exit: release anything still held, untouched.
  private release(): void {
    for (const spans of this.held.values()) for (const s of spans) this.next.onEnd(s);
    this.held.clear();
  }

  forceFlush(): Promise<void> {
    this.release();
    return this.next.forceFlush();
  }

  shutdown(): Promise<void> {
    this.release();
    return this.next.shutdown();
  }
}
