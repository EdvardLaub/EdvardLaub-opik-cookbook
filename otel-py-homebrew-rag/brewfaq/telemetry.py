"""OpenTelemetry setup: SDK + OTLP/HTTP exporter pointed at Opik + OpenAI auto-instrumentation."""
from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

OPIK_OTLP = "http://localhost:5173/api/v1/private/otel"
PROJECT = "otel-py-homebrew-rag"

_provider: TracerProvider | None = None
_roots: dict[int, object] = {}  # trace_id -> the still-open root span


class _RootTracker(SpanProcessor):
    """Remember each trace's open root span so request code can write input/output onto it.

    FastAPI emits its own root span ("POST /ask"). Opik fills the TRACE's Input/Output from
    the root span's attributes, so they must be set on that span, not on a child.
    """

    def on_start(self, span, parent_context=None):
        if span.parent is None:
            _roots[span.context.trace_id] = span

    def on_end(self, span):
        if span.parent is None:
            _roots.pop(span.context.trace_id, None)


def capture_content() -> bool:
    """Mirror the instrumentation's content switch so our own spans obey the same policy."""
    v = os.getenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "").strip().lower()
    return v not in ("", "false", "0", "no_content")


def set_trace_io(question: str | None = None, answer: str | None = None) -> None:
    """Put the question/answer on the root span -> Opik trace Input/Output (only if capture is on)."""
    root = _roots.get(trace.get_current_span().get_span_context().trace_id)
    if root is None:
        return
    if not capture_content():
        root.set_attribute("brewfaq.content_capture", "off")
        return
    root.set_attribute("brewfaq.content_capture", "on")
    if question is not None:
        root.set_attribute("input", question)
    if answer is not None:
        root.set_attribute("output", answer)


def setup_telemetry() -> TracerProvider:
    global _provider
    if _provider:
        return _provider
    base = os.getenv("OPIK_OTLP_ENDPOINT", OPIK_OTLP).rstrip("/")
    # projectName routes every span to this Opik project; Comet-Workspace picks the workspace.
    # (Opik Cloud would also need an Authorization header; local Opik needs none.)
    headers = {
        "projectName": os.getenv("OPIK_PROJECT_NAME", PROJECT),
        "Comet-Workspace": os.getenv("OPIK_WORKSPACE", "default"),
    }
    # Opik's OTLP endpoint takes HTTP/protobuf (not gRPC) on the /v1/traces path.
    exporter = OTLPSpanExporter(endpoint=f"{base}/v1/traces", headers=headers)
    provider = TracerProvider(resource=Resource.create({"service.name": "brewfaq"}))
    provider.add_span_processor(_RootTracker())
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    # Auto-instrumentation wraps openai: every chat/embeddings call becomes a span with
    # gen_ai.* attributes, which Opik maps to llm spans with model and token usage.
    OpenAIInstrumentor().instrument()
    _provider = provider
    return provider


def shutdown_telemetry() -> None:
    # BatchSpanProcessor buffers; without a flush the last spans are lost on exit.
    if _provider:
        _provider.shutdown()
