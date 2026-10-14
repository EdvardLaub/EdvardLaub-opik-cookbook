"""The scripted question set. Each question is aimed at one planted anomaly."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    key: str
    text: str


QUESTIONS = [
    Question(
        "outage",
        "Which array had a multi-day outage, and between which dates? "
        "List the dates on which it produced zero kWh.",
    ),
    Question(
        "underperformer",
        "One array's output dropped relative to its siblings at some point without any "
        "logged outage. Which array, from roughly which date, and by what percentage? "
        "Compare each array's kWh per kW of capacity before and after to account for size, "
        "and mention how weather could be ruled out.",
    ),
    Question(
        "glitch",
        "Is there any daily reading that is physically impossible? An array cannot "
        "produce more than capacity_kw * 24 kWh in a day. Name the array and date.",
    ),
]
