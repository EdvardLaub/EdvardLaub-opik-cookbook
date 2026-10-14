"""The Opik test suite: plain-language assertions generated from the ground truth.

The expected values live only in the assertions (not in the item data the
model's task receives), so the LLM judge compares the extraction against them
instead of reading answers off the input.
"""

from __future__ import annotations

from typing import Any

from labels import LABELS

SUITE_NAME = "openai-vision-shipping-labels"

# Rules every extraction must satisfy, judged from the output alone.
GLOBAL_ASSERTIONS = [
    "The output has carrier, tracking_number, service_level, ship_date, weight and both "
    "addresses, and none of them is null or empty (region may be empty for countries without one)",
    "ship_date is in YYYY-MM-DD format and weight_unit is one of lb, kg or oz",
    "The tracking number is a transcription of printed characters, not a placeholder "
    "like 'N/A', 'unknown' or a run of repeated digits",
]

# Judge flakiness: each label is extracted and judged three times, and it
# passes when at least two of the three runs pass.
EXECUTION_POLICY = {"runs_per_item": 3, "pass_threshold": 2}


def _fmt(addr: dict[str, str]) -> str:
    region = f" {addr['region']}" if addr["region"] else ""
    return f"{addr['name']}, {addr['street']}, {addr['city']}{region} {addr['postal_code']}, {addr['country']}"


def assertions_for(spec: dict[str, Any]) -> list[str]:
    """Expected values for one label, as sentences an LLM judge can grade."""
    w = spec["weight"]
    weight = f"The weight is {w['value']:g} {w['unit']}"
    if "printed_weight" in spec:
        p = spec["printed_weight"]
        weight += f" (the handwritten correction; the struck-through printed {p['value']:g} {p['unit']} is wrong)"
    return [
        f"The carrier is {spec['carrier']}, the service level is {spec['service_level']} "
        f"and the ship date is {spec['ship_date']}",
        f"The tracking number is {spec['tracking_number']} (differences in spacing are fine, any other "
        "differing character is a failure)",
        weight,
        f"The recipient is {_fmt(spec['recipient'])} and the sender is {_fmt(spec['sender'])} "
        "(minor abbreviation or capitalization differences are fine)",
    ]


def build_items() -> list[dict[str, Any]]:
    """One suite item per label. `data` is what the task receives."""
    return [
        {
            "data": {"image": f"labels/{spec['id']}.png", "kind": spec["defect"] or "clean"},
            "assertions": assertions_for(spec),
        }
        for spec in LABELS
    ]
