"""Opening Range Breakout (ORB) strategy.

The 'opening range' is the high and low of the first N minutes after the US
open (09:30 America/New_York). A long signal fires when price trades above the
range high; a short signal when it trades below the range low. The stop is the
opposite end of the range; the target is a multiple of the range height.
Positions are closed by the end of the session — no overnight hold.

Reality check: ORB is a real, widely-traded strategy. It does NOT win every
morning — false breakouts and chop days are normal. Use the backtest (run() /
`python -m bot.orb`) to see the real hit rate before trusting it.
"""
from dataclasses import dataclass
from datetime import time as dtime

import pandas as pd

from . import config

OPEN = dtime(9, 30)
CLOSE = dtime(16, 0)


def _range_end() -> dtime:
    h, m = divmod(30 + config.ORB_RANGE_MINUTES, 60)
    return dtime(9 + h, m)


@dataclass
class ORBSignal:
    symbol: str
    date: str
    time: str
    side: str  # "BUY" (long) or "SELL" (short)
    entry: float
    stop_loss: float
    take_profit: float
    or_high: float
    or_low: float

    @property
    def risk_per_share(self) -> float:
        return round(abs(self.entry - self.stop_loss), 2)

    @property
    def risk_reward(self) -> float:
        risk = abs(self.entry - self.stop_loss)
        reward = abs(self.take_profit - self.entry)
        return round(reward / risk, 1) if risk > 0 else 0.0

    @property
    def reason(self) -> str:
        direction = "above" if self.side == "BUY" else "below"
        return (f"Broke {direction} the {config.ORB_RANGE_MINUTES}-min opening "
                f"range (${self.or_low}–${self.or_high})")


@dataclass
class ORBTrade:
    symbol: str
    date: str
    side: str
    entry: float
    exit: float
    stop: float
    target: float
    reason: str

    @property
    def r_multiple(self) -> float:
        risk = abs(self.entry - self.stop)
        if risk == 0:
            return 0.0
        return (self.exit - self.entry) / risk if self.side == "BUY" \
            else (self.entry - self.exit) / risk


def opening_range(day_df: pd.DataFrame) -> tuple[float, float] | None:
    bars = day_df.between_time(OPEN, _range_end(), inclusive="left")
    if bars.empty:
        return None
    return float(bars["High"].max()), float(bars["Low"].min())


def first_breakout(day_df: pd.DataFrame, or_high: float, or_low: float):
    """Return (side, level, timestamp) of the first breakout, or None."""
    after = day_df.between_time(_range_end(), CLOSE)
    want = config.ORB_DIRECTION
    for ts, row in after.iterrows():
        if want in ("both", "long") and float(row["High"]) >= or_high:
            return "BUY", or_high, ts
        if want in ("both", "short") and float(row["Low"]) <= or_low:
            return "SELL", or_low, ts
    return None


def make_signal(symbol, day, or_high, or_low, side, level, ts) -> ORBSignal:
    height = or_high - or_low
    if side == "BUY":
        stop, target = or_low, level + config.ORB_TARGET_R * height
    else:
        stop, target = or_high, level - config.ORB_TARGET_R * height
    return ORBSignal(
        symbol=symbol, date=str(day), time=ts.strftime("%H:%M"), side=side,
        entry=round(level, 2), stop_loss=round(stop, 2),
        take_profit=round(target, 2),
        or_high=round(or_high, 2), or_low=round(or_low, 2),
    )


def _simulate(sig: ORBSignal, rest: pd.DataFrame) -> tuple[float, str]:
    """Walk the post-entry bars; stop is checked before target (conservative)."""
    for _, row in rest.iterrows():
        high, low = float(row["High"]), float(row["Low"])
        if sig.side == "BUY":
            if low <= sig.stop_loss:
                return sig.stop_loss, "stop"
            if high >= sig.take_profit:
                return sig.take_profit, "target"
        else:
            if high >= sig.stop_loss:
                return sig.stop_loss, "stop"
            if low <= sig.take_profit:
                return sig.take_profit, "target"
    return float(rest.iloc[-1]["Close"]), "eod"


def suggest_shares(entry: float, risk_per_share: float) -> int:
    if config.FIXED_STAKE > 0:
        return int(config.FIXED_STAKE // entry) if entry > 0 else 0
    if risk_per_share > 0:
        return int((config.ACCOUNT_SIZE * config.RISK_PER_TRADE) // risk_per_share)
    return 0


def format_alert(sig: ORBSignal) -> str:
    shares = suggest_shares(sig.entry, sig.risk_per_share)
    label = "🟢 LONG" if sig.side == "BUY" else "🔴 SHORT"
    return (
        f"⚡️ <b>ORB {label} {sig.symbol}</b>\n"
        f"<i>{sig.date} {sig.time} ET</i>\n\n"
        f"<b>Setup:</b> {sig.reason}\n\n"
        f"<b>Entry:</b> ${sig.entry}\n"
        f"<b>Stop-loss:</b> ${sig.stop_loss}  (risk ${sig.risk_per_share}/share)\n"
        f"<b>Take-profit:</b> ${sig.take_profit}  (1:{sig.risk_reward})\n"
        f"<b>Size:</b> {shares} shares\n"
        f"<b>Exit by the close</b> if neither level hits.\n\n"
        f"⚠️ ORB does not win every day — false breakouts happen. Not advice."
    )


# --- Backtest ---------------------------------------------------------------

def backtest_symbol(symbol: str, df: pd.DataFrame) -> list[ORBTrade]:
    trades: list[ORBTrade] = []
    for day in sorted({ts.date() for ts in df.index}):
        day_df = df[df.index.date == day].between_time(OPEN, CLOSE)
        if len(day_df) < 4:
            continue
        rng = opening_range(day_df)
        if not rng or rng[0] <= rng[1]:
            continue
        breakout = first_breakout(day_df, rng[0], rng[1])
        if not breakout:
            continue
        side, level, ts = breakout
        sig = make_signal(symbol, day, rng[0], rng[1], side, level, ts)
        rest = day_df[day_df.index > ts]
        if rest.empty:
            continue
        exit_price, reason = _simulate(sig, rest)
        trades.append(ORBTrade(symbol, str(day), side, sig.entry,
                               round(exit_price, 2), sig.stop_loss,
                               sig.take_profit, reason))
    return trades


def _print_report(result: dict, trades: list[ORBTrade]) -> None:
    days = len({t.date for t in trades})
    print("## ORB backtest results\n")
    print(f"- Symbols: {', '.join(config.WATCHLIST)}")
    print(f"- Window: last ~{config.ORB_BACKTEST_DAYS} sessions, "
          f"{config.ORB_INTERVAL} bars")
    print(f"- Rules: {config.ORB_RANGE_MINUTES}-min range, "
          f"{config.ORB_DIRECTION} breakouts, stop=opposite end, "
          f"target={config.ORB_TARGET_R:g}x range, exit by close\n")
    pf = result["profit_factor"]
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Trades (trading days) | {result['trades']} ({days}) |")
    print(f"| Win rate | {result['win_rate']:.1f}% |")
    print(f"| Avg R (expectancy) | {result['avg_r']:.2f}R |")
    print(f"| Profit factor | {'∞' if pf == float('inf') else f'{pf:.2f}'} |")
    print(f"| Total return | {result['total_return_pct']:.1f}% |")
    print(f"| Max drawdown | {result['max_drawdown_pct']:.1f}% |")
    print(f"| Max losing streak | {result['max_loss_streak']} |")
    print("\n> Only ~60 days of intraday data are available for free, so this is "
          "a SMALL sample — treat it as a sanity check, not proof. Past results "
          "don't predict the future; real fills include slippage and can lose.")


def run() -> None:
    from .data import get_intraday
    from .backtest import summarize

    all_trades: list[ORBTrade] = []
    for symbol in config.WATCHLIST:
        try:
            df = get_intraday(symbol, days=config.ORB_BACKTEST_DAYS)
        except Exception as exc:
            print(f"[warn] {symbol}: {exc}")
            continue
        if not df.empty:
            all_trades.extend(backtest_symbol(symbol, df))

    all_trades.sort(key=lambda t: t.date)
    result = summarize(all_trades, config.ACCOUNT_SIZE, config.RISK_PER_TRADE)
    _print_report(result, all_trades)


if __name__ == "__main__":
    run()
