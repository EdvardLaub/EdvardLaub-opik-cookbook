"""Typed field extraction from a shipping-label image with GPT-4o-mini vision."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

HERE = Path(__file__).parent
# Keys live in the repo-root .env (a local .env works too).
load_dotenv(HERE.parent / ".env")
load_dotenv(HERE / ".env")
# Always talk to the public OpenAI API, even if a proxy URL is inherited.
os.environ.pop("OPENAI_BASE_URL", None)

PROJECT_NAME = "openai-vision-shipping-labels"
# Every trace lands in this Opik project (read by the SDK at first use).
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import opik  # noqa: E402
from openai import OpenAI  # noqa: E402
from opik import Attachment, opik_context  # noqa: E402
from opik.integrations.openai import track_openai  # noqa: E402

MODEL = "gpt-4o-mini"
# track_openai wraps the client: every chat completion becomes an llm span
# (with the image prompt, token usage and estimated cost) under the trace.
client = track_openai(OpenAI(), project_name=PROJECT_NAME)

SYSTEM_PROMPT = """\
You read photos and scans of parcel shipping labels and extract typed fields.
Read only what is on the label. Never guess a character you cannot read: if a
value is partly illegible, give your best reading anyway but do not invent
digits to make it look complete.

- carrier: UPS, FedEx, USPS, DHL, or other.
- tracking_number: exactly as printed under the barcode, spaces kept.
- service_level: the service name printed on the label.
- ship_date: normalized to YYYY-MM-DD.
- weight_value and weight_unit (lb, kg or oz): the package weight. If a
  printed weight is struck through and a handwritten one is written beside it,
  the handwritten weight is the real one.
- sender and recipient: name, street, city, region (state/province, empty if
  none), postal_code, country (ISO 3166 alpha-2)."""


def _address_schema() -> dict[str, Any]:
    keys = ["name", "street", "city", "region", "postal_code", "country"]
    return {
        "type": "object",
        "properties": {k: {"type": "string"} for k in keys},
        "required": keys,
        "additionalProperties": False,
    }


FIELDS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "carrier": {"type": "string", "enum": ["UPS", "FedEx", "USPS", "DHL", "other"]},
        "tracking_number": {"type": "string"},
        "service_level": {"type": "string"},
        "ship_date": {"type": "string", "description": "YYYY-MM-DD"},
        "weight_value": {"type": "number"},
        "weight_unit": {"type": "string", "enum": ["lb", "kg", "oz"]},
        "sender": _address_schema(),
        "recipient": _address_schema(),
    },
    "required": [
        "carrier", "tracking_number", "service_level", "ship_date",
        "weight_value", "weight_unit", "sender", "recipient",
    ],
    "additionalProperties": False,
}


# @opik.track makes each call one trace (input = image path, output = fields)
# and gives the llm span above a parent to nest under.
@opik.track(project_name=PROJECT_NAME)
def extract_label(image_path: str) -> dict[str, Any]:
    """One extraction: label PNG in, typed fields out."""
    # Attach the PNG to the trace: the Opik UI shows the exact pixels the
    # model saw next to what it read. Without it the trace only has a path.
    opik_context.update_current_trace(
        attachments=[Attachment(data=image_path, content_type="image/png")],
        metadata={"label_id": Path(image_path).stem},
    )
    image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract the fields from this shipping label."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "high"},
                    },
                ],
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "label_fields", "strict": True, "schema": FIELDS_SCHEMA},
        },
    )
    return json.loads(response.choices[0].message.content)
