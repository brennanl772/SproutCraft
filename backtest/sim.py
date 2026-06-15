"""Position-sizing growth simulator.

This implements the exact challenge requested:

* Trade SPY (the S&P 500) long.
* Risk a fixed 3% of the *current* account on every trade.
* Use a 1:2 risk/reward bracket - the stop is placed 1.5x ATR below entry, the
  target twice that distance above. So a clean win adds +6% to the account and a
  clean stop loses -3%.
* Start with $20 and try to compound to $1,000,000.
* The account must never go negative (a gap through the stop on a leveraged
  position can do this) - if it does, the strategy has *failed*.

Position size is derived from the risk rule: to lose exactly 3% of the account
when a stop that is ``stop_pct`` away is hit, the notional must be
``0.03 / stop_pct`` times the account (i.e. the implied leverage). Tight stops
imply high leverage and therefore real gap risk - which is how a strategy can
blow up.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .strategies import atr


@dataclass
class GrowthResult:
    name: str
    start: float
    final_balance: float
    reached_target: bool
    failed_negative: bool
    trades_to_target: int | None      # trades taken to first cross $1M
    days_to_target: int | None        # calendar days to first cross $1M
    n_trades: int
    win_rate: float
    avg_trade_pct: float              # mean per-trade % change of account
    expectancy_pct: float            # same thing, kept explicit
    max_drawdown: float
    max_leverage: float
    failed_before_target: bool
    equity: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))


def simulate_growth(
    df: pd.DataFrame,
    entries: pd.Series,
    name: str,
    start: float = 20.0,
    target: float = 1_000_000.0,
    risk: float = 0.03,
    rr: float = 2.0,
    atr_n: int = 14,
    atr_mult: float = 1.5,
    max_hold: int = 60,
    cost_per_side: float = 0.0005,
    leverage_cap: float | None = None,
    trail: bool = False,
) -> GrowthResult:
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    a = atr(df, atr_n).values
    idx = df.index
    n = len(df)
    entries = entries.reindex(df.index).fillna(False).values.astype(bool)

    account = start
    in_trade = False
    entry_price = stop = tgt = leverage = 0.0
    hold = 0

    eq_dates, eq_vals = [idx[0]], [account]
    trades_pct: list[float] = []
    max_lev = 0.0
    peak = account
    max_dd = 0.0
    failed_negative = False
    reached_target = False
    trades_to_target = None
    days_to_target = None
    first_trade_date = None

    def realise(exit_price: float) -> float:
        move = (exit_price - entry_price) / entry_price
        gross = leverage * move
        cost = leverage * cost_per_side * 2.0   # round trip on notional
        return gross - cost

    for i in range(1, n):
        # ---- manage an open trade on bar i -------------------------------- #
        if in_trade:
            hold += 1
            exit_price = None
            if trail:
                # Chandelier trailing stop: ratchet the stop up under the highest
                # high seen since entry; no fixed profit target (let winners run).
                peak_price = max(peak_price, h[i])
                if not np.isnan(a[i]):
                    stop = max(stop, peak_price - atr_mult * a[i])
                if o[i] <= stop:
                    exit_price = o[i]
                elif l[i] <= stop:
                    exit_price = stop
            else:
                if o[i] <= stop:                 # gap down through stop
                    exit_price = o[i]
                elif o[i] >= tgt:                # gap up through target
                    exit_price = o[i]
                elif l[i] <= stop:               # stop hit intrabar (assume first)
                    exit_price = stop
                elif h[i] >= tgt:                # target hit intrabar
                    exit_price = tgt
                elif hold >= max_hold:           # time stop
                    exit_price = c[i]

            if exit_price is not None:
                r = realise(exit_price)
                account *= (1.0 + r)
                trades_pct.append(r)
                in_trade = False
                eq_dates.append(idx[i]); eq_vals.append(account)
                peak = max(peak, account)
                if peak > 0:
                    max_dd = min(max_dd, account / peak - 1.0)
                if account <= 0:
                    failed_negative = True
                    break
                if not reached_target and account >= target:
                    reached_target = True
                    trades_to_target = len(trades_pct)
                    days_to_target = (idx[i] - first_trade_date).days

        # ---- look for a new entry (signal on i-1, fill at open of i) ------ #
        if not in_trade and entries[i - 1] and not np.isnan(a[i - 1]):
            entry_price = o[i]
            risk_per_share = atr_mult * a[i - 1]
            if risk_per_share > 0 and entry_price > 0:
                stop = entry_price - risk_per_share
                tgt = entry_price + rr * risk_per_share
                stop_pct = risk_per_share / entry_price
                leverage = risk / stop_pct
                if leverage_cap is not None:
                    leverage = min(leverage, leverage_cap)
                max_lev = max(max_lev, leverage)
                in_trade = True
                hold = 0
                peak_price = entry_price
                if first_trade_date is None:
                    first_trade_date = idx[i]

    eq = pd.Series(eq_vals, index=pd.DatetimeIndex(eq_dates))
    n_trades = len(trades_pct)
    wins = [t for t in trades_pct if t > 0]
    win_rate = len(wins) / n_trades if n_trades else 0.0
    avg_trade = float(np.mean(trades_pct)) if trades_pct else 0.0
    failed_before_target = failed_negative and not reached_target

    return GrowthResult(
        name=name,
        start=start,
        final_balance=float(account),
        reached_target=reached_target,
        failed_negative=failed_negative,
        trades_to_target=trades_to_target,
        days_to_target=days_to_target,
        n_trades=n_trades,
        win_rate=win_rate,
        avg_trade_pct=avg_trade,
        expectancy_pct=avg_trade,
        max_drawdown=float(max_dd),
        max_leverage=float(max_lev),
        failed_before_target=failed_before_target,
        equity=eq,
    )


def buy_and_hold(df: pd.DataFrame, name: str = "Buy & Hold (1x, benchmark)",
                 start: float = 20.0, target: float = 1_000_000.0) -> GrowthResult:
    c = df["close"]
    final = start * float(c.iloc[-1] / c.iloc[0])
    eq = start * c / c.iloc[0]
    peak = eq.cummax()
    max_dd = float((eq / peak - 1.0).min())
    return GrowthResult(
        name=name, start=start, final_balance=final,
        reached_target=final >= target, failed_negative=False,
        trades_to_target=None, days_to_target=None, n_trades=1,
        win_rate=1.0 if final > start else 0.0,
        avg_trade_pct=final / start - 1.0, expectancy_pct=final / start - 1.0,
        max_drawdown=max_dd, max_leverage=1.0, failed_before_target=False,
        equity=eq,
    )
