"""A small, lookahead-safe backtest engine.

A strategy produces a *target position* series (values in, e.g., {0, 1} for
long/flat or {-1, 0, 1} if shorting) where the value at bar ``t`` is the
position decided using only information available at the close of bar ``t``.

The engine shifts that target forward by one bar before applying it to returns,
so a decision made on the close of day ``t`` earns the return from ``t`` to
``t+1`` - never the same-day return. Transaction costs are charged on the
absolute change in position.
"""
from __future__ import annotations

import pandas as pd

from . import metrics


# Round-trip-ish friction per unit of position change, as a fraction.
# 5 bps per side (commission + slippage) is a realistic, slightly conservative
# figure for a liquid ETF traded by a retail/small-prop account.
DEFAULT_COST_PER_SIDE = 0.0005


def run(name: str, prices: pd.DataFrame, target: pd.Series,
        cost_per_side: float = DEFAULT_COST_PER_SIDE):
    """Backtest ``target`` against ``prices['close']``.

    Returns ``(stats, equity_curve, net_returns)``.
    """
    close = prices["close"]
    asset_ret = close.pct_change().fillna(0.0)

    target = target.reindex(close.index).fillna(0.0)
    held = target.shift(1).fillna(0.0)          # position actually on, per bar

    turnover = held.diff().abs().fillna(held.abs())
    costs = turnover * cost_per_side

    net_ret = held * asset_ret - costs
    equity = (1.0 + net_ret).cumprod()

    stats = metrics.compute(name, net_ret, held)
    return stats, equity, net_ret
