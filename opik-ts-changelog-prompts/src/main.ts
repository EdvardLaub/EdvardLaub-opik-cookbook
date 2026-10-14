import { runTests, type TestSuiteItem } from "opik";
import { PROJECT_NAME, loadEnv } from "./env.js";
import { PROMPT_NAME } from "./prompts.js";
import { RELEASES } from "./releases.js";

loadEnv();
const { JUDGE_MODEL, MODEL, flushTraces, formatCommits, getOpik, writeChangelog } = await import("./changelog.js");
const { ensurePromptVersions } = await import("./prompts.js");

// The quality bar, in plain English. An LLM judge checks every assertion on every entry.
const GLOBAL_ASSERTIONS = [
  "Look only at the generated changelog entry (the output), not at the raw commit list in the input. The entry contains no commit hashes (short hex strings like 1a2b3c4), no issue or ticket numbers (like #123 or PROJ-456) and no CVE identifiers",
  "Look only at the generated changelog entry (the output), not at the raw commit list in the input. The entry does not describe internal engineering work: no internal class or module names, and nothing about refactors, test changes, CI changes, docs typo fixes or dependency bumps. User-visible features, fixes and CLI behaviour changes are fine",
  "If any commit in the input is marked breaking (a '!' or the word BREAKING), the entry (the output) has a clearly labelled 'Breaking changes' section that tells the user what to do; if no commit is breaking, the entry has no such section",
];

// Item-level assertions are checked in addition to the global ones.
const ITEM_ASSERTIONS: Record<string, string[]> = {
  "tidepool-2.0.0": ["The entry tells users that Node 16 is no longer supported and that the config key `sinks` is now `outputs`"],
  "tidepool-2.1.0": ["The entry warns that --since now treats bare numbers as seconds instead of minutes"],
  "tidepool-1.9.2": ["The entry mentions the security update for the TLS library without quoting a CVE identifier"],
};

async function main(): Promise<void> {
  const opik = getOpik();

  // 1. Prompt library: v1 and v2 of "release-notes-writer" (only the missing ones get created).
  const prompts = await ensurePromptVersions(opik);
  console.log(
    prompts.created.length
      ? `Created prompt versions: ${prompts.created.join(", ")}`
      : "Prompt library already holds v1 and v2, nothing created.",
  );

  // 2. Test suite. getOrCreateTestSuite makes a versioned dataset flagged as a test suite. The
  // global assertions apply to every item; globalExecutionPolicy runs each item 3 times and needs
  // 2 passes, which absorbs LLM and judge flakiness.
  const suite = await opik.getOrCreateTestSuite({
    name: PROJECT_NAME,
    projectName: PROJECT_NAME,
    globalAssertions: GLOBAL_ASSERTIONS,
    globalExecutionPolicy: { runsPerItem: 3, passThreshold: 2 },
  });
  // getOrCreateTestSuite returns an existing suite as it is: it ignores globalAssertions and
  // globalExecutionPolicy you pass on later runs. So edits to the assertions above would silently
  // never reach the judge. Compare with what the suite stores and push only real changes
  // (each change makes a new suite version in Opik).
  const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
  if (!same(await suite.getGlobalAssertions(), GLOBAL_ASSERTIONS)) {
    await suite.updateTestSettings({ globalAssertions: GLOBAL_ASSERTIONS });
    console.log("Updated the suite's global assertions.");
  }
  // Items carry the raw commits, so the judge can see what the entry should have covered. Items
  // already in the suite are not inserted again (reruns would pile up duplicates); their
  // item-level assertions are re-synced the same way.
  const existing = new Map((await suite.getItems()).map((i) => [String(i.data.release_id), i]));
  const stale = [...existing.values()].filter(
    (i) => !same(i.assertions, ITEM_ASSERTIONS[String(i.data.release_id)] ?? []),
  );
  if (stale.length)
    await suite.update(
      stale.map((i) => ({ id: i.id, assertions: ITEM_ASSERTIONS[String(i.data.release_id)] ?? [] })),
    );
  const items: TestSuiteItem[] = RELEASES.filter((r) => !existing.has(r.id)).map((r) => ({
    data: { release_id: r.id, release: formatCommits(r) },
    ...(ITEM_ASSERTIONS[r.id] ? { assertions: ITEM_ASSERTIONS[r.id]! } : {}),
  }));
  if (items.length) await suite.insert(items);

  // 3. Run the same suite once per prompt version. Each runTests call logs one experiment, linked
  // to the exact prompt version it tested (prompts: [...]); its task runs are traces in the project.
  const results = [];
  for (const [version, prompt] of Object.entries(prompts.byVersion)) {
    const result = await runTests({
      testSuite: suite,
      task: async (item) => {
        const release = RELEASES.find((r) => r.id === item.release_id)!;
        const output = await writeChangelog(release, prompt.prompt, {
          prompt_name: PROMPT_NAME,
          prompt_version: prompt.version,
          prompt_commit: prompt.commit,
        });
        return { input: item, output };
      },
      experimentName: `${PROMPT_NAME}-${version}`,
      experimentConfig: { prompt_version: version, prompt_commit: prompt.commit, model: MODEL },
      prompts: [prompt],
      // Judge model: a step up from the writer, because gpt-4o-mini mis-scored clean entries (see README).
      // No reasoning_effort override: it makes the judge call fail.
      model: JUDGE_MODEL,
      projectName: PROJECT_NAME,
      taskThreads: 5,
    });
    results.push({ version, result });
  }

  console.log("\n=== Prompt version comparison ===");
  for (const { version, result } of results) {
    console.log(
      `${PROMPT_NAME} ${version}: ${((result.passRate ?? 0) * 100).toFixed(0)}% pass rate ` +
        `(${result.itemsPassed}/${result.itemsTotal} releases passed, 2 of 3 runs required)`,
    );
    for (const item of result.itemResults.values()) {
      const first = item.testResults[0];
      const input = (first?.testCase.taskOutput as { input: { release_id: string } }).input;
      console.log(`  [${item.passed ? "PASS" : "FAIL"}] ${item.runsPassed}/${item.runsTotal} runs  ${input.release_id}`);
      if (!item.passed) {
        const reasons = new Set<string>();
        for (const run of item.testResults)
          for (const s of run.scoreResults)
            if (s.scoringFailed || s.value !== 1) reasons.add(`${s.name.slice(0, 70)}... -> ${(s.reason ?? "").slice(0, 160)}`);
        for (const r of [...reasons].slice(0, 2)) console.log(`         failed: ${r}`);
      }
    }
    if (result.experimentUrl) console.log(`  run: ${result.experimentUrl}`);
  }

  // Traces and experiment items are sent in batches; flush so nothing is lost at exit.
  await flushTraces();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
