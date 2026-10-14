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
`CodeAgent.run` trace per question (three in all). My run had 8, 10 and 8 spans: the root, a `Step N`
span per think-code-observe cycle, an `OpenAIModel.generate` llm span per model call, and a
`FinalAnswerTool` span.

Open the second trace, the Barn Roof question. Expand `OpenAIModel.generate` in step 2 and read the
output: the model's reasoning followed by the `<code>` block it wrote. In my run it split the data at
`solar_data['date'].median()`, averaged kWh per kW before and after, and computed a drop. Now open the
matching `Step 2` span: its output holds the execution log, `percentage_drop 13.144898`. That is the
whole story of the one failed check in my run: the agent named the right array (Barn Roof) but
reported a 13% drop "from the median date", while the real change is about 25% starting 1 May.
Splitting at the midpoint of the whole period blurs a step change, and you can see that choice
in the span rather than guessing at it. The other two answers (Pond Edge, 11 to 16 May; Hillside
Tracker, 9 April) were correct and their code and logs are right there too. Your run will differ in
detail, because the model's code varies run to run.

On the trace list, the input column is the briefing plus the question and the output column is the final
answer. The whole scripted run took about 30 seconds.

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


## How it's put together

- `solar_analyst/data.py`: loads the CSV and builds the briefing the agent receives with each question.
- `solar_analyst/agent.py`: `build_agent()`, a pandas-only `CodeAgent` on `gpt-4o-mini`.
- `solar_analyst/questions.py`: the scripted questions, one per planted anomaly.
- `solar_analyst/checks.py`: ground truth from the CSV and a keyword grader for the answers.
- `solar_analyst/tracing.py`: OTLP exporter to Opik, the instrumentor.
- `solar_analyst/cli.py`: `solar-analyst "<question>"` or `--scripted`, plus `--no-trace`.
- `data/solar_garden_daily.csv` and `scripts/generate_data.py`: the dataset and its seeded generator.
- `tests/`: ground truth and grader, data loading, the CLI with a stub agent.

---

*built with Opik · inspired by Opik's examples and documentation*
