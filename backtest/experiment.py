"""'What would it actually take?' — empirical answer.

The fixed 1:2 challenge reaches nowhere near $1M. This script relaxes the
assumptions one at a time to find what it really takes:

1. Let winners run (trailing ATR stop instead of a fixed 1:2 target).
2. Allow more volatility (test QQQ as well as SPY).
3. Sweep the leverage cap to find the minimum leverage that crosses $1M -
   and whether doing so blows the account negative.
"""
from __future__ import annotations

from . import data
from .strategies import STRATEGIES
from .sim import simulate_growth


def money(x):
    for u, d in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= d:
            return f"${x/d:.2f}{u}"
    return f"${x:.2f}"


START = 50.0


def main():
    print(f"WHAT WOULD IT ACTUALLY TAKE TO REACH ${int(START)} -> $1,000,000?\n")

    # Best entry edges from the main run.
    picks = ["Donchian 20d Breakout (Turtle)", "52-Week High Momentum",
             "Prior-Day-High Breakout (ORB-style)"]

    for sym in ("SPY", "QQQ"):
        df = data.load_daily(sym)
        print(f"\n################ {sym}  ({df.index[0].date()} -> {df.index[-1].date()}) ################")

        print("\n-- Step 1: let winners run (trailing stop), NO leverage (<=1x) --")
        for name in picks:
            r = simulate_growth(df, STRATEGIES[name](df), name, start=START, trail=True, leverage_cap=1.0)
            print(f"  {name:36} final {money(r.final_balance):>10}  "
                  f"reached={r.reached_target}  trades={r.n_trades}  "
                  f"win={r.win_rate*100:4.1f}%  maxDD={r.max_drawdown*100:5.1f}%")

        print("\n-- Step 2: let winners run + leverage sweep (best entry) --")
        best = "Donchian 20d Breakout (Turtle)"
        for lev in (1, 2, 3, 5, 8, 12, 20):
            r = simulate_growth(df, STRATEGIES[best](df), best, start=START, trail=True, leverage_cap=float(lev))
            tag = ("WENT NEGATIVE - FAILED" if r.failed_negative else
                   f"reached $1M in {r.trades_to_target} trades / {r.days_to_target} days"
                   if r.reached_target else "fell short")
            print(f"  cap {lev:>2}x  final {money(r.final_balance):>10}  "
                  f"peakLev {r.max_leverage:4.1f}x  maxDD {r.max_drawdown*100:6.1f}%  -> {tag}")


if __name__ == "__main__":
    main()
