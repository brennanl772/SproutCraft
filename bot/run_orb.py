"""Live ORB monitor.

Triggered by GitHub Actions near the open, it watches the watchlist for the
first opening-range breakout of the day and pushes an alert to Telegram. It
alerts each symbol at most once per day and stops at ORB_MONITOR_UNTIL (ET).
"""
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import config
from .data import get_intraday
from .orb import opening_range, first_breakout, make_signal, format_alert
from .notify import send

NY = ZoneInfo("America/New_York")


def _monitor_once(alerted: set) -> None:
    today = datetime.now(NY).date()
    for symbol in config.WATCHLIST:
        if symbol in alerted:
            continue
        try:
            df = get_intraday(symbol, days=2)
        except Exception as exc:
            print(f"[warn] {symbol}: {exc}")
            continue
        day_df = df[df.index.date == today].between_time("09:30", "16:00")
        if day_df.empty:
            continue
        rng = opening_range(day_df)
        if not rng or rng[0] <= rng[1]:
            continue
        breakout = first_breakout(day_df, rng[0], rng[1])
        if not breakout:
            continue
        side, level, ts = breakout
        sig = make_signal(symbol, today, rng[0], rng[1], side, level, ts)
        if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
            send(format_alert(sig))
        alerted.add(symbol)
        print(f"Alerted {symbol}: {side} @ {level}")


def main() -> None:
    hh, mm = (int(x) for x in config.ORB_MONITOR_UNTIL.split(":"))
    stop_at = datetime.now(NY).replace(hour=hh, minute=mm, second=0, microsecond=0)

    alerted: set = set()
    _monitor_once(alerted)  # immediate pass (also makes manual test runs useful)
    while datetime.now(NY) < stop_at and len(alerted) < len(config.WATCHLIST):
        time.sleep(60)
        _monitor_once(alerted)
    print("ORB monitoring finished.")


if __name__ == "__main__":
    main()
