"""Offline tests: no provider keys, no Opik server (OPIK_TRACK_DISABLE=true)."""

import dspy
import opik
from dspy.utils.dummies import DummyLM

import claimcheck


def test_corpus_has_numbered_sentences():
    lines = claimcheck.load_corpus().splitlines()
    assert lines[0].startswith("[S01] ") and len(lines) == 12


def test_every_example_cites_a_real_sentence():
    corpus = claimcheck.load_corpus()
    for name in ("train", "test"):
        for row in claimcheck.load_examples(name):
            assert row["verdict"] in claimcheck.VERDICTS
            if row["verdict"] == "NOT ENOUGH INFO":
                assert row["evidence"] == "none"
            else:
                assert f"[{row['evidence']}]" in corpus


def test_parse_answer_is_strict():
    assert claimcheck.parse_answer("REFUTED | evidence: S09") == ("REFUTED", "S09")
    assert claimcheck.parse_answer("NOT ENOUGH INFO | evidence: none")
    assert claimcheck.parse_answer("Refuted, see S09.") is None
    assert claimcheck.parse_answer("SUPPORTED | evidence: S03 because it says so") is None


def test_check_answer_scores_each_requirement():
    ok = claimcheck.check_answer("SUPPORTED | evidence: S03", "SUPPORTED", "S03")
    assert ok == {"format": True, "verdict": True, "citation": True}
    wrong = claimcheck.check_answer("SUPPORTED | evidence: S04", "REFUTED", "S03")
    assert wrong == {"format": True, "verdict": False, "citation": False}
    prose = claimcheck.check_answer("The claim is supported by S03.", "SUPPORTED", "S03")
    assert not any(prose.values())


def test_metric_uses_all_three_checks():
    example = claimcheck.to_examples(claimcheck.load_examples("train"))[0]
    good = dspy.Prediction(answer=example.answer)
    assert claimcheck.metric(example, good)
    assert not claimcheck.metric(example, dspy.Prediction(answer="SUPPORTED"))


def test_traced_program_runs_with_tracking_disabled():
    # The OpikCallback and @track wrappers must not get in the way of unit tests.
    from opik.integrations.dspy.callback import OpikCallback

    lm = DummyLM([{"reasoning": "S03 states it.", "answer": "SUPPORTED | evidence: S03"}])
    with dspy.context(lm=lm, callbacks=[OpikCallback(project_name="dspy-claim-verifier")]):
        out = claimcheck.verifier(corpus=claimcheck.load_corpus(), claim="x").answer
    assert claimcheck.parse_answer(out) == ("SUPPORTED", "S03")

    @opik.track
    def traced(a: int) -> int:
        return a + 1

    assert traced(1) == 2
