"""Run one Opik test suite on the claim verifier before and after compiling it."""

import os
import pathlib

PROJECT_NAME = "dspy-claim-verifier"
# Every trace from this process lands in this Opik project.
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

# The build machine may route providers through a proxy; use public APIs.
for var in ("OPENAI_BASE_URL", "OPENAI_API_BASE", "ANTHROPIC_BASE_URL"):
    os.environ.pop(var, None)

import dotenv
import dspy
import opik
from opik.integrations.dspy.callback import OpikCallback

import claimcheck

dotenv.load_dotenv(pathlib.Path(__file__).parents[1] / ".env")

MODEL = "openai/gpt-4o-mini"

# OpikCallback turns each DSPy call into a trace: a module span (ChainOfThought,
# Predict) with the LM call nested inside as an llm span carrying tokens and
# cost. log_graph=True also stores the module graph on the trace. Without it,
# DSPy runs fine and nothing shows up in Opik.
dspy.configure(
    lm=dspy.LM(MODEL, cache=False),
    callbacks=[OpikCallback(project_name=PROJECT_NAME, log_graph=True)],
)

# Suite-wide requirements, checked by an LLM judge on every item. They state
# the contract in plain words; the per-item assertion pins the expected label.
GLOBAL_ASSERTIONS = [
    "The answer is exactly one line of the form '<VERDICT> | evidence: <ID>' where "
    "VERDICT is SUPPORTED, REFUTED or NOT ENOUGH INFO and ID is a sentence id "
    "like S03 (or the word none), with no other words before or after it",
    "The evidence ID names a sentence from the corpus that is relevant to the claim, "
    "or is 'none' when the verdict is NOT ENOUGH INFO",
]

# Judges are noisy: run each item three times and require two passes. This is
# the suite's execution policy; it is stored on the suite and shown per run.
EXECUTION_POLICY = {"runs_per_item": 3, "pass_threshold": 2}


def make_task(program: dspy.Module, tally: dict[str, int]):
    """Wrap a DSPy program as a run_tests task; also tally the local checks."""
    corpus = claimcheck.load_corpus()

    def task(item: dict) -> dict:
        answer = program(corpus=corpus, claim=item["claim"]).answer
        # Local, deterministic checks (no judge) so the printed numbers do not
        # depend on judge noise; the suite's own verdicts are the source of truth.
        checks = claimcheck.check_answer(answer, item["verdict"], item["evidence"])
        tally["calls"] += 1
        for key, ok in checks.items():
            tally[key] += ok
        return {"input": {"claim": item["claim"]}, "output": answer}

    return task


def run_suite(suite, program, name: str, compiled: bool):
    tally = {"calls": 0, "format": 0, "verdict": 0, "citation": 0}
    # run_tests runs the task on each suite item, has the judge check the
    # assertions, and records one experiment (a "test-suite run") under `name`.
    result = opik.run_tests(
        test_suite=suite,
        task=make_task(program, tally),
        experiment_name=name,
        experiment_config={"program": "ChainOfThought(VerifyClaim)",
                           "compiled": compiled, "model": MODEL},
        worker_threads=4,
        generate_report=False,
    )
    print(f"{name:>16}: {result.pass_rate:.0%} pass "
          f"({result.items_passed}/{result.items_total} items) | local checks over "
          f"{tally['calls']} runs: format {tally['format']}, verdict {tally['verdict']}, "
          f"citation {tally['citation']}")
    return result


def main() -> None:
    client = opik.Opik()

    # The suite lives in the project; items insert with dedup so re-runs reuse it.
    suite = client.get_or_create_test_suite(
        name="claim-verifier-suite",
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        global_execution_policy=EXECUTION_POLICY,
    )
    suite.insert([
        {"data": row,
         "assertions": [f"The verdict is {row['verdict']} and the evidence is "
                        f"{row['evidence']}"]}
        for row in claimcheck.load_examples("test")
    ])

    run_suite(suite, claimcheck.verifier, "uncompiled", compiled=False)

    # max_labeled_demos=8 is the fix that matters: with 4, the demos were all
    # SUPPORTED/REFUTED (the teacher never produced a NOT ENOUGH INFO attempt
    # that passed the metric), so the compiled program answered NEI claims
    # without the "| evidence: none" tag. With 8, the unbootstrapped gold
    # examples, NEI ones included, are added as extra demos.
    optimizer = dspy.BootstrapFewShot(
        metric=claimcheck.metric, max_bootstrapped_demos=4,
        max_labeled_demos=8, max_rounds=1,
    )
    trainset = claimcheck.to_examples(claimcheck.load_examples("train"))
    compiled_program = optimizer.compile(claimcheck.verifier, trainset=trainset)

    compiled = run_suite(suite, compiled_program, "compiled", compiled=True)
    if compiled.experiment_url:
        print(f"\nView the runs: {compiled.experiment_url}")

    # Traces are sent from a background thread; flush so none are lost on exit.
    opik.flush_tracker()


if __name__ == "__main__":
    main()
