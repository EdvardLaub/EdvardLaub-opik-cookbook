// Plays four scripted customer requests through the banking assistant.
import { config } from "dotenv";
import { fileURLToPath } from "node:url";
import { RequestContext } from "@mastra/core/request-context";

// Example .env first, then the repo-root .env (provider keys live there).
config({
  path: [fileURLToPath(new URL("../.env", import.meta.url)), fileURLToPath(new URL("../../.env", import.meta.url))],
  quiet: true,
});

if (!process.env.OPENAI_API_KEY) {
  console.error("Missing OPENAI_API_KEY. Copy .env.example to .env and fill it in.");
  process.exit(1);
}

// Import Mastra only after env vars are loaded.
const { mastra } = await import("./mastra.ts");
const { bank } = await import("./tools.ts");

const CUSTOMER_ID = "CUS-3001"; // Maren Ostrowski, signed in for the whole demo

const REQUESTS = [
  "What's my checking balance?",
  "Show me my last four transactions on checking. Is anything there I should double-check?",
  "I think I lost my debit card for my checking account. Please freeze it.",
  "Can you tell me the balance on account ACC-7003?", // belongs to someone else: the tool must refuse
];

const agent = mastra.getAgent("bankingAgent");
const requestContext = new RequestContext([["customerId", CUSTOMER_ID]]);

for (const [i, request] of REQUESTS.entries()) {
  console.log(`\n=== Request ${i + 1} ===\nCustomer: ${request}`);
  const result = await agent.generate(request, { maxSteps: 6, requestContext });
  console.log(`Agent:    ${result.text}`);
}

console.log("\nCard states after the demo:", bank.listCards(CUSTOMER_ID).map((c) => `${c.id}=${c.status}`).join(", "));
