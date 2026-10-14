"""Offline tests: no provider keys, Opik tracking disabled (OPIK_TRACK_DISABLE=true)."""

from types import SimpleNamespace

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from postmortem.checks import score_postmortem
from postmortem.corpus import load_corpus, search
from postmortem.costs import cost_by_agent
from postmortem.team import EvidenceQuestion, InvestigationPlan, build_graph, format_notes


def test_corpus_has_four_sources():
    assert {e["source"] for e in load_corpus()} == {"alerts.md", "chat.md", "deploys.md", "logs.md"}


def test_search_finds_the_bad_deploy():
    top = search(load_corpus(), "which deploy changed the database pool size", k=2)
    assert any("r4411" in e["text"] for e in top)


def test_traced_search_runs_with_tracking_disabled():
    from postmortem.tracing import make_retrieve

    hits = make_retrieve()("rollback approval delay")  # an @opik.track function is still a plain call
    assert hits and all({"source", "text"} <= h.keys() for h in hits)


class ScriptedModel(FakeListChatModel):
    """Fake chat model that also supports with_structured_output for the planner."""

    def with_structured_output(self, schema, **kw):
        qs = [EvidenceQuestion(question=q, search_terms=q) for q in ("q1", "q2")]
        return SimpleNamespace(invoke=lambda msgs: InvestigationPlan(questions=qs))


def test_graph_loops_once_per_question():
    llm = ScriptedModel(responses=["answer", "answer", "the post-mortem"])
    app = build_graph(llm, retrieve=lambda q: [{"source": "logs.md", "text": "x"}]).compile()
    out = app.invoke({"incident": "outage"})
    assert len(out["findings"]) == 2 and out["postmortem"] == "the post-mortem"
    assert "### q1" in format_notes(out["findings"])


def test_score_postmortem():
    good = "Root cause: db.pool.maxConnections went from 100 to 10. Canary skipped; rollback approval slow; no pool alert."
    s = score_postmortem(good)
    assert s["root_cause_named"] == 1.0 and s["contributing_factors"] == 1.0 and s["blameless"] == 1.0
    assert score_postmortem("It reduced the maximum database connections from 100 to 10.")["root_cause_named"] == 1.0
    assert score_postmortem("It lowered minIdle from 20 to 10.")["root_cause_named"] == 0.0
    assert score_postmortem("The engineer should have caught it.")["blameless"] == 0.0


def test_cost_rolls_up_to_agents():
    def span(id, name, type, parent=None, cost=None, tokens=None):
        return SimpleNamespace(id=id, name=name, type=type, parent_span_id=parent,
                               total_estimated_cost=cost, usage={"total_tokens": tokens} if tokens else None)

    spans = [
        span("p", "planner", "general"), span("p1", "RunnableSequence", "general", "p"),
        span("p2", "ChatOpenAI", "llm", "p1", 0.001, 100),
        span("i1", "investigator", "general"), span("i1l", "ChatOpenAI", "llm", "i1", 0.002, 200),
        span("i2", "investigator", "general"), span("i2l", "ChatOpenAI", "llm", "i2", 0.003, 300),
        span("w", "writer", "general"), span("wl", "ChatOpenAI", "llm", "w", 0.01, 900),
    ]
    out = cost_by_agent(spans)
    assert out["investigator"] == {"passes": 2, "llm_calls": 2, "tokens": 500, "cost": 0.005}
    assert out["planner"]["cost"] == 0.001 and out["writer"]["tokens"] == 900


def test_recovery_search_terms_reach_the_rollback_evidence():
    # The prose question retrieved r4409 and early chat; the evidence vocabulary finds the rollback.
    prose = "What obstacles did the team encounter during the recovery process that delayed the restoration?"
    terms = "rollback approval approver deployctl phone second platform lead"
    corpus = load_corpus()
    texts = lambda q: " ".join(e["text"] for e in search(corpus, q))
    assert "Rollback rolling" not in texts(prose)
    assert "Rollback rolling" in texts(terms)
