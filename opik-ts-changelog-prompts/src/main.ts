import { flushAll } from "opik";
import { PROJECT_NAME, loadEnv } from "./env.js";
import { PROMPT_V1, PROMPT_V2 } from "./prompts.js";
import { RELEASES } from "./releases.js";

loadEnv();
const { flushTraces, writeChangelog } = await import("./changelog.js");

async function main(): Promise<void> {
  const release = RELEASES[0]!;
  for (const [label, prompt] of [["v1", PROMPT_V1], ["v2", PROMPT_V2]] as const) {
    console.log(`\n=== ${label} prompt, release ${release.version} ===\n`);
    console.log(await writeChangelog(release, prompt));
  }
  // Traces are sent in batches in the background; flush so none are lost when the process exits.
  await flushTraces();
  await flushAll();
  console.log(`\nTraces are in the Opik project "${PROJECT_NAME}".`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
