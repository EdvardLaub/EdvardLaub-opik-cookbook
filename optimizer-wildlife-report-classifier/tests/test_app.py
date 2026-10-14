from collections import Counter

from classify import classify_report, render
from scoring import is_valid_label, label_accuracy, normalise
from sightings import LABELS, REPORTS


def test_dataset_covers_every_label_evenly():
    counts = Counter(label for _, label in REPORTS)
    assert set(counts) == set(LABELS)
    assert min(counts.values()) == max(counts.values()) == 6


def test_normalise_is_light_touch():
    assert normalise(" Reptiles/Amphibians. ") == "reptiles_amphibians"
    assert normalise("**Marine life**") == "marine_life"


def test_metric_rejects_chatty_answers():
    item = {"label": "birds"}
    assert label_accuracy(item, "Birds.") == 1.0
    assert label_accuracy(item, "This is about birds.") == 0.0
    assert not is_valid_label("a bird thing")


def test_render_fills_placeholder():
    msgs = render([{"role": "user", "content": "{{report}}"}], "owl")
    assert msgs[0]["content"] == "owl"


class _Stub:
    class chat:
        class completions:
            @staticmethod
            def create(**kw):
                msg = type("M", (), {"content": "Insects."})
                return type("R", (), {"choices": [type("C", (), {"message": msg})]})


def test_traced_function_runs_with_stub_client():
    # @opik.track must not get in the way (tracking is disabled in CI).
    out = classify_report([{"role": "user", "content": "{{report}}"}], "beetle", client=_Stub)
    assert out == {"label": "insects", "valid": True, "raw": "Insects."}
