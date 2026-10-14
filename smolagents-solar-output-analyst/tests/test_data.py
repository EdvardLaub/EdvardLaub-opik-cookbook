from solar_analyst.data import briefing


def test_csv_shape(df):
    assert len(df) == 4 * 120
    assert set(df.columns) >= {"date", "array", "capacity_kw", "kwh", "outage_hours"}


def test_briefing_names_file_and_arrays():
    text = briefing()
    assert "solar_garden_daily.csv" in text
    assert "Barn Roof" in text and "2026-03-01" in text
