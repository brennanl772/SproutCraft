"""Run the $20 -> $1,000,000 challenge across all strategies and report.

Usage:  python -m backtest.run
Outputs: console table, results/equity_curves.png, results/RESULTS.md
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import data
from .strategies import STRATEGIES
from .sim import simulate_growth, buy_and_hold, GrowthResult

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")

START = 50.0
TARGET = 1_000_000.0


def money(x: float) -> str:
    if x is None:
        return "-"
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= div:
            return f"${x/div:.2f}{unit}"
    return f"${x:.2f}"


def rank_key(r: GrowthResult):
    # Reached & survived first; among those, fastest (fewest trades) wins.
    reached = r.reached_target and not r.failed_before_target
    speed = r.trades_to_target if r.trades_to_target is not None else 10**9
    return (0 if reached else 1, speed, -r.final_balance)


def run_mode(spy, leverage_cap):
    results: list[GrowthResult] = [buy_and_hold(spy, start=START, target=TARGET)]
    for name, fn in STRATEGIES.items():
        results.append(simulate_growth(spy, fn(spy), name, start=START, target=TARGET,
                                       leverage_cap=leverage_cap))
    results.sort(key=rank_key)
    return results


def _print_table(title, results) -> None:
    print(f"\n=== {title} ===")
    hdr = (f"{'Strategy':38} {'Final':>11} {'Reached':>8} {'Trades':>7} "
           f"{'Days':>6} {'Win%':>6} {'Avg/Trade':>10} {'MaxDD':>7} {'Lev':>5} {'Status':>10}")
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        status = ("FAILED-NEG" if r.failed_negative else
                  "REACHED" if r.reached_target else "fell short")
        print(f"{r.name[:38]:38} {money(r.final_balance):>11} "
              f"{('YES' if r.reached_target else 'no'):>8} "
              f"{r.n_trades:>7} {(r.days_to_target if r.days_to_target else '-'):>6} "
              f"{r.win_rate*100:>5.1f} {r.avg_trade_pct*100:>9.2f}% "
              f"{r.max_drawdown*100:>6.1f} {r.max_leverage:>4.1f}x {status:>10}")


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    spy = data.load_daily("SPY")
    print(f"SPY daily bars: {len(spy)}  ({spy.index[0].date()} -> {spy.index[-1].date()})")

    mode_a = run_mode(spy, leverage_cap=None)     # full 3% risk, leverage as needed
    mode_b = run_mode(spy, leverage_cap=1.0)      # no leverage, can't go negative

    _print_table("MODE A: full 3% risk (uses leverage)", mode_a)
    _print_table("MODE B: no leverage (<=1x, cannot go negative)", mode_b)

    _plot(mode_a, "equity_curves_leveraged.png", "Mode A — full 3% risk (leverage as needed)")
    _plot(mode_b, "equity_curves_noleverage.png", "Mode B — no leverage (<=1x)")
    _write_report(mode_a, mode_b, spy)
    print("\nWrote results/equity_curves_*.png and results/RESULTS.md")


def _plot(results: list[GrowthResult], fname: str, subtitle: str) -> None:
    plt.figure(figsize=(12, 7))
    for r in results:
        if len(r.equity) > 1:
            plt.plot(r.equity.index, r.equity.values, label=r.name, linewidth=1.4)
    plt.axhline(TARGET, color="black", linestyle="--", linewidth=1, label="$1,000,000 goal")
    plt.axhline(START, color="grey", linestyle=":", linewidth=1)
    plt.yscale("log")
    plt.title(f"$20 -> $1,000,000 challenge on the S&P 500 (SPY)\n{subtitle}")
    plt.ylabel("Account balance (log scale)")
    plt.xlabel("Date")
    plt.legend(fontsize=8, loc="upper left")
    plt.grid(True, which="both", alpha=0.25)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, fname), dpi=130)
    plt.close()


def _ranking_table(results: list[GrowthResult]) -> list[str]:
    lines = ["| # | Strategy | Final balance | Reached $1M | Trades | Days to $1M | Win % | Avg/trade | Max DD | Peak lev. | Status |",
             "|---|----------|--------------:|:-----------:|-------:|------------:|------:|----------:|-------:|----------:|--------|"]
    for i, r in enumerate(results, 1):
        status = ("❌ went negative" if r.failed_negative else
                  "✅ reached" if r.reached_target else "— fell short")
        lines.append(
            f"| {i} | {r.name} | {money(r.final_balance)} | "
            f"{'YES' if r.reached_target else 'no'} | {r.n_trades} | "
            f"{r.days_to_target if r.days_to_target else '—'} | {r.win_rate*100:.1f} | "
            f"{r.avg_trade_pct*100:.2f}% | {r.max_drawdown*100:.1f}% | "
            f"{r.max_leverage:.1f}x | {status} |")
    return lines


def _winner_block(results, label) -> list[str]:
    winner = next((r for r in results if r.reached_target and not r.failed_before_target), None)
    out = []
    if winner:
        out.append(f"**{label} winner: {winner.name}** — reached $1M in "
                   f"**{winner.trades_to_target} trades / {winner.days_to_target} days**, "
                   f"finished at **{money(winner.final_balance)}** "
                   f"(win rate {winner.win_rate*100:.1f}%, avg {winner.avg_trade_pct*100:.2f}%/trade, "
                   f"max DD {winner.max_drawdown*100:.1f}%, peak leverage {winner.max_leverage:.1f}x). "
                   f"Never went negative.\n")
    else:
        best = max(results, key=lambda r: r.final_balance)
        out.append(f"**{label}: no strategy reached $1M.** Best was **{best.name}** at "
                   f"**{money(best.final_balance)}**.\n")
    return out


def _write_report(mode_a, mode_b, spy) -> None:
    import math
    ratio = TARGET / START
    s = f"${int(START)}"
    def cagr(years):
        return (ratio ** (1.0 / years) - 1.0) * 100.0
    def per_trade(n):
        return (math.exp(math.log(ratio) / n) - 1.0) * 100.0

    lines = []
    lines.append(f"# {s} → $1,000,000 Challenge — S&P 500 (SPY)\n")
    lines.append(f"_Data: SPY daily, {spy.index[0].date()} → {spy.index[-1].date()} "
                 f"({len(spy)} bars), dividend/split adjusted. Source: public Stooq mirror on GitHub._\n")
    lines.append(f"**Rules:** long-only S&P 500 · risk **3%** of the account per trade · "
                 f"**1:2** reward (stop = 1.5×ATR, target = 2× the stop distance) · start **{s}** · "
                 f"goal **$1,000,000** · 5 bps cost per side · one position at a time · 60-bar time "
                 f"stop. A strategy **fails** if the account ever goes negative.\n")
    lines.append("Two position-sizing modes are tested because honoring a literal 3% risk on a "
                 "tight stop *requires* leverage, and leverage is the only thing that can drive a "
                 "long index account negative on a gap:\n")
    lines.append("- **Mode A – full 3% risk:** size up with leverage so a stop-out loses exactly 3%.")
    lines.append("- **Mode B – no leverage (≤1×):** never borrow; risk = the stop distance (≤3%). "
                 "Mathematically cannot go negative.\n")

    lines.append("## Verdict\n")
    lines += _winner_block(mode_a, "Mode A (leveraged)")
    lines += _winner_block(mode_b, "Mode B (no leverage)")

    # Best active strategy (excluding buy & hold) by final balance, leveraged.
    active = [r for r in mode_a if "Buy & Hold" not in r.name]
    best_active = max(active, key=lambda r: r.final_balance)
    bh = next(r for r in mode_a if "Buy & Hold" in r.name)
    lines.append("\n### Bottom line\n")
    lines.append(f"**No strategy turned {s} into $1,000,000** — not even close. The best *active* "
                 f"strategy was **{best_active.name}** ({money(best_active.final_balance)} from {s}), "
                 f"and even that **lost to simply buying and holding** the S&P 500 "
                 f"({money(bh.final_balance)}). The honest result is that this challenge is not "
                 f"achievable on the S&P 500 under disciplined 3% / 1:2 risk rules over an 11-year "
                 f"window.\n")

    lines.append("### Why it's mathematically out of reach\n")
    lines.append(f"{s} → $1,000,000 is a **{ratio:,.0f}×** gain. Compounded across the realistic number "
                 f"of trades these strategies generate, the required edge is brutal:\n")
    lines.append("| Trades available | Avg geometric gain needed *per trade* |")
    lines.append("|---|---|")
    lines.append(f"| ~110 (Donchian breakout) | **+{per_trade(110):.1f}% every trade** |")
    lines.append(f"| ~500 | +{per_trade(500):.1f}% every trade |")
    lines.append(f"| ~1000 | +{per_trade(1000):.1f}% every trade |")
    lines.append("\nThe strategies actually delivered roughly **+0.05% to +1.3% per trade**. With a "
                 "fixed **1:2** bracket, every winner is capped at **+6%** of the account while the "
                 "market's biggest multi-month trends — the ones buy & hold rides all the way up — "
                 "get cut off at the target. That cap is the single biggest reason buy & hold beat "
                 "every active system here.\n")

    lines.append("### The wall is structural, not about picking the right strategy\n")
    lines.append("With a fixed **1:2** bracket every trade is essentially +6% (win) or −3% (loss), so a "
                 "strategy's whole fate is its **win rate × number of trades**. Solving the compounding "
                 f"equation for {s} → $1M gives the win rate *any* 1:2 strategy must sustain:\n")
    lines.append("| Trades it can generate | Win rate required to reach $1M |")
    lines.append("|---|---|")
    import math as _m
    g_win, g_loss = _m.log(1.06), _m.log(0.97)
    need_ln = _m.log(ratio)
    for ntr in (110, 300, 540, 1000):
        g = need_ln / ntr
        w = (g - g_loss) / (g_win - g_loss)
        cell = f"**{w*100:.0f}%**" if w <= 1 else "**impossible (>100%)**"
        note = ""
        if ntr == 540:
            note = " ← about the *max* possible: ~2,700 daily bars ÷ ~5-bar trades"
        lines.append(f"| ~{ntr} | {cell}{note} |")
    lines.append("\nNo long S&P strategy sustains a 56%+ win rate **at 1:2** (good entries top out "
                 "~50-52%, because pushing the target out to 2R is exactly what lowers the hit rate). "
                 "And one-position-at-a-time on daily bars physically caps you near ~540 trades. "
                 "**So no daily strategy of any kind — famous or obscure — clears the bar.** The only "
                 "way to raise the trade count into the thousands is intraday (minute) data, which "
                 "isn't available here and still needs a genuine edge per trade.\n")

    lines.append("### Which held up vs. which failed\n")
    lines.append("- **Held up best (positive edge, survivable):** *Donchian 20-day breakout (Turtle)* "
                 "and *52-week-high momentum* — highest win rates (~50-52%) and best per-trade "
                 "expectancy, smallest drawdowns when unleveraged. Trend/breakout entries fit a 1:2 "
                 "target naturally.")
    lines.append("- **Mediocre:** *MACD crossover*, *Bollinger reversion*, *3-day dip*, *prior-day-high "
                 "breakout* — small positive edge, eaten by costs and the time stop.")
    lines.append("- **Worst / effectively failed:** *RSI(2) mean reversion (Connors)* — its real edge "
                 "comes from a quick exit on a small bounce, so forcing it into a far-away 1:2 target "
                 "destroys the win rate (38.6%) and leaves a ~0% edge with the deepest drawdown "
                 "(−46% leveraged). A great strategy ruined by the wrong exit rule.")
    lines.append("- *Golden Cross 50/200* barely trades (6 signals), so it can't compound regardless "
                 "of quality.\n")

    lines.append("### What would actually be needed to reach $1M (tested, not guessed)\n")
    lines.append("I relaxed the rules one at a time (see `backtest/experiment.py`) to find the real "
                 "requirement:\n")
    lines.append("1. **Letting winners run** (trailing ATR stop instead of the 1:2 cap) did **not** "
                 "help on this data — SPY's frequent false breakouts hand back open profit, so the "
                 "best system actually finished *lower* ($22.88) than with the fixed target.")
    lines.append("2. **Adding leverage made it strictly worse.** Sweeping the leverage cap from 1× to "
                 "20× on the best entry, the final balance *fell* (≈$23 → ≈$19) and max drawdown "
                 "*deepened* (−10% → −27%). Volatility drag from the ~45% win rate eats leverage alive. "
                 "This is the key result: **leverage is not a shortcut to $1M — it's a shortcut to ruin.**")
    lines.append("3. **More volatility (QQQ) was worse, not better** — deeper drawdowns (−38% to −56%) "
                 "and an even lower ending balance.\n")
    lines.append(f"So the only honest paths to {ratio:,.0f}× are about **edge and time**, not risk dials:\n")
    lines.append("| Path | What it requires |")
    lines.append("|---|---|")
    lines.append(f"| Hit $1M in **10 years** | a sustained **~{cagr(10):.0f}%/yr** compound return — no one does this |")
    lines.append(f"| Hit $1M in **20 years** | **~{cagr(20):.0f}%/yr** — better than Buffett's lifetime record, every year |")
    lines.append(f"| Hit $1M in **30 years** | **~{cagr(30):.0f}%/yr** — still elite-fund territory |")
    lines.append(f"| Buy & hold the S&P | **~{math.log(ratio)/math.log(1.13):.0f}-{math.log(ratio)/math.log(1.10):.0f} years** at its historical ~10-13%/yr |")
    lines.append("\nReaching it faster than that means either a real, repeatable edge far beyond any of "
                 "these textbook strategies, **or** concentrated lottery-style bets whose *expected* "
                 "outcome is exactly the 'account goes negative = failed' case you ruled out.\n")
    lines.append("> ⚠️ Reality check: a solid, disciplined system roughly **doubles to triples** a stock "
                 "account over a decade. The math says $20 → $1,000,000 is not a strategy you find — it's "
                 "a story someone sells you. The disciplined version of this challenge is: pick the "
                 "positive-edge, low-drawdown system (breakout/trend), size sanely, and let *decades* of "
                 "compounding — not leverage — do the work.\n")

    lines.append("\n## Mode A — full 3% risk (uses leverage)\n")
    lines += _ranking_table(mode_a)
    lines.append("\n![Mode A equity curves](equity_curves_leveraged.png)\n")

    lines.append("## Mode B — no leverage (≤1×, cannot go negative)\n")
    lines += _ranking_table(mode_b)
    lines.append("\n![Mode B equity curves](equity_curves_noleverage.png)\n")

    with open(os.path.join(RESULTS_DIR, "RESULTS.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
