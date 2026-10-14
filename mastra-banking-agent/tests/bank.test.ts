import { describe, expect, it } from "vitest";
import { BankError, loadBank } from "../src/bank.ts";

const MAREN = "CUS-3001";

describe("Bank", () => {
  it("returns recent transactions newest first, capped by limit", () => {
    const txs = loadBank().recentTransactions(MAREN, "ACC-7001", 3);
    expect(txs).toHaveLength(3);
    expect(txs.map((t) => t.date)).toEqual([...txs.map((t) => t.date)].sort().reverse());
  });

  it("refuses to read another customer's account", () => {
    expect(() => loadBank().getBalance(MAREN, "ACC-7003")).toThrow(BankError);
  });

  it("freezing a card changes in-memory state only", () => {
    const bank = loadBank();
    expect(bank.listCards(MAREN).every((c) => c.status === "active")).toBe(true);
    bank.freezeCard(MAREN, "CARD-5101");
    expect(bank.listCards(MAREN).map((c) => c.status)).toEqual(["frozen", "active"]);
    expect(loadBank().listCards(MAREN).every((c) => c.status === "active")).toBe(true); // fresh load: file untouched
  });

  it("cannot freeze someone else's card", () => {
    expect(() => loadBank().freezeCard(MAREN, "CARD-5103")).toThrow(BankError);
  });
});
