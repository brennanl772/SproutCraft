"""Backtest the user's uptrend swing strategy across assets.

Rules (longs only): enter when higher highs + higher lows are forming and price
is above the 20 EMA; stop just below the most recent higher low; take profit at
2x the risk distance (1:2). Position sized to risk 3% of the account.

Usage: python -m backtest.mystrategy
"""
from __future__ import annotations

import os

from . import data
from .strategies import uptrend_swing
from .sim import simulate_growth, buy_and_hold

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, TARGET = 50.0, 1_000_000.0

ASSETS = [
    ("SPY", lambda: data.load_daily("SPY")),
    ("QQQ", lambda: data.load_daily("QQQ")),
    ("BTC", lambda: data.load_ohlcv_csv("btc_daily.csv")),
    ("ETH", lambda: data.load_ohlcv_csv("eth_daily.csv")),
    ("XRP", lambda: data.load_xrp_daily()),
    ("ADA", lambda: data.load_ohlcv_csv("ada_daily.csv")),
    ("DOGE", lambda: data.load_ohlcv_csv("doge_daily.csv")),
    ("LTC", lambda: data.load_ohlcv_csv("ltc_daily.csv")),
    ("BNB", lambda: data.load_ohlcv_csv("bnb_daily.csv")),
]


def money(x):
    for u, d in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= d:
            return f"${x/d:.2f}{u}"
    return f"${x:.2f}"


def main():
    L = ["# Your uptrend swing strategy — backtest\n"]
    L.append("Longs only · higher highs + higher lows + price > 20 EMA · stop just below the last "
             "higher low · take profit at 2× risk (1:2) · risk 3%/trade · no leverage · start $50.\n")
    L.append("| Asset | Years | Final from $50 | vs buy & hold | Trades | Win % | Avg/trade | Max DD | $1M? |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    print(f"{'Asset':6}{'Final':>10}{'Buy&Hold':>10}{'Trades':>8}{'Win%':>6}{'MaxDD':>7}{'$1M':>5}")
    for label, loader in ASSETS:
        df = loader()
        entries, stops = uptrend_swing(df)
        r = simulate_growth(df, entries, label, start=START, target=TARGET,
                            leverage_cap=1.0, stops=stops)
        bh = buy_and_hold(df, start=START, target=TARGET)
        years = (df.index[-1] - df.index[0]).days / 365.25
        L.append(f"| {label} | {years:.1f} | {money(r.final_balance)} | {money(bh.final_balance)} | "
                 f"{r.n_trades} | {r.win_rate*100:.0f} | {r.avg_trade_pct*100:.2f}% | "
                 f"{r.max_drawdown*100:.0f}% | {'YES' if r.reached_target else 'no'} |")
        print(f"{label:6}{money(r.final_balance):>10}{money(bh.final_balance):>10}"
              f"{r.n_trades:>8}{r.win_rate*100:>5.0f}{r.max_drawdown*100:>6.0f}%"
              f"{('YES' if r.reached_target else 'no'):>5}")
    with open(os.path.join(ROOT, "results", "RESULTS_MYSTRATEGY.md"), "w") as f:
        f.write("\n".join(L))
    print("\nWrote results/RESULTS_MYSTRATEGY.md")


if __name__ == "__main__":
    main()
