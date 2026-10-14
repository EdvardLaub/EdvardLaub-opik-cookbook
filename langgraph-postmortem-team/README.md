# langgraph-postmortem-team

A planner, a looping investigator and a writer draft a blameless post-mortem for a fictional SaaS outage, traced with Opik.

Run it with `uv sync && uv run main.py` (keys come from the repo-root `.env`), then open the `langgraph-postmortem-team` project in Opik. Tests: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`.
