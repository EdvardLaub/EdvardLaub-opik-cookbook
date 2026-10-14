"""The post-mortem team: planner -> investigator (loops) -> writer."""

from typing import Callable

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from .corpus import load_corpus, search


class Finding(TypedDict):
    question: str
    answer: str
    sources: list[str]


class TeamState(TypedDict):
    incident: str
    questions: list[str]
    queries: list[str]
    findings: list[Finding]
    postmortem: str


class EvidenceQuestion(BaseModel):
    question: str = Field(description="A focused evidence question about the incident")
    search_terms: str = Field(
        description="6-10 literal words likely to appear in the logs, deploy notes, alerts or chat "
        "(e.g. deploy, rollback, approver, canary, pool, paged, acked, hypothesis, status page), not words from the question itself"
    )


class InvestigationPlan(BaseModel):
    """The planner's output: the evidence questions the investigators must answer."""

    questions: list[EvidenceQuestion] = Field(description="4 evidence questions")


def build_graph(llm: BaseChatModel, retrieve: Callable[[str], list[dict]] | None = None):
    """Build the (uncompiled) team graph around a chat model and a retrieval function."""
    corpus = load_corpus()
    retrieve = retrieve or (lambda q: search(corpus, q))

    def planner(state: TeamState) -> dict:
        plan = llm.with_structured_output(InvestigationPlan).invoke([
            ("system",
             "You lead a blameless post-mortem for a SaaS outage. The evidence is a set of "
             "log excerpts, a deploy history, an alert timeline and an incident chat "
             "transcript. Write exactly 4 evidence questions that together cover: customer "
             "impact and duration; what changed before impact began; why detection and "
             "diagnosis took as long as they did; and what slowed recovery."),
            ("user", state["incident"]),
        ])
        return {
            "questions": [q.question for q in plan.questions],
            "queries": [q.search_terms for q in plan.questions],
            "findings": [],
        }

    def investigator(state: TeamState) -> dict:
        # One pass per question: the loop the agent graph draws as a self-edge.
        question = state["questions"][len(state["findings"])]
        # Search with the question plus the planner's evidence vocabulary: question prose alone
        # ("obstacles", "restoration") matches nothing in logs and chat and returned the wrong sections.
        hits = retrieve(f"{question} {state['queries'][len(state['findings'])]}")
        excerpts = "\n\n---\n\n".join(f"[{h['source']}]\n{h['text']}" for h in hits)
        answer = llm.invoke([
            ("system",
             "You are an incident investigator. Answer the question using only the evidence "
             "below. Give exact timestamps (UTC) and numbers, and name the source file for "
             "each claim. If the evidence does not answer it, say so.\n\n" + excerpts),
            ("user", question),
        ])
        finding: Finding = {
            "question": question,
            "answer": answer.content,
            "sources": sorted({h["source"] for h in hits}),
        }
        return {"findings": state["findings"] + [finding]}

    def writer(state: TeamState) -> dict:
        notes = format_notes(state["findings"])
        draft = llm.invoke([
            ("system",
             "You write blameless post-mortems. Sections: Summary, Impact, Timeline (UTC), "
             "Root cause, Contributing factors, What went well, Action items. Describe "
             "people only by role (on-call engineer, incident commander), never by name, "
             "and frame causes as gaps in systems and process, not individual mistakes. "
             "List timeline events in chronological order. Use only the notes below, keep every timestamp and number exact. Under 600 words.\n\n"
             + notes),
            ("user", state["incident"]),
        ])
        return {"postmortem": draft.content}

    def route(state: TeamState) -> str:
        return "investigator" if len(state["findings"]) < len(state["questions"]) else "writer"

    graph = StateGraph(TeamState)
    graph.add_node("planner", planner)
    graph.add_node("investigator", investigator)
    graph.add_node("writer", writer)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "investigator")
    graph.add_conditional_edges("investigator", route, {"investigator": "investigator", "writer": "writer"})
    graph.add_edge("writer", END)
    return graph


def format_notes(findings: list[Finding]) -> str:
    return "\n\n".join(
        f"### {f['question']}\n{f['answer']}\n(Sources: {', '.join(f['sources'])})" for f in findings
    )
