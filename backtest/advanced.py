"""Advanced analysis addressing three follow-up questions:

1. Multi-timeframe: run the battery on DAILY, WEEKLY and 150-year MONTHLY data.
2. Better exit than fixed 1:2: compare 1:1 / 1:2 / 1:3 / trailing on a trend
   entry, and small vs large targets on a mean-reversion entry.
3. Tapered risk: start risk high (when the account is tiny) and decay to 3%.

(Intraday/minute timeframes are not available - the data hosts are blocked by
the environment's network allowlist - so the finest timeframe tested is daily.)
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import data
from .strategies import STRATEGIES, donchian_breakout, rsi2_meanrev
from .sim import simulate_growth, buy_and_hold

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = 50.0
TARGET = 1_000_000.0


def money(x):
    for u, d in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= d:
            return f"${x/d:.2f}{u}"
    return f"${x:.2f}"


def synth_ohlc_from_close(close: pd.Series) -> pd.DataFrame:
    """Build an OHLC frame from a close-only series (open = prior close)."""
    open_ = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([open_, close], axis=1).max(axis=1)
    low = pd.concat([open_, close], axis=1).min(axis=1)
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": 0.0})


def best_over_battery(df, **kw):
    """Run every strategy + buy&hold, return sorted results (no leverage)."""
    res = [buy_and_hold(df, start=START, target=TARGET)]
    for name, fn in STRATEGIES.items():
        try:
            res.append(simulate_growth(df, fn(df), name, start=START, target=TARGET, **kw))
        except Exception:
            pass
    res.sort(key=lambda r: (-(r.reached_target), -r.final_balance))
    return res


def main():
    out = []
    def emit(s=""):
        print(s); out.append(s)

    emit(f"# Advanced analysis — ${int(START)} → $1,000,000\n")

    # ---- 1) MULTI-TIMEFRAME ------------------------------------------------ #
    emit("## 1) All available timeframes (no leverage, fixed 1:2)\n")
    spy_d = data.load_daily("SPY")
    spy_w = data.resample_ohlc(spy_d, "W")
    shiller = data.load_shiller_total_return()
    spy_m = synth_ohlc_from_close(shiller["close"])

    frames = [
        ("Daily SPY (2015-2025)", spy_d),
        ("Weekly SPY (2015-2025)", spy_w),
        ("Monthly S&P total-return (1871-2026)", spy_m),
    ]
    emit("| Timeframe | Bars | Best strategy | Final | Reached $1M? | Went neg? |")
    emit("|---|---|---|---|---|---|")
    for label, df in frames:
        res = best_over_battery(df, leverage_cap=1.0)
        top = res[0]
        any_neg = any(r.failed_negative for r in res)
        emit(f"| {label} | {len(df)} | {top.name} | {money(top.final_balance)} | "
             f"{'YES' if top.reached_target else 'no'} | {'yes' if any_neg else 'no'} |")
    emit("\n*Even with 150 years of monthly data, buy & hold compounding is the ceiling — "
         "and only the 150-year run gets into seven figures, purely from time, not trading.*\n")

    # ---- 2) BETTER EXIT THAN 1:2 ------------------------------------------ #
    emit("## 2) Is there a better exit than fixed 1:2?\n")
    emit("**Trend entry (Donchian breakout), daily, no leverage:**\n")
    emit("| Exit rule | Final | Win % | Trades | Max DD |")
    emit("|---|---|---|---|---|")
    for label, kw in [("1:1 target", dict(rr=1.0)), ("1:2 target", dict(rr=2.0)),
                      ("1:3 target", dict(rr=3.0)), ("trailing stop (let it run)", dict(trail=True))]:
        r = simulate_growth(spy_d, donchian_breakout(spy_d), "Donchian", start=START,
                            target=TARGET, leverage_cap=1.0, **kw)
        emit(f"| {label} | {money(r.final_balance)} | {r.win_rate*100:.1f} | {r.n_trades} | {r.max_drawdown*100:.1f}% |")

    emit("\n**Mean-reversion entry (Connors RSI-2), daily, no leverage:**\n")
    emit("| Exit rule | Final | Win % | Trades |")
    emit("|---|---|---|---|")
    for label, rr in [("1:0.5 (quick target)", 0.5), ("1:1", 1.0), ("1:2", 2.0), ("1:3", 3.0)]:
        r = simulate_growth(spy_d, rsi2_meanrev(spy_d), "RSI2", start=START,
                            target=TARGET, leverage_cap=1.0, rr=rr)
        emit(f"| {label} | {money(r.final_balance)} | {r.win_rate*100:.1f} | {r.n_trades} |")
    emit("\n*Lesson: the 'best' reward ratio depends on the edge. Trend/breakout entries like a "
         "wider target or a trailing stop; mean-reversion entries want a small, quick target "
         "(high win rate). Forcing every strategy into 1:2 is itself suboptimal — but no single "
         "exit rule gets any of them near $1M.*\n")

    # ---- 3) TAPERED RISK --------------------------------------------------- #
    emit("## 3) Tapering risk from high → 3% (Donchian, daily)\n")
    emit("Risk starts high while the account is small and decays to 3% as it grows.\n")
    emit("| Risk schedule | Mode | Final | Reached $1M? | Peak lev | Max DD | Went negative? |")
    emit("|---|---|---|---|---|---|---|")
    schedules = [("flat 3%", None), ("10% → 3%", 0.10), ("25% → 3%", 0.25), ("50% → 3%", 0.50)]
    for label, rs in schedules:
        for mode, cap in [("no-leverage ≤1×", 1.0), ("leverage allowed", None)]:
            r = simulate_growth(spy_d, donchian_breakout(spy_d), "Donchian", start=START,
                                target=TARGET, leverage_cap=cap, risk_start=rs)
            emit(f"| {label} | {mode} | {money(r.final_balance)} | "
                 f"{'YES' if r.reached_target else 'no'} | {r.max_leverage:.1f}x | "
                 f"{r.max_drawdown*100:.1f}% | {'⚠️ YES — FAILED' if r.failed_negative else 'no'} |")
    emit("\n*Key trade-off: tapering risk up early only speeds things in **leverage-allowed** mode "
         "(no-leverage caps the real risk at the stop distance, so high targets do nothing). And the "
         "moment leverage is high enough to matter, a gap can drive the account negative — which is the "
         "exact failure you forbade. There is no setting that is both fast AND guaranteed non-negative.*\n")

    with open(os.path.join(ROOT, "results", "RESULTS_ADVANCED.md"), "w") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    main()
