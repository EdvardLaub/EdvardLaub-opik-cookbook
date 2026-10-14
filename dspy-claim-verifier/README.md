# dspy-claim-verifier

A DSPy claim verifier that fails its output contract until `BootstrapFewShot` compiles it, with the before and after run as two Opik test-suite runs.

## Run it yourself

1. `cp .env.example .env` and add `OPENAI_API_KEY` (or use a repo-root `.env`).
2. `uv sync`
3. `uv run main.py` (needs a reachable Opik; the README is completed with the final run in the next commit).
4. Offline tests: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## How it's put together

- `claimcheck.py`: corpus loader, strict answer parser, per-requirement checker, the DSPy signature and program.
- `main.py`: wires OpikCallback, builds the test suite, runs it uncompiled, compiles, runs it again.
- `data/`: fictional science corpus (`corpus.txt`) plus train and held-out test claims.
- `tests/`: offline tests for the parser, checker, metric and a traced call.
