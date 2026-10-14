# langgraph-postmortem-team

*Three kinds of agent, one outage, one trace deep enough to see the loop and the bill per agent.*

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LangGraph 1.2](https://img.shields.io/badge/langgraph-1.2-1C3C3C?style=flat)
![Opik 2.2](https://img.shields.io/badge/opik-2.2.100-2f54eb?style=flat)

After an outage, someone has to read a pile of logs, a deploy list, alert history and a noisy chat
channel and turn them into a calm, blameless write-up. That is a good job for a team of agents, and a
hard one to debug: when the write-up blames the wrong change, was the plan bad, did an investigator
search the wrong evidence, or did the writer misread a correct finding? One trace should answer that, and
it should also tell you which agent is spending the money.

## What you'll build

A LangGraph team that writes the post-mortem for a made-up incident at "Brightloom", an invoicing SaaS.
On 2026-10-02 a config-only release (r4411) cut a database pool from 100 to 10 connections, skipped canary,
and took checkout success from 99.1% to 31% for about 54 minutes. The evidence lives offline in `data/`:
log excerpts, a deploy history, an alert timeline and an incident-channel transcript.

```
planner ──> investigator ──┐
               ^           │ more questions? loop
               └───────────┘ all answered? ──> writer ──> post-mortem
```

- **planner**: structured output, four evidence questions, each with search terms in the evidence's own vocabulary.
- **investigator**: one pass per question; searches `data/` (a small keyword ranker, no vector DB) and answers with timestamps and sources. The conditional edge loops it four times.
- **writer**: drafts Summary / Impact / Timeline / Root cause / Contributing factors / What went well / Action items, naming roles, not people.

All agents use `gpt-4o-mini`. Afterwards `main.py` attaches three rule-based scores to the trace and prints a cost-per-agent table.

## See it in Opik

Open the `langgraph-postmortem-team` project and the newest trace (Opik names it `LangGraph`). In my verified
run it held 22 spans: 12 `general`, 6 `llm`, 4 `tool`, total estimated cost **$0.0018** for 6,176 tokens.

- **Tree.** Top-level spans are `planner`, then four `investigator` spans, then `writer`. Each investigator
  holds a `search_evidence` tool span (input: the question plus the planner's search terms; output: the four
  sections it matched), a `ChatOpenAI` llm span, and a `route` span. The planner holds its own `ChatOpenAI` span.
- **Graph view.** The trace's graph tab draws planner, investigator with its self-loop, and writer, so the
  loop is visible instead of inferred from repeated names.
- **Cost per agent.** Only llm spans carry cost; the node spans show none. `costs.py` rolls each llm span up to
  its node. This run: planner $0.000140 (1 pass), investigators $0.000995 (4 passes, 3,624 tokens),
  writer $0.000694 (1 pass, 2,095 tokens). The loop is the biggest line item, and each extra evidence
  question the planner asks adds a whole investigator pass.
- **Feedback scores.** The trace row has `root_cause_named` (1.0 here), `contributing_factors` (0.33) and
  `blameless` (1.0). They come from regexes, not a judge, and they move between runs: the model sometimes
  writes "minIdle" as the cause (0.0), or skips the pool-alerting gap (this run). That variance is the point
  of having them next to the trace.

## Run it yourself

1. `cp .env.example .env` and set `OPENAI_API_KEY` (or rely on the repo-root `.env`, which `main.py` loads).
2. Point the SDK at your Opik: `opik configure` for Cloud or a local server (local needs no key).
3. `uv sync`
4. `uv run main.py` (about 25 s)
5. Open the project `langgraph-postmortem-team` in Opik and click the newest trace.

Offline tests, no keys and no tracking: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- Change `INCIDENT` in `main.py` to ask for a customer-facing summary only, and compare the writer's token cost.
- Make the planner ask for 2 questions (edit its system prompt): two investigator spans, and the table's
  investigator row drops accordingly.
- Delete the `search_terms` field from `EvidenceQuestion` and rerun: look at the `search_evidence` outputs for
  the "slow recovery" question (see the first gotcha).
- Edit `data/deploys.md` so r4411 says it changed `minIdle`, and see whether `root_cause_named` drops to 0.

## Gotchas we hit

**The recovery section of the post-mortem was thin; the rollback never showed up.** In the trace, the fourth
`search_evidence` tool span returned r4409, a pre-incident deploy, and an early chat section, but not the
rollback chat or rollback deploy. Cause: the planner writes questions in prose ("obstacles", "restoration",
"functionality") that appear nowhere in logs or chat, so the keyword ranker matched noise. Fix: ask the
planner for `search_terms` in the evidence's vocabulary and search with `f"{question} {search_terms}"`
(see `EvidenceQuestion` and `investigator` in `postmortem/team.py`; `tests/test_team.py` covers it).

**Cost is `null` on the `planner` / `investigator` spans.** LangGraph node spans are `general` spans; Opik
computes cost only on `llm` spans (`ChatOpenAI`, here), and the trace total is their sum. Roll the cost up
yourself by walking each llm span's `parent_span_id` chain to a node name, as `cost_by_agent` does.

**The trace is called `LangGraph`, not your project or app.** `track_langgraph` names the trace after the
graph. Use the project, tags (`postmortem`) and feedback columns to find a run.

**Plain helper functions are not spans.** The ranker is an ordinary function, so `OpikTracer` does not see
it. Decorate it with `@opik.track(name="search_evidence", type="tool")` (done in `postmortem/tracing.py`)
so every search shows its input and output; this also keeps retrieval visible if a LangChain retriever run
is ever dropped by the tracer.

## How it's put together

- `main.py`: builds the team, runs it, logs feedback scores, flushes, prints the cost table.
- `postmortem/team.py`: state, planner / investigator / writer nodes and the graph (no Opik code).
- `postmortem/corpus.py`: loads `data/` by `##` section and ranks sections for a query.
- `postmortem/tracing.py`: `OpikTracer` plus `track_langgraph`, and the `search_evidence` tool wrapper.
- `postmortem/costs.py`: rolls llm-span cost and tokens up to agent nodes; reads them back from Opik.
- `postmortem/checks.py`: the three rule-based post-mortem scores.
- `data/`: `logs.md`, `deploys.md`, `alerts.md`, `chat.md`, the fictional evidence.
- `tests/test_team.py`: corpus, search, a traced call with tracking off, the graph loop with a fake model, scores, cost roll-up.

---

*built with Opik · inspired by Opik's examples and documentation*
