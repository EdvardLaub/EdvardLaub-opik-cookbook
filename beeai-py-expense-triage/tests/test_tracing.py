from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from expense_triage.tracing import OpikSpanTuner, opik_otlp_settings


class Capture(SpanExporter):
    def __init__(self):
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS


def test_tuner_drops_token_noise_and_adds_provider_attributes():
    sink = Capture()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(OpikSpanTuner(sink)))
    tracer = provider.get_tracer("t")
    with tracer.start_as_current_span("ReAct"):
        with tracer.start_as_current_span("new_token"):
            pass
        with tracer.start_as_current_span(
            "OpenAIChatModel",
            attributes={
                "openinference.span.kind": "LLM",
                "llm.provider": "openai",
                "llm.model_name": "gpt-4o-mini",
                "llm.token_count.prompt": 100,
                "llm.token_count.completion": 20,
            },
        ):
            pass
    names = [s.name for s in sink.spans]
    assert "new_token" not in names and names == ["OpenAIChatModel", "ReAct"]
    llm = sink.spans[0].attributes
    assert llm["gen_ai.system"] == "openai" and llm["gen_ai.usage.input_tokens"] == 100
    assert llm["gen_ai.request.model"] == "gpt-4o-mini" and llm["gen_ai.usage.output_tokens"] == 20


def test_otlp_settings_route_to_the_project(monkeypatch):
    monkeypatch.setenv("OPIK_URL_OVERRIDE", "http://localhost:5173/api/")
    monkeypatch.setenv("OPIK_WORKSPACE", "default")
    monkeypatch.delenv("OPIK_API_KEY", raising=False)
    url, headers = opik_otlp_settings("demo")
    assert url == "http://localhost:5173/api/v1/private/otel/v1/traces"
    assert headers["projectName"] == "demo" and headers["Comet-Workspace"] == "default"
