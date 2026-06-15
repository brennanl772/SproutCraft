"""Alpaca market-data loader (free tier).

Reads credentials from environment variables:

    APCA_API_KEY_ID
    APCA_API_SECRET_KEY

Get them free (no cost, no card for paper trading) at https://alpaca.markets →
"Paper Trading" → "API Keys". The free tier uses the IEX feed, which is plenty
for backtesting SPY on daily / intraday timeframes.

Returns the same OHLCV frame shape as ``data.load_daily`` so the whole
backtester works unchanged on Alpaca data, including intraday timeframes.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

import pandas as pd

DATA_URL = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"

# Valid Alpaca timeframe strings.
TIMEFRAMES = {"1Min", "5Min", "15Min", "30Min", "1Hour", "1Day", "1Week", "1Month"}


def _keys() -> tuple[str, str]:
    kid = os.environ.get("APCA_API_KEY_ID")
    sec = os.environ.get("APCA_API_SECRET_KEY")
    if not kid or not sec:
        raise RuntimeError(
            "Alpaca keys not found. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY "
            "(free paper-trading keys from https://alpaca.markets)."
        )
    return kid, sec


def get_bars(symbol: str = "SPY", timeframe: str = "1Day",
             start: str = "2016-01-01", end: str | None = None,
             feed: str = "iex", adjustment: str = "all") -> pd.DataFrame:
    """Fetch historical bars, following pagination, into an OHLCV frame."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"timeframe must be one of {sorted(TIMEFRAMES)}")
    kid, sec = _keys()
    headers = {"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec}

    rows: list[dict] = []
    page_token = None
    while True:
        params = {
            "timeframe": timeframe, "start": start, "limit": 10000,
            "feed": feed, "adjustment": adjustment,
        }
        if end:
            params["end"] = end
        if page_token:
            params["page_token"] = page_token
        url = DATA_URL.format(symbol=symbol) + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
        rows.extend(payload.get("bars") or [])
        page_token = payload.get("next_page_token")
        if not page_token:
            break

    if not rows:
        raise RuntimeError(f"No bars returned for {symbol} {timeframe} from {start}.")

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert(None)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low",
                            "c": "close", "v": "volume"})
    df = df.set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def fetch_to_csv(symbol: str = "SPY", timeframe: str = "1Day",
                 start: str = "2016-01-01", out_dir: str | None = None) -> str:
    """Fetch and cache bars to ``data/alpaca_<symbol>_<timeframe>.csv``."""
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    df = get_bars(symbol, timeframe, start)
    path = os.path.join(out_dir, f"alpaca_{symbol}_{timeframe}.csv")
    df.to_csv(path)
    return path


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    tf = sys.argv[2] if len(sys.argv) > 2 else "1Day"
    start = sys.argv[3] if len(sys.argv) > 3 else "2016-01-01"
    try:
        p = fetch_to_csv(sym, tf, start)
        df = pd.read_csv(p, index_col=0)
        print(f"Saved {len(df)} bars to {p}  ({df.index[0]} -> {df.index[-1]})")
    except RuntimeError as e:
        print(e)
