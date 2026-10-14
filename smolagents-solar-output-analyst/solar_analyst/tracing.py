"""Send the agent's spans to Opik over OpenTelemetry."""

import configparser
import os
from pathlib import Path

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

PROJECT_NAME = "smolagents-solar-output-analyst"
CLOUD_URL = "https://www.comet.com/opik/api/"


def opik_otlp_settings(project: str = PROJECT_NAME) -> tuple[str, dict[str, str]]:
    """OTLP traces URL and headers for Opik (local by default, cloud if OPIK_API_KEY is set).

    Reads OPIK_URL_OVERRIDE / OPIK_WORKSPACE / OPIK_API_KEY from the environment, falling back
    to ~/.opik.config. Never hardcode keys.
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


class OpikAttributeFixer(SpanExporter):
    """Wraps the OTLP exporter and rewrites span attributes just before they leave the process.

    Two problems show up without it (both seen in Opik with the raw OpenInference spans):
    * cost is empty: Opik only prices an llm span that carries gen_ai.* provider/model/usage
      attributes, and OpenInference emits llm.* ones;
    * token usage is double counted: the CodeAgent.run span repeats the totals of its
      model calls, so the trace-level usage is twice the real figure.
    """

    def __init__(self, inner: SpanExporter):
        self.inner = inner

    def export(self, spans):
        return self.inner.export([self._fix(s) for s in spans])

    def shutdown(self):
        self.inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000):
        return self.inner.force_flush(timeout_millis)

    @staticmethod
    def _fix(span: ReadableSpan) -> ReadableSpan:
        attrs = dict(span.attributes or {})
        kind = attrs.get("openinference.span.kind")
        if kind == "LLM":
            # gen_ai.* attributes: Opik maps them to span.provider/model and to prompt_tokens /
            # completion_tokens usage keys, which is what its cost calculator needs.
            attrs["gen_ai.system"] = attrs.get("llm.provider", "openai")
            attrs["gen_ai.request.model"] = attrs.get("llm.model_name", "")
            attrs["gen_ai.usage.input_tokens"] = attrs.get("llm.token_count.prompt", 0)
            attrs["gen_ai.usage.output_tokens"] = attrs.get("llm.token_count.completion", 0)
        else:
            # only llm spans keep token counts, so the trace total is the sum of the model calls
            for key in [k for k in attrs if k.startswith("llm.token_count.")]:
                del attrs[key]
        return ReadableSpan(
            name=span.name, context=span.context, parent=span.parent, resource=span.resource,
            attributes=attrs, events=span.events, links=span.links, kind=span.kind,
            instrumentation_scope=span.instrumentation_scope, status=span.status,
            start_time=span.start_time, end_time=span.end_time,
        )


def setup_tracing(project: str = PROJECT_NAME):
    """Instrument smolagents; returns the TracerProvider so the caller can flush it."""
    # Imported here so tests and `--no-trace` runs don't need the exporter wiring.
    from openinference.instrumentation.smolagents import SmolagentsInstrumentor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider

    url, headers = opik_otlp_settings(project)
    provider = TracerProvider()
    # OTLP exporter -> Opik's OpenTelemetry endpoint: each exported span becomes an Opik span.
    provider.add_span_processor(BatchSpanProcessor(OpikAttributeFixer(OTLPSpanExporter(endpoint=url, headers=headers))))
    # SmolagentsInstrumentor patches CodeAgent/Model/Tool calls: one trace per agent.run, with a
    # span per step, per LLM call and per code execution (the generated code lands in these spans).
    SmolagentsInstrumentor().instrument(tracer_provider=provider)
    return provider
