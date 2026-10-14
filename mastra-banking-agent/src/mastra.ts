import { Mastra } from "@mastra/core/mastra";
import { bankingAgent } from "./agent.ts";

export const mastra = new Mastra({
  agents: { bankingAgent },
});
