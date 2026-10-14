# pydantic-ai-lost-and-found-intake

*Messy desk notes in, typed records out, and a test suite that tells you when the model made something up.*

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat)
![Pydantic AI](https://img.shields.io/badge/pydantic--ai-2.x-E92063?style=flat)
![Opik](https://img.shields.io/badge/Opik-2.2.100-2f54eb?style=flat)

At the fictional Marlowe Hall concert venue, ushers, bartenders and cloakroom staff scribble
notes about things people leave behind: "glasses. tortoiseshell frames. thats all i know -- night
shift". An LLM can turn these into tidy database rows, and that is exactly the danger: a tidy
row looks right whether the values came from the note or from the model's imagination. This
example logs the notes into a typed `FoundItemRecord`, traces every call into Opik, and
checks the records two ways so invented values show up as failures.

## What you'll build

- `lostfound/` is a small package: `models.py` (the record), `agent.py` (a Pydantic AI agent on
  `gpt-4o-mini`), `notes.py` (six fictional notes), `grounding.py` (an offline word-level check),
  `tracing.py` (the OpenTelemetry setup), `suite.py` (the Opik test suite) and `cli.py`.
- A CLI with three subcommands: `extract "<note>"`, `intake` (all six notes, with grounding
  flags) and `suite` (the Opik test suite).
- Tracing goes through the Logfire/OpenTelemetry bridge into Opik's OTLP endpoint. Pydantic AI
  has no Opik callback, so the agent emits OTel spans and Opik ingests them.
- A test suite of plain-language assertions: four rules for every record, plus two or three
  expectations per note. Every note runs three times (`runs_per_item=3`, pass if 2 of 3 pass).

## See it in Opik

Run `uv run lostfound suite`, then open the project **pydantic-ai-lost-and-found-intake**.

- **Traces**: 18 traces (6 notes x 3 runs). Each one is an `evaluation_task` that contains `task`,
  then `intake_note` (your traced function), then `invoke_agent intake_agent`, then
  `chat gpt-4o-mini`. The `chat` span has type `llm` with token usage and an estimated cost
  (about $0.0001 per extraction). The judge's own calls sit beside them as `llm_judge` spans.
- **Test Suites** > `pydantic-ai-lost-and-found-intake` > the experiment `intake-gpt-4o-mini`:
  in my run 5 of 6 items passed (83%). The failing row was the glasses note. The model filed
  "night shift" under `found_when`; the note never says when the glasses were found, so
  the assertion "found_where and found_when are null" failed.
- A whole suite run costs well under a cent in model calls (about $0.008 including the judge).

`uv run lostfound intake` produces six traces named `intake_note` with the same span tree
minus the evaluation wrappers.

## Run it yourself

1. `cd pydantic-ai-lost-and-found-intake && cp .env.example .env` and add `OPENAI_API_KEY`
   (the repo-root `.env` is read too). Local Opik needs no key; Opik Cloud needs `opik configure`
   plus `OPIK_OTLP_ENDPOINT` from `.env.example`.
2. `uv sync`
3. `uv run lostfound intake` to log the six notes and see grounding flags.
4. `uv run lostfound suite` to run the test suite and print the experiment link.
5. `uv run lostfound extract "red scarf by the coat check, handed in by Lena 555-0101"` for one note.

Offline tests (no key, no Opik server):
`env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- Remove "never guess or invent" from `SYSTEM_PROMPT` in `agent.py`, re-run the suite, and
  compare the two experiments.
- Change `MODEL` to a larger model and see whether the glasses note still fails.
- Add a seventh note with a tempting guess (a "Nokia" with no brand written, say) to `notes.py` and
  to `_EXPECTATIONS` in `suite.py`, and watch `lostfound intake` flag the invented word.
- Set `runs_per_item` to 1 and see how much more the pass/fail result jumps between runs.

## Gotchas we hit

- **`UserError: Set the OPENAI_API_KEY environment variable` on import.** Pydantic AI resolves the
  provider when the `Agent` is built, so any import (including your tests) needs a key. Build
  the agent lazily with `Agent(..., defer_model_check=True)`, as `get_agent()` does.
- **Every agent run prints a span tree in the terminal.** `logfire.configure` logs to the console
  by default. Pass `console=False`.
- **Traces split in two, or the agent spans miss the project.** Tracing goes through
  OTel, not `@opik.track`: set the OTLP endpoint and the `Comet-Workspace` and `projectName`
  headers, and add `OpikSpanProcessor` to `logfire.configure` so the agent spans nest under your
  `@opik.track` function. Call `setup_tracing()` before the first agent run, and flush
  with `logfire.force_flush()` plus `opik.flush_tracker()`.
- **The offline grounding check passes a hallucination.** It only checks that every word of a
  value occurs somewhere in the note, so "night shift" in `found_when` goes unflagged (0 of 6 records
  flagged in my `intake` run). Real words in the wrong field need the judge.

## How it's put together

- `lostfound/models.py`: the `FoundItemRecord` Pydantic model.
- `lostfound/agent.py`: the lazily built agent and `intake_note()`.
- `lostfound/notes.py`: the fictional desk notes.
- `lostfound/grounding.py`: `ungrounded_fields()`, the deterministic word-level check.
- `lostfound/tracing.py`: OTLP setup, the `@opik.track` wrapper, flush.
- `lostfound/suite.py`: global and per-item assertions, `run_suite()`.
- `lostfound/cli.py`: the `extract`, `intake` and `suite` subcommands.
- `tests/test_app.py`: stubbed-model tests for the agent, the traced wrapper with tracking
  disabled, grounding, suite data and the CLI.

---
*built with Opik · inspired by Opik's examples and documentation*
