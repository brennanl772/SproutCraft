# Stock Signal Bot

A Telegram bot that scans a stock watchlist once per day after the US close and
messages you any fresh entry signals — with the reason, stop-loss, take-profit,
risk/reward, and a suggested position size.

**Design (honest):**
- **Deterministic rules decide the trade.** EMA crossover (`EMA20`/`EMA50`) with a
  long-term trend filter (`SMA200`) and an **ATR-based** stop and target. This is
  the part that is backtestable and risk-capped.
- **ChatGPT only explains it.** The OpenAI layer writes the plain-English rationale
  and a risk caution. It never changes the price levels. It's optional — without an
  API key you still get the rule-based reason.

> ⚠️ This is a mechanical strategy, not financial advice and not a guaranteed
> winner. It has losing trades and drawdowns. Run the backtest and judge it on
> real data before risking money. "Never goes negative" does not exist.

## What runs where

Three GitHub Actions (free, no computer needed):
- **`Stock Signals`** — daily cron after market close → sends alerts to Telegram.
- **`Paper Trading`** — daily cron → tracks how the strategy would do with
  *hypothetical* money from your start date, persists a ledger
  (`bot/paper_state.json`), and pings you when a paper position closes. **Watch
  this for a few weeks before risking anything real.**
- **`Backtest`** — run manually (Actions tab → *Run workflow*) → posts real
  historical metrics (win rate, profit factor, **max drawdown**, losing streak)
  to the run summary.

> ⏰ **Scheduling caveat:** GitHub only fires `schedule:` crons from a repo's
> **default branch**. While this lives on a feature branch, the daily runs won't
> auto-trigger — use **Run workflow** (manual dispatch) to test, and merge to the
> default branch once you want the daily cadence.

## One-time setup (all doable from your phone)

### 1. Create the Telegram bot
1. Open Telegram, message **@BotFather**, send `/newbot`, follow the prompts.
2. Copy the **bot token** it gives you (looks like `123456:ABC-DEF...`).
3. Message **@userinfobot** — it replies with your numeric **chat id**.
4. Send your new bot any message once (so it's allowed to DM you).

### 2. Add the secrets/vars in GitHub
Repo → **Settings → Secrets and variables → Actions**.

**Secrets** (encrypted):
| Name | Value |
|---|---|
| `TELEGRAM_TOKEN` | the BotFather token |
| `TELEGRAM_CHAT_ID` | your chat id from @userinfobot |
| `OPENAI_API_KEY` | your OpenAI key (optional — omit to skip AI commentary) |

**Variables** (optional overrides — defaults shown):
| Name | Default |
|---|---|
| `WATCHLIST` | `SPY,AAPL,MSFT,NVDA,AMZN,GOOGL,META` |
| `ACCOUNT_SIZE` | `10000` |
| `RISK_PER_TRADE` | `0.01` (1%) |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `BACKTEST_PERIOD` | `10y` |

### 3. Try it
- Actions → **Backtest** → *Run workflow* → read the metrics in the summary.
- Actions → **Stock Signals** → *Run workflow* to test a live scan (only messages
  you if something triggered today).

## Tuning
All knobs live in `bot/config.py` (or override via the Action variables above):
EMA lengths, trend filter, ATR multiplier, risk/reward, watchlist, risk %.

## Run locally (optional)
```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... OPENAI_API_KEY=...
python -m bot.backtest      # historical metrics
python -m bot.run_signals   # one live scan
```
