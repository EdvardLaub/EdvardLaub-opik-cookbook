# mastra-banking-agent

*A retail-banking chat assistant built with Mastra, where every tool call shows up as a real `execute_tool` span in Opik.*

![Node](https://img.shields.io/badge/node-22.13%2B-339933?style=flat&logo=node.js&logoColor=white)
![Mastra](https://img.shields.io/badge/%40mastra%2Fcore-1.77-0b0b0b?style=flat)
![Opik](https://img.shields.io/badge/Opik-OTel%20ingestion-2f54eb?style=flat)

A banking assistant that can move state (freeze a card) is exactly the kind of agent you want to be able to audit. The chat transcript only tells you what the assistant *said*. It does not tell you which account id the model typed into a tool, whether it looked before it acted, or what the tool actually returned. This example puts a small agent loop under Opik so every one of those decisions is a span you can click.

## What you'll build

"Larkspur Savings & Trust" is a fictional bank whose customers live in `data/bank.json`. A Mastra `Agent` on `gpt-4o-mini` serves one signed-in customer, Maren Ostrowski, with four tools:

| Tool | Kind | What it does |
|---|---|---|
| `listAccounts` | read-only | her accounts and cards (ids, last four digits, card status) |
| `getBalance` | read-only | balance of one account |
| `getRecentTransactions` | read-only | newest-first transactions on one account |
| `freezeCard` | mutates in-memory state | marks a card as frozen (nothing is written back to the JSON file) |

The signed-in customer travels in Mastra's request context, not in the prompt, and ownership is checked inside the bank layer. So when the fourth demo request asks for someone else's account, the tool answers with an error object and the model has to explain it, which makes a good trace to study.

Tracing is configuration, not code. `src/mastra.ts` registers Mastra's `Observability` with an `OtelExporter`, and the agent and tool files never mention Opik.

## See it in Opik

Run the demo, then open the **`mastra-banking-agent`** project in Opik (http://localhost:5173 for a local install) and open the **Traces** tab. There are four traces, one per customer request, named `invoke_agent larkspur-banking-agent`.

Click the trace for *"I think I lost my debit card for my checking account. Please freeze it."* and expand the tree. The loop is visible step by step:

- `invoke_agent` is the root; under it, one `agent_step` per round of the loop.
- Step 1 holds an `llm` span (`chat gpt-4o-mini`, 376 tokens) and a `tool` span `execute_tool listAccounts`: the model first asked which cards exist.
- Step 2 holds `chat gpt-4o-mini` (497 tokens) and `execute_tool freezeCard`. Its input is `{"cardId": "CARD-5101"}`, the id the model picked from the previous tool result, and its output is `{"cardId": "CARD-5101", "last4": "8842", "status": "frozen"}`.
- Step 3 is the final `chat gpt-4o-mini` call (558 tokens) that writes the reply. The trace totals 1,431 tokens and about $0.00024; the whole four-request run costs under a tenth of a cent. Exact numbers vary a little from run to run, since the model chooses its own steps.

The tool spans have type `tool`, so the **Spans** tab can be filtered to just them, which is the quickest way to audit every card freeze. The other three traces are shorter or longer in the way you'd expect: the balance question chains `listAccounts` then `getBalance`, and the request for account `ACC-7003` is a single `execute_tool getBalance` whose output is `{"error": "Account ACC-7003 not found for this customer"}`.

Prefer the terminal? `npm run tree` reads the project back through Opik's REST API and prints the same tree with arguments and token counts.

## Run it yourself

1. Have Opik running (local default: http://localhost:5173) and an OpenAI key in `.env`.
2. `cp .env.example .env` and fill in `OPENAI_API_KEY` (a `.env` further up the directory tree is picked up too).
3. `npm install`
4. `npm run demo`: four scripted customer requests, about 15 seconds.
5. `npm run tree` to print the newest traces from Opik, or open the project in the UI.

For Opik Cloud, drop `OPIK_URL_OVERRIDE`, set `OPIK_API_KEY` and `OPIK_WORKSPACE` in `.env`.

## Poke around

- Change the last demo request to an account you do own, `ACC-7002`, and compare the `execute_tool getBalance` output with the error version.
- Soften the `freezeCard` description in `src/tools.ts` ("freeze cards to be safe") and ask a vague question like "my wallet feels light". Check the **Spans** tab for any unrequested `execute_tool freezeCard`.
- Set `maxSteps: 1` in `src/demo.ts` and watch the tree shrink to a single `chat` span that never gets to see a tool result.
- Add a fifth tool in `src/tools.ts`, register it in `src/agent.ts`, and see a new `execute_tool` name appear without touching any tracing code.

## Gotchas we hit

**The trace's Output column is empty (and Input is a blob of `mastra.*` keys).**
Mastra records the reply on the root span as `mastra.agent_run.output`, a key Opik's OTLP mapping does not recognise. Opik does read plain `input` and `output` attributes, so `src/opik-export.ts` hands `OtelExporter` its own `SpanExporter` that copies the customer message and the reply text onto those two attributes for `agent_run` spans:

```ts
new OtelExporter({
  provider: { custom: { endpoint, headers, protocol: "http/json" } },
  exporter: makeOpikSpanExporter({ url: endpoint, headers }),
});
```

**`opentelemetry disabled: [OtelExporter] Provider configuration is required`.**
Passing only `exporter: ...` to `OtelExporter` silently turns tracing off. A `provider` block is mandatory even when you bring your own exporter; give it the `custom` endpoint and headers as above.

**Every `llm` span shows tokens but the cost is empty (null).**
Mastra reports the model provider as the AI SDK id, `openai.responses`. Opik only prices a call when the provider is a name it recognises, and `openai.responses` is not one. `tidyAttributes` in `src/opik-export.ts` trims the id to its first segment and writes it to both attributes Opik may read:

```ts
const family = provider.split(".")[0];           // "openai.responses" -> "openai"
out["gen_ai.provider.name"] = family;
out["gen_ai.system"] = family;                   // the attribute Opik's OTLP mapping reads as `provider`
```

After the change all 11 `llm` spans in the demo carry a cost and the provider column reads `openai`.

## Running without Opik

`OPIK_TRACK_DISABLE=true` makes `src/mastra.ts` skip the observability config entirely, so nothing is exported. The vitest config sets it, which is why `npm test` needs neither keys nor a running Opik:

```
env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true npm test
```

## How it's put together

- `data/bank.json`: fictional customers, accounts, cards and transactions.
- `src/bank.ts`: the in-memory bank; reads are lookups, `freezeCard` is the only mutation, ownership is enforced here.
- `src/tools.ts`: the four Mastra tools; errors come back as `{ error }` so the model can explain them.
- `src/agent.ts`: the assistant's instructions, model and tools.
- `src/mastra.ts`: the Mastra instance and the Opik wiring (OTLP URL, `projectName` header, tracking switch).
- `src/opik-export.ts`: the span exporter that fills in trace Input/Output.
- `src/demo.ts`: the four scripted requests, then `mastra.shutdown()` to flush spans.
- `scripts/show-trace-tree.ts`: prints the newest traces from Opik as a tree.
- `tests/`: `bank.test.ts` and `tools.test.ts` (lookups, ownership, freeze), `export.test.ts` (attribute mapping), `agent-loop.test.ts` (the real agent against a scripted model with tracking disabled: one tool step, then an answer).

---

*built with Opik · inspired by Opik's examples and documentation*
