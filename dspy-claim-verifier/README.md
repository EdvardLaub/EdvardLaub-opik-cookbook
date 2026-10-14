# dspy-claim-verifier

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB) ![DSPy](https://img.shields.io/badge/DSPy-3.x-8B0000) ![Opik](https://img.shields.io/badge/Opik-2.2.100-2f54eb)

*A claim checker that knows the science and ignores the paperwork, until the optimizer teaches it the paperwork.*

Your downstream code wants `SUPPORTED | evidence: S03`. The model, asked to "check the claim against the corpus", says `SUPPORTED`, or a friendly paragraph. Nothing is wrong with its judgement; it just never saw your contract. This example makes that gap measurable: one Opik test suite, run once against the raw DSPy program and once after `BootstrapFewShot` has compiled it.

## What you'll build

A `dspy.ChainOfThought` program that checks short claims against twelve numbered sentences of invented science facts (`data/corpus.txt`: a retreating glacier, a color-changing mineral, a seed vault). Every answer must be exactly one line:

```
SUPPORTED | evidence: S03
REFUTED | evidence: S09
NOT ENOUGH INFO | evidence: none
```

The signature names the three verdicts but says nothing about the line shape or the evidence tag. `BootstrapFewShot` compiles the program from eight labeled claims (`data/train.json`), scored by a purely programmatic metric (exact format, right verdict, right sentence id), so compiling spends no judge tokens. Eight held-out claims (`data/test.json`) form an Opik test suite, run before and after.

## See it in Opik

Open the `dspy-claim-verifier` project, then **Experiments**. The suite `claim-verifier-suite` has two runs:

- `uncompiled`: **0 of 8 items pass** (0%). The program often gets the verdict right but writes it as a bare label, so the format assertion and the evidence assertion fail on all 24 runs (8 items x 3 runs). The only assertions that pass are a few "NOT ENOUGH INFO" cases where the judge accepts the absence of an id.
- `compiled`: **7 of 8 items pass** (88%). The format assertion passes 24/24. The one failing item is a judge call, not a program error: the relevance assertion ("the evidence id names a relevant sentence") passed only 22/24 times, and a local deterministic check over the same 24 runs finds format, verdict and citation all correct 24/24. Treat 88% as the honest judge-scored number and 100% as what the deterministic check says.

Each run executes every item three times and needs two passes (the suite's execution policy), because the judge is noisy.

Then open **Traces**. There are 52: 48 suite-task traces (2 runs x 8 items x 3), each with a `ChainOfThought` span holding a `Predict` span and an `LM: openai - gpt-4o-mini` llm span with token usage and cost, plus 4 stand-alone `ChainOfThought` traces from the bootstrap phase, the teacher attempts the optimizer harvested demos from. Open one compiled trace and read the LM input: it now carries eight demos (four with reasoning, four plain), including two `NOT ENOUGH INFO | evidence: none` ones. Open an uncompiled one: no demos, and an answer like `SUPPORTED`. The four bootstrap traces also carry the module graph. A full run costs roughly $0.03 and takes about three minutes.

## Run it yourself

1. `cd dspy-claim-verifier`
2. `cp .env.example .env` and set `OPENAI_API_KEY` (a repo-root `.env` works too). Opik is read from `~/.opik.config` or the `OPIK_*` environment variables; for a local server run `opik configure --use_local`.
3. `uv sync`
4. `uv run main.py`
5. Offline tests (no keys, no server): `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- Set `max_labeled_demos=4` again in `main.py` and rerun: watch the compiled program invent verdicts for the unanswerable claims (see the first gotcha).
- Drop the citation clause from `check_answer`'s use in `metric` and recompile; the optimizer can no longer tell a well-cited demo from a sloppy one.
- Add a claim whose answer needs two sentences and see which assertion decays.
- Change `runs_per_item` to 1 and compare how much the pass rate wobbles between reruns.

## Gotchas we hit

**The compiled program answers `UNSUPPORTED` or `NONE | no evidence in corpus` on unanswerable claims.** With `max_bootstrapped_demos=4, max_labeled_demos=4`, the four demos were all SUPPORTED or REFUTED: the teacher never produced a NOT ENOUGH INFO attempt that passed the metric, because the raw program doesn't know that label's exact spelling, and the labeled-demo budget was already used up by the bootstrapped ones. Fix: name the three labels in the signature docstring, and raise the labeled budget so unbootstrapped gold examples are added as extra demos:

```python
dspy.BootstrapFewShot(metric=claimcheck.metric, max_bootstrapped_demos=4,
                      max_labeled_demos=8, max_rounds=1)
```

In the Opik trace, check that the compiled LM input contains an `evidence: none` demo; before this fix the compiled run scored 75% (6/8), failing both unanswerable items.

**The suite reports 7/8 although every local check passes.** A judge assertion is probabilistic. The suite is created with `global_execution_policy={"runs_per_item": 3, "pass_threshold": 2}` to absorb that, and `main.py` also prints deterministic format, verdict and citation counts from the task itself so you can tell judge noise from a real regression.

## How it's put together

- `claimcheck.py`: corpus loader, strict answer parser, per-requirement checker, the DSPy signature and program, and the compile-time metric.
- `main.py`: configures `OpikCallback`, creates the suite, runs it uncompiled, compiles with `BootstrapFewShot`, runs it again, flushes.
- `data/corpus.txt`, `data/train.json`, `data/test.json`: the fictional corpus and the labeled claims.
- `tests/test_claimcheck.py`: offline tests for the parser, checker, metric, data integrity and a traced call with tracking disabled.

---

*built with Opik · inspired by Opik's examples and documentation*
