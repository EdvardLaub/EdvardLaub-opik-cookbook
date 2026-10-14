// The workshop's three tools. The lookup logic is plain functions over the
// data (easy to unit-test); createTool only wraps them for the agent.
import { createTool } from "@voltagent/core";
import { z } from "zod";
import { loadJobs, loadParts, loadSlots } from "./data.ts";
import type { Job, Part, Slot } from "./data.ts";

export function findJob(
  jobs: Job[],
  query: { ticket_id?: string; customer_name?: string },
): Job | undefined {
  if (query.ticket_id) {
    return jobs.find((j) => j.ticket_id.toLowerCase() === query.ticket_id!.trim().toLowerCase());
  }
  if (query.customer_name) {
    const needle = query.customer_name.trim().toLowerCase();
    return jobs.find((j) => j.customer.toLowerCase().includes(needle));
  }
  return undefined;
}

export function searchParts(parts: Part[], query: { sku?: string; keyword?: string }): Part[] {
  if (query.sku) {
    const sku = query.sku.trim().toLowerCase();
    return parts.filter((p) => p.sku.toLowerCase() === sku);
  }
  const words = (query.keyword ?? "").toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  return parts.filter((p) => {
    const hay = `${p.name} ${p.fits}`.toLowerCase();
    return words.every((w) => hay.includes(w));
  });
}

export function freeSlots(
  slots: Slot[],
  opts: { minutes_needed: number; on_or_after?: string },
): Slot[] {
  return slots
    .filter((s) => !s.booked && s.minutes >= opts.minutes_needed)
    .filter((s) => !opts.on_or_after || s.date >= opts.on_or_after)
    .sort((a, b) => `${a.date} ${a.start}`.localeCompare(`${b.date} ${b.start}`))
    .slice(0, 3);
}

export const lookupJobTicket = createTool({
  name: "lookup_job_ticket",
  description:
    "Look up a repair job ticket by ticket id or by customer name. Pass only the argument the " +
    "customer actually gave; leave the other one out. " +
    "Returns the bike, the issue, the status, the parts needed, the labour minutes and the quote.",
  parameters: z.object({
    ticket_id: z.string().optional().describe("Ticket id exactly as the customer wrote it (format WS-####)"),
    customer_name: z.string().optional().describe("Customer name, full or partial"),
  }),
  execute: async (args) => findJob(loadJobs(), args) ?? { error: "No matching job ticket found." },
});

export const checkPartsStock = createTool({
  name: "check_parts_stock",
  description:
    "Check workshop stock for a part by exact SKU or by keywords (e.g. 'touring tyre'). " +
    "Returns name, price in EUR and units in stock; 0 means out of stock.",
  parameters: z.object({
    sku: z.string().optional().describe("Exact part SKU, only if it is already known from a ticket"),
    keyword: z.string().optional().describe("Keywords describing the part"),
  }),
  execute: async (args) => {
    const hits = searchParts(loadParts(), args);
    return hits.length ? { parts: hits } : { error: "No matching part." };
  },
});

export const findFreeSlots = createTool({
  name: "find_free_slots",
  description:
    "Find the earliest free workshop booking slots (up to 3) long enough for the job. " +
    "Dates are ISO (YYYY-MM-DD). Today is 2026-10-30.",
  parameters: z.object({
    minutes_needed: z.number().int().positive().describe("Labour minutes the job needs"),
    on_or_after: z.string().optional().describe("Earliest acceptable date, YYYY-MM-DD"),
  }),
  execute: async (args) => {
    const slots = freeSlots(loadSlots(), args);
    return slots.length ? { slots } : { error: "No free slot long enough." };
  },
});

export const workshopTools = [lookupJobTicket, checkPartsStock, findFreeSlots];
