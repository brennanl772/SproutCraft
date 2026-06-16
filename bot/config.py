"""Configuration for the stock signal bot.

Every value can be overridden with an environment variable (handy for
GitHub Actions secrets/vars). Empty env vars fall back to the defaults.
"""
import os


def _str(name: str, default: str) -> str:
    return os.getenv(name) or default


def _int(name: str, default: int) -> int:
    return int(os.getenv(name) or default)


def _float(name: str, default: float) -> float:
    return float(os.getenv(name) or default)


# --- Universe ---------------------------------------------------------------
WATCHLIST = [s.strip().upper() for s in
             _str("WATCHLIST", "SPY,AAPL,MSFT,NVDA,AMZN,GOOGL,META").split(",")
             if s.strip()]

# --- Strategy parameters ----------------------------------------------------
EMA_FAST = _int("EMA_FAST", 20)
EMA_SLOW = _int("EMA_SLOW", 50)
TREND_SMA = _int("TREND_SMA", 200)
ATR_PERIOD = _int("ATR_PERIOD", 14)
ATR_STOP_MULT = _float("ATR_STOP_MULT", 2.0)
RISK_REWARD = _float("RISK_REWARD", 2.0)

# --- Money management (used only to suggest a position size) -----------------
ACCOUNT_SIZE = _float("ACCOUNT_SIZE", 10_000.0)
RISK_PER_TRADE = _float("RISK_PER_TRADE", 0.01)  # fraction of equity per trade

# --- Data -------------------------------------------------------------------
SIGNAL_PERIOD = _str("SIGNAL_PERIOD", "400d")   # lookback for live signals
BACKTEST_PERIOD = _str("BACKTEST_PERIOD", "10y")  # lookback for backtests

# --- Telegram ---------------------------------------------------------------
TELEGRAM_TOKEN = _str("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = _str("TELEGRAM_CHAT_ID", "")
