import OpenAI from "openai";
import { Opik, getTrackContext, track } from "opik";
import { trackOpenAI } from "opik-openai";
import { PROJECT_NAME } from "./env.js";
import { findLeaks } from "./checks.js";
import type { Release } from "./releases.js";

/** Which prompt-library version produced an entry. */
export interface PromptRef {
  prompt_name: string;
  prompt_version: string | undefined;
  prompt_commit: string | undefined;
}

export const MODEL = "gpt-4o-mini";
/** Model behind the test-suite judge. */
export const JUDGE_MODEL = "gpt-4.1-mini";

/** The user message: the release version plus the raw commit lines, exactly as git printed them. */
export function formatCommits(release: Release): string {
  return `Release ${release.version}\n\nCommits:\n${release.commits.map((c) => `- ${c}`).join("\n")}`;
}

// Built lazily so unit tests can import this module without an API key or an Opik server.
let openai: OpenAI | undefined;
let opik: Opik | undefined;
const getOpenAI = () => (openai ??= new OpenAI());
export const getOpik = () => (opik ??= new Opik({ projectName: PROJECT_NAME }));
/** Test seam: swap in a stub OpenAI client. */
export const setOpenAI = (client: OpenAI) => {
  openai = client;
};

// track() opens a trace named "write_changelog" and records the arguments (the release and the
// exact system prompt text) as its input and the returned Markdown as its output. Without it the
// completion below would be a stand-alone trace with no record of which prompt produced it.
export const writeChangelog = track(
  { name: "write_changelog", type: "general", projectName: PROJECT_NAME },
  async (release: Release, systemPrompt: string, promptRef?: PromptRef): Promise<string> => {
    const ctx = getTrackContext();
    // Stamp the prompt version on the trace so a Traces-tab row says which library version wrote it.
    if (promptRef) ctx?.trace.update({ metadata: { ...promptRef } });
    // trackOpenAI wraps the client: each completion becomes a span with the messages, model and
    // token usage (Opik derives cost from them). parent = the current span nests it under this
    // trace; without parent the SDK would start a separate trace per call.
    const parent = ctx?.span;
    const client = trackOpenAI(getOpenAI(), {
      client: getOpik(),
      generationName: "chat-completion",
      ...(parent ? { parent } : {}),
    });
    const response = await client.chat.completions.create({
      model: MODEL,
      temperature: 0,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: formatCommits(release) },
      ],
    });
    const entry = response.choices[0]?.message?.content ?? "";

    // A deterministic lint next to the LLM judge. trace.score logs a feedback score on the trace
    // (a "no_hash_or_ticket_leaks" column in the Traces table): 1 = clean, 0 = a leak, reason lists it.
    const leaks = findLeaks(entry);
    const leaked = [...leaks.hashes, ...leaks.tickets];
    ctx?.trace.score({
      name: "no_hash_or_ticket_leaks",
      value: leaked.length ? 0 : 1,
      ...(leaked.length ? { reason: `Leaked: ${leaked.join(", ")}` } : {}),
    });
    return entry;
  },
) as (release: Release, systemPrompt: string, promptRef?: PromptRef) => Promise<string>;

/** Send any queued traces and spans to Opik. Call once before the process exits. */
export async function flushTraces(): Promise<void> {
  await getOpik().flush();
}
