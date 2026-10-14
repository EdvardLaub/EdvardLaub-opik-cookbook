"""The RAG graph: retrieve -> generate."""

from typing_extensions import TypedDict

import opik
from langchain_openai import ChatOpenAI
from opik.integrations.langchain import OpikTracer, track_langgraph
from langgraph.graph import END, START, StateGraph

from boating_rag.retriever import build_retriever, search

SYSTEM_PROMPT = (
    "You are the Harbor Authority boating-safety assistant. Answer using only "
    "the handbook excerpts below. If the excerpts do not cover the question, "
    "say you don't know. Be concise.\n\n"
)


PROJECT_NAME = "langgraph-boating-safety-rag"


class State(TypedDict):
    question: str
    context: list[str]
    answer: str


def format_prompt(question: str, context: list[str]) -> list[tuple[str, str]]:
    """Build the chat messages: excerpts in the system prompt, question as user."""
    return [
        ("system", SYSTEM_PROMPT + "\n\n---\n\n".join(context)),
        ("user", question),
    ]


def build_graph(retriever=None, llm=None):
    """Compile the two-node graph. Both dependencies can be stubbed in tests."""
    retriever = retriever or build_retriever()
    llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def retrieve(state: State) -> dict:
        return {"context": search(retriever, state["question"])}

    def generate(state: State) -> dict:
        reply = llm.invoke(format_prompt(state["question"], state["context"]))
        return {"answer": reply.content}

    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    # track_langgraph attaches an OpikTracer to the compiled graph once: every
    # invoke() becomes one trace, with the retrieve / generate nodes and the
    # ChatOpenAI call as nested spans (llm span carries tokens and cost).
    tracer = OpikTracer(project_name=PROJECT_NAME)
    return track_langgraph(graph.compile(), tracer)
