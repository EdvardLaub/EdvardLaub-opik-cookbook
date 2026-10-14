// An exporter decorator: rewrites each span's attributes with the mapping
// layer, then hands the spans to the real (OTLP) exporter.
import type { ReadableSpan, SpanExporter } from "@opentelemetry/sdk-trace-base";
import { mapSpanAttributes } from "./mapping.ts";

type ResultCallback = Parameters<SpanExporter["export"]>[1];

export class GenAIMappingExporter implements SpanExporter {
  constructor(private readonly inner: SpanExporter) {}

  export(spans: ReadableSpan[], done: ResultCallback): void {
    for (const span of spans) {
      // ReadableSpan.attributes is writable at runtime; replace in place.
      const mapped = mapSpanAttributes(span.attributes as Record<string, unknown>);
      for (const key of Object.keys(span.attributes)) delete (span.attributes as Record<string, unknown>)[key];
      Object.assign(span.attributes, mapped);
    }
    this.inner.export(spans, done);
  }

  shutdown(): Promise<void> {
    return this.inner.shutdown();
  }

  forceFlush(): Promise<void> {
    return this.inner.forceFlush?.() ?? Promise.resolve();
  }
}
