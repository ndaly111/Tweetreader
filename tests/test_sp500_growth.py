import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sp500_growth import (
    HistoricalSeries,
    calculate_implied_growth,
    load_historical_data,
    run_pipeline,
    upsert_implied_growth,
)


def test_load_historical_data_merges_multiple_csvs(tmp_path: Path) -> None:
    (tmp_path / "pe.csv").write_text("""date,pe_ratio\n2024-01-01,20\n2024-01-02,22\n""")
    (tmp_path / "rates.csv").write_text("""date,treasury_yield\n2024-01-01,4.5\n2024-01-02,4.6\n""")

    series = load_historical_data(tmp_path)

    assert list(series.data.columns) == ["date", "pe_ratio", "risk_free_rate"]
    assert len(series.data) == 2
    assert series.data.iloc[0]["pe_ratio"] == 20
    assert series.data.iloc[1]["risk_free_rate"] == 4.6


def test_calculate_implied_growth_handles_decimal_rates() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "pe_ratio": [20.0, 21.0],
            "risk_free_rate": [0.045, 0.047],
        }
    )

    growth = calculate_implied_growth(HistoricalSeries(df))
    values = growth.data["implied_growth"].tolist()

    # Rates are in decimal form, so the helper should scale them to percent first.
    assert values == [20.0 - 4.5, 21.0 - 4.7]


def test_upsert_implied_growth_persists_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "spy.sqlite"
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "pe_ratio": [22.0, 21.5],
            "risk_free_rate": [4.2, 4.1],
            "implied_growth": [17.8, 17.4],
        }
    )
    written = upsert_implied_growth(db_path, HistoricalSeries(df))

    assert written == 2

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT date, implied_growth, pe_ratio, risk_free_rate FROM implied_growth ORDER BY date").fetchall()

    assert rows == [
        ("2024-01-01", 17.8, 22.0, 4.2),
        ("2024-01-02", 17.4, 21.5, 4.1),
    ]


def test_run_pipeline_end_to_end(tmp_path: Path) -> None:
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    (csv_dir / "pe.csv").write_text("""date,PE Ratio\n2024-01-01,20\n2024-01-02,22\n""")
    (csv_dir / "rates.csv").write_text("""date,10Y Rate\n2024-01-01,4.5\n2024-01-02,4.6\n""")

    db_path = tmp_path / "db.sqlite"

    inserted = run_pipeline(csv_dir, db_path)
    assert inserted == 2

    with sqlite3.connect(db_path) as conn:
        stored = conn.execute("SELECT implied_growth FROM implied_growth ORDER BY date").fetchall()

    assert stored == [(15.5,), (17.4,)]
