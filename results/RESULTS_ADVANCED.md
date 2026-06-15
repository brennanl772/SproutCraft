# Advanced analysis — $50 → $1,000,000

## 1) All available timeframes (no leverage, fixed 1:2)

| Timeframe | Bars | Best strategy | Final | Reached $1M? | Went neg? |
|---|---|---|---|---|---|
| Daily SPY (2015-2025) | 2703 | Buy & Hold (1x, benchmark) | $194.24 | no | no |
| Weekly SPY (2015-2025) | 562 | Buy & Hold (1x, benchmark) | $194.24 | no | no |
| Monthly S&P total-return (1871-2026) | 1865 | Buy & Hold (1x, benchmark) | $54.63M | YES | no |

*Even with 150 years of monthly data, buy & hold compounding is the ceiling — and only the 150-year run gets into seven figures, purely from time, not trading.*

## 2) Is there a better exit than fixed 1:2?

**Trend entry (Donchian breakout), daily, no leverage:**

| Exit rule | Final | Win % | Trades | Max DD |
|---|---|---|---|---|
| 1:1 target | $86.71 | 61.3 | 212 | -10.7% |
| 1:2 target | $109.76 | 51.8 | 110 | -9.6% |
| 1:3 target | $104.85 | 40.9 | 88 | -9.7% |
| trailing stop (let it run) | $57.19 | 44.5 | 146 | -10.2% |

**Mean-reversion entry (Connors RSI-2), daily, no leverage:**

| Exit rule | Final | Win % | Trades |
|---|---|---|---|
| 1:0.5 (quick target) | $39.67 | 63.6 | 121 |
| 1:1 | $40.56 | 50.9 | 108 |
| 1:2 | $49.75 | 38.6 | 101 |
| 1:3 | $59.86 | 32.1 | 84 |

*Lesson: the 'best' reward ratio depends on the edge. Trend/breakout entries like a wider target or a trailing stop; mean-reversion entries want a small, quick target (high win rate). Forcing every strategy into 1:2 is itself suboptimal — but no single exit rule gets any of them near $1M.*

## 3) Tapering risk from high → 3% (Donchian, daily)

Risk starts high while the account is small and decays to 3% as it grows.

| Risk schedule | Mode | Final | Reached $1M? | Peak lev | Max DD | Went negative? |
|---|---|---|---|---|---|---|
| flat 3% | no-leverage ≤1× | $109.76 | no | 1.0x | -9.6% | no |
| flat 3% | leverage allowed | $184.10 | no | 5.3x | -18.6% | no |
| 10% → 3% | no-leverage ≤1× | $121.59 | no | 1.0x | -9.6% | no |
| 10% → 3% | leverage allowed | $1.27K | no | 16.7x | -45.9% | no |
| 25% → 3% | no-leverage ≤1× | $121.59 | no | 1.0x | -9.6% | no |
| 25% → 3% | leverage allowed | $7.02K | no | 39.1x | -75.1% | no |
| 50% → 3% | no-leverage ≤1× | $121.59 | no | 1.0x | -9.6% | no |
| 50% → 3% | leverage allowed | $0.12 | no | 88.8x | -100.0% | no |

*Key trade-off: tapering risk up early only speeds things in **leverage-allowed** mode (no-leverage caps the real risk at the stop distance, so high targets do nothing). And the moment leverage is high enough to matter, a gap can drive the account negative — which is the exact failure you forbade. There is no setting that is both fast AND guaranteed non-negative.*
