"""The intake agent: one Pydantic AI Agent with FoundItemRecord as its output type."""

from functools import lru_cache
from typing import Any

from pydantic_ai import Agent

from .models import FoundItemRecord

MODEL = "openai:gpt-4o-mini"

SYSTEM_PROMPT = (
    "You log items handed in at the Marlowe Hall concert venue lost-and-found desk. "
    "Notes are scribbled by ushers, bartenders and cloakroom staff. Fill in only what "
    "the note actually says. If a field is not stated, leave it null; never guess or "
    "invent a color, brand, name or contact."
)



@lru_cache(maxsize=1)
def get_agent() -> Agent:
    """Built lazily; defer_model_check skips the provider-key check so tests need no API key."""
    return Agent(MODEL, output_type=FoundItemRecord, system_prompt=SYSTEM_PROMPT, defer_model_check=True, name="intake_agent")


def intake_note(note: str) -> dict[str, Any]:
    """One extraction: desk note in, typed record (as a dict) out."""
    return get_agent().run_sync(note).output.model_dump()
