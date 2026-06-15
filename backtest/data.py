"""Data loaders for the bundled, real historical datasets.

Two real datasets are bundled (downloaded from public GitHub-hosted sources):

* ``data/spy_qqq_daily.csv`` - SPY & QQQ daily OHLCV, 2015-2025, dividend/split
  adjusted (Stooq). Used for the daily/swing strategy backtests.
* ``data/shiller_sp500_monthly.csv`` - Robert Shiller's monthly S&P 500 series,
  1871-present, including dividends. Used to build a total-return index for the
  truly long-term (150-year) trend/momentum tests.
"""
from __future__ import annotations

import os

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_daily(symbol: str = "SPY") -> pd.DataFrame:
    """Return a daily OHLCV frame for ``symbol`` indexed by date.

    Columns: open, high, low, close, volume.
    """
    path = os.path.join(DATA_DIR, "spy_qqq_daily.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[df["ticker"].str.upper() == symbol.upper()].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = df[df["close"] > 0].dropna(subset=["close"])
    return df


def load_ohlcv_csv(filename: str) -> pd.DataFrame:
    """Load any cached OHLCV CSV from ``data/`` (e.g. an Alpaca fetch).

    Expects a date/datetime index column plus open/high/low/close/volume.
    """
    path = filename if os.path.isabs(filename) else os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df.index)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].astype(float).sort_index()
    return df[df["close"] > 0].dropna(subset=["close"])


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample a daily OHLCV frame to a coarser timeframe (e.g. 'W', 'ME')."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = df.resample(rule).agg(agg).dropna(subset=["close"])
    return out


def load_shiller_total_return() -> pd.DataFrame:
    """Return Shiller's monthly S&P 500 with a reconstructed total-return index.

    The returned frame is indexed by month and contains:

    * ``price``  - nominal S&P 500 price level.
    * ``close``  - a total-return index (dividends reinvested), normalised to the
      price level at the first observation so it is directly comparable.

    Dividends in the source are reported as a trailing-annual figure, so the
    monthly cash yield is approximated as ``dividend / 12 / price``.
    """
    path = os.path.join(DATA_DIR, "shiller_sp500_monthly.csv")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").set_index("Date")
    df = df.rename(columns={"SP500": "price", "Dividend": "dividend"})
    df = df[["price", "dividend"]].copy()
    # Drop trailing rows with no real price (the source pads future months).
    df = df[df["price"] > 0]
    df["dividend"] = df["dividend"].fillna(0.0)

    price_ret = df["price"].pct_change().fillna(0.0)
    div_yield = (df["dividend"] / 12.0 / df["price"]).fillna(0.0)
    total_ret = price_ret + div_yield
    tr_index = (1.0 + total_ret).cumprod()
    df["close"] = tr_index / tr_index.iloc[0] * df["price"].iloc[0]
    return df
