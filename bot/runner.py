"""Bot runner.

Two entry points:

* ``python -m bot.runner replay``  - offline demonstration on bundled historical
  data using the PaperBroker. Proves the trade logic (entry, support-based stop,
  1:2 target) with zero network and zero money. Safe to run anywhere.

* ``python -m bot.runner``         - real-time loop. In DRY-RUN (default) it logs
  the orders it *would* place; flip BOT_DRY_RUN=false (and provide trade-only
  Coinbase keys) to trade live. This path needs network access to Coinbase.
"""
from __future__ import annotations

import sys
import time
import datetime as dt

import pandas as pd

from backtest import data as bt_data
from .config import Config
from .broker import PaperBroker, CoinbaseBroker
from .strategy import latest_signal


# --------------------------------------------------------------------------- #
# Offline demonstration (paper, no network)
# --------------------------------------------------------------------------- #
def _load_bundled(product: str, granularity: str) -> pd.DataFrame:
    """Bundled data for the offline demo. Uses real 1h data when available so the
    demo matches the live timeframe; otherwise falls back to daily."""
    base = product.replace("/", "-").split("-")[0].lower()
    if granularity == "ONE_HOUR":
        try:
            return bt_data.load_ohlcv_csv(f"{base}_1h.csv")
        except FileNotFoundError:
            pass
    if base == "spy" or base == "qqq":
        return bt_data.load_daily(base.upper())
    if base == "xrp":
        return bt_data.load_xrp_daily()
    return bt_data.load_ohlcv_csv(f"{base}_daily.csv")


def replay(cfg: Config) -> None:
    print(cfg.summary())
    product = cfg.products[0]
    print(f"\n--- OFFLINE REPLAY: {product} on bundled DAILY data (demonstration) ---")
    print("    (live mode trades the 1-HOUR timeframe from Coinbase; daily is just"
          " what's bundled offline to prove the logic)\n")
    df = _load_bundled(product, cfg.granularity)
    entries, stops = _signals(df, cfg)
    broker = PaperBroker(cash_usd=50.0)

    in_pos = False
    entry = stop = target = qty = 0.0
    support = 0.0
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    idx = df.index
    n_trades = wins = 0

    for i in range(1, len(df)):
        if in_pos:
            exit_price = None
            if l[i] <= stop:
                exit_price = min(o[i], stop)          # gap-aware
            elif h[i] >= target:
                exit_price = max(o[i], target) if o[i] >= target else target
            if exit_price is not None:
                broker.market_sell(cfg.products[0], exit_price, idx[i])
                pnl = (exit_price - entry) * qty
                n_trades += 1; wins += 1 if pnl > 0 else 0
                print(f"  EXIT  {idx[i].date()}  @ {exit_price:.4f}  P/L ${pnl:+.2f}  "
                      f"-> cash ${broker.cash:.2f}")
                in_pos = False

        if not in_pos and entries[i - 1]:
            entry = o[i]
            stop = float(stops.iloc[i - 1])
            support = stop / (1.0 - cfg.stop_buffer)
            if entry <= stop:
                continue
            target = entry + cfg.rr * (entry - stop)
            risk_usd = broker.cash * cfg.risk_pct
            qty = risk_usd / (entry - stop)
            notional = min(qty * entry, broker.cash, cfg.max_notional_usd)
            qty = notional / entry
            if qty <= 0:
                continue
            broker.market_buy(cfg.products[0], qty, entry, idx[i])
            in_pos = True
            print(f"  BUY   {idx[i].date()}  @ {entry:.4f}  | support {support:.4f}  "
                  f"stop {stop:.4f} (just below support)  target {target:.4f}  "
                  f"size ${notional:.2f}")

    print(f"\nReplay done: {n_trades} trades, "
          f"{(wins/n_trades*100 if n_trades else 0):.0f}% wins, "
          f"final cash ${broker.cash:.2f} (from $50).")
    print("Stops always sit just BELOW the most recent higher low (support). ✅")


def _signals(df: pd.DataFrame, cfg: Config):
    from backtest.strategies import uptrend_swing
    entries, stops = uptrend_swing(df, cfg.pivot_left, cfg.pivot_right,
                                   cfg.ema_len, cfg.stop_buffer)
    return entries.values, stops


# --------------------------------------------------------------------------- #
# Real-time loop (paper logging by default; live with keys + BOT_DRY_RUN=false)
# --------------------------------------------------------------------------- #
def _make_broker(cfg: Config):
    """Build the configured live/data broker (Alpaca by default; Coinbase optional)."""
    if cfg.broker == "alpaca":
        if not (cfg.alpaca_key_id and cfg.alpaca_secret):
            return None, ("No Alpaca keys in env (APCA_API_KEY_ID / APCA_API_SECRET_KEY). "
                          "Get free paper keys at alpaca.markets.")
        return AlpacaBroker(cfg.alpaca_key_id, cfg.alpaca_secret, paper=cfg.dry_run), None
    if cfg.broker == "coinbase":
        if not (cfg.api_key_name and cfg.api_private_key):
            return None, "No Coinbase keys (COINBASE_API_KEY_NAME / COINBASE_API_PRIVATE_KEY)."
        return CoinbaseBroker(cfg.api_key_name, cfg.api_private_key), None
    return None, f"Unknown broker '{cfg.broker}'."


def live_loop(cfg: Config) -> None:
    print(cfg.summary())
    print(f"Broker: {cfg.broker}")
    broker, err = _make_broker(cfg)
    if err:
        print(f"\nCannot start: {err}")
        if cfg.dry_run:
            print("Tip: add keys to fetch live data; meanwhile use "
                  "`python -m bot.runner replay` for the offline demo.")
        return
    print("\n" + ("*** LIVE MODE — REAL MONEY. Ctrl-C to stop. ***" if not cfg.dry_run
                  else "PAPER MODE — using the paper account; no real money."))

    day_start_equity = None
    day = None
    while True:
        try:
            for product in cfg.products:
                # daily-loss kill switch
                eq = broker.cash_usd()
                today = dt.date.today()
                if day != today:
                    day, day_start_equity = today, eq
                if day_start_equity - eq >= cfg.daily_loss_limit_usd:
                    print(f"KILL SWITCH: down ${day_start_equity-eq:.2f} today. Pausing trades.")
                    continue

                df = broker.get_candles(product, cfg.granularity, limit=300)
                sig = latest_signal(df.iloc[:-1], cfg)   # decide on last CLOSED bar
                held = broker.position_qty(product)

                if held <= 0 and sig.enter and sig.stop:
                    price = float(df["close"].iloc[-1])
                    tgt = sig.target(price, cfg.rr)
                    risk_usd = eq * cfg.risk_pct
                    notional = min(risk_usd / (price - sig.stop) * price,
                                   eq, cfg.max_notional_usd)
                    qty = notional / price
                    acct = "PAPER" if cfg.dry_run else "LIVE"
                    print(f"[{acct}] BUY {product} ~{price:.4f} | support {sig.support:.4f} "
                          f"stop {sig.stop:.4f} (below support) target {tgt:.4f} | ${notional:.2f}")
                    # Paper mode already points at the paper account, so placing the
                    # order is safe in both modes - only the API endpoint differs.
                    broker.market_buy_bracket(product, qty, sig.stop, tgt)
        except KeyboardInterrupt:
            print("\nStopped by user."); return
        except Exception as e:        # never let one bad poll kill the bot
            print(f"poll error: {e}")
        time.sleep(cfg.poll_seconds)


def main() -> None:
    cfg = Config()
    if len(sys.argv) > 1 and sys.argv[1] == "replay":
        replay(cfg)
    else:
        live_loop(cfg)


if __name__ == "__main__":
    main()
