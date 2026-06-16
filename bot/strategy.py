"""Trend-following signal logic: EMA crossover with a long-term trend filter
and ATR-based stop-loss / take-profit. Long-only.

This is a transparent, mechanical strategy. It is NOT guaranteed to be
profitable and WILL have losing trades and drawdowns. Use backtest.py to
judge it on real historical data before trading anything real.
"""
from dataclasses import dataclass

import pandas as pd

from . import config
from .indicators import ema, sma, atr


@dataclass
class Signal:
    symbol: str
    date: str
    side: str  # "BUY"
    entry: float  # reference price (latest close)
    stop_loss: float
    take_profit: float
    atr: float
    reason: str

    @property
    def risk_per_share(self) -> float:
        return round(self.entry - self.stop_loss, 2)

    @property
    def risk_reward(self) -> float:
        risk = self.entry - self.stop_loss
        reward = self.take_profit - self.entry
        return round(reward / risk, 1) if risk > 0 else 0.0


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = ema(out["Close"], config.EMA_FAST)
    out["ema_slow"] = ema(out["Close"], config.EMA_SLOW)
    out["sma_trend"] = sma(out["Close"], config.TREND_SMA)
    out["atr"] = atr(out, config.ATR_PERIOD)

    cross_up = (out["ema_fast"] > out["ema_slow"]) & \
               (out["ema_fast"].shift(1) <= out["ema_slow"].shift(1))
    uptrend = out["Close"] > out["sma_trend"]
    out["entry_signal"] = cross_up & uptrend

    out["exit_signal"] = (out["ema_fast"] < out["ema_slow"]) & \
                         (out["ema_fast"].shift(1) >= out["ema_slow"].shift(1))
    return out


def _build_signal(symbol: str, date: str, entry: float, atr_val: float) -> Signal:
    stop = entry - config.ATR_STOP_MULT * atr_val
    target = entry + config.ATR_STOP_MULT * atr_val * config.RISK_REWARD
    reason = (f"EMA{config.EMA_FAST} crossed above EMA{config.EMA_SLOW} "
              f"while price is above SMA{config.TREND_SMA} (uptrend)")
    return Signal(
        symbol=symbol,
        date=date,
        side="BUY",
        entry=round(entry, 2),
        stop_loss=round(stop, 2),
        take_profit=round(target, 2),
        atr=round(atr_val, 2),
        reason=reason,
    )


def signal_for_latest_bar(symbol: str, df: pd.DataFrame) -> Signal | None:
    """Return a Signal if the most recent CLOSED bar triggered an entry."""
    data = compute_indicators(df).dropna()
    if data.empty:
        return None
    last = data.iloc[-1]
    if not bool(last["entry_signal"]):
        return None
    return _build_signal(symbol, str(data.index[-1].date()),
                         float(last["Close"]), float(last["atr"]))
