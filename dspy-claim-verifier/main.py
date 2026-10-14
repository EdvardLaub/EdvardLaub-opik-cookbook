"""Run the claim verifier uncompiled, compile it, run it again."""

import os
import pathlib

# The build machine may route providers through a proxy; use public APIs.
for var in ("OPENAI_BASE_URL", "OPENAI_API_BASE", "ANTHROPIC_BASE_URL"):
    os.environ.pop(var, None)

import dotenv
import dspy

import claimcheck

dotenv.load_dotenv(pathlib.Path(__file__).parents[1] / ".env")

MODEL = "openai/gpt-4o-mini"
dspy.configure(lm=dspy.LM(MODEL, cache=False))


def score(program, rows: list[dict]) -> dict[str, int]:
    corpus = claimcheck.load_corpus()
    totals = {"format": 0, "verdict": 0, "citation": 0, "all": 0}
    for row in rows:
        answer = program(corpus=corpus, claim=row["claim"]).answer
        checks = claimcheck.check_answer(answer, row["verdict"], row["evidence"])
        for key, ok in checks.items():
            totals[key] += ok
        totals["all"] += all(checks.values())
    return totals


def main() -> None:
    test_rows = claimcheck.load_examples("test")
    print("uncompiled:", score(claimcheck.verifier, test_rows))

    optimizer = dspy.BootstrapFewShot(
        metric=claimcheck.metric, max_bootstrapped_demos=4,
        max_labeled_demos=4, max_rounds=1,
    )
    trainset = claimcheck.to_examples(claimcheck.load_examples("train"))
    compiled = optimizer.compile(claimcheck.verifier, trainset=trainset)
    print("compiled:  ", score(compiled, test_rows))


if __name__ == "__main__":
    main()
