// Scripted demo: replays the customer requests in data/requests.json through
// the workshop assistant, one after another, and prints the answers.
import "./env.ts";
import { VoltAgent } from "@voltagent/core";
import { workshopAssistant } from "./agent.ts";
import { createObservability, PROJECT_NAME } from "./telemetry/index.ts";
import { loadScenarios } from "./data.ts";

// VoltAgent puts the system prompt inside the messages array, which makes the
// AI SDK print a warning per request; drop that one known line.
const realWarn = console.warn.bind(console);
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("System messages in the prompt")) return;
  realWarn(...args);
};

if (!process.env.OPENAI_API_KEY) {
  console.error("Missing OPENAI_API_KEY. Copy .env.example to .env and fill it in.");
  process.exit(1);
}

// Passing `observability` is what sends every agent run to Opik over OTLP.
// No `server` option: this stays a script, not an HTTP service.
const observability = createObservability();
new VoltAgent({ agents: { workshopAssistant }, observability });

for (const [i, scenario] of loadScenarios().entries()) {
  console.log(`\n=== ${i + 1}. ${scenario.title} ===`);
  console.log(`Customer:  ${scenario.message}`);
  const result = await workshopAssistant.generateText(scenario.message);
  console.log(`Assistant: ${result.text}`);
  // Total tokens for the whole run (all model steps), to compare with Opik.
  console.log(`(tokens this request: ${result.totalUsage?.totalTokens})`);
}
// Flush the batch span processor so the last spans reach Opik before exit.
await observability.shutdown();
console.log(`\nDone. Open the "${PROJECT_NAME}" project in Opik to see the traces.`);
process.exit(0);
