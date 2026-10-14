// All Opik wiring for the app lives in this one module.
import { registerOTel } from "@vercel/otel";
import { registerTelemetry } from "ai";
import { OpenTelemetry } from "@ai-sdk/otel";
import { OpikExporter } from "opik-vercel";
import { Opik } from "opik";

import { PROJECT_NAME, TRACE_NAME } from "./config";

/** Pure helper (unit-tested): turn runtimeContext into the span attributes Opik reads. */
export function opikSpanAttributes(
  runtimeContext: Record<string, unknown> | undefined,
): Record<string, string> {
  const attributes: Record<string, string> = {};
  if (runtimeContext?.threadId != null) {
    attributes["ai.telemetry.metadata.threadId"] = String(runtimeContext.threadId);
  }
  if (runtimeContext?.traceName != null) {
    attributes["ai.telemetry.metadata.traceName"] = String(runtimeContext.traceName);
  }
  return attributes;
}

let registered = false;

/** Called once from instrumentation.ts when the Next.js server boots. */
export function registerOpik(): void {
  if (registered) return;
  registered = true;

  // OpikExporter is an OpenTelemetry SpanExporter: it groups the AI SDK spans
  // of one streamText call into one Opik trace (llm span with usage and cost
  // underneath). Without it nothing reaches Opik. The Opik client pins the project.
  registerOTel({
    serviceName: PROJECT_NAME,
    traceExporter: new OpikExporter({
      client: new Opik({ projectName: PROJECT_NAME }),
      tags: ["nextjs", "streaming", "stargazing"],
    }),
  });

  // AI SDK v7 emits no OTel spans until a telemetry integration is registered.
  // enrichSpan copies the route's threadId/traceName into the attributes
  // opik-vercel reads, which is what groups turns into Opik threads.
  registerTelemetry(
    new OpenTelemetry({
      usage: true,
      enrichSpan: ({ runtimeContext }) => opikSpanAttributes(runtimeContext),
    }),
  );
}

/** Per-call telemetry settings for streamText; pass these next to a runtimeContext. */
export function telemetrySettings() {
  return {
    // getSettings sets isEnabled/recordInputs/recordOutputs and the trace name,
    // so the trace carries the full prompt and reply text.
    ...OpikExporter.getSettings({ name: TRACE_NAME }),
    // v7 only copies runtimeContext keys that are explicitly allowed onto spans.
    includeRuntimeContext: { threadId: true, traceName: true },
  };
}
