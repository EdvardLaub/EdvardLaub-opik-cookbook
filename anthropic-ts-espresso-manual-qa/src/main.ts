import { Opik, runTests, type TestSuiteItem } from "opik";
import { loadEnv } from "./env.js";

loadEnv();
// Must be set before the Opik client is created: it decides which project every trace lands in.
process.env.OPIK_PROJECT_NAME ??= "anthropic-ts-espresso-manual-qa";

const { answerQuestion, MANUAL, MODEL, PROJECT_NAME } = await import("./qa.js");

// The quality bar, in plain English. An LLM judge checks every assertion on every answer.
const GLOBAL_ASSERTIONS = [
  "Every excerpt wrapped in <quote> tags appears verbatim, character for character, in the manual provided as context. If there are no quotes, the response must say the manual does not cover the question",
  "The quoted excerpts genuinely support the factual claims made in the answer",
  "The response addresses the question that was asked",
];

const QUESTIONS = [
  "How often should I descale, and what must I never use?",
  "What is the factory brew temperature and how do I change it?",
  "How long does a good double shot take, and what do I do if it runs too fast?",
  "How do I get extra warranty coverage, and what does the warranty exclude?",
  "What does a blinking red READY light mean?",
  "Does the machine have a Wi-Fi app for scheduling brews?", // not in the manual on purpose
];

// Item-level assertions are checked in addition to the global ones.
const ITEM_ASSERTIONS: Record<string, string[]> = {
  [QUESTIONS[0]!]: [
    "The response says to descale every 3 months with tap water or every 6 months with filtered water",
    "The response says never to use vinegar",
  ],
  [QUESTIONS[5]!]: [
    "The response says the manual does not cover a Wi-Fi app and does not invent app features",
  ],
};

async function main(): Promise<void> {
  const client = new Opik({ projectName: PROJECT_NAME });

  // getOrCreateTestSuite makes a versioned dataset flagged as a test suite. Global assertions
  // apply to every item; globalExecutionPolicy reruns each item 3 times and requires 2 passes,
  // which absorbs LLM and judge flakiness.
  const suite = await client.getOrCreateTestSuite({
    name: PROJECT_NAME,
    projectName: PROJECT_NAME,
    globalAssertions: GLOBAL_ASSERTIONS,
    globalExecutionPolicy: { runsPerItem: 3, passThreshold: 2 },
  });

  // Items carry the question AND the manual: the judge sees the task's input, so it can
  // verify quotes against the document. No expected answers, so the judge can't cheat.
  const existing = new Set((await suite.getItems()).map((i) => String(i.data.question)));
  const items: TestSuiteItem[] = QUESTIONS.filter((q) => !existing.has(q)).map((question) => ({
    data: { question, context: MANUAL },
    ...(ITEM_ASSERTIONS[question] ? { assertions: ITEM_ASSERTIONS[question] } : {}),
  }));
  if (items.length) await suite.insert(items);

  // runTests answers every item (3 runs each), has the judge score each assertion, and logs
  // one experiment of the test-suite type. Each task run is a trace in the project.
  const result = await runTests({
    testSuite: suite,
    task: async (item) => ({
      input: item,
      output: await answerQuestion(String(item.question)),
    }),
    // Judge model: Claude again, so one key is enough. No reasoning_effort override here.
    model: MODEL,
    projectName: PROJECT_NAME,
    taskThreads: 4,
  });

  console.log(
    `\nPass rate: ${((result.passRate ?? 0) * 100).toFixed(0)}% ` +
      `(${result.itemsPassed}/${result.itemsTotal} items passed, 2 of 3 runs required)`,
  );
  for (const item of result.itemResults.values()) {
    const first = item.testResults[0];
    const question = String((first?.testCase.taskOutput as { input: { question: string } }).input.question);
    console.log(`  [${item.passed ? "PASS" : "FAIL"}] ${item.runsPassed}/${item.runsTotal} runs  ${question}`);
    if (!item.passed) {
      for (const run of item.testResults)
        for (const s of run.scoreResults)
          if (s.scoringFailed || s.value !== 1) console.log(`         failed: ${s.name}: ${s.reason}`);
    }
  }
  if (result.experimentUrl) console.log(`\nView the run: ${result.experimentUrl}`);

  // Traces and experiment items are sent in batches; flush so nothing is lost at exit.
  await client.flush();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
