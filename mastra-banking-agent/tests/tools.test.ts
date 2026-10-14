import { describe, expect, it } from "vitest";
import { RequestContext } from "@mastra/core/request-context";
import { getBalance, getRecentTransactions } from "../src/tools.ts";

const ctx = (customerId: string) => ({ requestContext: new RequestContext([["customerId", customerId]]) }) as any;

describe("tools", () => {
  it("getBalance reads the signed-in customer's account", async () => {
    const res: any = await getBalance.execute!({ accountId: "ACC-7001" }, ctx("CUS-3001"));
    expect(res).toMatchObject({ accountId: "ACC-7001", balance: 2431.18 });
  });

  it("returns an error object, not a throw, for an account the customer does not own", async () => {
    const res: any = await getBalance.execute!({ accountId: "ACC-7003" }, ctx("CUS-3001"));
    expect(res.error).toMatch(/not found/);
  });

  it("getRecentTransactions respects the limit", async () => {
    const res: any = await getRecentTransactions.execute!({ accountId: "ACC-7001", limit: 2 }, ctx("CUS-3001"));
    expect(res.transactions).toHaveLength(2);
  });
});
