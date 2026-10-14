// The assistant's tools. Three are read-only lookups; freezeCard is the only
// one that changes state (in memory). The signed-in customer comes from the
// request context, not from the model, so the model cannot ask for someone else's data.
import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { BankError, loadBank, type Bank } from "./bank.ts";

export const bank: Bank = loadBank();

// Failures are returned as data ({ error }) so the model can explain them,
// rather than thrown, which would abort the whole agent run.
export function guard<T extends object>(fn: () => T): T | { error: string } {
  try { return fn(); } catch (e) {
    if (e instanceof BankError) return { error: e.message };
    throw e;
  }
}

const customerOf = (ctx: { requestContext?: { get: (k: string) => unknown } }) => String(ctx.requestContext?.get("customerId") ?? "");

export const listAccounts = createTool({
  id: "listAccounts",
  description: "List the signed-in customer's accounts and cards (ids, types, last four digits). Call this first to find the right account or card id.",
  inputSchema: z.object({}),
  execute: async (_input, ctx) => {
    const customerId = customerOf(ctx);
    return {
      accounts: bank.listAccounts(customerId).map(({ id, type, last4 }) => ({ id, type, last4 })),
      cards: bank.listCards(customerId).map(({ id, accountId, last4, status }) => ({ id, accountId, last4, status })),
    };
  },
});

export const getBalance = createTool({
  id: "getBalance",
  description: "Read-only. Current balance of one account.",
  inputSchema: z.object({ accountId: z.string().describe("Account id such as ACC-7001") }),
  execute: async ({ accountId }, ctx) =>
    guard(() => {
      const a = bank.getBalance(customerOf(ctx), accountId);
      return { accountId: a.id, type: a.type, currency: a.currency, balance: a.balance };
    }),
});

export const getRecentTransactions = createTool({
  id: "getRecentTransactions",
  description: "Read-only. Most recent transactions on one account, newest first. Negative amounts are debits.",
  inputSchema: z.object({
    accountId: z.string().describe("Account id such as ACC-7001"),
    limit: z.number().int().min(1).max(10).default(5),
  }),
  execute: async ({ accountId, limit }, ctx) =>
    guard(() => ({ accountId, transactions: bank.recentTransactions(customerOf(ctx), accountId, limit) })),
});

export const freezeCard = createTool({
  id: "freezeCard",
  description: "Freeze a debit card so it cannot be used. This changes state: only call it after the customer clearly asks to freeze a specific card.",
  inputSchema: z.object({ cardId: z.string().describe("Card id such as CARD-5101") }),
  execute: async ({ cardId }, ctx) =>
    guard(() => {
      const c = bank.freezeCard(customerOf(ctx), cardId);
      return { cardId: c.id, last4: c.last4, status: c.status };
    }),
});
