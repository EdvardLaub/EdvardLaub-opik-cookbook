"""Offline tests: no provider keys, no Opik. OTEL_SDK_DISABLED makes the tracing a no-op."""
import os

os.environ["OTEL_SDK_DISABLED"] = "true"  # OpenTelemetry's own switch: spans become no-ops

from fastapi.testclient import TestClient  # noqa: E402

from brewfaq import server, telemetry  # noqa: E402
from brewfaq.corpus import Chunk, load_chunks, split_markdown  # noqa: E402
from brewfaq.rag import Hit, cosine, format_context, rank  # noqa: E402


def test_split_markdown_makes_one_chunk_per_section():
    md = "# Title\n\n## One\nalpha\n\n## Two\nbeta\n"
    chunks = split_markdown("x.md", md)
    assert [c.heading for c in chunks] == ["One", "Two"]
    assert chunks[0].text.startswith("Title - One")


def test_guide_loads_all_five_chapters():
    chunks = load_chunks()
    assert len({c.source for c in chunks}) == 5
    assert any("66 C" in c.text for c in chunks)


def test_rank_orders_by_cosine():
    vecs = [[1, 0], [0, 1], [0.9, 0.1]]
    assert [i for i, _ in rank([1, 0], vecs, 2)] == [0, 2]
    assert cosine([0, 0], [1, 1]) == 0.0


def test_format_context_numbers_excerpts():
    hits = [Hit(Chunk("a.md", "h", "text A"), 0.9), Hit(Chunk("b.md", "h", "text B"), 0.8)]
    assert format_context(hits).startswith("[1] (a.md) text A\n\n[2] (b.md)")


def test_capture_content_follows_the_env_var(monkeypatch):
    name = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
    monkeypatch.delenv(name, raising=False)
    assert telemetry.capture_content() is False
    monkeypatch.setenv(name, "span_only")
    assert telemetry.capture_content() is True


class StubRag:
    def retrieve(self, q, k=3):
        return [Hit(Chunk("01-mashing.md", "Strike water", "mash at 66 C"), 0.9)]

    def generate(self, q, hits):
        return "Mash at 66 C."


def test_traced_endpoint_works_with_telemetry_disabled():
    # /ask goes through the root-span helper and the retrieve span; with the SDK disabled it must not break
    server.app.state.rag = StubRag()
    r = TestClient(server.app).post("/ask", json={"question": "Mash temperature?"})
    assert r.status_code == 200
    assert r.json() == {"answer": "Mash at 66 C.", "sources": ["01-mashing.md"]}
