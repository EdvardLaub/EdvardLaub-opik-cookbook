"""Corpus loader: turns the markdown handbook into one chunk per '##' section."""

import pathlib

DATA_DIR = pathlib.Path(__file__).parents[1] / "data"


def load_chunks(data_dir: pathlib.Path = DATA_DIR) -> list[str]:
    """Split each chapter on its '##' headings so one chunk covers one topic.

    Every chunk keeps its chapter title as a prefix so the retriever (and a
    reader of the trace) can tell which chapter it came from.
    """
    chunks = []
    for path in sorted(data_dir.glob("*.md")):
        title, *sections = path.read_text().split("\n## ")
        for section in sections:
            chunks.append(f"{title.strip()}\n\n## {section.strip()}")
    return chunks
