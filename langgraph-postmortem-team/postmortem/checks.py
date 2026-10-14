"""Cheap rule-based checks that score a drafted post-mortem against the known facts."""

import re

# Facts a correct post-mortem must carry, taken from the evidence in data/.
ROOT_CAUSE = (  # pool max 100 -> 10, not minIdle
    r"(max\w*[ .]?(db\.pool\.)?(database )?connections?|pool (size|limit|maximum)).{0,80}\b100\b.{0,30}\b10\b"
)
CONTRIBUTING = {
    "canary": r"canary",
    "rollback_approval": r"(second|secondary) approver|rollback approval|approval",
    "pool_visibility": r"pool.{0,40}(alert|dashboard|monitor|visib)|(alert|dashboard|monitor).{0,40}pool",
}
BLAME_WORDS = r"\b(fault|blame[sd]?|negligen\w*|careless\w*|incompeten\w*|should have|failed to)\b"


def score_postmortem(text: str) -> dict[str, float]:
    """Return 0/1 scores: root cause named correctly, contributing-factor coverage, blamelessness."""
    low = text.lower()
    root = float(bool(re.search(ROOT_CAUSE, low, re.S)))
    found = sum(bool(re.search(p, low)) for p in CONTRIBUTING.values())
    return {
        "root_cause_named": root,
        "contributing_factors": found / len(CONTRIBUTING),
        "blameless": float(not re.search(BLAME_WORDS, low)),
    }
