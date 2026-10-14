"""Offline checks for the Opik tracing layer: no provider keys, no Opik server."""

from types import SimpleNamespace

from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage
from smolagents import CodeAgent, OpenAIModel

from solar_analyst.tracing import OpikAttributeFixer, opik_otlp_settings


class FakeCompletions:
    """Replies with a fixed code block that answers at once, with fixed token usage."""

    def create(self, **kwargs):
        msg = ChatCompletionMessage(role="assistant", content='Thought: done.\n<code>\nfinal_answer("ok")\n</code>')
        return ChatCompletion(
            id="c1", created=0, model="gpt-4o-mini", object="chat.completion",
            choices=[Choice(index=0, finish_reason="stop", message=msg)],
            usage=CompletionUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
        )


def stub_model() -> OpenAIModel:
    # a real OpenAIModel (the class the instrumentor wraps) whose client never touches the network
    model = OpenAIModel(model_id="gpt-4o-mini", api_key="not-a-real-key")
    model.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    return model


def test_instrumented_agent_runs_with_a_stub_model_and_attributes_are_fixed():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(OpikAttributeFixer(exporter)))
    SmolagentsInstrumentor().instrument(tracer_provider=provider)
    try:
        # the instrumented agent.run works offline and tracing doesn't change its answer
        assert CodeAgent(tools=[], model=stub_model()).run("hi") == "ok"
    finally:
        SmolagentsInstrumentor().uninstrument()

    spans = exporter.get_finished_spans()
    llm = [s for s in spans if s.attributes.get("openinference.span.kind") == "LLM"]
    agent = [s for s in spans if s.attributes.get("openinference.span.kind") == "AGENT"]
    assert llm and agent
    # llm spans carry the gen_ai.* attributes Opik prices from; the agent span no longer repeats tokens
    assert llm[0].attributes["gen_ai.usage.input_tokens"] == 100
    assert llm[0].attributes["gen_ai.usage.output_tokens"] == 20
    assert not any(k.startswith("llm.token_count") for k in agent[0].attributes)


def test_otlp_settings_route_to_the_project(monkeypatch):
    monkeypatch.setenv("OPIK_URL_OVERRIDE", "http://localhost:5173/api/")
    monkeypatch.setenv("OPIK_WORKSPACE", "default")
    monkeypatch.delenv("OPIK_API_KEY", raising=False)
    url, headers = opik_otlp_settings("demo-project")
    assert url == "http://localhost:5173/api/v1/private/otel/v1/traces"
    assert headers == {"Comet-Workspace": "default", "projectName": "demo-project"}
