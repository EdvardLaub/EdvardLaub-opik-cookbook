"""Loading the production CSV and describing it to the agent."""

from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "solar_garden_daily.csv"


def load_production(path: Path = CSV_PATH) -> pd.DataFrame:
    """Daily production, one row per array per day, dates parsed."""
    return pd.read_csv(path, parse_dates=["date"])


def briefing(path: Path = CSV_PATH) -> str:
    """The context prepended to every question: where the file is and what the columns mean."""
    df = load_production(path)
    arrays = ", ".join(sorted(df["array"].unique()))
    return f"""\
You are the data analyst for Larkspur Community Solar Garden.
Daily production data, one row per array per day ({df['date'].min():%Y-%m-%d} to \
{df['date'].max():%Y-%m-%d}), is the CSV file at: {path}

Columns: date, array, capacity_kw, kwh (energy produced that day), cloud_cover_pct,
avg_temp_c (both are site-wide, same for every array on a given day), outage_hours
(hours the array's inverter was logged as down).
Arrays: {arrays}.

Load the file with pandas and answer with concrete numbers computed from it.
Give the final answer as one or two plain sentences, not a raw Python object.
"""
