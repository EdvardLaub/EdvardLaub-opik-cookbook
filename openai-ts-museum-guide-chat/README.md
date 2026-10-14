# openai-ts-museum-guide-chat

*A museum visitor-guide chatbot in TypeScript whose chats show up in Opik as conversations, with a price tag per turn.*

![Node 22](https://img.shields.io/badge/node-22-339933?style=flat&logo=node.js&logoColor=white)
![TypeScript strict](https://img.shields.io/badge/TypeScript-strict-3178C6?style=flat&logo=typescript&logoColor=white)
![opik 2.2.100](https://img.shields.io/badge/opik-2.2.100-2f54eb?style=flat)
![tests vitest](https://img.shields.io/badge/tests-vitest-6E9F18?style=flat&logo=vitest&logoColor=white)

A visitor asks the guide three questions in a row, and the model sees all three. Your logs do not: by default each answer is a separate API call, and "what did that visit cost?" or "did the visitor leave happy?" has no home. This example is a small guide for the Fernwick Museum of Natural History (entirely made up) that groups every visit into one Opik thread, shows what each turn cost, and records a thumbs-up after the fact.

## What you'll build

- `MuseumGuide`, one object per visitor conversation. It keeps the message history and calls `gpt-4o-mini` through the OpenAI TypeScript SDK.
- Each question becomes one Opik trace tagged with the conversation's `threadId`. Inside the trace, the completion is a span recorded by `opik-openai`, carrying model, tokens and estimated cost.
- A scripted demo with two visitors: a family planning a Saturday (ticket prices, opening times, the touch tank) and a wheelchair user asking about step-free access and quiet hours, who ends on a question the guide's facts don't cover (a vegan cafe menu).
- After the run, a `visitor-satisfaction` feedback score is attached to one trace by id, and the demo reads the traces back to print cost per turn.

## See it in Opik

Open the `openai-ts-museum-guide-chat` project in the local Opik (`http://localhost:5173`).

- **Threads tab**: two rows, `family-saturday-visit` and `wheelchair-and-quiet-hour`, each with 6 messages (3 visitor questions, 3 guide answers). Open one and it reads as a chat transcript.
- **Traces tab**: six traces named `answer-visitor-question`. Expand one and you will find a single child span, `guide-reply`, with model `gpt-4o-mini-2024-07-18` and provider `openai`. Estimated cost is around $0.00008 to $0.00009 per turn; our run totalled $0.000533 for all six.
- **Prompt tokens grow each turn**, because the whole history is re-sent: 399, 457, 514 for the family visit and 385, 455, 518 for the wheelchair visit. Cost per turn creeps up with conversation length, and this is where you see it.
- **Feedback scores column**: exactly one trace, the touch-tank answer ("open from 10:30 to 15:30 only"), shows `visitor-satisfaction = 1`.
- In the family thread, the first answer quoted £42 for two adults and two children. The guide's own price list has a £38 family ticket, so the model missed the cheaper option. Models do not always do this, so your run may differ, but when it happens this is where you spot it: open the trace and read the input messages next to the answer.

## Run it yourself

1. Install: `npm install`
2. Put `OPENAI_API_KEY` in a `.env` (this folder or the repo root; see `.env.example`).
3. Point the SDK at your Opik. For a local self-hosted Opik:
   `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default`
   (For Opik Cloud, set `OPIK_API_KEY` and `OPIK_WORKSPACE` instead.)
4. Run: `npm run demo` (about 15 seconds, well under a cent)
5. Type-check: `npm run typecheck`. Offline tests: `npm test`.

The demo ends with a table of cost per turn read back from Opik, e.g. `family-saturday-visit  $0.000080  <trace id>`.

## Poke around

- Change the thumbs-up in `src/demo.ts` to `value: 0.0` on the first family turn (the ticket quote) and sort the Traces tab by `visitor-satisfaction`.
- Add a fourth question to a conversation and watch the prompt-token count of that turn in the span.
- Switch `MODEL` in `src/guide.ts` to `gpt-4.1-mini` and compare per-turn cost against the earlier run.
- Remove `threadId` from `this.opik.trace(...)` and re-run: the Threads tab stops showing these conversations and you are back to isolated rows.

## Gotchas we hit

**`npm install` fails with `ERESOLVE ... peer opik@"^1.8.61" from opik-openai@2.2.100`.**
Cause: `opik-openai` still declares a peer dependency on the old `opik` 1.x line, while the current `opik` is 2.x (it also needs `openai@^6`, not the v4 that older docs show). Fix: an npm override so the integration accepts the installed `opik`:
```json
"overrides": { "opik-openai": { "opik": "$opik" } }
```

**`trace.id` is `undefined`, so the feedback score has nothing to attach to.**
Cause: the `Trace` object returned by `opik.trace(...)` keeps its fields under `.data`. Fix: use `trace.data.id`.

**The feedback score never appears.**
Cause: `opik.logTracesFeedbackScores([...])` returns `void`; it only queues the score, and the trace it points to has to exist server-side. Fix: `await opik.flush()` before scoring (so the trace exists) and again after (so the score is sent).

**The `guide-reply` span type shows `general`, not `llm`.**
Cause: with `opik-openai@2.2.100` the wrapped call is recorded as a `general` span; model, provider, token usage and cost are still filled in, so cost tracking works. Nothing to fix, just do not filter on span type `llm` to find your completions.

## How it's put together

- `src/museum.ts`: the fictional museum's facts, the system prompt builder and `quoteTickets()`.
- `src/guide.ts`: `MuseumGuide`, with message memory, a trace per turn tagged with `threadId`, and `trackOpenAI` for the completion span.
- `src/demo.ts`: the two scripted visits, the post-run feedback score and the cost-per-turn readout.
- `tests/museum.test.ts`: prompt contents and ticket pricing.
- `tests/guide.test.ts`: runs `ask()` through the real tracing wrapper with a stubbed OpenAI client; checks memory and the returned trace id.
- `vitest.config.ts`: sets `OPIK_TRACK_DISABLE=true` for tests, so no test run is logged to Opik and none needs an API key.
- `.env.example`, `.gitignore`, `package.json`, `tsconfig.json`: setup.

---
*built with Opik · inspired by Opik's examples and documentation*
