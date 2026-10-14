// Wires VoltAgent's OpenTelemetry layer to Opik. This module (plus mapping.ts
// and exporter.ts) is the only place that knows tracing exists.
import { VoltAgentObservability } from "@voltagent/core";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { GenAIMappingExporter } from "./exporter.ts";

export const PROJECT_NAME = process.env.OPIK_PROJECT_NAME ?? "voltagent-bike-workshop";

// OPIK_URL_OVERRIDE is the same variable the Opik SDKs read, e.g.
// http://localhost:5173/api/ for a local Opik; default is Opik Cloud.
function otlpUrl(): string {
  const base = (process.env.OPIK_URL_OVERRIDE ?? "https://www.comet.com/opik/api").replace(/\/+$/, "");
  return `${base}/v1/private/otel/v1/traces`;
}

// OPIK_TRACK_DISABLE=true is the same switch the Opik SDKs honour: no span
// processor is attached, so nothing is exported (used by the offline tests).
export const trackingDisabled = () => /^(1|true)$/i.test(process.env.OPIK_TRACK_DISABLE ?? "");

export function createObservability(): VoltAgentObservability {
  if (trackingDisabled()) return new VoltAgentObservability({ serviceName: "voltagent-bike-workshop", spanProcessors: [] });

  // The OTLP exporter posts spans to Opik's OTel endpoint; the projectName
  // header decides which Opik project the traces land in.
  const headers: Record<string, string> = {
    "Comet-Workspace": process.env.OPIK_WORKSPACE ?? process.env.OPIK_WORKSPACE_NAME ?? "default",
    projectName: PROJECT_NAME,
  };
  if (process.env.OPIK_API_KEY) headers.Authorization = process.env.OPIK_API_KEY;

  return new VoltAgentObservability({
    serviceName: "voltagent-bike-workshop",
    spanProcessors: [
      new BatchSpanProcessor(new GenAIMappingExporter(new OTLPTraceExporter({ url: otlpUrl(), headers }))),
    ],
  });
}
