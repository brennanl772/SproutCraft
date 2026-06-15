"""Bot configuration. Defaults are SAFE: paper mode, tiny size.

Everything can be overridden by environment variables so no secrets or live
flags ever live in the code or git.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _envf(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _envb(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    # --- broker / what to trade ---
    # "alpaca" trades BOTH the S&P (SPY) and crypto (BTC/USD), is free, has paper
    # trading, and is reachable. (Coinbase is crypto-only and blocked here.)
    broker: str = os.environ.get("BOT_BROKER", "alpaca")
    products: list[str] = field(default_factory=lambda:
                                os.environ.get("BOT_PRODUCTS", "SPY,BTC/USD").split(","))
    granularity: str = os.environ.get("BOT_GRANULARITY", "ONE_HOUR")  # 1h chart

    # --- strategy params (match the backtest / Pine bot) ---
    ema_len: int = int(_envf("BOT_EMA_LEN", 20))
    # Swing strength 12 is tuned for the noisy 1h timeframe (filters wiggles so
    # only real higher-lows count). Backtest showed 3 works on daily but loses
    # on 1h; 12 lifts BTC 1h win rate to ~42% and cuts drawdown to ~35%.
    pivot_left: int = int(_envf("BOT_PIVOT_LEFT", 12))
    pivot_right: int = int(_envf("BOT_PIVOT_RIGHT", 12))
    rr: float = _envf("BOT_RR", 2.0)              # 1:2 reward
    stop_buffer: float = _envf("BOT_STOP_BUFFER", 0.001)  # 0.1% below the higher low (support)
    risk_pct: float = _envf("BOT_RISK_PCT", 0.03)         # risk 3% of equity per trade

    # --- SAFETY RAILS (all on by default) ---
    dry_run: bool = _envb("BOT_DRY_RUN", True)            # paper by default; must opt in to live
    max_notional_usd: float = _envf("BOT_MAX_NOTIONAL_USD", 50.0)   # hard cap per position
    daily_loss_limit_usd: float = _envf("BOT_DAILY_LOSS_LIMIT_USD", 10.0)  # kill switch
    require_trade_only_key: bool = _envb("BOT_REQUIRE_TRADE_ONLY_KEY", True)
    poll_seconds: int = int(_envf("BOT_POLL_SECONDS", 300))

    # --- credentials (live only; read from env, never hard-coded) ---
    # Alpaca (recommended): free paper keys from alpaca.markets
    alpaca_key_id: str | None = os.environ.get("APCA_API_KEY_ID")
    alpaca_secret: str | None = os.environ.get("APCA_API_SECRET_KEY")
    # Coinbase (crypto-only alternative)
    api_key_name: str | None = os.environ.get("COINBASE_API_KEY_NAME")
    api_private_key: str | None = os.environ.get("COINBASE_API_PRIVATE_KEY")

    def summary(self) -> str:
        mode = "DRY-RUN (paper)" if self.dry_run else "*** LIVE — REAL MONEY ***"
        return (f"Mode: {mode}\n"
                f"Products: {', '.join(self.products)}  Timeframe: {self.granularity}\n"
                f"Risk/trade: {self.risk_pct*100:.1f}%  R:R 1:{self.rr:g}  "
                f"Stop buffer: {self.stop_buffer*100:.2f}% below support\n"
                f"Max notional/trade: ${self.max_notional_usd:g}  "
                f"Daily loss kill-switch: ${self.daily_loss_limit_usd:g}")
