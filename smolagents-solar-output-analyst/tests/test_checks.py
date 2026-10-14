import pandas as pd

from solar_analyst.checks import grade, ground_truth


def test_ground_truth_finds_the_planted_anomalies(df):
    t = ground_truth(df)
    assert t.outage_array == "Pond Edge"
    assert (t.outage_start, t.outage_end) == (pd.Timestamp("2026-05-11"), pd.Timestamp("2026-05-16"))
    assert t.drop_array == "Barn Roof" and t.drop_from.month == 5
    assert 20 < t.drop_pct < 30
    assert (t.glitch_array, t.glitch_date) == ("Hillside Tracker", pd.Timestamp("2026-04-09"))


def test_grade_accepts_common_date_formats(df):
    t = ground_truth(df)
    assert grade("outage", "Pond Edge was down from May 11 to May 16, 2026.", t)
    assert grade("outage", "pond edge: 2026-05-11 through 2026-05-16", t)
    assert grade("glitch", "Hillside Tracker on April 9 read 2950 kWh", t)
    assert grade("underperformer", "Barn Roof dropped about 25% from May", t)


def test_grade_rejects_wrong_array_or_dates(df):
    t = ground_truth(df)
    assert not grade("outage", "North Meadow was down May 11 to May 16", t)
    assert not grade("outage", "Pond Edge was down in March", t)
    assert not grade("glitch", "Hillside Tracker misread on 2026-04-10", t)
