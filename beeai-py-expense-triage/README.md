# beeai-py-expense-triage

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![BeeAI](https://img.shields.io/badge/beeai--framework-0.1.85-f5c518?style=flat)
![Opik](https://img.shields.io/badge/Opik-OpenTelemetry-2f54eb?style=flat)

**A ReAct agent that reviews expense reports, and a trace that shows every thought, tool call and model call behind each verdict.**

An expense reviewer that answers "escalate" is only useful if you can see *why*. Did the agent read the per-diem table, or guess? Did it notice that the same taxi ride was already paid last week? A ReAct agent hides that reasoning behind one `agent.run()` call, and when it is wrong you cannot tell a bad prompt from a bad tool result. This example puts a small [BeeAI](https://framework.beeai.dev/) agent in front of the fictional finance desk at Fernwood Outfitters and sends its OpenInference spans to Opik over plain OpenTelemetry, then scores each trace so the wrong verdicts are one filter away.

## What you'll build

- A BeeAI Python `ReActAgent` on `gpt-4o-mini` (temperature 0) with three tools over local JSON files: `lookup_expense_policy`, `check_per_diem` and `get_prior_claims`.
- Six scripted expense reports in `data/reports.json`, each with a known right answer: `approve`, `needs-receipt` or `escalate`. The agent never sees that label.
- `expense_triage/tracing.py`: a `TracerProvider` with a `BatchSpanProcessor`, the OTLP exporter pointed at Opik, and `BeeAIInstrumentor`. No Opik decorators anywhere in the agent code.
- A small exporter wrapper that fixes two things the raw spans get wrong in Opik (see Gotchas).
- A grading step that logs `decision_correct` and `tool_calls` feedback scores onto each trace with the Opik SDK.

## See it in Opik

Run the demo, then open the **beeai-py-expense-triage** project in Opik (local: http://localhost:5173) and go to the **Traces** tab. After one run there are six traces, named `triage R-1001` to `triage R-1006`, each tagged `expense-triage` plus the expense category. The columns show a `decision_correct` and a `tool_calls` feedback score, token usage and an estimated cost of roughly 0.0005 to 0.0008 USD per report (about 0.004 USD for all six).

Open `triage R-1003` (the 142 USD Boston dinner). The tree under it is a `triage R-1003` parent span, then a `ReAct` span for the agent run, and inside that the loop in order: an `OpenAIChatModel` llm span, then a `lookup_expense_policy` span, a second llm span, a `check_per_diem` span, a third llm span, a `get_prior_claims` span, and a final llm span that writes the verdict. Click `check_per_diem` to see the exact input `{"amount_usd": 142.0, "category": "meals", "city": "Boston", "days": 1}` and the output with `"limit_usd": 80` and `"over_by_usd": 62.0`. Click the `ReAct` span and open its metadata: the keys `iterations.1.thought`, `iterations.1.tool_name`, `iterations.2.tool_input` and so on hold the agent's written reasoning for every turn.

Compare it with `triage R-1006` (the 310 USD client dinner), which has only two llm spans and one tool span. The agent read the policy, saw the 200 USD pre-approval limit and escalated without checking prior claims, which is visible in `tool_calls = 1`. And try the failure mode: run `uv run expense-triage R-1005 --max-iterations 2`. The `triage R-1005` and `ReAct` spans are flagged with an error, the loop stops after two llm spans and two tool spans, the trace metadata carries the `AgentError: Agent was not able to resolve the task in 2 iterations.` exception event, the output reads `ERROR: AgentError...` and `decision_correct` is 0. That is what an under-budgeted agent looks like.

## Run it yourself

1. Make sure Opik is reachable. Local self-hosted is picked up from `~/.opik.config` (`url_override` and `workspace`); for Opik Cloud set `OPIK_API_KEY`, `OPIK_WORKSPACE` and leave the URL unset.
2. `cp .env.example .env` and put your OpenAI key in it (or keep it in a `.env` one directory up; both are read).
3. `uv run expense-triage` runs all six reports (about 30 seconds). `uv run expense-triage R-1003` runs one.
4. Read the printed `PASS`/`FAIL` table, then open the project in Opik.
5. Offline tests: `uv run pytest` (no keys or Opik needed).

## Poke around

- Sort the Traces table by `tool_calls`, then compare a 3-tool trace with a 1-tool trace. Same agent, different amount of checking; which one would you trust more?
- Run `uv run expense-triage --max-iterations 2` and filter on `decision_correct = 0`. In our run all six reports failed this way (the loop needs more than two turns even for the shortest one); compare where each loop was cut, then raise the budget to 3 and see which reports recover.
- Edit `data/per_diem.json` so Boston meals allow 150 USD and rerun `R-1003`. The `check_per_diem` span output changes (`within_limit` flips to true); check whether the verdict follows it, which is the grounding you want.
- Add a seventh report in `data/reports.json` that is a duplicate in everything except the amount. Does the agent still catch it? The `get_prior_claims` span shows what it compared.

## Gotchas we hit

**`ValueError: The positional input argument is required.`, or `AttributeError: 'ReActAgentOutput' object has no attribute 'result'`.** The BeeAI Python docs (and the Opik integration page) show `agent.run(prompt=..., execution=AgentExecutionConfig(...))` and `response.result.text`, which is the TypeScript shape. In `beeai-framework` 0.1.85 the prompt is positional, limits are keyword arguments and the answer is the last output message:

```python
response = await agent.run(text, max_iterations=8, max_retries_per_step=3, total_max_retries=10)
answer = response.last_message.text
```

**One trace holds about 250 `new_token` spans.** `ReActAgent` streams, and the instrumentation emits one span per streamed chunk (256 to 258 in a three-tool run) which buries the handful of llm and tool spans. Setting `stream=False` is not an option: the ReAct runner then fails with `The generated output does not adhere to the schema. Nothing valid has been parsed yet!`. Drop them in the exporter instead, as `OpikSpanTuner` does:

```python
self.inner.export([s for s in spans if s.name != "new_token"])
```

**Token usage shows up but cost is empty, and the llm span has no provider.** The raw spans carry `llm.token_count.*` and `llm.model_name`, which Opik maps to usage and model, but nothing that sets the provider, so no price is computed. Add the `gen_ai.*` attributes before export and Opik fills in `provider = openai` and `total_estimated_cost` (0.000213 USD for a 1,272-prompt-token call here):

```python
attrs["gen_ai.system"] = "openai"
attrs["gen_ai.request.model"] = attrs["llm.model_name"]
attrs["gen_ai.usage.input_tokens"] = attrs["llm.token_count.prompt"]
attrs["gen_ai.usage.output_tokens"] = attrs["llm.token_count.completion"]
```

**There are no iteration spans and the tool spans are typed `general`.** The Python instrumentation emits one `ReAct` span with flat children, and Opik derives span type `llm` only from model and usage attributes, so tool calls are not marked `tool`. Read the loop from the order of llm and tool-named spans, and from the `iterations.N.*` keys in the `ReAct` span metadata. The estimated cost also ignores the cached-token discount that OpenAI applies to repeated system prompts, so treat it as an upper bound.

## How it's put together

- `expense_triage/agent.py`: builds the `ReActAgent`, holds the reviewer instructions, opens the per-report parent span (`opik.tags`, `opik.metadata.*`) and returns a `TriageResult`.
- `expense_triage/tools.py`: the three tools, as plain functions plus their BeeAI `@tool` wrappers.
- `expense_triage/tracing.py`: OTLP setup for Opik, `BeeAIInstrumentor`, and the `OpikSpanTuner` exporter wrapper.
- `expense_triage/scoring.py`: compares the decision with the expected label.
- `expense_triage/feedback.py`: finds each report's trace by `metadata.report_id` and logs the feedback scores.
- `expense_triage/cli.py`: `expense-triage [report-id] [--max-iterations N] [--no-trace]`.
- `expense_triage/data.py` and `data/`: the fictional policy, per-diems, prior claims and reports.
- `tests/`: tools, decision parsing, grading, the span tuner and a stubbed agent run under the no-op tracer (`uv run pytest`).

---

*built with Opik · inspired by Opik's examples and documentation*
