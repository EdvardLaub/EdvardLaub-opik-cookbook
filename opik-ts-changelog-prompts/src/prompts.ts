import type { Opik, Prompt } from "opik";
import { PROJECT_NAME } from "./env.js";

export const PROMPT_NAME = "release-notes-writer";

// v1: the first thing anyone writes. It never says what to leave out or how to treat breaking changes.
export const PROMPT_V1 = `You write release notes for Tidepool, an open-source log-tailing CLI.
Turn the commit messages you are given into a changelog entry for the release.`;

// v2: the same job with explicit rules for audience, noise and breaking changes.
export const PROMPT_V2 = `You write release notes for Tidepool, an open-source log-tailing CLI.
Turn the commit messages you are given into a user-facing changelog entry for the release.

Rules:
- The reader is a Tidepool user, not a contributor. Describe what changes for them.
- Never include commit hashes, issue or ticket numbers (#123, TIDE-123), or CVE-style codes in the body.
- Never mention internal class or module names, refactors, tests, CI, docs typos or dependency bumps.
  Skip a commit entirely if a user would not notice it.
- If any commit is breaking (marked "!" or BREAKING), start the entry with a "Breaking changes" section.
  For each one, say what changed and what the user must do to migrate.
- Put the remaining items under "Added", "Fixed" or "Improved", one plain-English sentence each.
- If nothing is breaking, do not write a "Breaking changes" section.
- Output Markdown, starting with the heading "## <version>".`;

const VERSIONS = [
  { version: "v1", text: PROMPT_V1, note: "Initial version: summarize the commits." },
  {
    version: "v2",
    text: PROMPT_V2,
    note: "Audience and noise rules: no hashes or internal jargon, skip invisible commits, add a Breaking changes section with migration steps.",
  },
] as const;

/** Just the slice of the Opik client this module needs (lets tests pass a stub). */
export type PromptClient = Pick<Opik, "createPrompt" | "getPrompt">;

export interface PromptVersions {
  v1: Prompt;
  v2: Prompt;
  /** Which versions this call had to create (empty on a rerun). */
  created: string[];
}

/**
 * Make sure the prompt library holds exactly v1 and v2 of the prompt, creating only what is missing.
 *
 * The TS SDK's createPrompt does not deduplicate: calling it again with unchanged text still adds a
 * new version (v3, v4, ...). So we look each version up first and only create the absent ones,
 * which keeps reruns from polluting the version history.
 */
export async function ensurePromptVersions(client: PromptClient): Promise<PromptVersions> {
  const found: Record<string, Prompt> = {};
  const created: string[] = [];
  for (const { version, text, note } of VERSIONS) {
    let prompt = await client.getPrompt({ name: PROMPT_NAME, version, projectName: PROJECT_NAME });
    if (!prompt) {
      // createPrompt adds one immutable version to the library entry; the change description is
      // what the version list and the diff view show next to it.
      prompt = await client.createPrompt({
        name: PROMPT_NAME,
        prompt: text,
        projectName: PROJECT_NAME,
        changeDescription: note,
      });
      created.push(version);
    }
    found[version] = prompt;
  }
  return { v1: found.v1!, v2: found.v2!, created };
}
