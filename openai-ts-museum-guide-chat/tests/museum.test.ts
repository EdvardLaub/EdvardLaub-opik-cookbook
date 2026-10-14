import { describe, expect, it } from "vitest";
import { ACCESSIBILITY, EXHIBITS, TICKETS, buildSystemPrompt, quoteTickets } from "../src/museum.js";

describe("system prompt", () => {
  it("contains every exhibit, the opening hours and the ticket prices", () => {
    const prompt = buildSystemPrompt();
    for (const e of EXHIBITS) expect(prompt).toContain(e.name);
    expect(prompt).toContain("Saturday and Sunday: 09:00-18:00");
    expect(prompt).toContain(`Adult ${TICKETS.adult}`);
    expect(prompt).toContain(ACCESSIBILITY[2]!);
  });

  it("tells the model not to invent facts", () => {
    expect(buildSystemPrompt()).toMatch(/Never invent/);
  });
});

describe("quoteTickets", () => {
  it("adds up separate tickets", () => {
    expect(quoteTickets(1, 2)).toBe(14 + 7 * 2);
    expect(quoteTickets(1, 0, 1)).toBe(14 + 11);
  });

  it("uses the family ticket for 2 adults + 1-3 children when it is cheaper", () => {
    expect(quoteTickets(2, 2)).toBe(38); // 42 separately
    expect(quoteTickets(2, 1)).toBe(35); // separate is cheaper than 38
  });
});
