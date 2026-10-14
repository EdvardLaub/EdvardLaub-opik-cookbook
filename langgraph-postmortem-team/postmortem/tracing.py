"""Opik wiring for the post-mortem team."""

import opik
from opik.integrations.langchain import OpikTracer, track_langgraph

from .corpus import load_corpus, search

PROJECT_NAME = "langgraph-postmortem-team"


def make_retrieve():
    """Return the evidence search, wrapped so it is always recorded in the trace."""
    corpus = load_corpus()

    # A named tool span under the investigator node, with the question in and the matched
    # sections out. Plain functions are invisible to OpikTracer; this also keeps retrieval
    # visible should the tracer drop a LangChain retriever run.
    @opik.track(name="search_evidence", type="tool", project_name=PROJECT_NAME)
    def search_evidence(query: str) -> list[dict]:
        return search(corpus, query)

    return search_evidence


def trace_graph(compiled):
    """Wrap a compiled graph so each invoke is one Opik trace, and return (app, tracer)."""
    # track_langgraph attaches the tracer to every invoke and records the graph's structure on
    # the trace, which powers the agent-graph view (the investigator self-loop included). Each
    # node pass becomes a span with its ChatOpenAI llm span (tokens, cost) nested inside.
    tracer = OpikTracer(project_name=PROJECT_NAME, tags=["postmortem"])
    return track_langgraph(compiled, tracer), tracer
