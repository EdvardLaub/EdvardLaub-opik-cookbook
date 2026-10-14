import { runTests, type TestSuiteItem } from "opik";
import { PROJECT_NAME, loadEnv } from "./env.js";
import { PROMPT_NAME } from "./prompts.js";
import { RELEASES } from "./releases.js";

loadEnv();
const { MODEL, flushTraces, formatCommits, getOpik, writeChangelog } = await import("./changelog.js");
const { ensurePromptVersions } = await import("./prompts.js");

// The quality bar, in plain English. An LLM judge checks every assertion on every entry.
const GLOBAL_ASSERTIONS = [
  "The entry contains no commit hashes (short hex strings such as d41e8aa), no issue or ticket numbers (such as #412 or TIDE-871) and no CVE identifiers",
  "The entry mentions no internal-only changes: no internal class or module names (such as StreamMux or LineSplitter), and no refactors, test changes, CI changes, docs typo fixes or dependency bumps",
  "If any commit is marked breaking (a '!' or the word BREAKING), the entry has a clearly labelled 'Breaking changes' section that tells the user what to do; if no commit is breaking, the entry has no such section",
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
  const byVersion = { v1: prompts.v1, v2: prompts.v2 };
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
  // Items carry the raw commits, so the judge can see what the entry should have covered. Items
  // already in the suite are skipped, so reruns do not pile up duplicates.
  const existing = new Set((await suite.getItems()).map((i) => String(i.data.release_id)));
  const items: TestSuiteItem[] = RELEASES.filter((r) => !existing.has(r.id)).map((r) => ({
    data: { release_id: r.id, release: formatCommits(r) },
    ...(ITEM_ASSERTIONS[r.id] ? { assertions: ITEM_ASSERTIONS[r.id]! } : {}),
  }));
  if (items.length) await suite.insert(items);

  // 3. Run the same suite once per prompt version. Each runTests call logs one experiment, linked
  // to the exact prompt version it tested (prompts: [...]); its task runs are traces in the project.
  const results = [];
  for (const version of ["v1", "v2"] as const) {
    const prompt = byVersion[version];
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
      // Judge model. No reasoning_effort override: it makes the judge call fail.
      model: MODEL,
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
          for (const s of run.scoreResults) if (s.scoringFailed || s.value !== 1) reasons.add(s.name);
        console.log(`         failed: ${[...reasons].join(" | ")}`);
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
