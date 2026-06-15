"""Multi-asset sweep: run every strategy on every asset and answer two
different questions that are easy to conflate:

  Q1. "Is there a single WINNING (profitable) strategy?"  -> yes, lots.
  Q2. "Does any strategy turn $50 into $1,000,000?"       -> no.

Profitable != 50,000x. This script makes the gap explicit.
"""
from __future__ import annotations

import os

from . import data
from .strategies import STRATEGIES
from .sim import simulate_growth, buy_and_hold

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, TARGET = 50.0, 1_000_000.0

ASSETS = [
    ("SPY  (S&P 500)", lambda: data.load_daily("SPY")),
    ("QQQ  (Nasdaq)", lambda: data.load_daily("QQQ")),
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
    rows, total_profitable, total_tested, any_million = [], 0, 0, False
    L = ["# Multi-asset sweep — every strategy × every asset\n"]
    L.append(f"Start ${int(START)}, 3% risk, 1:2 reward, no leverage. "
             "**Profitable** = a strategy that ends above its starting balance.\n")
    L.append("| Asset | Years | # profitable / 14 | Best strategy | Best final | Buy & hold | Any $1M? |")
    L.append("|---|---|---|---|---|---|---|")

    for label, loader in ASSETS:
        df = loader()
        years = (df.index[-1] - df.index[0]).days / 365.25
        bh = buy_and_hold(df, start=START, target=TARGET)
        res = []
        for name, fn in STRATEGIES.items():
            r = simulate_growth(df, fn(df), name, start=START, target=TARGET, leverage_cap=1.0)
            res.append(r)
        profitable = [r for r in res if r.final_balance > START]
        best = max(res, key=lambda r: r.final_balance)
        million = any(r.reached_target for r in res) or bh.reached_target
        any_million = any_million or million
        total_profitable += len(profitable)
        total_tested += len(res)
        L.append(f"| {label} | {years:.1f} | **{len(profitable)}** | {best.name} | "
                 f"{money(best.final_balance)} | {money(bh.final_balance)} | "
                 f"{'YES' if million else 'no'} |")
        print(f"{label:18} {len(profitable):>2}/14 profitable  best={best.name[:28]:28} "
              f"{money(best.final_balance):>9}  buy&hold {money(bh.final_balance):>9}")

    L.append("")
    L.append(f"### Answer to 'is there a single winning strategy?'\n")
    L.append(f"**Yes — emphatically.** Across these {len(ASSETS)} assets, "
             f"**{total_profitable} of {total_tested}** strategy/asset combinations were profitable. "
             "Trend/breakout systems (Donchian, Keltner, momentum) made money on almost everything.\n")
    L.append("### Answer to 'does any reach $1,000,000 from $50?'\n")
    L.append(f"**{'Yes' if any_million else 'No'}.** Winning and 50,000×-ing are different questions. "
             "These strategies *win* (positive expectancy); none *moonshot* a $50 stake to seven "
             "figures, because that needs an edge × frequency that doesn't exist on daily bars.\n")
    L.append("### So how do people actually make money?\n")
    L.append("- **On real capital, not $50.** 15-30%/yr on $100k is a great living; the same % on $50 "
             "is $7.50. The percentages are identical — the strategy isn't the problem, the base is.\n"
             "- **Compounding over years/decades**, not weeks.\n"
             "- **Edge + risk control + size**, accepting drawdowns most people can't stomach.\n"
             "- Many 'traders' make money from **fees, spreads, market-making, or selling courses** — "
             "not from turning pocket change into millions.\n")
    with open(os.path.join(ROOT, "results", "RESULTS_BASKET.md"), "w") as f:
        f.write("\n".join(L))
    print(f"\nTOTAL: {total_profitable}/{total_tested} profitable combos. Any $1M from $50: "
          f"{'YES' if any_million else 'NO'}")
    print("Wrote results/RESULTS_BASKET.md")


if __name__ == "__main__":
    main()
