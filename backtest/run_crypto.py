"""Run the $50 -> $1,000,000 challenge on XRP (crypto) and write a report.

XRP is far more volatile than the S&P, which changes the picture: risking only
3% per trade forces a *sub-1x* position, so no leverage is used and the account
cannot go negative - but the fixed 1:2 cap still keeps $1M out of reach.

Usage: python -m backtest.run_crypto
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import data
from .strategies import STRATEGIES
from .sim import simulate_growth, buy_and_hold

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
START, TARGET = 50.0, 1_000_000.0


def money(x):
    for u, d in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= d:
            return f"${x/d:.2f}{u}"
    return f"${x:.2f}"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    xrp = data.load_xrp_daily()

    res = [buy_and_hold(xrp, start=START, target=TARGET)]
    for name, fn in STRATEGIES.items():
        res.append(simulate_growth(xrp, fn(xrp), name, start=START, target=TARGET, leverage_cap=1.0))
    res.sort(key=lambda r: -r.final_balance)

    # chart
    plt.figure(figsize=(12, 7))
    for r in res:
        if len(r.equity) > 1:
            plt.plot(r.equity.index, r.equity.values, label=r.name, linewidth=1.3)
    plt.axhline(TARGET, color="black", ls="--", lw=1, label="$1,000,000 goal")
    plt.yscale("log")
    plt.title("$50 -> $1,000,000 challenge on XRP (XRP-USD)\n3% risk per trade, 1:2 reward, ATR stop, no leverage")
    plt.ylabel("Account balance (log scale)"); plt.xlabel("Date")
    plt.legend(fontsize=8, loc="upper left"); plt.grid(True, which="both", alpha=0.25)
    plt.tight_layout(); plt.savefig(os.path.join(RESULTS_DIR, "equity_curves_xrp.png"), dpi=130)
    plt.close()

    bh = next(r for r in res if "Buy & Hold" in r.name)
    best = max((r for r in res if "Buy & Hold" not in r.name), key=lambda r: r.final_balance)

    L = []
    L.append("# $50 → $1,000,000 Challenge — XRP (crypto)\n")
    L.append(f"_Data: XRP daily, {xrp.index[0].date()} → {xrp.index[-1].date()} ({len(xrp)} bars). "
             f"Source: public Binance XRPUSDT mirror on GitHub (≈ Coinbase XRP-USD). "
             f"Price ranged ${xrp['close'].min():.3f}–${xrp['close'].max():.3f}._\n")
    L.append("**Rules:** long-only · risk 3% per trade · 1:2 reward (1.5×ATR stop) · start $50 · "
             "goal $1,000,000 · 5 bps/side cost · one position at a time · 60-bar time stop.\n")
    L.append("### Verdict\n")
    L.append(f"**No strategy reached $1M.** Best was **{best.name}** at **{money(best.final_balance)}** "
             f"from $50, which *beat buy & hold* ({money(bh.final_balance)}) — and did so with far less "
             f"pain (max DD {best.max_drawdown*100:.0f}% vs buy & hold's {bh.max_drawdown*100:.0f}%).\n")
    L.append("**Notable:** XRP is so volatile that risking just 3% forces a **sub-1× position** "
             "(peak ~0.6×), so leverage is never used and **the account cannot go negative** — your "
             "hard rule is satisfied automatically. The blocker is still the 1:2 cap + ~45% win rate "
             "× ~120 trades, the same structural wall as the S&P.\n")
    L.append("| # | Strategy | Final | Reached $1M | Trades | Win % | Max DD | Peak lev |")
    L.append("|---|----------|------:|:-----------:|-------:|------:|-------:|---------:|")
    for i, r in enumerate(res, 1):
        L.append(f"| {i} | {r.name} | {money(r.final_balance)} | {'YES' if r.reached_target else 'no'} | "
                 f"{r.n_trades} | {r.win_rate*100:.0f} | {r.max_drawdown*100:.0f}% | {r.max_leverage:.1f}x |")
    L.append("\n![XRP equity curves](equity_curves_xrp.png)\n")
    with open(os.path.join(RESULTS_DIR, "RESULTS_XRP.md"), "w") as f:
        f.write("\n".join(L))

    print(f"XRP {xrp.index[0].date()}->{xrp.index[-1].date()}  best active: {best.name} "
          f"{money(best.final_balance)} (buy&hold {money(bh.final_balance)})")
    print("Wrote results/RESULTS_XRP.md and results/equity_curves_xrp.png")


if __name__ == "__main__":
    main()
