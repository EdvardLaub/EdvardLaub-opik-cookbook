"""Field-by-field comparison of an extraction against the ground truth in labels.py.

Pure functions, no model and no network: they normalize the way a human
would (spacing and case in tracking numbers, unit conversion for weights)
and then say which fields match.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

TO_KG = {"kg": 1.0, "lb": 0.45359237, "oz": 0.0283495231}
ADDRESS_PARTS = ["name", "street", "city", "postal_code", "country"]
FIELDS = ["carrier", "tracking_number", "service_level", "ship_date", "weight", "sender", "recipient"]


def norm_tracking(value: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", value.upper())


def norm_text(value: str) -> str:
    """Lowercase, fold accents and ß/ss (Straße == Strasse), drop punctuation."""
    folded = unicodedata.normalize("NFKD", value.casefold().replace("ß", "ss"))
    return re.sub(r"[^a-z0-9]", "", folded)


def weight_matches(expected: dict[str, Any], value: Any, unit: Any) -> bool:
    """Same weight after converting to kg, within 2% (so 2.3 kg == 5.07 lb)."""
    if unit not in TO_KG or not isinstance(value, (int, float)):
        return False
    want = expected["value"] * TO_KG[expected["unit"]]
    got = value * TO_KG[unit]
    return abs(got - want) <= 0.02 * want


def address_matches(expected: dict[str, str], got: dict[str, str] | None) -> bool:
    if not isinstance(got, dict):
        return False
    return all(norm_text(expected[p]) == norm_text(str(got.get(p, ""))) for p in ADDRESS_PARTS)


def score_extraction(spec: dict[str, Any], got: dict[str, Any]) -> dict[str, bool]:
    """{field: matched?} for the seven scored fields of one label."""
    return {
        "carrier": got.get("carrier") == spec["carrier"],
        "tracking_number": norm_tracking(got.get("tracking_number", "")) == norm_tracking(spec["tracking_number"]),
        "service_level": norm_text(got.get("service_level", "")) == norm_text(spec["service_level"]),
        "ship_date": got.get("ship_date") == spec["ship_date"],
        "weight": weight_matches(spec["weight"], got.get("weight_value"), got.get("weight_unit")),
        "sender": address_matches(spec["sender"], got.get("sender")),
        "recipient": address_matches(spec["recipient"], got.get("recipient")),
    }
