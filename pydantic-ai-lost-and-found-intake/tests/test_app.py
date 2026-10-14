"""Offline tests: no provider key, no Opik server (run with OPIK_TRACK_DISABLE=true)."""

import pytest
from pydantic_ai.models.test import TestModel

from lostfound.agent import get_agent, intake_note
from lostfound.cli import build_parser, traced_intake
from lostfound.grounding import ungrounded_fields
from lostfound.models import FoundItemRecord
from lostfound.notes import NOTES
from lostfound.suite import TEST_ITEMS


@pytest.fixture
def stub_model():
    """Swap the OpenAI model for a canned one so no network call is made."""
    model = TestModel(custom_output_args={"item_type": "scarf", "color": "navy"})
    with get_agent().override(model=model):
        yield model


def test_intake_returns_record_dict(stub_model):
    record = intake_note("navy scarf")
    assert record["item_type"] == "scarf" and record["brand"] is None
    FoundItemRecord(**record)


def test_traced_function_runs_with_tracking_disabled(stub_model):
    # @opik.track must be a transparent pass-through when OPIK_TRACK_DISABLE=true.
    assert traced_intake("navy scarf")["color"] == "navy"


def test_grounding_flags_invented_brand():
    record = {"item_type": "phone", "brand": "Apple", "color": None, "found_where": "stage door"}
    assert ungrounded_fields(record, "iPhone found by the stage door") == {"brand": ["apple"]}


def test_grounding_accepts_accents_and_case():
    note = "green backpack with a Fjällräven fox patch"
    assert ungrounded_fields({"brand": "Fjallraven", "color": "GREEN"}, note) == {}


def test_grounding_ignores_null_fields():
    assert ungrounded_fields({"item_type": "ring", "color": None}, "a ring") == {}


def test_suite_items_match_notes_and_hide_answers():
    assert [i["data"]["note"] for i in TEST_ITEMS] == NOTES
    assert all(len(i["assertions"]) >= 2 for i in TEST_ITEMS)


def test_cli_has_three_subcommands():
    args = build_parser().parse_args(["extract", "blue hat"])
    assert args.command == "extract" and args.note == "blue hat"
    for cmd in ("intake", "suite"):
        assert build_parser().parse_args([cmd]).command == cmd
