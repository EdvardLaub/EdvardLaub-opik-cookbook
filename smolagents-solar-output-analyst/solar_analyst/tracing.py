"""Send the agent's spans to Opik over OpenTelemetry."""

import configparser
import os
from pathlib import Path

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


def setup_tracing(project: str = PROJECT_NAME):
    """Instrument smolagents; returns the TracerProvider so the caller can flush it."""
    # Imported here so tests and `--no-trace` runs don't need the exporter wiring.
    from openinference.instrumentation.smolagents import SmolagentsInstrumentor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    url, headers = opik_otlp_settings(project)
    provider = TracerProvider()
    # OTLP exporter -> Opik's OpenTelemetry endpoint: each exported span becomes an Opik span.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=url, headers=headers)))
    # SmolagentsInstrumentor patches CodeAgent/Model/Tool calls: one trace per agent.run, with a
    # span per step, per LLM call and per code execution (the generated code lands in these spans).
    SmolagentsInstrumentor().instrument(tracer_provider=provider)
    return provider
