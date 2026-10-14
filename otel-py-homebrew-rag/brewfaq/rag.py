"""Embed the chunks once, retrieve by cosine similarity, answer with a chat model."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

from openai import OpenAI

from .corpus import Chunk

CHAT_MODEL = os.getenv("BREWFAQ_CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("BREWFAQ_EMBED_MODEL", "text-embedding-3-small")
TOP_K = 3

SYSTEM_PROMPT = (
    "You are the Hollowbrook home-brewing FAQ assistant. Answer using ONLY the "
    "numbered excerpts from the Hollowbrook guide. Give temperatures in Celsius "
    "with Fahrenheit in brackets when the excerpt has it. If the excerpts do not "
    "contain the answer, say you don't know. Keep it under 80 words."
)


@dataclass
class Hit:
    chunk: Chunk
    score: float


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def rank(query_vec: list[float], vectors: list[list[float]], k: int) -> list[tuple[int, float]]:
    """Indices and scores of the k vectors closest to query_vec, best first."""
    scored = [(i, cosine(query_vec, v)) for i, v in enumerate(vectors)]
    return sorted(scored, key=lambda t: t[1], reverse=True)[:k]


def format_context(hits: list[Hit]) -> str:
    return "\n\n".join(
        f"[{i}] ({h.chunk.source}) {h.chunk.text}" for i, h in enumerate(hits, start=1)
    )


class BrewRag:
    def __init__(self, chunks: list[Chunk], client: OpenAI | None = None):
        self.client = client or OpenAI()
        self.chunks = chunks
        self.vectors: list[list[float]] = []

    def build_index(self) -> None:
        resp = self.client.embeddings.create(
            model=EMBED_MODEL, input=[c.text for c in self.chunks]
        )
        self.vectors = [d.embedding for d in resp.data]

    def retrieve(self, question: str, k: int = TOP_K) -> list[Hit]:
        resp = self.client.embeddings.create(model=EMBED_MODEL, input=question)
        top = rank(resp.data[0].embedding, self.vectors, k)
        return [Hit(self.chunks[i], score) for i, score in top]

    def generate(self, question: str, hits: list[Hit]) -> str:
        resp = self.client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Excerpts:\n{format_context(hits)}\n\nQuestion: {question}",
                },
            ],
        )
        return resp.choices[0].message.content or ""

    def ask(self, question: str) -> tuple[str, list[Hit]]:
        hits = self.retrieve(question)
        return self.generate(question, hits), hits
