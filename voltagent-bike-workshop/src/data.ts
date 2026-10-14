// Loads the fictional workshop data from data/*.json. Everything the tools
// know comes from these three files, so the demo needs no database.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export type Job = {
  ticket_id: string;
  customer: string;
  bike: string;
  issue: string;
  status: "quoted" | "waiting_for_parts" | "in_workshop" | "ready_for_pickup";
  parts_needed: string[];
  labour_minutes: number;
  quote_eur: number;
};

export type Part = { sku: string; name: string; price_eur: number; stock: number; fits: string };

export type Slot = {
  slot_id: string;
  date: string;
  start: string;
  mechanic: string;
  minutes: number;
  booked: boolean;
};

export type Scenario = { title: string; message: string };

function load<T>(file: string): T {
  const path = fileURLToPath(new URL(`../data/${file}`, import.meta.url));
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

export const loadJobs = () => load<Job[]>("jobs.json");
export const loadParts = () => load<Part[]>("parts.json");
export const loadSlots = () => load<Slot[]>("slots.json");
export const loadScenarios = () => load<Scenario[]>("requests.json");
