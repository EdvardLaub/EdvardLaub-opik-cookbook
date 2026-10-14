// The "core banking system" of Larkspur Savings & Trust: a few fictional
// customers loaded from data/bank.json. Reads are pure lookups; the only
// mutation is freezeCard, which flips a flag in this process's memory.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export interface Account { id: string; customerId: string; type: string; currency: string; balance: number; last4: string }
export interface Card { id: string; accountId: string; customerId: string; network: string; last4: string; status: "active" | "frozen" }
export interface Transaction { id: string; accountId: string; date: string; merchant: string; category: string; amount: number }
export interface Customer { id: string; name: string }
interface BankData { bank: string; customers: Customer[]; accounts: Account[]; cards: Card[]; transactions: Transaction[] }

export class BankError extends Error {}

export function loadBank(path = fileURLToPath(new URL("../data/bank.json", import.meta.url))): Bank {
  return new Bank(JSON.parse(readFileSync(path, "utf8")) as BankData);
}

export class Bank {
  constructor(private data: BankData) {}

  get name() { return this.data.bank; }

  // Ownership is enforced here, so a tool can never read another customer's data
  // no matter which id the model passes in.
  private ownedAccount(customerId: string, accountId: string): Account {
    const a = this.data.accounts.find((x) => x.id === accountId);
    if (!a || a.customerId !== customerId) throw new BankError(`Account ${accountId} not found for this customer`);
    return a;
  }

  listAccounts(customerId: string): Account[] {
    return this.data.accounts.filter((a) => a.customerId === customerId);
  }

  listCards(customerId: string): Card[] {
    return this.data.cards.filter((c) => c.customerId === customerId);
  }

  getBalance(customerId: string, accountId: string): Account {
    return this.ownedAccount(customerId, accountId);
  }

  recentTransactions(customerId: string, accountId: string, limit = 5): Transaction[] {
    this.ownedAccount(customerId, accountId);
    return this.data.transactions
      .filter((t) => t.accountId === accountId)
      .sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id))
      .slice(0, limit);
  }

  freezeCard(customerId: string, cardId: string): Card {
    const card = this.data.cards.find((c) => c.id === cardId && c.customerId === customerId);
    if (!card) throw new BankError(`Card ${cardId} not found for this customer`);
    card.status = "frozen"; // in-memory only: nothing is written back to data/bank.json
    return card;
  }
}
