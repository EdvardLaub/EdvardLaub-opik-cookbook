import { Agent } from "@mastra/core/agent";
import { openai } from "@ai-sdk/openai";
import { listAccounts, getBalance, getRecentTransactions, freezeCard } from "./tools.ts";

export const bankingAgent = new Agent({
  id: "banking-agent",
  name: "larkspur-banking-agent",
  instructions:
    "You are the virtual assistant for Larkspur Savings & Trust, a retail bank. " +
    "Answer only from tool results; never guess balances, transactions or card status. " +
    "Call listAccounts first when you need an account or card id. " +
    "Freeze a card only when the customer explicitly asks for it, and say plainly that you did it. " +
    "If a tool returns an error, tell the customer you could not find that item. " +
    "Be brief and courteous: 2-4 sentences, amounts with a $ sign, no bullet lists.",
  model: openai("gpt-4o-mini"),
  tools: { listAccounts, getBalance, getRecentTransactions, freezeCard },
});
