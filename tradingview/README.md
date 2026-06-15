# Uptrend Swing Bot — TradingView setup

This is your uptrend swing strategy as a TradingView **Pine Script strategy**,
built for the **1-hour chart** on **XRP/USD *and* BTC/USD (Coinbase)** — it's the
same script, just add it to each chart. TradingView has the real 1h Coinbase data
natively, so you backtest and run it right where the data lives — all from your
phone or browser.

> ~1 trade a day is expected and totally fine — the bot waits for an intact
> uptrend rather than forcing trades.

## 1. Load it (phone or desktop)
1. In TradingView open **XRP/USD** (Coinbase), set the timeframe to **1h**.
2. Open the **Pine Editor** (bottom panel; on mobile use the browser site).
3. Paste the contents of [`uptrend_bot.pine`](uptrend_bot.pine).
4. Tap **Add to chart**.
5. **Repeat for BTC/USD** (Coinbase, 1h) — same script, add it to that chart too.
   Create a separate alert per chart so each symbol trades independently.

## 2. Backtest it (this is your "paper" proof)
- Open the **Strategy Tester** tab. Look at:
  - **Net Profit**, **% Profitable** (you want comfortably above ~34% at 1:2),
    **Profit Factor** (>1.3 is decent), and **Max Drawdown**.
- Tune the inputs (gear icon): **Trend EMA**, **Swing strength**, **Reward:Risk**,
  **Stop buffer**, **Risk %**. Re-check the tester after each change.
- ⚠️ Don't over-tune to make the past look perfect ("curve fitting"). Pick
  settings that are robust across different date ranges, not just the best number.

## 3. Paper-trade with live alerts (no money at risk)
1. Click the **Alarm clock (Alerts)** → **Create Alert**.
2. Condition: **XRP Uptrend Swing Bot** → **alert() function calls only**.
3. Set it to **Once Per Bar Close** and leave the webhook empty for now.
4. You'll get a notification (phone push, if the TradingView app is installed)
   every time the bot would BUY, with the entry/stop/target. Watch it for a few
   weeks and confirm it behaves like the backtest.

## 4. Go live (real money) — later, and carefully
TradingView itself doesn't place Coinbase orders; it sends a **webhook** when an
alert fires, and a connector executes it. Options:
- A webhook→exchange connector (e.g. 3Commas, Pinescript-to-broker services), or
- A small self-hosted webhook receiver that calls the Coinbase API. (I can build
  this in this repo when you're ready — your Coinbase key goes in **environment
  secrets**, never in chat or git.)

### Before any real money
- **Spot only, no leverage** → the account *cannot* go negative.
- Start with an amount you can fully afford to lose (yes, even $20–$50).
- Keep paper-trading running in parallel for a while.
- Past backtest performance does **not** guarantee future results.

## Safety notes baked into the script
- Position is sized to risk your chosen **% of equity**, but **capped at the
  account balance** — it never buys on margin, so a crash can't take you below $0.
- The stop sits just **below the most recent higher low**; the target is **2× the
  risk** distance (your 1:2 rule).
- Orders fill on the **next bar** (no lookahead), so the backtest is honest.
