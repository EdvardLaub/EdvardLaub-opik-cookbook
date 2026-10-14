# opik-ts-changelog-prompts

*A changelog-writing prompt that lives in Opik's prompt library: v1 leaks commit hashes and jargon and passes 0% of its tests, v2 passes 100%.*

![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)
![Node](https://img.shields.io/badge/node-20%2B-339933?style=flat&logo=node.js&logoColor=white)
![Opik SDK](https://img.shields.io/badge/opik-2.2.100-2f54eb?style=flat)
![Tests](https://img.shields.io/badge/tests-vitest-6E9F18?style=flat&logo=vitest&logoColor=white)

Release notes are the one piece of LLM output that strangers read. Hand a model a raw `git log` and it will cheerfully paste `a3f9c21` into the notes, name your internal `StreamMux` class, list the CI tweaks, and bury the one line that will break someone's config. The fix is a better prompt, but a prompt edit is only progress if you can prove it, and only repeatable if you know which wording was live. This example puts the prompt in the Opik prompt library as immutable versions and runs the same test suite against each one.

## What you'll build

A small TypeScript app for a fictional open-source CLI called Tidepool. Given the commit list of a release, it asks `gpt-4o-mini` for a user-facing changelog entry. The system prompt is not in the code path at runtime: it is stored in the Opik prompt library as `release-notes-writer`.

- **v1** is the obvious first draft: "turn these commits into a changelog entry."
- **v2** adds rules: write for users, no hashes or ticket numbers, no internal names or CI noise, a `Breaking changes` section with migration steps when a commit is breaking, and security fixes always kept (a rule the test suite taught me, see below).

A test suite of five releases with three plain-English assertions (plus a few per-release ones) runs once per version, judged by an LLM. Each run is an Opik experiment, linked to the prompt version it tested, and every task run is a trace you can open.

## See it in Opik

Open the **`opik-ts-changelog-prompts`** project, then look at four places.

1. **Prompt library, `release-notes-writer`.** Two versions, each with a commit id (`e549f3af` for v1, `37e78605` for v2 in my run; yours will differ) and a change description, so the history reads "Initial version" then "Audience and noise rules". Rerunning the demo does not add a v3: the app looks each version up before creating it.
2. **Experiments.** Two of them, `release-notes-writer-v1` and `release-notes-writer-v2`, each with 15 task runs (5 releases x 3 runs per item). v1 passes 0 of 5 releases. v2 passes 5 of 5. Each experiment is linked to its prompt version, and its configuration holds the exact prompt text it ran with.
3. **Traces.** One clean run leaves 30 traces (2 experiments x 15). Each one is an `evaluation_task` trace. Open one and you see `write_changelog` (input: the release and the full system prompt text; output: the Markdown entry; metadata: `prompt_name`, `prompt_version`, `prompt_commit`) with the OpenAI completion nested under it as `chat-completion` (gpt-4o-mini, token usage, an estimated cost around $0.00013 to $0.00015). The judge's own calls sit in the same trace. The OpenAI integration records the completion as a `general` span, not an `llm` one; usage and cost still arrive.
4. **Feedback scores column.** Every trace carries `no_hash_or_ticket_leaks`, a cheap regex check run in code. It is 1 on all 15 v2 traces, and 0 on 10 of the 15 v1 traces: v1 leaks a hash or ticket number in two runs out of three.

The judge's reasons are the useful part. For v1 they read like "The changelog entry includes a 'Chores' section describing dependency bumps" or "includes the reference (Related to TIDE-930)". And v2 was not right the first time: my first v2 passed four releases and failed `tidepool-1.9.2`, because "skip anything a user would not notice" made it drop the TLS security fix. The suite caught it, I added the "always keep security fixes" rule, and v2 went to 5 of 5.

## Run it yourself

1. Start a local Opik (or point at Opik Cloud, see `.env.example`).
2. `cp .env.example .env`, add `OPENAI_API_KEY` (a `.env` in a parent folder also works).
3. `npm install`
4. `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default` (not needed for Opik Cloud)
5. `npm run demo` (about 30 to 60 seconds; the two experiments cost roughly $0.03 in OpenAI calls, judge included)
6. Optional: `npm test` (offline, no key, no Opik; the vitest config sets `OPIK_TRACK_DISABLE=true`, the SDK's switch for turning tracing off)

The demo prints a pass rate per version, the failing releases with the judge's reason, and a link to each run.

## Poke around

- Add a third entry to `VERSIONS` in `src/prompts.ts` (say, one that asks for a one-line summary at the top) and rerun: the library gains a v3 and you get three experiments. Editing the text of v2 in place does not create v3; the app warns that the library copy differs from the code.
- Make that v3 a copy of v2 without the "always keep security fixes" line and watch `tidepool-1.9.2` fail again.
- Add a sixth release to `src/releases.ts` with a breaking change that is easy to miss (a default value flipping). Rerun: only the new item is inserted.
- Change `runsPerItem` and `passThreshold` in `src/main.ts` and see how the pass rate reacts to a flaky judge.

## Gotchas we hit

**`npm install` fails with `ERESOLVE ... peer opik@"^1.8.61" from opik-openai@2.2.100`.** `opik-openai` still declares a peer dependency on the old 1.x `opik` while 2.2.100 is current. Add an override to `package.json` so npm accepts the installed `opik`:

```json
"overrides": { "opik-openai": { "opik": "$opik" } }
```

**You edit an assertion and the judge keeps quoting the old one.** `getOrCreateTestSuite` returns an existing suite as it is and ignores the `globalAssertions` you pass the second time. The failure reasons in the console show the old text. `src/main.ts` now compares `suite.getGlobalAssertions()` with the code and calls `suite.updateTestSettings({ globalAssertions })` only when they differ (each change makes a new suite version). Item-level assertions are re-synced the same way with `suite.update(...)`.

**v2 scores 0% to 20% even though its output is clean.** With `model: "gpt-4o-mini"` as the judge, clean entries were failed with reasons like "mentions an internal change (the `--help` command)", because the judge also sees the raw commit list in the input, full of hashes and class names. Two changes fixed it: say in each assertion which side to judge ("Look only at the generated changelog entry (the output), not at the raw commit list in the input"), and use a stronger judge, `model: "gpt-4.1-mini"`. Do not add `reasoning_effort` to the judge settings; the call fails.

**Lots of `AI SDK Warning: System messages in the prompt or messages fields...` lines.** The SDK's built-in judge sends its instructions as a system message through the Vercel AI SDK. It is harmless noise, one line per judge call; filter it with `npm run demo 2>&1 | grep -v "AI SDK Warning"`.

## How it's put together

- `src/main.ts`: the orchestration. Ensures the prompt versions, syncs the suite, runs `runTests` once per version, prints the comparison, flushes.
- `src/prompts.ts`: the v1 and v2 prompt text and `ensurePromptVersions`, which creates only the versions the library is missing.
- `src/changelog.ts`: `writeChangelog`, traced with `track` and `trackOpenAI`; stamps prompt metadata and the leak score on the trace.
- `src/checks.ts`: the regex lint for commit hashes and ticket numbers.
- `src/releases.ts`: the five fictional Tidepool releases (raw `git log` lines).
- `src/env.ts`: loads `.env` files and sets the Opik project name.
- `tests/app.test.ts`: offline vitest tests for formatting, the leak lint, idempotent prompt registration with a fake library, drift warning, and a traced call with tracking disabled and a stubbed OpenAI client.

*built with Opik · inspired by Opik's examples and documentation*
