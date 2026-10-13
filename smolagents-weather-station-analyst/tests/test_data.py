import csv
import runpy
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "readings.csv"


@pytest.fixture
def regenerated(tmp_path, monkeypatch):
    """Run make_data.py in a scratch folder so the committed CSV is untouched."""
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(ROOT / "make_data.py"))
    return tmp_path / "data" / "readings.csv"


def test_generator_is_deterministic_and_matches_committed_csv(regenerated):
    assert regenerated.read_text() == CSV.read_text()


def test_csv_loads_with_expected_shape():
    df = pd.read_csv(CSV, parse_dates=["timestamp"])
    assert list(df.columns) == ["timestamp", "temp_c", "humidity_pct", "wind_kmh", "rain_mm"]
    assert len(df) == 14 * 24 + 1  # fortnight of hours plus the duplicated row
    assert df.timestamp.min() == pd.Timestamp("2026-03-02 00:00")
    assert df.timestamp.max() == pd.Timestamp("2026-03-15 23:00")


def test_planted_faults_are_present():
    df = pd.read_csv(CSV, parse_dates=["timestamp"])
    # one temperature dropout sentinel, on 7 March at 15:00
    dropout = df[df.temp_c == -99.9]
    assert list(dropout.timestamp) == [pd.Timestamp("2026-03-07 15:00")]
    # wind sensor stuck at 0.0 for 30 straight hours
    assert (df.wind_kmh == 0.0).sum() == 30
    # exactly one rainy hour appears twice (5 March 06:00)
    dupes = df[df.duplicated("timestamp", keep=False)]
    assert len(dupes) == 2
    assert dupes.timestamp.iloc[0] == pd.Timestamp("2026-03-05 06:00")
    assert dupes.rain_mm.iloc[0] >= 1.5
