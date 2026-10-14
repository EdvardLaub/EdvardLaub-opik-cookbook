// Pure helpers (no Opik, no network) so they are easy to unit test.

/** Collapse runs of whitespace so line wraps in the manual don't break matching. */
export function normalize(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

/** Pull every <quote>...</quote> excerpt out of a model answer. */
export function extractQuotes(answer: string): string[] {
  return [...answer.matchAll(/<quote>([\s\S]*?)<\/quote>/g)].map((m) => normalize(m[1] ?? ""));
}

export interface QuoteCheck {
  quotes: string[];
  missing: string[];
  allVerbatim: boolean;
}

/** A quote is verbatim when it is a substring of the manual (whitespace-normalised). */
export function checkQuotes(answer: string, manual: string): QuoteCheck {
  const haystack = normalize(manual);
  const quotes = extractQuotes(answer);
  const missing = quotes.filter((q) => q.length === 0 || !haystack.includes(q));
  return { quotes, missing, allVerbatim: quotes.length > 0 && missing.length === 0 };
}
