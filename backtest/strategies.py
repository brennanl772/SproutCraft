"""Well-known systematic entry strategies, expressed as long-entry triggers.

Each strategy is reduced to a single thing: *when does it want to enter a long?*
Exits are NOT defined here - every strategy is traded with the same risk-managed
bracket (3% account risk, 1:2 reward, ATR stop) by ``sim.py`` so we compare the
quality of the entry edge on a level playing field.

A strategy function takes a daily OHLCV frame and returns a boolean Series:
``True`` on a bar means "enter long at the next bar's open".

All indicators are computed using information available up to and including the
signalling bar, so shifting the fill to the next open keeps the test
lookahead-safe.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Indicators
# --------------------------------------------------------------------------- #
def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def rsi(close: pd.Series, n: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder smoothing.
    avg_gain = gain.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    signal = line.ewm(span=sig, adjust=False).mean()
    return line, signal


def _crosses_above(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


# --------------------------------------------------------------------------- #
# Entry strategies
# --------------------------------------------------------------------------- #
def rsi2_meanrev(df: pd.DataFrame) -> pd.Series:
    """Connors RSI(2): buy oversold dips inside an uptrend."""
    close = df["close"]
    return (rsi(close, 2) < 10) & (close > sma(close, 200))


def bollinger_reversion(df: pd.DataFrame) -> pd.Series:
    """Buy when price closes below the lower Bollinger band, in an uptrend."""
    close = df["close"]
    mid = sma(close, 20)
    sd = close.rolling(20).std(ddof=0)
    lower = mid - 2.0 * sd
    return (close < lower) & (close > sma(close, 200))


def three_day_dip(df: pd.DataFrame) -> pd.Series:
    """Connors-style high-probability pullback: 3 consecutive lower closes."""
    close = df["close"]
    down = close.diff() < 0
    three = down & down.shift(1) & down.shift(2)
    return three & (close > sma(close, 200))


def donchian_breakout(df: pd.DataFrame) -> pd.Series:
    """Turtle 20-day breakout: close exceeds the prior 20-day high."""
    close = df["close"]
    prior_high = close.shift(1).rolling(20).max()
    return close > prior_high


def golden_cross(df: pd.DataFrame) -> pd.Series:
    """Classic 50/200 SMA golden cross."""
    close = df["close"]
    return _crosses_above(sma(close, 50), sma(close, 200))


def macd_cross(df: pd.DataFrame) -> pd.Series:
    """MACD line crossing above its signal line, in an uptrend."""
    close = df["close"]
    line, signal = macd(close)
    return _crosses_above(line, signal) & (close > sma(close, 200))


def new_high_momentum(df: pd.DataFrame) -> pd.Series:
    """52-week-high momentum: close makes a new 252-day high."""
    close = df["close"]
    prior_high = close.shift(1).rolling(252).max()
    return close > prior_high


def prior_day_high_breakout(df: pd.DataFrame) -> pd.Series:
    """Daily cousin of the opening-range breakout: close clears yesterday's high
    while in an uptrend. (True intraday ORB needs minute data, which is not
    available here - this is the honest daily approximation.)"""
    close = df["close"]
    return (close > df["high"].shift(1)) & (close > sma(close, 50))


def ibs_reversion(df: pd.DataFrame) -> pd.Series:
    """Internal Bar Strength: buy when the close is near the bar's low.
    One of the highest win-rate daily edges known on equity indices."""
    rng = (df["high"] - df["low"]).replace(0.0, np.nan)
    ibs = (df["close"] - df["low"]) / rng
    return (ibs < 0.2) & (df["close"] > sma(df["close"], 200))


def williams_r(df: pd.DataFrame) -> pd.Series:
    """Williams %R oversold inside an uptrend."""
    hh = df["high"].rolling(14).max()
    ll = df["low"].rolling(14).min()
    wr = -100.0 * (hh - df["close"]) / (hh - ll).replace(0.0, np.nan)
    return (wr < -90) & (df["close"] > sma(df["close"], 200))


def stochastic_reversion(df: pd.DataFrame) -> pd.Series:
    """Slow stochastic %K oversold inside an uptrend."""
    ll = df["low"].rolling(14).min()
    hh = df["high"].rolling(14).max()
    k = 100.0 * (df["close"] - ll) / (hh - ll).replace(0.0, np.nan)
    k = k.rolling(3).mean()
    return (k < 20) & (df["close"] > sma(df["close"], 200))


def rsi14_oversold(df: pd.DataFrame) -> pd.Series:
    """Classic RSI(14) < 30 oversold, with trend filter."""
    return (rsi(df["close"], 14) < 30) & (df["close"] > sma(df["close"], 200))


def lower_low_reversal(df: pd.DataFrame) -> pd.Series:
    """Buy a 5-day low that closes up (failed breakdown), in an uptrend."""
    five_low = df["low"].rolling(5).min()
    return ((df["low"] <= five_low) & (df["close"] > df["open"]) &
            (df["close"] > sma(df["close"], 200)))


def keltner_breakout(df: pd.DataFrame) -> pd.Series:
    """Volatility breakout above an upper Keltner channel."""
    ema = df["close"].ewm(span=20, adjust=False).mean()
    upper = ema + 2.0 * atr(df, 20)
    return df["close"] > upper


STRATEGIES = {
    "RSI(2) Mean Reversion (Connors)": rsi2_meanrev,
    "Bollinger Band Reversion": bollinger_reversion,
    "3-Day Dip Buy (Connors)": three_day_dip,
    "Donchian 20d Breakout (Turtle)": donchian_breakout,
    "Golden Cross 50/200": golden_cross,
    "MACD Crossover": macd_cross,
    "52-Week High Momentum": new_high_momentum,
    "Prior-Day-High Breakout (ORB-style)": prior_day_high_breakout,
    "Internal Bar Strength (IBS)": ibs_reversion,
    "Williams %R Oversold": williams_r,
    "Stochastic Oversold": stochastic_reversion,
    "RSI(14) Oversold": rsi14_oversold,
    "5-Day Low Reversal": lower_low_reversal,
    "Keltner Volatility Breakout": keltner_breakout,
}
