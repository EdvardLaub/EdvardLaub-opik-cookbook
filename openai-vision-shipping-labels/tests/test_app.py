import json
from types import SimpleNamespace

from PIL import Image

import extractor
from labels import LABELS, render_all
from scoring import score_extraction, weight_matches
from suite import assertions_for, build_items

CLEAN = LABELS[0]


def _perfect(spec):
    return {
        "carrier": spec["carrier"],
        "tracking_number": spec["tracking_number"].replace(" ", "").lower(),
        "service_level": spec["service_level"],
        "ship_date": spec["ship_date"],
        "weight_value": spec["weight"]["value"],
        "weight_unit": spec["weight"]["unit"],
        "sender": dict(spec["sender"]),
        "recipient": dict(spec["recipient"]),
    }


def test_score_ignores_tracking_spacing_and_case():
    assert all(score_extraction(CLEAN, _perfect(CLEAN)).values())


def test_score_flags_a_misread_digit_and_wrong_weight():
    got = _perfect(CLEAN)
    got["tracking_number"] = "1Z 4A7 R20 03 8841 2098"
    got["weight_value"] = 2.0
    scores = score_extraction(CLEAN, got)
    assert not scores["tracking_number"] and not scores["weight"]
    assert scores["carrier"] and scores["recipient"]


def test_address_comparison_folds_eszett_and_accents():
    spec = next(s for s in LABELS if s["id"] == "08_dhl_lowres")
    got = _perfect(spec)
    got["sender"]["street"] = "Kaiserstraße 8"
    got["recipient"]["street"] = "17 rue des tanneurs"
    assert score_extraction(spec, got)["sender"] and score_extraction(spec, got)["recipient"]


def test_weight_unit_conversion():
    assert weight_matches({"value": 2.3, "unit": "kg"}, 5.07, "lb")
    assert not weight_matches({"value": 2.3, "unit": "kg"}, 2.3, "lb")


def test_handwritten_label_expects_the_correction():
    spec = next(s for s in LABELS if s["defect"] == "handwritten")
    weight_line = assertions_for(spec)[2]
    assert "3.5 lb" in weight_line and "2 lb" in weight_line and "struck-through" in weight_line


def test_suite_has_one_item_per_label_and_hides_answers_from_the_task_data():
    items = build_items()
    assert len(items) == len(LABELS) == 8
    assert all(set(i["data"]) == {"image", "kind"} for i in items)


def test_render_all_draws_distinct_pngs(tmp_path):
    paths = render_all(tmp_path)
    assert len(paths) == 8
    sizes = {Image.open(p).size for p in paths.values()}
    assert len(sizes) > 1  # skewed and low-res labels are not the clean canvas size


def test_traced_extract_label_runs_with_tracking_disabled(tmp_path, monkeypatch):
    """@track and the attachment call are harmless when tracking is off."""
    path = render_all(tmp_path)[CLEAN["id"]]
    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(_perfect(CLEAN))))])
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: reply)))
    monkeypatch.setattr(extractor, "client", fake)
    got = extractor.extract_label(str(path))
    assert all(score_extraction(CLEAN, got).values())
