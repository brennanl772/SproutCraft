# Uptrend Swing Bot (Alpaca)

Runs your strategy live or on paper: **longs only · higher highs + higher lows +
price > EMA · stop just below the most recent higher low (support) · take profit
at 2× risk · spot only (no leverage → can't go negative).**

Defaults to **Alpaca**, which trades **both the S&P (SPY) and crypto (BTC/USD)**,
is free, has a paper account, and is reachable. (Coinbase/Kraken/Robinhood are
either crypto-only, lack an official stock API, or are blocked here.)

## Safety rails (all on by default)
- **Paper by default** (`BOT_DRY_RUN=true`) — uses the Alpaca *paper* account, no real money.
- **Spot only**, sized so notional never exceeds your cash → account cannot go negative.
- **Max notional per trade** (`BOT_MAX_NOTIONAL_USD`, default $50) and a
  **daily-loss kill switch** (`BOT_DAILY_LOSS_LIMIT_USD`, default $10).
- Stock entries use a native **bracket order** so the stop + 1:2 target sit on the exchange.

## Try it now — offline, no account
```bash
pip install -r requirements.txt
python -m bot.runner replay            # demo on bundled BTC 1h data
BOT_PRODUCTS="SPY" python -m bot.runner replay
```
Every trade prints its support level, the stop just below it, and the 2× target.

## Paper-trade live (free Alpaca keys)
1. alpaca.markets → sign up (free, no card for paper) → **Paper Trading → API Keys → Generate**.
2. Put them in the environment (never in chat/git):
   `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`.
3. Run:
   ```bash
   python -m bot.runner                # PAPER mode, polls + trades the paper account
   ```
   This is also how I'll **validate SPY on the 1-hour timeframe** (Alpaca gives me
   the intraday data I can't get otherwise).

## Go live (real money) — only after paper looks good
```bash
BOT_DRY_RUN=false python -m bot.runner   # *** routes to the LIVE account ***
```
Use **trade-only** API keys, keep `BOT_MAX_NOTIONAL_USD` small, and run it on an
always-on host (a cheap cloud box) since it must run 24/7 — not in a temporary session.

## Validation status (honest)
| Market / timeframe | Status |
|---|---|
| BTC 1h | ✅ backtested on real data (tuned pivot=12): profitable, ~−35% max DD |
| SPY daily | ✅ backtested: $50→$79, 49% win, −14% DD |
| **SPY 1h** | ⏳ **not yet validated** — needs Alpaca intraday data (add paper keys and I'll run it) |

> Not financial advice. Backtests don't guarantee the future. Start small.
