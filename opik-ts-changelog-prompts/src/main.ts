import OpenAI from "openai";
import { loadEnv } from "./env.js";
import { writeChangelog } from "./changelog.js";
import { PROMPT_V1, PROMPT_V2 } from "./prompts.js";
import { RELEASES } from "./releases.js";

loadEnv();

async function main(): Promise<void> {
  const client = new OpenAI();
  const release = RELEASES[0]!;
  for (const [label, prompt] of [["v1", PROMPT_V1], ["v2", PROMPT_V2]] as const) {
    console.log(`\n=== ${label} prompt, release ${release.version} ===\n`);
    console.log(await writeChangelog(client, prompt, release));
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
