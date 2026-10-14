# smolagents-solar-output-analyst

**Ask a code-writing agent about a solar farm's output, then open Opik and read the pandas it actually ran.**

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![smolagents 1.26](https://img.shields.io/badge/smolagents-1.26-FFD21E?style=flat)
![OpenTelemetry](https://img.shields.io/badge/tracing-OpenInference%20%2B%20OTLP-425CC7?style=flat)
![Opik](https://img.shields.io/badge/Opik-local%20or%20cloud-2f54eb?style=flat)

An agent that answers by writing and running Python can be wrong in a way a chatbot cannot: it hands
you a precise-looking *number* produced by code you never saw. If the code compared the wrong windows
or averaged the wrong column, the sentence still reads like a fact. This example makes that failure
inspectable. A smolagents `CodeAgent` investigates the production log of a fictional community solar
garden, and every snippet it generates, every execution log it reads back, and every token it spends
is exported to Opik, so a suspicious answer can be traced to the line of pandas that produced it.

## What you'll build

The Larkspur Community Solar Garden has four arrays (North Meadow, Barn Roof, Pond Edge, Hillside
Tracker). `data/solar_garden_daily.csv` holds 480 rows: one per array per day, 1 March to 28 June 2026,
with `kwh`, `capacity_kw`, site-wide cloud cover and temperature, and logged `outage_hours`. Three
anomalies are planted in it:

1. **Pond Edge** has an inverter outage from 11 to 16 May (zero kWh, 24 outage hours a day).
2. **Barn Roof** quietly loses about 25% of its yield from 1 May, with no outage logged and the same weather as its siblings.
3. **Hillside Tracker** logs 2,950 kWh on 9 April, more than the 2,880 kWh a 120 kW array could make in 24 hours.

The package is small: `data.py` loads the CSV and writes the briefing, `agent.py` builds a `CodeAgent`
on `gpt-4o-mini` that may import only pandas, `questions.py` holds one question per anomaly, and
`cli.py` either answers a question you type or runs the scripted set and grades each answer against
ground truth computed from the CSV (`checks.py`). Tracing lives in `tracing.py`: OpenInference's
`SmolagentsInstrumentor` plus an OTLP exporter pointed at Opik.

## See it in Opik

Run the scripted set, then open the **smolagents-solar-output-analyst** project. There is one
`CodeAgent.run` trace per question (three in all). Mine had 8, 14 and 6 spans: the root, a `Step N`
span per think-code-observe cycle, an `OpenAIModel.generate` llm span per model call, and a
`FinalAnswerTool` span.

Open the second trace, the Barn Roof question, which is the hard one. Expand an `OpenAIModel.generate`
span and read its output: the model's reasoning followed by the `<code>` block it wrote. Then open the
`Step` span that ran it, whose output holds the execution log. In my run the agent took a
rolling mean of kWh per kW, computed day-over-day drops, and `Step 4` printed a table with
`percentage_drop` values of 105.66, 106.34 and 107.98 for three different arrays. The final answer
repeated those numbers ("Barn Roof and North Meadow dropped on 2026-03-03 by approximately 105.66%"),
and the check printed `FAIL underperformer`. The answer sounds quantitative; the trace shows it
compared consecutive days (noise) instead of each array against its siblings over weeks, which
is exactly what the CSV's planted step change needs. An earlier run of the same question named Barn
Roof but reported a 13% drop "from the median date", also visible as a median-date split in the
generated code. The other two answers (Pond Edge, 11 to 16 May; Hillside Tracker, 9 April) were
correct in both runs. Expect your run to differ in detail; the model's code varies.

On the trace list the columns are filled: input is the briefing plus the question, output is the
final answer, and `usage` and `total_estimated_cost` hold the sum of the model calls. The Barn Roof
trace used 21,636 prompt tokens and cost about $0.0042; the whole scripted run cost roughly $0.007 and
took about 30 seconds.

## Run it yourself

1. Put `OPENAI_API_KEY` in a `.env` (`cp .env.example .env`), or in a `.env` one level up. Opik
   settings come from `~/.opik.config` or `OPIK_URL_OVERRIDE` / `OPIK_WORKSPACE` / `OPIK_API_KEY`
   (local Opik needs no key; leave `OPIK_API_KEY` unset).
2. `uv sync`
3. `uv run solar-analyst --scripted` runs the three questions and prints PASS/FAIL per question.
4. `uv run solar-analyst "Which array produced the most energy in May?"` asks your own question.
5. Open the `smolagents-solar-output-analyst` project in Opik, newest trace first.

Add `--no-trace` to run without exporting spans. Tests need no keys and no Opik:
`env -u OPENAI_API_KEY uv run pytest`.

## Poke around

- Ask something the data cannot answer ("which array has the best warranty?") and watch in the step
  spans how the agent discovers the column is missing.
- Tighten the question: add "find the exact date the drop starts using a 7-day rolling mean" to the
  Barn Roof question in `questions.py` and see whether the generated code changes and the check passes.
- Remove `"pandas"` from `additional_authorized_imports` in `agent.py`; the first `Step` span's output
  should show an import error from the executor instead of a dataframe.
- Regenerate the data with different anomalies by editing `scripts/generate_data.py`, then check the
  answers against `solar_analyst/checks.py`.

## Gotchas we hit

**The cost column is empty, and trace usage is twice what the model calls add up to.** The raw
OpenInference spans carry `llm.provider`, `llm.token_count.*` and so on, and Opik shows token counts
for them but no `total_estimated_cost`, even though the llm spans have `model=gpt-4o-mini` and
`provider=openai`. On top of that, the `CodeAgent.run` span repeats its children's token totals, so
the trace-level usage (9,812 prompt tokens in my first try) is double the real figure (4,906). In my runs
Opik only priced spans whose usage carried `prompt_tokens` / `completion_tokens` keys, which it fills from
`gen_ai.*` attributes. The fix in `tracing.py` is an exporter wrapper that, just before export, adds
`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`
to LLM spans and removes `llm.token_count.*` from every other span:

```python
provider.add_span_processor(BatchSpanProcessor(OpikAttributeFixer(OTLPSpanExporter(endpoint=url, headers=headers))))
```

Adding only `gen_ai.system` and the model name was not enough; the token attributes were needed.

## How it's put together

- `solar_analyst/data.py`: loads the CSV and builds the briefing the agent receives with each question.
- `solar_analyst/agent.py`: `build_agent()`, a pandas-only `CodeAgent` on `gpt-4o-mini`.
- `solar_analyst/questions.py`: the scripted questions, one per planted anomaly.
- `solar_analyst/checks.py`: ground truth from the CSV and a keyword grader for the answers.
- `solar_analyst/tracing.py`: OTLP exporter to Opik, the instrumentor, and the attribute fixer.
- `solar_analyst/cli.py`: `solar-analyst "<question>"` or `--scripted`, plus `--no-trace`.
- `data/solar_garden_daily.csv` and `scripts/generate_data.py`: the dataset and its seeded generator.
- `tests/`: ground truth and grader, data loading, the CLI with a stub agent, and the tracing layer with a fake OpenAI client.

---

*built with Opik · inspired by Opik's examples and documentation*
