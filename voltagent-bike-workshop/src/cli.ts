// Scripted demo: replays the customer requests in data/requests.json through
// the workshop assistant, one after another, and prints the answers.
import "./env.ts";
import { VoltAgent } from "@voltagent/core";
import { workshopAssistant } from "./agent.ts";
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

// No `server` option: this stays a script, not an HTTP service.
new VoltAgent({ agents: { workshopAssistant } });

for (const [i, scenario] of loadScenarios().entries()) {
  console.log(`\n=== ${i + 1}. ${scenario.title} ===`);
  console.log(`Customer:  ${scenario.message}`);
  const result = await workshopAssistant.generateText(scenario.message);
  console.log(`Assistant: ${result.text}`);
}
process.exit(0);
