// The agent definition: model, instructions and tools. Nothing here knows
// how (or whether) the run is observed.
import { Agent } from "@voltagent/core";
import type { AgentModelValue } from "@voltagent/core";
import { workshopTools } from "./tools.ts";

// The model is a parameter so tests can inject a stub instead of calling
// OpenAI. The default string is resolved by VoltAgent's model router to the AI
// SDK's OpenAI provider, which reads OPENAI_API_KEY from the environment.
export const createWorkshopAssistant = (model: AgentModelValue = "openai/gpt-4o-mini") =>
  new Agent({
    name: "spoke-and-sprocket-assistant",
    model,
    instructions:
      "You are the front-desk assistant at Spoke & Sprocket, a small bicycle-repair workshop. " +
      "Never guess: look up the job ticket, check part stock and find booking slots with the tools. " +
      "A job can only be booked once every part it needs is in stock; if a part is out of stock, " +
      "say which one and do not offer a slot. Prices are in EUR. Answer in 2-4 friendly sentences.",
    tools: workshopTools,
  });

export const workshopAssistant = createWorkshopAssistant();
