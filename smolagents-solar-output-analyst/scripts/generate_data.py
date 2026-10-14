"""Regenerate data/solar_garden_daily.csv (deterministic; seed fixed).

Four arrays at the fictional Larkspur Community Solar Garden, 1 Mar - 28 Jun 2026,
one row per array per day. Three anomalies are planted on purpose:

  1. Pond Edge     - inverter outage, 11-16 May: zero output, outage_hours = 24
  2. Barn Roof     - silent ~25% under-performance from 1 May (new neighbour's
                     building shades it), no outage logged, weather unchanged
  3. Hillside Trkr - 9 Apr meter glitch: kwh far above what the array can physically produce
"""

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

ARRAYS = {  # name: (capacity_kw, relative yield)
    "North Meadow": (250, 1.00),
    "Barn Roof": (90, 0.95),
    "Pond Edge": (150, 0.97),
    "Hillside Tracker": (120, 1.22),
}
OUT = Path(__file__).parent.parent / "data" / "solar_garden_daily.csv"


def main() -> None:
    rng = random.Random(2026)
    start, days = date(2026, 3, 1), 120
    rows = []
    for d in range(days):
        day = start + timedelta(days=d)
        # one weather observation per day, shared by all arrays
        cloud = min(100, max(0, int(rng.gauss(35, 28))))
        temp = round(8 + 14 * math.sin(math.pi * d / days) + rng.gauss(0, 2), 1)
        sun_hours = 4.4 + 2.6 * math.sin(math.pi / 2 * d / days)  # lengthening days
        for name, (cap, rel) in ARRAYS.items():
            kwh = cap * sun_hours * 0.82 * rel * (1 - 0.8 * cloud / 100) * rng.uniform(0.96, 1.04)
            outage = 0
            if name == "Barn Roof" and day >= date(2026, 5, 1):
                kwh *= 0.75
            if name == "Pond Edge" and date(2026, 5, 11) <= day <= date(2026, 5, 16):
                kwh, outage = 0.0, 24
            if name == "Hillside Tracker" and day == date(2026, 4, 9):
                kwh = 2950.0
            rows.append([day.isoformat(), name, cap, round(kwh, 1), cloud, temp, outage])
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "array", "capacity_kw", "kwh", "cloud_cover_pct", "avg_temp_c", "outage_hours"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
