"""Scan the watchlist for fresh entry signals on the latest daily close and
push any to Telegram. Run once per day after the US close (GitHub Actions).
"""
from . import config
from .data import get_history
from .strategy import Signal, signal_for_latest_bar
from .brain import explain
from .notify import send


def format_signal(sig: Signal, rationale: str | None) -> str:
    shares = 0
    if sig.risk_per_share > 0:
        shares = int((config.ACCOUNT_SIZE * config.RISK_PER_TRADE) / sig.risk_per_share)

    analysis = f"\n<b>Analysis:</b> {rationale}\n" if rationale else ""
    return (
        f"📈 <b>SIGNAL: {sig.side} {sig.symbol}</b>\n"
        f"<i>{sig.date} daily close</i>\n\n"
        f"<b>Trigger:</b> {sig.reason}\n"
        f"{analysis}"
        f"\n<b>Entry:</b> ~${sig.entry} (use next open)\n"
        f"<b>Stop-loss:</b> ${sig.stop_loss}  (risk ${sig.risk_per_share}/share)\n"
        f"<b>Take-profit:</b> ${sig.take_profit}\n"
        f"<b>Risk/Reward:</b> 1:{sig.risk_reward}\n"
        f"<b>Suggested size:</b> {shares} shares "
        f"(risking {config.RISK_PER_TRADE * 100:.0f}% of ${config.ACCOUNT_SIZE:,.0f})\n\n"
        f"⚠️ Mechanical signal + AI commentary — not financial advice. "
        f"It can lose. Manage your risk."
    )


def main() -> None:
    signals: list[Signal] = []
    for symbol in config.WATCHLIST:
        try:
            df = get_history(symbol, period=config.SIGNAL_PERIOD)
            if df.empty:
                continue
            sig = signal_for_latest_bar(symbol, df)
            if sig:
                signals.append(sig)
        except Exception as exc:  # keep scanning the rest of the watchlist
            print(f"[warn] {symbol}: {exc}")

    if not signals:
        print("No new signals on the latest close.")
        return

    for sig in signals:
        rationale = explain(sig)
        send(format_signal(sig, rationale))
        print(f"Sent signal for {sig.symbol}")


if __name__ == "__main__":
    main()
