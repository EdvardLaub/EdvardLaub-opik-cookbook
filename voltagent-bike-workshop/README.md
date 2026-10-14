# voltagent-bike-workshop

*A VoltAgent front-desk assistant for a bike-repair shop, traced to Opik over plain OpenTelemetry with the attribute mapping that makes tokens, cost and tool calls show up.*

![Node](https://img.shields.io/badge/node-20.19%2B-339933?style=flat&logo=node.js&logoColor=white)
![VoltAgent](https://img.shields.io/badge/%40voltagent%2Fcore-2.11.0-1b1f23?style=flat)
![Tests](https://img.shields.io/badge/tests-vitest-6e9f18?style=flat)

VoltAgent emits OpenTelemetry spans out of the box, and Opik ingests OTLP, so connecting the two looks like a five-minute job. Then you open the trace and find a span input that is a wall of `entity.id` / `agent.stateSnapshot` / `tool.parameters` keys, no tool arguments you can read, and a model with no price attached. The spans are there; they just aren't speaking the GenAI vocabulary (`gen_ai.*`) that Opik understands. This project is a small, complete example of closing that gap: a three-tool agent for a fictional workshop, plus a ~100-line mapping layer between VoltAgent's attributes and Opik's.

## What you'll build

"Spoke & Sprocket" is a one-room bicycle workshop with an assistant on its front desk. The assistant (`gpt-4o-mini`, a VoltAgent `Agent`) has three tools over JSON files in `data/`:

- `lookup_job_ticket` finds a repair ticket by ticket id or customer name,
- `check_parts_stock` checks stock by SKU or keyword,
- `find_free_slots` returns the earliest free booking slots long enough for a job.

`npm run demo` replays three scripted customer requests from `data/requests.json`: a status question, a "can you book me in?" that has to notice a cassette is out of stock and refuse to offer a slot, and a walk-in question mixing a stock check with a slot search.

The code is split by concern so the Opik-specific part is easy to lift out:

```
src/agent.ts            the agent: model, instructions, tools
src/tools.ts            the three tools (plain lookup functions + createTool wrappers)
src/telemetry/          everything that knows about Opik: mapping, exporter, wiring
src/cli.ts              the scripted demo
```

## See it in Opik

Open the **voltagent-bike-workshop** project on your Opik (`http://localhost:5173` for a local install). After a demo run it holds three traces named `spoke-and-sprocket-assistant`, one per customer request.

Open the Ines Calloway one (the booking request). The trace input and output columns are the customer's sentence and the assistant's answer. The span tree has five rows:

- `spoke-and-sprocket-assistant` (general): the agent run itself.
- `llm:generateText` (llm): model `gpt-4o-mini`, provider `openai`, token usage (about 700 tokens in one run) and an estimated cost around $0.00014. The input is the system prompt plus the customer message, rendered as chat messages.
- `tool.execution:lookup_job_ticket`, then two `tool.execution:check_parts_stock` (tool): the input is the exact arguments the model chose, e.g. `{"sku": "CAS-11-34", "keyword": "cassette"}`, and the output is what the shelf returned, `"stock": 0`.

That last pair is the point of the example. The assistant's answer ("I can't offer a slot until the cassette arrives") is correct, and the span with `stock: 0` is the evidence. When the model gets a booking wrong, you see which argument it passed and what the shop data said, not just a friendly sentence.

## Run it yourself

1. `cd voltagent-bike-workshop && npm install`
2. `cp .env.example .env` and fill in `OPENAI_API_KEY` (an `.env` in a parent folder also works). For a local Opik keep `OPIK_URL_OVERRIDE=http://localhost:5173/api/` and `OPIK_WORKSPACE=default`; for Opik Cloud set `OPIK_URL_OVERRIDE=https://www.comet.com/opik/api`, `OPIK_WORKSPACE` and `OPIK_API_KEY`.
3. `npm run demo` (about 15 seconds, well under a cent).
4. `npm run verify` reads the project back through Opik's REST API and checks that every llm span has token usage and a cost.
5. `npm test` runs the offline tests; no keys or Opik needed.

## Poke around

- In `src/telemetry/mapping.ts`, delete the `gen_ai.usage.*` loop and re-run. The traces still arrive, but the llm span loses its token counts and `npm run verify` fails.
- Change the `inferProvider` result to `undefined` for `gpt-` models: usage stays, but cost goes missing, because Opik needs a recognised provider plus model to price a span.
- Make the data lie. Set `CAS-11-34` to `stock: 5` in `data/parts.json` and watch the answer in request 2 flip, with the changed tool output visible in the span.
- Swap the model in `src/agent.ts` for `anthropic/claude-haiku-4-5` (add `ANTHROPIC_API_KEY`); `inferProvider` already maps `claude*` names.

## Gotchas we hit

**The span input is a huge attribute dump and the tool arguments are buried in it.** Opik puts every attribute it does not recognise into the span's input field. VoltAgent's own attributes (`entity.*`, `agent.stateSnapshot`, `tool.parameters`, ...) are all unrecognised. Fix: map the useful ones to `gen_ai.*` / `input.value` / `output.value` and drop the rest, as `mapSpanAttributes` does.

**Tokens appear but the cost is empty.** Opik prices a span only when it knows the provider. VoltAgent records the provider on the root span only, so the llm span has a model and no provider. Fix: set `gen_ai.provider.name` on the llm span (`inferProvider` does it from the model name).

**The exporter silently needs OpenTelemetry 2.x.** `VoltAgentObservability` takes span processors built from `@opentelemetry/sdk-trace-base` 2.x; the 1.x API (`new BasicTracerProvider().addSpanProcessor`) is gone. Install `@opentelemetry/sdk-trace-base@2.1.0` with `@opentelemetry/exporter-trace-otlp-http@0.205.0`, and keep them in the same major.

**The model copies the example id from a tool description.** With "e.g. WS-2041" in the `lookup_job_ticket` description, `gpt-4o-mini` filled `ticket_id` with `WS-2041` even when the customer only gave a name, and the assistant answered about somebody else's bike. The tool span's arguments made this obvious in seconds. Fix: describe the format (`WS-####`), not an example value.

## How it's put together

- `src/agent.ts`: the agent factory (the model is injectable so tests can stub it).
- `src/tools.ts`: the three tools; the lookup logic is separate pure functions.
- `src/data.ts`: loads `data/*.json`.
- `src/telemetry/mapping.ts`: pure VoltAgent-to-`gen_ai.*` attribute mapping.
- `src/telemetry/exporter.ts`: an exporter decorator that applies the mapping before OTLP export.
- `src/telemetry/index.ts`: builds the `VoltAgentObservability` with an OTLP exporter pointed at Opik; `OPIK_TRACK_DISABLE=true` turns export off.
- `src/cli.ts`: the scripted demo CLI. `src/verify.ts`: reads the traces back from Opik.
- `src/env.ts`: loads `.env` files.
- `data/`: jobs, parts, slots and the scripted customer requests.
- `tests/`: tools, mapping and exporter tests, plus an agent run on a stubbed model with tracking disabled.

---

*built with Opik · inspired by Opik's examples and documentation*
