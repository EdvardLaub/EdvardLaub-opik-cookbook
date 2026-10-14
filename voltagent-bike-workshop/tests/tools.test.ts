import { describe, expect, it } from "vitest";
import { loadJobs, loadParts, loadSlots } from "../src/data.ts";
import { findJob, freeSlots, searchParts } from "../src/tools.ts";

describe("workshop tools", () => {
  it("finds a job by ticket id or partial customer name", () => {
    const jobs = loadJobs();
    expect(findJob(jobs, { ticket_id: "ws-2041" })?.customer).toBe("Ines Calloway");
    expect(findJob(jobs, { customer_name: "nandakumar" })?.ticket_id).toBe("WS-2043");
    expect(findJob(jobs, { ticket_id: "WS-9999" })).toBeUndefined();
  });

  it("searches parts by sku and by keyword, reporting zero stock", () => {
    const parts = loadParts();
    expect(searchParts(parts, { sku: "CAS-11-34" })[0]?.stock).toBe(0);
    expect(searchParts(parts, { keyword: "touring tyre" }).map((p) => p.sku)).toEqual(["TYR-26x2"]);
    expect(searchParts(parts, {})).toEqual([]);
  });

  it("returns only free, long-enough slots in date order", () => {
    const slots = freeSlots(loadSlots(), { minutes_needed: 90 });
    expect(slots.map((s) => s.slot_id)).toEqual(["S-1101", "S-1103", "S-1105"]);
    expect(freeSlots(loadSlots(), { minutes_needed: 90, on_or_after: "2026-11-04" })[0]?.slot_id).toBe("S-1105");
  });
});
