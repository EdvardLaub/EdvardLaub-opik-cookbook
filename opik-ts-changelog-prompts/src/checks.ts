/** Cheap deterministic lint for the leaks v1 is known for. The LLM judge covers everything else. */
export interface LeakReport {
  hashes: string[];
  tickets: string[];
}

// A git short hash is 7 hex chars with at least one digit and one letter, so plain words and years don't match.
const HASH = /\b(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7}\b/g;
const TICKET = /(?:#\d{2,}|\b[A-Z]{2,6}-\d{2,}\b)/g;

export function findLeaks(entry: string): LeakReport {
  return {
    hashes: [...new Set(entry.match(HASH) ?? [])],
    tickets: [...new Set(entry.match(TICKET) ?? [])],
  };
}
