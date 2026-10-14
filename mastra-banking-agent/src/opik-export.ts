// The Opik-facing half of the app: a SpanExporter that sits between Mastra's OtelExporter and
// Opik's OTLP endpoint. Everything Opik-specific that Mastra's span attributes don't give us
// for free is done here, in one small pure function that is easy to unit test.
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";
import type { ExportResult } from "@opentelemetry/core";

type Attrs = Record<string, unknown>;

// Mastra stores the agent's reply on the root span as `mastra.agent_run.output` ({ text, files }),
// a key Opik does not recognise, so the trace's Output column stays empty. Opik does read plain
// `input` / `output` attributes, so we copy the customer's message and the final answer there.
export function tidyAttributes(attrs: Attrs): Attrs {
  if (attrs["mastra.span.type"] !== "agent_run") return attrs;
  const out: Attrs = { ...attrs };
  if (typeof attrs["mastra.agent_run.input"] === "string") out["input"] = attrs["mastra.agent_run.input"];
  const text = extractText(attrs["mastra.agent_run.output"]);
  if (text !== undefined) out["output"] = text;
  return out;
}

function extractText(raw: unknown): string | undefined {
  if (typeof raw !== "string") return undefined;
  try {
    const parsed = JSON.parse(raw) as { text?: unknown };
    return typeof parsed.text === "string" ? parsed.text : raw;
  } catch {
    return raw;
  }
}

export function makeOpikSpanExporter({ url, headers }: { url: string; headers: Record<string, string> }): SpanExporter {
  // OTLPTraceExporter speaks OTLP/HTTP (JSON) to Opik's /v1/private/otel/v1/traces route.
  const inner = new OTLPTraceExporter({ url, headers });
  return {
    export(spans: ReadableSpan[], done: (r: ExportResult) => void) {
      // Mastra's spans are plain objects; we swap each span's attribute bag for the tidied copy
      // just before it is serialised, so the trace that reaches Opik carries Input and Output.
      for (const s of spans) (s as { attributes: Attrs }).attributes = tidyAttributes(s.attributes as Attrs);
      inner.export(spans, done);
    },
    shutdown: () => inner.shutdown(),
    forceFlush: () => inner.forceFlush(),
  };
}
