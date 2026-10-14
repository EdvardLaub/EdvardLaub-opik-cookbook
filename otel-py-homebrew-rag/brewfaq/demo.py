"""One-command demo: boot the service, ask scripted questions over HTTP, shut it down.

Two passes against the SAME Opik project:
  1. content capture OFF (the instrumentation default): spans arrive, but empty of text
  2. content capture ON: prompts, completions and the trace input/output all land
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time

import httpx

PORT = int(os.getenv("PORT", "4430"))
BASE = f"http://127.0.0.1:{PORT}"

PASS_OFF = ["What temperature should I mash at?"]
PASS_ON = [
    "What temperature should I mash at?",
    "My beer tastes like butterscotch. What went wrong?",
    "How much priming sugar do I need for 20 litres?",
    "Which hop makes the best hazy IPA?",  # not in the guide: the model should say it doesn't know
]

CAPTURE_ENV = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"


def run_pass(label: str, capture: bool, questions: list[str]) -> None:
    env = {**os.environ, "PORT": str(PORT)}
    if capture:
        # Opt in to the newer GenAI conventions and put message content on the spans themselves
        # (the default path emits it as log events, which this app does not export to Opik).
        env["OTEL_SEMCONV_STABILITY_OPT_IN"] = "gen_ai_latest_experimental"
        env[CAPTURE_ENV] = "span_only"
    else:
        env.pop("OTEL_SEMCONV_STABILITY_OPT_IN", None)
        env.pop(CAPTURE_ENV, None)
    print(f"\n=== pass: {label} ===")
    server = subprocess.Popen([sys.executable, "-m", "brewfaq.server"], env=env)
    try:
        for _ in range(120):  # startup embeds the guide first; the port opens only afterwards
            try:  # a bare TCP connect, so readiness probes don't show up as traces in Opik
                socket.create_connection(("127.0.0.1", PORT), timeout=1).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("server did not come up")
        for q in questions:
            r = httpx.post(f"{BASE}/ask", json={"question": q}, timeout=60)
            r.raise_for_status()
            body = r.json()
            print(f"Q: {q}\nA: {body['answer']}\n   sources: {', '.join(body['sources'])}")
    finally:
        # SIGINT = graceful uvicorn shutdown, which runs shutdown_telemetry() and flushes spans.
        server.send_signal(signal.SIGINT)
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()


def main() -> None:
    run_pass("content capture OFF", capture=False, questions=PASS_OFF)
    run_pass("content capture ON", capture=True, questions=PASS_ON)
    print("\nDone. Open the otel-py-homebrew-rag project in Opik.")


if __name__ == "__main__":
    main()
