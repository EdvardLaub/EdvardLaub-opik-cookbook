import type OpenAI from "openai";
import type { Release } from "./releases.js";

export const MODEL = "gpt-4o-mini";

/** The user message: the release version plus the raw commit lines, exactly as git printed them. */
export function formatCommits(release: Release): string {
  return `Release ${release.version}\n\nCommits:\n${release.commits.map((c) => `- ${c}`).join("\n")}`;
}

/** Write the changelog entry for one release using the given system prompt text. */
export async function writeChangelog(
  client: OpenAI,
  systemPrompt: string,
  release: Release,
): Promise<string> {
  const response = await client.chat.completions.create({
    model: MODEL,
    temperature: 0,
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: formatCommits(release) },
    ],
  });
  return response.choices[0]?.message?.content ?? "";
}
