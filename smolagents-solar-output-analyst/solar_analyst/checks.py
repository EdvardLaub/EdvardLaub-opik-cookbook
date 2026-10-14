"""Ground truth for the planted anomalies, and a keyword grader for the agent's answers.

The truth is computed straight from the CSV with plain pandas, so you can compare it with
the pandas the agent wrote (visible in the Opik spans) and see whether the two agree.
"""

import re
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Truth:
    outage_array: str
    outage_start: pd.Timestamp
    outage_end: pd.Timestamp
    drop_array: str
    drop_from: pd.Timestamp
    drop_pct: float
    glitch_array: str
    glitch_date: pd.Timestamp


def ground_truth(df: pd.DataFrame) -> Truth:
    down = df[df["outage_hours"] > 0]
    bad = df[df["kwh"] > df["capacity_kw"] * 24].iloc[0]

    # yield per kW, relative to the same-day mean of the *other* arrays (cancels weather)
    clean = df[(df["outage_hours"] == 0) & (df["kwh"] <= df["capacity_kw"] * 24)].copy()
    clean["yield"] = clean["kwh"] / clean["capacity_kw"]
    wide = clean.pivot(index="date", columns="array", values="yield")
    rel = wide.div((wide.sum(axis=1).values[:, None] - wide) / (wide.notna().sum(axis=1).values[:, None] - 1))
    smooth = rel.rolling(7, min_periods=4).median()
    baseline = rel.iloc[:30].median()
    drop = (smooth.iloc[-1] / baseline - 1).idxmin()
    below = smooth[drop] < 0.9 * baseline[drop]
    return Truth(
        outage_array=down["array"].iloc[0],
        outage_start=down["date"].min(),
        outage_end=down["date"].max(),
        drop_array=drop,
        drop_from=below[below].index[0],
        drop_pct=round(float(100 * (1 - smooth[drop].iloc[-1] / baseline[drop])), 1),
        glitch_array=bad["array"],
        glitch_date=bad["date"],
    )


def _date_forms(d: pd.Timestamp) -> str:
    """A regex matching the usual ways an LLM writes a date: 2026-05-11, May 11, 11 May."""
    mon, day = d.strftime("%B"), d.day
    return rf"{d:%Y-%m-%d}|{mon[:3]}\w*\.? {day}\b|\b{day} {mon[:3]}"


def grade(key: str, answer: str, truth: Truth) -> bool:
    """True if the answer names the right array and the right date(s)."""
    text = str(answer).lower()
    has = lambda pattern: re.search(pattern.lower(), text) is not None  # noqa: E731
    if key == "outage":
        return truth.outage_array.lower() in text and has(_date_forms(truth.outage_start)) and has(
            _date_forms(truth.outage_end)
        )
    if key == "underperformer":
        return truth.drop_array.lower() in text and has(rf"{truth.drop_from:%B}|{truth.drop_from:%b}\b|{truth.drop_from:%Y-%m}")
    if key == "glitch":
        return truth.glitch_array.lower() in text and has(_date_forms(truth.glitch_date))
    raise KeyError(key)
