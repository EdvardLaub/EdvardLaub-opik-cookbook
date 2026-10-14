"""A DSPy claim verifier over a small fictional science corpus.

The house output format is strict and lives only in worked examples, never in
the signature:  VERDICT | evidence: <sentence id>
e.g.  "SUPPORTED | evidence: S03"  or  "NOT ENOUGH INFO | evidence: none".
"""

import json
import pathlib
import re

import dspy

DATA = pathlib.Path(__file__).parent / "data"
VERDICTS = ("SUPPORTED", "REFUTED", "NOT ENOUGH INFO")

# The whole answer must be exactly this shape, nothing before or after.
ANSWER_FORMAT = re.compile(
    r"^(SUPPORTED|REFUTED|NOT ENOUGH INFO) \| evidence: (S\d{2}|none)$"
)


def load_corpus() -> str:
    """The corpus as one prompt-ready block: '[S01] sentence' per line."""
    lines = []
    for raw in (DATA / "corpus.txt").read_text().splitlines():
        sid, sentence = (part.strip() for part in raw.split("|", 1))
        lines.append(f"[{sid}] {sentence}")
    return "\n".join(lines)


def load_examples(name: str) -> list[dict]:
    return json.loads((DATA / f"{name}.json").read_text())


def parse_answer(answer: str) -> tuple[str, str] | None:
    """(verdict, evidence) if the answer obeys the format exactly, else None."""
    match = ANSWER_FORMAT.match(answer.strip())
    return (match.group(1), match.group(2)) if match else None


def check_answer(answer: str, verdict: str, evidence: str) -> dict[str, bool]:
    """Score one answer on the three requirements, independently."""
    parsed = parse_answer(answer)
    found_verdict = parsed[0] if parsed else None
    return {
        "format": parsed is not None,
        "verdict": found_verdict == verdict,
        "citation": parsed is not None and parsed[1] == evidence,
    }


class VerifyClaim(dspy.Signature):
    """Check the claim against the corpus. The verdict is one of SUPPORTED,
    REFUTED or NOT ENOUGH INFO."""

    corpus: str = dspy.InputField(desc="numbered science facts, one per line")
    claim: str = dspy.InputField()
    answer: str = dspy.OutputField()


# The signature names the three labels but not the answer format or the evidence
# tag, so the raw program answers with a bare label or prose; only compiled demos
# teach the "<VERDICT> | evidence: <ID>" shape.
verifier = dspy.ChainOfThought(VerifyClaim)


def to_examples(rows: list[dict]) -> list[dspy.Example]:
    corpus = load_corpus()
    return [
        dspy.Example(
            corpus=corpus, claim=r["claim"],
            answer=f"{r['verdict']} | evidence: {r['evidence']}",
            verdict=r["verdict"], evidence=r["evidence"],
        ).with_inputs("corpus", "claim")
        for r in rows
    ]


def metric(example: dspy.Example, prediction, trace=None) -> bool:
    """Compile-time metric: exact format, right verdict, right evidence id."""
    return all(check_answer(prediction.answer, example.verdict, example.evidence).values())

