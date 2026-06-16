"""Lookahead-safe backtest for the trend strategy.

Long-only, one position per symbol at a time. A signal on bar *t* fills at
bar *t+1*'s OPEN (no lookahead). Each open position exits on stop-loss,
take-profit, or an opposite EMA cross — whichever comes first. When both the
stop and the target fall inside the same bar we assume the STOP hit first
(conservative).

Position sizing risks a fixed fraction of equity per trade, compounding.
Reports honest metrics including max drawdown and worst losing streak.
"""
from dataclasses import dataclass

import numpy as np

from . import config
from .data import get_history
from .strategy import compute_indicators


@dataclass
class Trade:
    symbol: str
    entry_date: str
    exit_date: str
    entry: float
    exit: float
    stop: float
    target: float
    reason: str

    @property
    def r_multiple(self) -> float:
        risk = self.entry - self.stop
        return (self.exit - self.entry) / risk if risk > 0 else 0.0


def backtest_symbol(symbol: str, df) -> tuple[list[Trade], dict | None]:
    """Return (closed trades, still-open position or None)."""
    data = compute_indicators(df).dropna()
    rows = list(data.itertuples())
    trades: list[Trade] = []

    in_pos = False
    entry_price = stop = target = 0.0
    entry_date = ""

    for i in range(len(rows) - 1):
        row, nxt = rows[i], rows[i + 1]
        if not in_pos:
            if getattr(row, "entry_signal"):
                entry_price = float(nxt.Open)
                atr_val = float(row.atr)
                stop = entry_price - config.ATR_STOP_MULT * atr_val
                target = entry_price + config.ATR_STOP_MULT * atr_val * config.RISK_REWARD
                entry_date = str(nxt.Index.date())
                in_pos = True
            continue

        exit_price, reason = None, ""
        if float(row.Low) <= stop:
            exit_price, reason = stop, "stop-loss"
        elif float(row.High) >= target:
            exit_price, reason = target, "take-profit"
        elif getattr(row, "exit_signal"):
            exit_price, reason = float(nxt.Open), "ema-exit"

        if exit_price is not None:
            trades.append(Trade(
                symbol, entry_date, str(row.Index.date()),
                round(entry_price, 2), round(exit_price, 2),
                round(stop, 2), round(target, 2), reason,
            ))
            in_pos = False

    open_pos = None
    if in_pos:
        open_pos = {
            "entry_date": entry_date,
            "entry": round(entry_price, 2),
            "stop": round(stop, 2),
            "target": round(target, 2),
        }
    return trades, open_pos


def summarize(trades: list[Trade], starting_equity: float, risk: float) -> dict:
    result = {
        "trades": 0, "win_rate": 0.0, "avg_r": 0.0, "profit_factor": 0.0,
        "total_return_pct": 0.0, "max_drawdown_pct": 0.0,
        "max_loss_streak": 0, "final_equity": starting_equity,
    }
    if not trades:
        return result

    equity = starting_equity
    curve = [equity]
    for t in trades:
        equity += equity * risk * t.r_multiple
        curve.append(equity)
    curve = np.array(curve)
    peak = np.maximum.accumulate(curve)
    max_dd = float(((curve - peak) / peak).min())

    rs = [t.r_multiple for t in trades]
    wins = [r for r in rs if r > 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(r for r in rs if r <= 0))

    streak = worst = 0
    for r in rs:
        streak = streak + 1 if r <= 0 else 0
        worst = max(worst, streak)

    result.update(
        trades=len(trades),
        win_rate=100 * len(wins) / len(trades),
        avg_r=sum(rs) / len(trades),
        profit_factor=(gross_win / gross_loss) if gross_loss else float("inf"),
        total_return_pct=100 * (equity - starting_equity) / starting_equity,
        max_drawdown_pct=100 * max_dd,
        max_loss_streak=worst,
        final_equity=equity,
    )
    return result


def print_report(result: dict, starting_equity: float) -> None:
    print("## Backtest results\n")
    print(f"- Symbols: {', '.join(config.WATCHLIST)}")
    print(f"- Period: {config.BACKTEST_PERIOD}")
    print(f"- Strategy: EMA{config.EMA_FAST}/{config.EMA_SLOW} cross, "
          f"SMA{config.TREND_SMA} trend filter, {config.ATR_STOP_MULT}x ATR stop, "
          f"1:{config.RISK_REWARD:.0f} target")
    print(f"- Risk per trade: {config.RISK_PER_TRADE * 100:.0f}% of equity\n")
    pf = result["profit_factor"]
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Trades | {result['trades']} |")
    print(f"| Win rate | {result['win_rate']:.1f}% |")
    print(f"| Avg R (expectancy) | {result['avg_r']:.2f}R |")
    print(f"| Profit factor | {'∞' if pf == float('inf') else f'{pf:.2f}'} |")
    print(f"| Total return | {result['total_return_pct']:.1f}% |")
    print(f"| Max drawdown | {result['max_drawdown_pct']:.1f}% |")
    print(f"| Max losing streak | {result['max_loss_streak']} |")
    print(f"| Start → end equity | ${starting_equity:,.0f} → ${result['final_equity']:,.0f} |")
    print("\n> Past performance does not predict future results. Simplified "
          "fills, no commissions or slippage. Real trading will differ and can "
          "lose money.")


def run() -> None:
    all_trades: list[Trade] = []
    for symbol in config.WATCHLIST:
        try:
            df = get_history(symbol, period=config.BACKTEST_PERIOD)
        except Exception as exc:
            print(f"[warn] {symbol}: {exc}")
            continue
        if not df.empty:
            trades, _ = backtest_symbol(symbol, df)
            all_trades.extend(trades)

    all_trades.sort(key=lambda t: t.entry_date)
    result = summarize(all_trades, config.ACCOUNT_SIZE, config.RISK_PER_TRADE)
    print_report(result, config.ACCOUNT_SIZE)


if __name__ == "__main__":
    run()
