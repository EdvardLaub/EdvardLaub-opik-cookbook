"""Use the winning prompt from the Opik prompt library on a brand-new report."""

import opik
from opik.integrations.openai import track_openai
from openai import OpenAI

from scoring import is_valid_label, normalise


def render(messages: list[dict], report: str) -> list[dict]:
    """Fill the library's mustache {{report}} placeholder."""
    return [{**m, "content": m["content"].replace("{{report}}", report)} for m in messages]


# @track makes this one trace; the track_openai-wrapped client adds an llm span
# inside it with token usage and cost, so the call is one readable trace.
@opik.track(name="classify_report")
def classify_report(messages: list[dict], report: str, client=None) -> dict:
    client = client or track_openai(OpenAI())
    resp = client.chat.completions.create(
        model="gpt-4o-mini", messages=render(messages, report), temperature=0
    )
    raw = resp.choices[0].message.content or ""
    return {"label": normalise(raw), "valid": is_valid_label(raw), "raw": raw}
