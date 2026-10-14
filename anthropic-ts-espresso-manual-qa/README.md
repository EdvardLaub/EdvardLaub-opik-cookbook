<div align="center">

# Espresso Manual Q&A with Verbatim Citations

**`anthropic-ts-espresso-manual-qa`**

*Claude has to quote the manual. A plain-English test suite checks every quote, three runs per question.*

![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?style=flat&logo=typescript&logoColor=white)
![Anthropic SDK](https://img.shields.io/badge/@anthropic--ai/sdk-0.133-191919?style=flat)
[![Opik](https://img.shields.io/badge/opik-2.2.100-2f54eb?style=flat)](https://github.com/comet-ml/opik)
![Node](https://img.shields.io/badge/node-20%2B-339933?style=flat&logo=nodedotjs&logoColor=white)

</div>

---

A support bot that answers from a product manual has one failure that hurts: the
confident answer that is not in the manual. "Descale with vinegar, it works fine" is
fluent, plausible, and voids the warranty. This example is a Q&A script over a
fictional espresso-machine manual (the Marlowe Barista M2, shipped in `docs/`). Claude
must wrap every claim in a `<quote>` copied from the manual, and an Opik **test suite**
turns "did it quote faithfully?" into pass/fail per question.

## What you'll build

- `src/qa.ts`: a Q&A function using the official Anthropic TypeScript SDK
  (`claude-haiku-4-5`). The manual goes into the system prompt together with the rule
  "answer only from the manual, quote it character for character".
- **Manual tracing.** Opik's integrations list has no TypeScript Anthropic wrapper (the
  `track_anthropic`-style integration exists for Python only). So the Anthropic call is
  wrapped with Opik's `track()` as an `llm` span, and `enrichSpan` records the model,
  `provider: "anthropic"` and token usage by hand from the response. Opik then estimates cost
  from that provider + model + usage.
- `src/main.ts`: a test suite with three global assertions, two item-level assertions and six
  questions (one of them is deliberately not in the manual). The suite's execution policy runs
  each question 3 times and requires 2 passes.
- `src/quotes.ts`: a strict, deterministic quote checker used next to the LLM judge.

**Why the TS SDK and not a Python helper.** The Opik TS SDK (2.2.100) ships
`getOrCreateTestSuite`, `suite.insert` with per-item `assertions`, and `runTests`, so
everything runs in one TypeScript process. No Python script is needed.

## See it in Opik

Open the `anthropic-ts-espresso-manual-qa` project. In the verified run there were **18 traces**
(6 questions x 3 runs), each named `evaluation_task`. Open one: the tree holds
`llm_task` > `answer_question` > `anthropic_messages_create` (the `llm` span, about 1,160 tokens
and about $0.0016 for Haiku 4.5), plus an `llm_judge` span with the judge's own `llm` call inside
(about 2,870 tokens, about $0.0043). The traces table also has a `quotes_verbatim` feedback column.
That column came out as 11 passes, 4 fails and 3 empty (the three Wi-Fi answers, which correctly
quote nothing, are left unscored).

Now open **Test suites** (or Experiments) and pick the suite `anthropic-ts-espresso-manual-qa`.
The run shows 6 of 6 items passing, each at 3/3 runs, with every assertion averaging 1.0. Open an
item to see each assertion's verdict and the judge's reason, and click through to the trace behind it.

An honest wrinkle worth seeing: the 4 failing `quotes_verbatim` scores. On those traces the model
re-capitalised the start of a quote (`register your machine within 30 days...` instead of `Register
...`) or dropped the final period. The LLM judge was happy with all of them; the strict substring
check was not. Two checkers, two strictness levels, both visible side by side.

## Run it yourself

1. `npm install`
2. Put `ANTHROPIC_API_KEY` in a `.env` (this folder or a parent; copy `.env.example`).
3. Point the SDK at Opik (local shown; for Cloud use your URL and `OPIK_API_KEY`):
   `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default`
4. `npm run demo` (about 30 seconds, roughly 10 cents of Haiku calls)
5. Open the project in Opik and look at the traces and the test-suite run.

Offline tests (no keys, no Opik): `OPIK_TRACK_DISABLE=true npm test`.

## Poke around

- Weaken the prompt: delete "copied character-for-character" in `SYSTEM_PROMPT`, rerun, and
  compare the two suite runs in Opik. Watch which assertions start to fail.
- Add a question the manual cannot answer ("What is the boiler's wattage?") with its own
  assertion, such as "The response does not state a number".
- Set `runsPerItem` to 1 in `globalExecutionPolicy` and rerun a few times; items near the
  threshold will flicker between pass and fail.
- Add a failing global assertion ("The response contains no `<quote>` tags") via
  `suite.updateTestSettings({ globalAssertions })` and see every item go red with reasons.

## Gotchas we hit

**The strict check and the judge disagree.** Symptom: some traces show `quotes_verbatim = 0` while
the suite reports 3/3 runs passing. Cause: `checkQuotes` demands an exact substring (whitespace
normalised), while the LLM judge tolerates trivial re-capitalisation. Fix: decide which bar you
mean. To make the judge as strict as the code, say so in the assertion ("including capitalisation
and punctuation"), or relax `checkQuotes` by lower-casing both sides in `normalize`.

**`AI SDK Warning: System messages in the prompt or messages fields...` printed many times.**
Cause: the SDK's built-in judge sends its instructions as a system message through the Vercel AI
SDK. It is harmless noise from inside `opik`, one line per judge call; filter it with
`npm run demo 2>&1 | grep -v "AI SDK Warning"`.

**A rerun adds another full set of traces.** Symptom: twice the traces after two runs.
Cause: every `runTests` call is a new experiment and its task runs are always new traces (the
suite and its items are reused by name, and `main.ts` skips questions already inserted). Fix:
delete the earlier traces, or point `OPIK_PROJECT_NAME` at a scratch project while iterating.

## How it's put together

- `src/main.ts`: builds the suite (assertions, execution policy, items), calls `runTests`, prints per-question results, flushes.
- `src/qa.ts`: the Anthropic call (manual `llm` span with usage) and the `answer_question` wrapper that logs `quotes_verbatim`.
- `src/quotes.ts`: pure quote extraction and verbatim checking.
- `src/env.ts`: loads the nearest `.env` and drops any proxy `ANTHROPIC_BASE_URL`.
- `docs/manual.md`: the fictional owner's manual.
- `tests/qa.test.ts`: offline vitest tests: quote parsing and checking, plus a traced call with tracking disabled and a stubbed client.

---

*built with Opik · inspired by Opik's examples and documentation*
