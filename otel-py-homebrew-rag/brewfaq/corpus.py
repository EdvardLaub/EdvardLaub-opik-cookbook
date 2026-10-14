"""Load the brewing guide from docs/ and split it into one chunk per section."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


@dataclass(frozen=True)
class Chunk:
    source: str  # file name, e.g. "02-fermentation.md"
    heading: str  # the "## ..." section title
    text: str  # chapter title + heading + body, so a chunk stands on its own


def split_markdown(source: str, markdown: str) -> list[Chunk]:
    """Split on '## ' headings; the '# ' title is prepended to every chunk."""
    title = ""
    heading = None
    body: list[str] = []
    chunks: list[Chunk] = []

    def flush() -> None:
        if heading is not None and any(line.strip() for line in body):
            text = f"{title} - {heading}\n" + "\n".join(body).strip()
            chunks.append(Chunk(source, heading, text))

    for line in markdown.splitlines():
        if line.startswith("## "):
            flush()
            heading, body = line[3:].strip(), []
        elif line.startswith("# "):
            title = line[2:].strip()
        else:
            body.append(line)
    flush()
    return chunks


def load_chunks(docs_dir: Path = DOCS_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        chunks.extend(split_markdown(path.name, path.read_text(encoding="utf-8")))
    return chunks
