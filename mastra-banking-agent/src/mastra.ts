import { Mastra } from "@mastra/core/mastra";
import { Observability } from "@mastra/observability";
import { OtelExporter } from "@mastra/otel-exporter";
import { bankingAgent } from "./agent.ts";

// Opik's OpenTelemetry endpoint. Local Opik: OPIK_URL_OVERRIDE=http://localhost:5173/api/
// Opik Cloud: leave it unset and set OPIK_API_KEY + OPIK_WORKSPACE.
const opikBase = (process.env.OPIK_URL_OVERRIDE ?? "https://www.comet.com/opik/api").replace(/\/+$/, "");

export const PROJECT = process.env.OPIK_PROJECT_NAME ?? "mastra-banking-agent";

export const mastra = new Mastra({
  agents: { bankingAgent },
  // Mastra's Observability layer records agent runs, model calls and tool executions as spans;
  // the OtelExporter ships them to Opik, where each agent.generate() call becomes one trace
  // (root invoke_agent span -> agent_step -> chat / execute_tool children).
  observability: new Observability({
    configs: {
      default: {
        serviceName: PROJECT,
        exporters: [
          new OtelExporter({
            provider: {
              custom: {
                endpoint: `${opikBase}/v1/private/otel/v1/traces`,
                protocol: "http/json",
                headers: {
                  // projectName routes the traces into this Opik project (default project otherwise);
                  // Comet-Workspace picks the workspace. Authorization is only needed on Opik Cloud.
                  projectName: PROJECT,
                  "Comet-Workspace": process.env.OPIK_WORKSPACE ?? "default",
                  ...(process.env.OPIK_API_KEY ? { Authorization: process.env.OPIK_API_KEY } : {}),
                },
              },
            },
          }),
        ],
      },
    },
  }),
});
