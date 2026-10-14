import { Mastra } from "@mastra/core/mastra";
import { Observability } from "@mastra/observability";
import { OtelExporter } from "@mastra/otel-exporter";
import { bankingAgent } from "./agent.ts";
import { makeOpikSpanExporter } from "./opik-export.ts";

// Opik's OpenTelemetry endpoint. Local Opik: OPIK_URL_OVERRIDE=http://localhost:5173/api/
// Opik Cloud: leave it unset and set OPIK_API_KEY + OPIK_WORKSPACE.
const opikBase = (process.env.OPIK_URL_OVERRIDE ?? "https://www.comet.com/opik/api").replace(/\/+$/, "");

export const PROJECT = process.env.OPIK_PROJECT_NAME ?? "mastra-banking-agent";

const otlpUrl = `${opikBase}/v1/private/otel/v1/traces`;
const otlpHeaders: Record<string, string> = {
  // projectName routes the traces into this Opik project (default project otherwise);
  // Comet-Workspace picks the workspace. Authorization is only needed on Opik Cloud.
  projectName: PROJECT,
  "Comet-Workspace": process.env.OPIK_WORKSPACE ?? "default",
  ...(process.env.OPIK_API_KEY ? { Authorization: process.env.OPIK_API_KEY } : {}),
};

// Tracking switch for tests and offline runs: OPIK_TRACK_DISABLE=true leaves Mastra with no
// observability config at all, so nothing is exported and nothing tries to reach Opik.
const trackingDisabled = ["true", "1"].includes((process.env.OPIK_TRACK_DISABLE ?? "").toLowerCase());

export const mastra = new Mastra({
  agents: { bankingAgent },
  // Mastra's Observability layer records agent runs, model calls and tool executions as spans;
  // the OtelExporter ships them to Opik, where each agent.generate() call becomes one trace
  // (root invoke_agent span -> agent_step -> chat / execute_tool children).
  observability: trackingDisabled ? undefined : new Observability({
    configs: {
      default: {
        serviceName: PROJECT,
        exporters: [
          new OtelExporter({
            // OtelExporter insists on a provider block, even when it is handed its own exporter below.
            provider: { custom: { endpoint: otlpUrl, headers: otlpHeaders, protocol: "http/json" } },
            // Opik ingests traces only; skip the log signal so nothing is POSTed to a /v1/logs route it lacks.
            signals: { logs: false },
            // Our own SpanExporter (src/opik-export.ts) replaces the built-in one, so span
            // attributes can be tidied before Opik ingests them.
            exporter: makeOpikSpanExporter({ url: otlpUrl, headers: otlpHeaders }),
          }),
        ],
      },
    },
  }),
});
