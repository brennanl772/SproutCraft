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
