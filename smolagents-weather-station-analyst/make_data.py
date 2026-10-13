"""Regenerates data/readings.csv (fictional Larkspur Hill station). Deterministic; the CSV is committed."""
import csv, math, random
from datetime import datetime, timedelta

random.seed(7)
start = datetime(2026, 3, 2)
rows = []
for h in range(14 * 24):
    t = start + timedelta(hours=h)
    d, hr = divmod(h, 24)
    temp = 9 + 5 * math.sin((hr - 9) / 24 * 2 * math.pi) + 0.15 * d + random.gauss(0, 0.6)
    hum = max(35, min(98, 72 - 18 * math.sin((hr - 9) / 24 * 2 * math.pi) + random.gauss(0, 4)))
    wind = max(0.5, 11 + 6 * math.sin(d / 2) + random.gauss(0, 3))
    rain = 0.0
    if d in (3, 4) and 6 <= hr <= 16 and random.random() < 0.7:
        rain = round(random.uniform(0.4, 2.2), 1)
    if d == 10 and 14 <= hr <= 19:
        rain = round(random.uniform(0.2, 0.8), 1)
    rows.append([t.strftime("%Y-%m-%d %H:%M"), round(temp, 1), round(hum, 1), round(wind, 1), rain])

# Planted anomalies
for i in range(7 * 24 + 2, 7 * 24 + 32):   # wind sensor stuck at 0.0 for 30 hours (day 8-9)
    rows[i][3] = 0.0
rows[5 * 24 + 15][1] = -99.9               # temperature dropout sentinel
i = next(k for k, r in enumerate(rows) if r[4] >= 1.5 and k > 3 * 24)  # duplicated rainy hour
rows.insert(i + 1, list(rows[i]))

with open("data/readings.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["timestamp", "temp_c", "humidity_pct", "wind_kmh", "rain_mm"]); w.writerows(rows)
print(len(rows), "rows; duplicated:", rows[i][0], rows[i][4])
