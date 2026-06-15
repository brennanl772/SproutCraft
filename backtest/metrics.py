"""Performance metrics computed from a strategy's daily/period returns.

All functions are pure and operate on a pandas Series of *periodic* (per-bar)
net returns plus the per-bar target position used to realise them.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass
class Stats:
    name: str
    total_return: float      # cumulative, e.g. 2.5 == +250%
    cagr: float              # annualised compound growth
    vol: float               # annualised volatility
    sharpe: float            # annualised, rf = 0
    sortino: float           # annualised, downside-only
    max_drawdown: float      # most negative peak-to-trough (e.g. -0.35)
    calmar: float            # cagr / |max_drawdown|
    exposure: float          # fraction of bars holding a position
    n_trades: int            # number of round-trip trades
    win_rate: float          # fraction of trades that made money
    profit_factor: float     # gross wins / gross losses
    avg_trade: float         # mean per-trade return

    def as_row(self) -> dict:
        return asdict(self)


def _annualisation(index: pd.Index) -> float:
    """Bars per year inferred from the index spacing."""
    if len(index) < 3:
        return 252.0
    days = (index[-1] - index[0]).days / (len(index) - 1)
    if days <= 0:
        return 252.0
    if days < 4:        # roughly daily trading bars
        return 252.0
    if days < 45:       # roughly monthly bars
        return 12.0
    return 365.25 / days


def _trade_returns(returns: pd.Series, position: pd.Series) -> list[float]:
    """Compound per-bar returns within each contiguous holding period."""
    pos = position.fillna(0.0).values
    rets = returns.fillna(0.0).values
    trades: list[float] = []
    in_trade = False
    cur = 1.0
    for p, r in zip(pos, rets):
        if p != 0 and not in_trade:
            in_trade = True
            cur = 1.0
        if in_trade:
            cur *= (1.0 + r)
            if p == 0:  # position closed this bar (return already realised)
                trades.append(cur - 1.0)
                in_trade = False
    if in_trade:
        trades.append(cur - 1.0)
    return trades


def compute(name: str, returns: pd.Series, position: pd.Series) -> Stats:
    returns = returns.fillna(0.0)
    ann = _annualisation(returns.index)

    equity = (1.0 + returns).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    years = max((returns.index[-1] - returns.index[0]).days / 365.25, 1e-9)
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0)

    vol = float(returns.std(ddof=0) * np.sqrt(ann))
    mean_ann = float(returns.mean() * ann)
    sharpe = mean_ann / vol if vol > 0 else 0.0

    downside = returns[returns < 0]
    dvol = float(downside.std(ddof=0) * np.sqrt(ann)) if len(downside) else 0.0
    sortino = mean_ann / dvol if dvol > 0 else 0.0

    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    max_dd = float(drawdown.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0

    exposure = float((position.fillna(0.0) != 0).mean())

    trades = _trade_returns(returns, position)
    n_trades = len(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    win_rate = len(wins) / n_trades if n_trades else 0.0
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0
    avg_trade = float(np.mean(trades)) if trades else 0.0

    return Stats(
        name=name,
        total_return=total_return,
        cagr=cagr,
        vol=vol,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=max_dd,
        calmar=calmar,
        exposure=exposure,
        n_trades=n_trades,
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_trade=avg_trade,
    )
