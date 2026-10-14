# optimizer-wildlife-report-classifier

[![Python](https://img.shields.io/badge/python-3.12+-blue?style=flat)](pyproject.toml)
[![opik-optimizer](https://img.shields.io/badge/opik--optimizer-3.2.0-orange?style=flat)](pyproject.toml)

*A vague prompt routes citizen wildlife reports badly. Let Opik's optimizer rewrite it, and read the score curve to see why.*

Volunteers send notes like "otter slid into the river by the mill" to a fictional app, Marshline Nature Watch, and each note must reach the right group of specialists: birds, mammals, reptiles_amphibians, insects, marine_life, or not_a_sighting. The first-draft prompt names the groups but never says how to answer, so the model replies in sentences and exact-match scoring marks nearly everything wrong. Rather than guessing at rewrites, you hand the prompt, a labelled dataset and a metric to the optimizer and keep whatever scores higher.

## What you'll build

One script, `main.py`:

1. uploads 36 labelled fictional reports as an Opik dataset (6 per group, with tricky ones: a seahorse, a bat, a turtle at sea, a whale-shaped cloud);
2. saves the weak baseline prompt to the prompt library as version 1;
3. runs `MetaPromptOptimizer` for at most 6 trials (gpt-4.1-mini writes candidate prompts, gpt-4o-mini classifies);
4. saves the winner as version 2, then fetches it back from the library and routes one brand-new report.

## See it in Opik

Run the script and open the `optimizer-wildlife-report-classifier` project (use the project-pinned "run link" it prints). In my run:

- **Optimization run**: 6 trials plus the baseline. Baseline accuracy 0.222; the scores across trials were 0.0, 1.0, 1.0, 0.889, 1.0, 1.0. One candidate collapsed to 0.0 and one slipped to 0.889, so the curve is a climb with noise rather than a straight line. Click a trial to read the exact prompt it tested.
- **Prompts** tab: `wildlife-report-router` has two versions. v1 is the baseline ("Weak hand-written baseline"); v2's change description reads `MetaPromptOptimizer winner: accuracy 0.222 -> 1.000`. The winning text tells the model to output only the group name, which is the missing rule.
- **Traces**: 255 traces in the project: 252 `evaluation_task` (7 evaluations x 36 reports), 2 `optimization_algorithm` and 1 `classify_report`. Each trace holds an `llm` span with token usage and cost; the whole run cost about $0.009 in those llm spans.
- **Datasets**: `wildlife-reports-labelled`, 36 items; **Experiments**: 7, one per evaluated prompt.

Your numbers will differ: the model and the optimizer's search are not deterministic.

## Run it yourself

1. `cp .env.example .env` and set `OPENAI_API_KEY` (or rely on a repo-root `.env`). For a local Opik nothing else is needed; for Opik Cloud also set `OPIK_API_KEY` and `OPIK_WORKSPACE`.
2. `uv sync`
3. `uv run main.py` (about one minute, a cent or two).
4. Open the printed run link, then the Prompts tab.
5. Tests, offline: `OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- Swap `REASONER` for `openai/gpt-4o-mini` and re-run: weaker prompt-writers often keep the verbose output and the curve stays flat.
- Delete the group list from `WEAK_SYSTEM`. The optimizer cannot guess label names it never sees, and scores stay low.
- Remove `skip_perfect_score=False` and watch the run stop as soon as a trial reaches about 0.95.
- Loosen `normalise` in `scoring.py` so "This is birds" passes, and see how little there is left to optimize.

## Gotchas we hit

- **Symptom:** the printed `get_run_link()` opens an empty-looking page. **Cause:** it opens in whichever project the UI last showed. **Fix:** build the link from the optimization record: `info = client.rest_client.optimizations.get_optimization_by_id(result.optimization_id)` then `{ui}/{workspace}/projects/{info.project_id}/optimizations/{id}` (see `main.py`).
- **Symptom:** `client.get_chat_prompt(name="wildlife-report-router")` returns `None` right after saving. **Cause:** prompts are scoped to a project. **Fix:** pass `project_name=PROJECT_NAME`; the messages are on `.template`.
- **Symptom:** a saved prompt shows `{report}` not substituting. **Cause:** the optimizer uses single braces, the library uses mustache. **Fix:** `content.replace("{report}", "{{report}}")` before `create_chat_prompt`.
- **Symptom:** the optimization finishes after one trial. **Cause:** `skip_perfect_score` stops at `perfect_score=0.95`. **Fix:** `MetaPromptOptimizer(..., skip_perfect_score=False)`.
- **Symptom:** `result.llm_cost_total` is `None`. **Cause:** not populated here. **Fix:** read cost from the llm spans (`total_estimated_cost`).

## How it's put together

- `main.py`: dataset, baseline, optimizer run, library saves, fresh-report check.
- `sightings.py`: the 36 labelled reports and the six labels.
- `scoring.py`: normalisation and the exact-match metric.
- `classify.py`: `classify_report`, a traced function using a `track_openai` client and a library prompt.
- `tests/test_app.py`: dataset balance, metric, prompt rendering, and the traced function with a stub client.

*built with Opik · inspired by Opik's examples and documentation*
