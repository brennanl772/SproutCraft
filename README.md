# SproutCraft — Strategy Backtester

A small, honest backtesting toolkit that answers a specific challenge:

> Starting with **$50**, risking **3%** per trade with a **1:2** reward, trading
> the **S&P 500 (SPY)** long — which well-known strategy compounds to
> **$1,000,000** fastest without the account ever going negative?

It tests a battery of famous, objectively-defined strategies on **real**
historical data, sizes positions by the 3%/1:2 risk rule, and reports which got
furthest, which held up long term, and which failed.

## TL;DR result

**None of them reach $1,000,000** — and the reason is structural, not a matter of
picking the "right" strategy. With a fixed 1:2 bracket, a strategy's fate is just
`win rate × number of trades`, and daily S&P data physically caps you near ~540
non-overlapping trades. To hit $1M you'd need a **56%+ win rate sustained at 1:2**
(no long S&P strategy does — good entries top out ~50-52%). **Leverage makes it
worse, not better** (volatility drag). Plain **buy & hold beat every active
strategy.** Full analysis with tables and charts in
[`results/RESULTS.md`](results/RESULTS.md).

## Run it

```bash
pip install -r requirements.txt
python -m backtest.run         # main challenge -> console + results/RESULTS.md + charts
python -m backtest.experiment  # "what would it actually take?" (trailing stops, leverage sweep, QQQ)
python -m backtest.advanced    # all timeframes + exit-rule comparison + tapered risk -> results/RESULTS_ADVANCED.md
```

## Layout

| File | Purpose |
|------|---------|
| `backtest/data.py` | Loads the bundled real datasets (SPY/QQQ daily; Shiller monthly). |
| `backtest/strategies.py` | 14 well-known entry strategies (RSI-2/Connors, Turtle/Donchian, IBS, Williams %R, MACD, momentum, etc.). |
| `backtest/sim.py` | Position-sizing growth simulator (3% risk, 1:2 bracket, ATR stop, optional trailing, leverage cap, fail-on-negative). |
| `backtest/engine.py`, `metrics.py` | Lookahead-safe return engine + performance metrics (Sharpe, Sortino, max DD, etc.). |
| `backtest/run.py` | Runs the full challenge and writes the report + charts. |
| `backtest/experiment.py` | Empirically tests what it would take to actually reach $1M. |
| `backtest/advanced.py` | Multi-timeframe (daily/weekly/150yr monthly), exit-rule comparison, and tapered-risk analysis. |
| `backtest/alpaca_data.py` | Free Alpaca market-data loader (set `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY`) — pulls daily *and* intraday bars. |
| `data/` | Real historical data (SPY/QQQ daily 2015-2025; Shiller S&P monthly 1871-present). |
| `results/` | Generated report and equity-curve charts. |

## Method notes (so the numbers are trustworthy)

- **No lookahead:** signals computed at a bar's close are filled at the *next*
  bar's open.
- **Costs:** 5 bps per side (commission + slippage).
- **One position at a time**, 60-bar time stop.
- **Position sizing:** size set so a stop-out loses exactly 3% of the account,
  which implies leverage on tight stops. A "no leverage (≤1×)" mode is also run —
  the only configuration that *cannot* go negative under any gap.
- Data is dividend/split adjusted (total-return basis).

> ⚠️ This is research/education, not financial advice. Past results don't predict
> the future, and "$X → $1,000,000" challenges are marketing, not strategies.
