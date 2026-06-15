"""Turn a candle history into the bot's current decision, reusing the exact
same uptrend logic that was backtested in ``backtest.strategies``.
"""
from __future__ import annotations

import pandas as pd

from backtest.strategies import uptrend_swing


class Signal:
    def __init__(self, enter: bool, support: float | None, stop: float | None):
        self.enter = enter
        self.support = support      # the most recent higher low (support level)
        self.stop = stop            # just BELOW support

    def target(self, entry: float, rr: float) -> float | None:
        if self.stop is None or entry <= self.stop:
            return None
        return entry + rr * (entry - self.stop)


def latest_signal(df: pd.DataFrame, cfg) -> Signal:
    """Compute the decision on the last CLOSED bar of ``df``."""
    entries, stops = uptrend_swing(df, cfg.pivot_left, cfg.pivot_right,
                                   cfg.ema_len, cfg.stop_buffer)
    enter = bool(entries.iloc[-1])
    stop = stops.iloc[-1]
    stop = float(stop) if pd.notna(stop) else None
    support = stop / (1.0 - cfg.stop_buffer) if stop is not None else None
    return Signal(enter, support, stop)
