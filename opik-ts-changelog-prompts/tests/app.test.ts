import type { Prompt } from "opik";
import { describe, expect, it, vi } from "vitest";
import { findLeaks } from "../src/checks.js";
import { RELEASES } from "../src/releases.js";
import { formatCommits } from "../src/changelog.js";
import { ensurePromptVersions, PROMPT_V1, PROMPT_V2 } from "../src/prompts.js";

describe("fixture and formatting", () => {
  it("formats raw commits exactly as git printed them, with hashes", () => {
    const text = formatCommits(RELEASES[1]!);
    expect(text).toContain("Release 1.9.2");
    expect(text).toContain("- a3f9c21 fix(parser)");
  });

  it("has breaking and non-breaking releases, so the breaking-change assertion cuts both ways", () => {
    const breaking = RELEASES.filter((r) => r.commits.some((c) => /!:|BREAKING/.test(c)));
    expect(breaking.length).toBeGreaterThan(0);
    expect(breaking.length).toBeLessThan(RELEASES.length);
  });
});

describe("leak lint", () => {
  it("flags hashes and ticket numbers", () => {
    const leaks = findLeaks("Fixed a crash (a3f9c21, closes #412) and a refactor [TIDE-871].");
    expect(leaks.hashes).toEqual(["a3f9c21"]);
    expect(leaks.tickets).toEqual(["#412", "TIDE-871"]);
  });

  it("leaves a clean entry alone", () => {
    const leaks = findLeaks("## 2.0.0\n\n### Breaking changes\n- Node 16 is no longer supported.");
    expect(leaks).toEqual({ hashes: [], tickets: [] });
  });
});

/** A stand-in for the Opik client: an in-memory prompt library that counts createPrompt calls. */
function fakeLibrary() {
  const store = new Map<string, Prompt>();
  const createPrompt = vi.fn(async (o: { prompt: string }) => {
    const version = `v${store.size + 1}`;
    const p = { prompt: o.prompt, version, commit: `c${store.size + 1}` } as Prompt;
    store.set(version, p);
    return p;
  });
  const getPrompt = vi.fn(async (o: { version?: string }) => store.get(o.version ?? "") ?? null);
  return { client: { createPrompt, getPrompt } as never, createPrompt };
}

describe("ensurePromptVersions", () => {
  it("creates v1 and v2 on an empty library, in order", async () => {
    const { client, createPrompt } = fakeLibrary();
    const result = await ensurePromptVersions(client);
    expect(result.created).toEqual(["v1", "v2"]);
    expect(Object.keys(result.byVersion)).toEqual(["v1", "v2"]);
    expect(createPrompt.mock.calls.map((c) => c[0].prompt)).toEqual([PROMPT_V1, PROMPT_V2]);
  });

  it("is idempotent: a rerun creates nothing, so no v3 appears", async () => {
    const { client, createPrompt } = fakeLibrary();
    await ensurePromptVersions(client);
    const again = await ensurePromptVersions(client);
    expect(again.created).toEqual([]);
    expect(createPrompt).toHaveBeenCalledTimes(2);
  });
});

describe("prompt drift", () => {
  it("warns, but does not create a version, when the library copy differs from the code", async () => {
    const { client, createPrompt } = fakeLibrary();
    await ensurePromptVersions(client);
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    // Simulate someone editing v2 in the library: same version id, different text.
    const edited = await (client as never as { getPrompt: (o: object) => Promise<{ prompt: string }> }).getPrompt({ version: "v2" });
    edited.prompt = "edited in the UI";
    await ensurePromptVersions(client);
    expect(warn).toHaveBeenCalledOnce();
    expect(createPrompt).toHaveBeenCalledTimes(2);
    warn.mockRestore();
  });
});

describe("traced writeChangelog with tracking disabled", () => {
  it("still runs the function and returns the model text", async () => {
    const { setOpenAI, writeChangelog } = await import("../src/changelog.js");
    const create = vi.fn().mockResolvedValue({
      model: "gpt-4o-mini",
      choices: [{ message: { content: "## 2.0.0\n\n- Node 16 is no longer supported." } }],
      usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
    });
    setOpenAI({ chat: { completions: { create } } } as never);
    const entry = await writeChangelog(RELEASES[0]!, PROMPT_V2);
    expect(entry).toContain("Node 16");
    expect(create.mock.calls[0]![0].messages[0].content).toBe(PROMPT_V2);
  });
});
