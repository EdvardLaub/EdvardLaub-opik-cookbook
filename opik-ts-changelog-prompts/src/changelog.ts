import OpenAI from "openai";
import { Opik, getTrackContext, track } from "opik";
import { trackOpenAI } from "opik-openai";
import { PROJECT_NAME } from "./env.js";
import type { Release } from "./releases.js";

export const MODEL = "gpt-4o-mini";

/** The user message: the release version plus the raw commit lines, exactly as git printed them. */
export function formatCommits(release: Release): string {
  return `Release ${release.version}\n\nCommits:\n${release.commits.map((c) => `- ${c}`).join("\n")}`;
}

// Built lazily so unit tests can import this module without an API key or an Opik server.
let openai: OpenAI | undefined;
let opik: Opik | undefined;
const getOpenAI = () => (openai ??= new OpenAI());
const getOpik = () => (opik ??= new Opik({ projectName: PROJECT_NAME }));
/** Test seam: swap in a stub OpenAI client. */
export const setOpenAI = (client: OpenAI) => {
  openai = client;
};

// track() opens a trace named "write_changelog" and records the arguments (the release and the
// exact system prompt text) as its input and the returned Markdown as its output. Without it the
// completion below would be a stand-alone trace with no record of which prompt produced it.
export const writeChangelog = track(
  { name: "write_changelog", type: "general", projectName: PROJECT_NAME },
  async (release: Release, systemPrompt: string): Promise<string> => {
    // trackOpenAI wraps the client: each completion becomes a span with the messages, model and
    // token usage (Opik derives cost from them). parent = the current span nests it under this
    // trace; without parent the SDK would start a separate trace per call.
    const parent = getTrackContext()?.span;
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
    return response.choices[0]?.message?.content ?? "";
  },
) as (release: Release, systemPrompt: string) => Promise<string>;

/** Send any queued traces and spans to Opik. Call once before the process exits. */
export async function flushTraces(): Promise<void> {
  await getOpik().flush();
}
