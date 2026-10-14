"""Offline tests: no provider keys, no Opik server. Run with tracking disabled."""

import re
import zlib
from types import SimpleNamespace

from langchain_core.embeddings import Embeddings

from boating_rag.corpus import load_chunks
from boating_rag.evaluation import DATASET_ITEMS, make_task
from boating_rag.graph import build_graph, format_prompt
from boating_rag.retriever import build_retriever, search


class HashEmbeddings(Embeddings):
    """Bag-of-words vectors from hashed tokens: deterministic and offline."""

    def _vec(self, text: str) -> list[float]:
        vec = [0.0] * 256
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vec[zlib.crc32(word.encode()) % 256] += 1.0
        return vec

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class StubLLM:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content="stub answer")


def test_corpus_splits_one_chunk_per_section():
    chunks = load_chunks()
    assert len(chunks) >= 20
    assert all(c.startswith("# ") and "\n\n## " in c for c in chunks)


def test_retriever_finds_the_right_section():
    retriever = build_retriever(HashEmbeddings(), k=2)
    top = search(retriever, "children under 13 must wear a life jacket in the cabin")
    assert len(top) == 2
    assert "## Children" in top[0]


def test_prompt_puts_excerpts_in_system_and_question_in_user():
    messages = format_prompt("Who gives way?", ["chunk A", "chunk B"])
    assert messages[0][0] == "system" and "chunk A" in messages[0][1] and "chunk B" in messages[0][1]
    assert messages[1] == ("user", "Who gives way?")


def test_traced_graph_runs_with_tracking_disabled():
    # build_graph wraps the graph with OpikTracer; with OPIK_TRACK_DISABLE=true
    # it must still behave like a plain graph.
    llm = StubLLM()
    app = build_graph(retriever=build_retriever(HashEmbeddings(), k=3), llm=llm)
    result = app.invoke({"question": "What is the harbor speed limit?"})
    assert result["answer"] == "stub answer"
    assert len(result["context"]) == 3
    assert any("5 knots" in c for c in result["context"])
    assert "What is the harbor speed limit?" == llm.messages[1][1]


def test_eval_task_returns_judge_fields():
    fake_app = SimpleNamespace(invoke=lambda s: {"answer": "A", "context": ["c1"]})
    out = make_task(fake_app)({"question": "Q?"})
    assert out == {"output": "A", "context": ["c1"]}


def test_dataset_items_are_complete():
    assert len(DATASET_ITEMS) >= 6
    assert all(i["question"] and i["expected_output"] for i in DATASET_ITEMS)
