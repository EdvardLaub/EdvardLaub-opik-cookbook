"""The offline evidence: four files in data/, searched by keyword overlap."""

import math
import pathlib
import re

DATA_DIR = pathlib.Path(__file__).parents[1] / "data"

# Question filler that would otherwise look "rare" in a tiny corpus.
STOPWORDS = frozenset(
    "the a an and or of to in for is are was were be been what how why when which "
    "who did does do it its on at by as with from that this there than then after "
    "before during any more most about into not no so".split()
)


def load_corpus(data_dir: pathlib.Path = DATA_DIR) -> list[dict]:
    """One searchable entry per '##' section of every evidence file."""
    entries = []
    for path in sorted(data_dir.glob("*.md")):
        title, *sections = path.read_text().split("\n## ")
        for section in sections:
            entries.append({"source": path.name, "text": f"{title.strip()}\n\n## {section.strip()}"})
    return entries


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


def search(corpus: list[dict], query: str, k: int = 4) -> list[dict]:
    """Rank sections by rarity-weighted overlap with the query terms."""
    docs = [_terms(e["text"]) for e in corpus]

    def idf(term: str) -> float:
        n = sum(term in d for d in docs)
        return math.log(len(docs) / n) + 0.1 if n else 0.0

    q = _terms(query)
    scores = [sum(idf(t) for t in q if t in d) for d in docs]
    ranked = sorted(zip(scores, corpus), key=lambda p: p[0], reverse=True)
    return [e for s, e in ranked[:k] if s > 0]
