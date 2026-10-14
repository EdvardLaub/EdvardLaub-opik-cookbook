"""Deterministic hallucination check: is each extracted value backed by the note?

A word-level test, not a judge: every word of a non-null field must occur in the source
note (accents and case ignored). It is cheap and runs offline. It misses a real word put
in the wrong field (a shift name filed as finder_name), which is why the Opik suite
adds an LLM judge on top.
"""

import re
import unicodedata
from typing import Any

# Fields we hold to the grounding rule. item_type is a label the model may normalise
# ("iPhone" -> "phone"), so it is exempt.
CHECKED_FIELDS = (
    "color",
    "brand",
    "found_where",
    "found_when",
    "finder_name",
    "finder_contact",
    "distinguishing_marks",
)


def _words(text: str) -> set[str]:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return set(re.findall(r"[a-z0-9]+", folded))


def ungrounded_fields(record: dict[str, Any], note: str) -> dict[str, list[str]]:
    """Map field name -> words that appear in the value but nowhere in the note."""
    note_words = _words(note)
    bad: dict[str, list[str]] = {}
    for field in CHECKED_FIELDS:
        value = record.get(field)
        if not value:
            continue
        missing = sorted(_words(str(value)) - note_words)
        if missing:
            bad[field] = missing
    return bad
