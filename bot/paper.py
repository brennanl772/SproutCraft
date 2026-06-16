"""Forward paper-trading tracker.

Watches the same mechanical strategy trade *hypothetically* from the day you
start, so you can see how it would have done with no real money on the line.

It is idempotent: each run rebuilds the picture from price history and counts
only trades whose entry is on/after the recorded start date, then persists a
JSON ledger. Missing or double runs can't corrupt the book.
"""
import json
import os
from datetime import date

from . import config
from .backtest import backtest_symbol, summarize


def _today() -> str:
    return date.today().isoformat()


class PaperBook:
    def __init__(self, path: str):
        self.path = path
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path) as fh:
                return json.load(fh)
        return {
            "start_date": _today(),
            "starting_equity": config.ACCOUNT_SIZE,
            "equity": config.ACCOUNT_SIZE,
            "closed": [],
            "open": {},
        }

    def save(self) -> None:
        with open(self.path, "w") as fh:
            json.dump(self.state, fh, indent=2)

    def update(self, history_fn):
        """Recompute the forward book. history_fn(symbol) -> OHLC DataFrame."""
        start = self.state["start_date"]
        prev_ids = {(c["symbol"], c["entry_date"]) for c in self.state["closed"]}

        closed, open_pos = [], {}
        for symbol in config.WATCHLIST:
            try:
                df = history_fn(symbol)
            except Exception as exc:
                print(f"[warn] {symbol}: {exc}")
                continue
            if df is None or df.empty:
                continue
            trades, op = backtest_symbol(symbol, df)
            closed.extend(t for t in trades if t.entry_date >= start)
            if op and op["entry_date"] >= start:
                open_pos[symbol] = op

        closed.sort(key=lambda t: t.exit_date)
        equity = config.ACCOUNT_SIZE
        for t in closed:
            equity += equity * config.RISK_PER_TRADE * t.r_multiple

        stats = summarize(closed, config.ACCOUNT_SIZE, config.RISK_PER_TRADE)
        new_closed = [t for t in closed if (t.symbol, t.entry_date) not in prev_ids]

        self.state["equity"] = round(equity, 2)
        self.state["closed"] = [
            {"symbol": t.symbol, "entry_date": t.entry_date, "exit_date": t.exit_date,
             "entry": t.entry, "exit": t.exit, "reason": t.reason,
             "r": round(t.r_multiple, 2)}
            for t in closed
        ]
        self.state["open"] = open_pos
        return self.summary(stats, new_closed, open_pos), new_closed

    def summary(self, stats: dict, new_closed: list, open_pos: dict) -> str:
        eq = self.state["equity"]
        ret = 100 * (eq - config.ACCOUNT_SIZE) / config.ACCOUNT_SIZE
        lines = [
            f"🧾 <b>Paper trading update</b> ({_today()})",
            f"Equity: ${eq:,.0f} ({ret:+.1f}% since {self.state['start_date']})",
        ]
        if new_closed:
            lines.append(f"\n<b>Closed since last run:</b> {len(new_closed)}")
            for t in new_closed:
                mark = "✅" if t.r_multiple > 0 else "❌"
                lines.append(f"  {mark} {t.symbol} {t.r_multiple:+.2f}R ({t.reason})")
        lines.append(f"\n<b>Open positions:</b> {len(open_pos)}")
        for sym, op in open_pos.items():
            lines.append(f"  • {sym}: entry ${op['entry']}, stop ${op['stop']}, "
                         f"target ${op['target']}")
        lines.append(f"\nTo date: {stats['trades']} trades, "
                     f"win rate {stats['win_rate']:.0f}%, "
                     f"max drawdown {stats['max_drawdown_pct']:.1f}%")
        lines.append("⚠️ Hypothetical — no real money. Mechanical strategy; "
                     "past results don't predict the future.")
        return "\n".join(lines)
