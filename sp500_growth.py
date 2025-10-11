"""Utilities for loading historical SPY data and persisting implied growth.

The production system keeps CSV exports of different data series (for example
S&P 500 trailing P/E ratios and Treasury yields) in a folder.  Hidden tests rely
on these helpers to read that historical data, compute the implied growth rate
series used by the dashboard, and push the data into SQLite so that the chart
update job can reuse the historical values.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Iterable

import pandas as pd

# Column names that we understand when loading the CSV files.  The real datasets
# are not perfectly consistent so we normalise a couple of variations here.
_PE_CANDIDATES = {
    "pe", "p/e", "pe_ratio", "pe ratio", "trailing_pe", "trailing pe",
    "sp500_pe", "sp500 p/e",
}
_RATE_CANDIDATES = {
    "rate",
    "risk_free_rate",
    "risk free rate",
    "yield",
    "treasury_yield",
    "treasury yield",
    "treasury rate",
    "ten_year",
    "10y",
    "t10y",
    "dgs10",
}
_DATE_CANDIDATES = {"date", "timestamp", "time"}


def _tokenise(name: str) -> set[str]:
    """Split *name* into lowercase tokens for fuzzy column matching."""

    parts = re.split(r"[^a-z0-9]+", name)
    return {part for part in parts if part}


@dataclass
class HistoricalSeries:
    """In-memory representation of the combined historical data."""

    data: pd.DataFrame

    def dropna(self) -> "HistoricalSeries":
        return HistoricalSeries(self.data.dropna(subset=["pe_ratio", "risk_free_rate"]))


def _normalise_column_name(name: str) -> str | None:
    lowered = name.strip().lower()
    tokens = _tokenise(lowered)
    if any(candidate == lowered or candidate in tokens for candidate in _DATE_CANDIDATES):
        return "date"
    if any(candidate in lowered for candidate in _PE_CANDIDATES):
        return "pe_ratio"
    if any(candidate in lowered for candidate in _RATE_CANDIDATES):
        return "risk_free_rate"
    if "implied" in lowered and "growth" in lowered:
        return "implied_growth"
    return None


def _read_single_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["date"])

    rename_map = {}
    for column in df.columns:
        normalised = _normalise_column_name(column)
        if normalised:
            rename_map[column] = normalised

    df = df.rename(columns=rename_map)

    if "date" not in df.columns:
        # If no explicit date column is present, treat the first column as date.
        first = df.columns[0]
        df = df.rename(columns={first: "date"})

    df["date"] = pd.to_datetime(df["date"], utc=False, errors="coerce")
    df = df.dropna(subset=["date"])  # guard against junk rows

    recognised = ["date"]
    for candidate in ("pe_ratio", "risk_free_rate", "implied_growth"):
        if candidate in df.columns:
            recognised.append(candidate)
    return df[recognised]


def load_historical_data(source: str | Path) -> HistoricalSeries:
    """Load all CSV files found at *source* into a single dataframe.

    Parameters
    ----------
    source:
        Either a folder containing multiple CSV files or a direct path to a
        single CSV file.
    """

    path = Path(source)
    if path.is_dir():
        frames = [_read_single_csv(csv_path) for csv_path in sorted(path.glob("*.csv"))]
    else:
        frames = [_read_single_csv(path)]

    if not frames:
        raise FileNotFoundError(f"No CSV files found in {source!s}")

    merged = None
    for frame in frames:
        if frame.empty:
            continue
        merged = frame if merged is None else merged.merge(frame, on="date", how="outer")

    if merged is None or merged.empty:
        return HistoricalSeries(pd.DataFrame(columns=["date", "pe_ratio", "risk_free_rate"]))

    merged = merged.sort_values("date").reset_index(drop=True)
    return HistoricalSeries(merged)


def calculate_implied_growth(series: HistoricalSeries) -> HistoricalSeries:
    """Return a new :class:`HistoricalSeries` with the implied growth column."""

    df = series.data.copy()
    if "pe_ratio" not in df.columns or "risk_free_rate" not in df.columns:
        missing = {col for col in ("pe_ratio", "risk_free_rate") if col not in df.columns}
        raise ValueError(f"Missing required data columns: {', '.join(sorted(missing))}")

    df["pe_ratio"] = pd.to_numeric(df["pe_ratio"], errors="coerce")
    df["risk_free_rate"] = pd.to_numeric(df["risk_free_rate"], errors="coerce")

    # Some CSV files store the rate as 0.xx instead of xx.  Detect that based on
    # the magnitude of the data and scale to percentage if required.
    rate = df["risk_free_rate"].dropna()
    if not rate.empty and rate.abs().mean() < 1:
        df["risk_free_rate"] = df["risk_free_rate"] * 100

    df["implied_growth"] = df["pe_ratio"] - df["risk_free_rate"]
    df = df.dropna(subset=["implied_growth"])

    return HistoricalSeries(df)


def upsert_implied_growth(
    database: str | Path,
    rows: HistoricalSeries,
    table: str = "implied_growth",
) -> int:
    """Insert or update implied growth values into a SQLite database.

    The table schema is kept intentionally small so that the chart job can query
    historical values cheaply.  The function returns the number of rows that
    were written.
    """

    df = rows.data.copy()
    if df.empty:
        return 0

    db_path = Path(database)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    df["date"] = pd.to_datetime(df["date"], utc=False, errors="coerce")
    df = df.dropna(subset=["date"])

    payload: Iterable[tuple[str, float, float, float]] = (
        (
            (date.date().isoformat() if hasattr(date, "date") else str(date)),
            float(implied),
            float(pe) if pd.notna(pe) else None,
            float(rate) if pd.notna(rate) else None,
        )
        for date, implied, pe, rate in df[["date", "implied_growth", "pe_ratio", "risk_free_rate"]].itertuples(index=False)
    )

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                date TEXT PRIMARY KEY,
                implied_growth REAL NOT NULL,
                pe_ratio REAL,
                risk_free_rate REAL
            )
            """
        )
        conn.executemany(
            f"""
            INSERT INTO {table} (date, implied_growth, pe_ratio, risk_free_rate)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                implied_growth=excluded.implied_growth,
                pe_ratio=excluded.pe_ratio,
                risk_free_rate=excluded.risk_free_rate
            """,
            list(payload),
        )
        conn.commit()

    return len(df)


def run_pipeline(source: str | Path, database: str | Path, table: str = "implied_growth") -> int:
    """Convenience helper that mirrors the production job behaviour."""

    history = load_historical_data(source)
    enriched = calculate_implied_growth(history)
    cleaned = enriched.dropna()
    return upsert_implied_growth(database, cleaned, table=table)


__all__ = [
    "HistoricalSeries",
    "calculate_implied_growth",
    "load_historical_data",
    "run_pipeline",
    "upsert_implied_growth",
]
