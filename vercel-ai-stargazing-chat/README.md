# vercel-ai-stargazing-chat

*A streaming night-sky assistant on the Vercel AI SDK, traced with `opik-vercel` and graded by a live Opik rule while you chat.*

![TypeScript](https://img.shields.io/badge/typescript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)
![Next.js](https://img.shields.io/badge/next.js-16-000000?style=flat&logo=nextdotjs&logoColor=white)
![AI SDK](https://img.shields.io/badge/ai%20sdk-7-000000?style=flat)
![opik-vercel](https://img.shields.io/badge/opik--vercel-2.2.100-2f54eb?style=flat)

A chat reply is a stream, not a return value, so the usual "log the function result" habit has nothing to grab. And a chatbot that sounds confident is exactly the kind that quietly gets a detail wrong. This example puts both problems on one small app: **Nova**, the assistant of a fictional amateur astronomy club (the Lantern Ridge Astronomy Circle). Every streamed turn becomes an Opik trace, the turns of a conversation are stitched into a thread, and an online evaluation rule fact-checks each reply against the club's guide as it arrives.

## What you'll build

A Next.js app whose pieces are deliberately split into modules:

- `data/` holds the fictional knowledge: an observing guide (loaner telescopes, dark adaptation, session rules) and a sky-events calendar.
- `src/lib/knowledge.ts` retrieves the best guide sections and events for the member's last message and puts them in the prompt.
- `src/lib/model.ts` owns the model (`gpt-4o-mini`) and the persona prompt.
- `src/lib/telemetry.ts` owns everything Opik: the exporter, the AI SDK v7 telemetry registration and the per-call settings.
- `src/lib/chat-handler.ts` is the route logic; `src/app/api/chat/route.ts` is a one-line wrapper around it.
- `src/lib/online-rule.ts` creates the LLM-as-judge rule through Opik's REST API, idempotently.
- `npm run demo` creates the rule, boots the app, plays three scripted conversations over HTTP, waits for the judge's scores and shuts the server down.

## See it in Opik

Open the **`vercel-ai-stargazing-chat`** project (workspace `default`).

**Traces.** A clean demo run leaves 12 rows. Six are `observing-chat-turn`, one per chat message. Open one: the tree is a `step 1` span (general) with a `chat gpt-4o-mini` span (llm) inside it. The input holds the system prompt with the retrieved guide excerpts plus the whole conversation so far; the output is the reply text; the llm span carries token usage (about 320 to 480 prompt tokens, 37 to 62 completion tokens) and an estimated cost of roughly $0.00007 to $0.0001 per turn. The reply left the server as a stream, yet the trace is complete. The other six rows are named `online_evaluation`: those are the judge's own runs, which Opik records in the same project. Filter by name if you want only the chat turns.

**Threads.** Three threads (`stargazing-...`), each with four messages: the Jupiter planning chat, the loaner-telescope chat and the "questions the guide cannot answer" chat. The thread id is the chat id, carried from the route into the trace.

**Feedback scores.** Each `observing-chat-turn` trace has a `grounded_answer` score, written by the rule a few seconds after the trace landed. In our verified runs the Jupiter and the "guide cannot answer" threads scored 1 on both turns, and the loaner thread scored 0 on both: the model told a beginner Marlow was fine for the Orion Nebula and invented a loan period, while the guide says one week and recommends Pip. The judge's reason sits next to each score. Model output varies, so your exact scores may differ, and the judge is itself a small model whose reasons are sometimes imperfect; treat the score as a signal to read the trace, not a verdict.

**Online evaluation tab.** Under the project's rules you will find one rule, `grounded_answer`, enabled, sampling 100 percent. It is created by code, not clicked together, and re-running the demo reuses it.

## Run it yourself

1. Have an Opik instance running (local default is `http://localhost:5173`), then `cp .env.example .env` and set `OPENAI_API_KEY` (or put it in a `.env` one folder up; both are read). Opik needs a stored OpenAI provider key for the judge, which you add under Configuration > AI providers.
2. `npm install`
3. `npm run demo`. It takes under a minute and costs a few cents.
4. Open the project in Opik and look at Traces, Threads and the rules tab.

For manual chat use `npm run dev` and browse to http://localhost:4220. Run `npm run ensure-rule` first if the rule does not exist yet: a rule only grades traces that arrive after it is enabled.

Tests: `npm test` runs offline in about a second. They need no keys, and tracking can be switched off with `OPIK_TRACK_DISABLE=true`.

## Poke around

- Soften the judge in `JUDGE_PROMPT` (`src/lib/online-rule.ts`), re-run `npm run ensure-rule` (it updates the existing rule in place) and see which scores flip.
- Add a fourth conversation to `scripts/conversations.ts` that asks for a number the guide does not give, such as Marlow's weight.
- Delete a section from `data/observing-guide.md` and watch the assistant either admit the gap or invent an answer, and what the judge makes of it.
- Change `sampling_rate` to 0.5 and count how many chat traces get scored.

## Gotchas we hit

1. **Symptom: the app answers, but the project stays empty (no chat traces, no threads).** AI SDK v7 does not emit OpenTelemetry spans on its own. Cause: telemetry needs an explicit integration, and thread ids only travel if the runtime context is allowed onto spans. Fix, as in `src/lib/telemetry.ts`: `registerTelemetry(new OpenTelemetry({ usage: true, enrichSpan }))` once at startup, plus `runtimeContext: { threadId }` and `includeRuntimeContext: { threadId: true }` on each `streamText` call. We removed the registration to check: the demo ran fine and no `observing-chat-turn` trace appeared.
2. **Symptom: `npm install` fails with `ERESOLVE ... peer opik@"^1.8.75" from opik-vercel`.** The package declares a stale peer range. Fix: add `"overrides": { "opik-vercel": { "opik": "2.2.100" } }` to `package.json` (matching your direct `opik` version).
3. **Symptom: the rule exists but no trace gets a score.** A rule only evaluates traces that arrive after it is created and enabled, and the judge needs an OpenAI key stored on the Opik server. Fix: create the rule before sending traffic (the demo does), and when re-running delete traces, not the rule.
4. **Symptom: duplicate `grounded_answer` rules after a few runs.** Creating a rule is not deduplicated. `ensureRule` lists the project's rules by name, reuses the first, deletes extras and PATCHes the definition so edits to the judge prompt apply.
5. **Symptom: Next.js prints "Node.js module is loaded ... not supported in the Edge Runtime" for `instrumentation.ts`.** Cause: Node-only imports sit in the file Next also compiles for Edge. Fix: keep `instrumentation.ts` to a runtime check plus `await import("./instrumentation.node")`, and import the Opik code after the environment is loaded, since `opik-vercel` builds a default client at import time.

## How it's put together

- `data/observing-guide.md`, `data/sky-events.json`: the fictional guide and calendar.
- `src/lib/knowledge.ts`: parsing and keyword retrieval, builds the grounding block.
- `src/lib/model.ts`: model and persona prompt.
- `src/lib/telemetry.ts`: `OpikExporter`, `registerTelemetry`, per-call telemetry settings.
- `src/lib/chat-handler.ts`: route logic (`streamText` with grounded system prompt).
- `src/lib/online-rule.ts`: judge prompt, rule payload, idempotent REST setup.
- `src/lib/config.ts`: project and trace names.
- `src/app/`: chat page, layout and the one-line route.
- `src/instrumentation.ts`, `src/instrumentation.node.ts`: Next.js startup hook and the Node-only Opik registration.
- `scripts/demo.ts`, `scripts/conversations.ts`, `scripts/ensure-rule.ts`: the scripted demo, its conversations, the standalone rule setup.
- `tests/`: retrieval, telemetry helpers, rule payload, and the route handler with a stubbed model.

---

*built with Opik · inspired by Opik's examples and documentation*
