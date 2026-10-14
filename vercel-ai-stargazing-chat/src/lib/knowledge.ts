// Domain knowledge for the assistant: a small fictional observing guide and
// sky-events calendar, plus a keyword retriever. No Opik code lives here, so
// it is plain, offline-testable logic.
import { readFileSync } from "node:fs";
import path from "node:path";

export interface GuideSection {
  title: string;
  body: string;
}

export interface SkyEvent {
  date: string; // YYYY-MM-DD
  title: string;
  kind: string;
  detail: string;
}

const DATA_DIR = path.join(process.cwd(), "data");

/** Split the markdown guide into one section per "## " heading. */
export function parseGuide(markdown: string): GuideSection[] {
  return markdown
    .split(/^## /m)
    .slice(1) // drop the "# Title" preamble
    .map((chunk) => {
      const [title, ...rest] = chunk.split("\n");
      return { title: (title ?? "").trim(), body: rest.join("\n").trim() };
    });
}

export function loadGuide(dir = DATA_DIR): GuideSection[] {
  return parseGuide(readFileSync(path.join(dir, "observing-guide.md"), "utf8"));
}

export function loadEvents(dir = DATA_DIR): SkyEvent[] {
  const raw = JSON.parse(readFileSync(path.join(dir, "sky-events.json"), "utf8"));
  return raw.events as SkyEvent[];
}

const STOP = new Set([
  "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "it", "my", "i", "we",
  "do", "does", "can", "how", "what", "when", "which", "with", "at", "be", "are", "should",
  "this", "that", "me", "you", "your", "there", "any", "about",
]);

/** Lowercase word tokens with a crude plural strip, so "meteors" matches "meteor". */
export function tokenize(text: string): string[] {
  return (text.toLowerCase().match(/[a-z0-9]+/g) ?? [])
    .filter((w) => !STOP.has(w))
    .map((w) => (w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w));
}

function overlap(query: Set<string>, text: string): number {
  let score = 0;
  for (const token of new Set(tokenize(text))) if (query.has(token)) score += 1;
  return score;
}

/** Top-k guide sections by keyword overlap; a title hit counts triple. */
export function retrieveGuide(query: string, sections: GuideSection[], k = 2): GuideSection[] {
  const q = new Set(tokenize(query));
  return sections
    .map((s) => ({ s, score: overlap(q, s.body) + 3 * overlap(q, s.title) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map((x) => x.s);
}

/** Top-k calendar events by keyword overlap across title, kind and detail. */
export function retrieveEvents(query: string, events: SkyEvent[], k = 2): SkyEvent[] {
  const q = new Set(tokenize(query));
  return events
    .map((e) => ({ e, score: overlap(q, `${e.title} ${e.kind} ${e.detail}`) + 2 * overlap(q, e.title) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map((x) => x.e);
}

/** The grounding block that is appended to the system prompt for one turn. */
export function buildContext(
  query: string,
  guide: GuideSection[] = loadGuide(),
  events: SkyEvent[] = loadEvents(),
): string {
  const sections = retrieveGuide(query, guide);
  const hits = retrieveEvents(query, events);
  const parts: string[] = [];
  if (sections.length) {
    parts.push("OBSERVING GUIDE EXCERPTS:\n" + sections.map((s) => `[${s.title}] ${s.body}`).join("\n\n"));
  }
  if (hits.length) {
    parts.push("SKY EVENTS CALENDAR:\n" + hits.map((e) => `${e.date} - ${e.title}: ${e.detail}`).join("\n"));
  }
  return parts.length ? parts.join("\n\n") : "No matching guide excerpts or calendar events were found.";
}
