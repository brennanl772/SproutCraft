"""Historical daily price data via yfinance (free, no API key)."""
import pandas as pd
import yfinance as yf

from . import config


def get_history(symbol: str, period: str | None = None) -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=period or config.SIGNAL_PERIOD,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    # yfinance returns a column MultiIndex even for a single ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def get_intraday(symbol: str, interval: str | None = None,
                 days: int | None = None) -> pd.DataFrame:
    """Intraday OHLC, indexed in America/New_York time."""
    df = yf.download(
        symbol,
        period=f"{days or config.ORB_BACKTEST_DAYS}d",
        interval=interval or config.ORB_INTERVAL,
        auto_adjust=True,
        progress=False,
        prepost=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df
