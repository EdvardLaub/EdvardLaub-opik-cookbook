"""Send the agent's spans to Opik over OpenTelemetry (no Opik decorators in the app code)."""

import configparser
import os
from pathlib import Path

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter

PROJECT_NAME = "beeai-py-expense-triage"
CLOUD_URL = "https://www.comet.com/opik/api/"


def opik_otlp_settings(project: str = PROJECT_NAME) -> tuple[str, dict[str, str]]:
    """OTLP traces URL and headers for Opik (local by default, cloud if OPIK_API_KEY is set).

    Reads OPIK_URL_OVERRIDE / OPIK_WORKSPACE / OPIK_API_KEY from the environment, falling back
    to ~/.opik.config (what `opik configure` writes). Never hardcode keys.
    """
    cfg = configparser.ConfigParser()
    cfg.read(Path.home() / ".opik.config")
    get = lambda key, env: os.getenv(env) or cfg.get("opik", key, fallback="")  # noqa: E731
    base = get("url_override", "OPIK_URL_OVERRIDE") or CLOUD_URL
    headers = {
        "Comet-Workspace": get("workspace", "OPIK_WORKSPACE") or "default",
        # projectName routes every trace to this Opik project instead of "Default Project"
        "projectName": project,
    }
    if api_key := get("api_key", "OPIK_API_KEY"):
        headers["Authorization"] = api_key
    return base.rstrip("/") + "/v1/private/otel/v1/traces", headers


class OpikSpanTuner(SpanExporter):
    """Wraps the OTLP exporter and adjusts spans just before they leave the process.

    Two things look wrong in Opik with the raw OpenInference spans from BeeAI:
    * the ReAct agent streams, and every streamed chunk is its own `new_token` span, so one
      report yields ~250 spans that bury the 4 llm and 3 tool spans worth reading;
    * llm spans carry token counts but no provider, so Opik shows usage and leaves cost empty.
    """

    NOISE = {"new_token"}

    def __init__(self, inner: SpanExporter):
        self.inner = inner

    def export(self, spans):
        return self.inner.export([self._fix(s) for s in spans if s.name not in self.NOISE])

    def shutdown(self):
        self.inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000):
        return self.inner.force_flush(timeout_millis)

    @staticmethod
    def _fix(span: ReadableSpan) -> ReadableSpan:
        attrs = dict(span.attributes or {})
        if attrs.get("openinference.span.kind") == "LLM":
            # gen_ai.system is the attribute Opik maps to span.provider; with provider + model +
            # usage it can price the call (total_estimated_cost). Without it cost stays empty.
            attrs["gen_ai.system"] = attrs.get("llm.provider", "openai")
            attrs["gen_ai.request.model"] = attrs.get("llm.model_name", "")
            attrs["gen_ai.usage.input_tokens"] = attrs.get("llm.token_count.prompt", 0)
            attrs["gen_ai.usage.output_tokens"] = attrs.get("llm.token_count.completion", 0)
        return ReadableSpan(
            name=span.name, context=span.context, parent=span.parent, resource=span.resource,
            attributes=attrs, events=span.events, links=span.links, kind=span.kind,
            instrumentation_scope=span.instrumentation_scope, status=span.status,
            start_time=span.start_time, end_time=span.end_time,
        )


def setup_tracing(project: str = PROJECT_NAME):
    """Instrument BeeAI; returns the TracerProvider so the caller can flush it before exit."""
    from openinference.instrumentation.beeai import BeeAIInstrumentor
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    url, headers = opik_otlp_settings(project)
    provider = TracerProvider()
    # OTLP exporter -> Opik's OpenTelemetry endpoint: every finished OTel span becomes an Opik span.
    provider.add_span_processor(BatchSpanProcessor(OpikSpanTuner(OTLPSpanExporter(endpoint=url, headers=headers))))
    # BeeAIInstrumentor hooks the framework's event emitter: each agent.run becomes one trace
    # with a span per ReAct iteration, per chat-model call and per tool call.
    BeeAIInstrumentor().instrument(tracer_provider=provider)
    # Make it the global provider so the app's own spans (see agent.triage_report) join the same traces.
    trace.set_tracer_provider(provider)
    return provider
