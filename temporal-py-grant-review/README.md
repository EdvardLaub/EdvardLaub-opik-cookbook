# temporal-py-grant-review

*A grant application, reviewed by a Temporal workflow whose Opik trace crosses two processes.*

A fictional neighbourhood foundation (the Larkfield Neighbourhood Foundation) reviews community-grant
applications with a durable Temporal workflow: an eligibility check against a charity register (which
times out on its first attempt and succeeds on retry), LLM scoring with `gpt-4o-mini`, and an LLM-written
decision letter. A client process starts each workflow; a separately spawned worker process runs it.

## Run it

1. `cp .env.example .env` and add `OPENAI_API_KEY` (or rely on the repo-root `.env`).
2. `uv run python -m grantreview` starts a local Temporal dev server on port 4240 (downloaded on first
   run, no Docker), spawns the worker, reviews three applications and prints the letters.
3. Open project `temporal-py-grant-review` in Opik at http://localhost:5173.

Offline tests: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`.

## Files

- `grantreview/workflows.py`, `activities.py`, `llm.py` - the review and its three activities.
- `grantreview/worker.py`, `demo.py` - the worker process and the self-contained client entry point.
- `grantreview/tracing.py` - OpenTelemetry export to Opik, shared by both processes.
- `tests/test_app.py` - rules, retry behaviour, score parsing and a traced call with tracing off.

*built with Opik · inspired by Opik's examples and documentation*
