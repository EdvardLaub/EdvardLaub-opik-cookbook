"""Opik tracing for Temporal, over OpenTelemetry. Both processes call setup_tracing().

Temporal's TracingInterceptor emits spans for every client call, workflow run and activity
attempt, and carries the trace context inside Temporal's own headers. That is what lets a
span started in the worker process hang under a span started in the client process. Each
process exports its spans to Opik's OTLP endpoint; the shared projectName header makes them
land in one project, where Opik joins them by trace id.
"""

import configparser
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from opentelemetry import trace

PROJECT_NAME = "temporal-py-grant-review"
LOCAL_OTLP = "http://localhost:5173/api/v1/private/otel"

_provider = None


def _opik_settings() -> tuple[str | None, str]:
    """API key and workspace from env or ~/.opik.config (local Opik has no key)."""
    cfg = configparser.ConfigParser()
    cfg.read(Path.home() / ".opik.config")
    api_key = os.getenv("OPIK_API_KEY") or cfg.get("opik", "api_key", fallback=None)
    workspace = os.getenv("OPIK_WORKSPACE") or cfg.get("opik", "workspace", fallback="default")
    return api_key, workspace


def setup_tracing(service_name: str):
    """Install the OTLP exporter for this process and return Temporal's interceptor.

    Pass the result to Client.connect(interceptors=[...]) and Worker(interceptors=[...]).
    """
    global _provider
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from temporalio.contrib.opentelemetry import TracingInterceptor

    api_key, workspace = _opik_settings()
    # projectName routes the spans into the Opik project (the client and the worker must
    # send the same one or the halves of a trace land in different projects). Local Opik
    # takes no Authorization header.
    headers = {"Comet-Workspace": workspace, "projectName": PROJECT_NAME}
    if api_key:
        headers["Authorization"] = api_key
    endpoint = os.getenv("OPIK_OTLP_ENDPOINT", LOCAL_OTLP).rstrip("/") + "/v1/traces"

    _provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers)))
    trace.set_tracer_provider(_provider)
    return TracingInterceptor()


def flush() -> None:
    """Push the batched spans out before the process exits, or the last ones are lost."""
    if _provider is not None:
        _provider.force_flush()


@contextmanager
def request_root(name: str) -> Iterator[None]:
    """Client-side root span. The workflow's spans nest under it via Temporal's headers."""
    with trace.get_tracer("grantreview").start_as_current_span(name):
        yield


@contextmanager
def llm_span(name: str, model: str, messages: list[dict]) -> Iterator[trace.Span]:
    """Record one chat completion as an OTel span carrying gen_ai.* attributes.

    Opik reads these attributes to build an llm span: model, provider and the messages.
    Call record_completion() on the yielded span to add the answer and token usage.
    """
    with trace.get_tracer("grantreview").start_as_current_span(name) as span:
        span.set_attribute("gen_ai.system", "openai")  # a recognised provider lets Opik price the call
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.request.model", model)
        for i, m in enumerate(messages):
            span.set_attribute(f"gen_ai.prompt.{i}.role", m["role"])
            span.set_attribute(f"gen_ai.prompt.{i}.content", m["content"])
        yield span


def record_completion(span: trace.Span, response) -> None:
    """Attach the answer and token usage from an OpenAI response to the llm span."""
    span.set_attribute("gen_ai.response.model", response.model)
    span.set_attribute("gen_ai.completion.0.role", "assistant")
    span.set_attribute("gen_ai.completion.0.content", response.choices[0].message.content or "")
    if response.usage:
        span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", response.usage.completion_tokens)
