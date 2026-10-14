"""Opik tracing for Pydantic AI, through the OpenTelemetry / Logfire bridge.

Pydantic AI has no Opik callback and `@opik.track` cannot see inside it. Instead the
agent emits OpenTelemetry spans (via logfire's instrumentation) and we point the OTLP
exporter at Opik's OTel endpoint.
"""

import configparser
import os
from pathlib import Path
from typing import Any, Callable

PROJECT_NAME = "pydantic-ai-lost-and-found-intake"
LOCAL_OTLP = "http://localhost:5173/api/v1/private/otel"

_configured = False


def _opik_settings() -> tuple[str | None, str]:
    """API key and workspace from env or ~/.opik.config (local Opik has no key)."""
    cfg = configparser.ConfigParser()
    cfg.read(Path.home() / ".opik.config")
    api_key = os.getenv("OPIK_API_KEY") or cfg.get("opik", "api_key", fallback=None)
    workspace = os.getenv("OPIK_WORKSPACE") or cfg.get("opik", "workspace", fallback="default")
    return api_key, workspace


def setup_tracing() -> None:
    """Send Pydantic AI's OTel spans to Opik. Call once, before the first agent run."""
    global _configured
    if _configured:
        return
    api_key, workspace = _opik_settings()

    # OTLP exporter settings. projectName is what routes the spans into the Opik
    # project; it names the destination project. Local Opik needs no Authorization.
    headers = [f"Comet-Workspace={workspace}", f"projectName={PROJECT_NAME}"]
    if api_key:
        headers.insert(0, f"Authorization={api_key}")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", os.getenv("OPIK_OTLP_ENDPOINT", LOCAL_OTLP))
    os.environ.setdefault("OTEL_EXPORTER_OTLP_HEADERS", ",".join(headers))
    os.environ["OTEL_METRICS_EXPORTER"] = "none"
    os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME  # the @opik.track trace goes to the same project

    import logfire
    from opik.integrations.otel import OpikSpanProcessor

    # OpikSpanProcessor attaches the OTel spans to the surrounding @opik.track trace, so
    # one note becomes ONE trace instead of a trace from each side. logfire exports them
    # over OTLP (picked up from the env vars above); send_to_logfire=False keeps the data local.
    logfire.configure(send_to_logfire=False, console=False, additional_span_processors=[OpikSpanProcessor()])
    # Emits invoke_agent and chat <model> spans (with tokens, cost, messages) for every run.
    logfire.instrument_pydantic_ai()
    _configured = True


def traced(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a function in an Opik trace named after it; the agent's OTel spans nest inside."""
    import opik

    return opik.track(name="intake_note", project_name=PROJECT_NAME)(fn)


def flush() -> None:
    """Push everything out before the process exits, or the last spans are lost."""
    import logfire
    import opik

    logfire.force_flush()  # OTel batch exporter: agent and model spans
    opik.flush_tracker()  # Opik SDK queue: the intake_note trace itself
