---
video_id: uJy9XIJq1cQ
title: "Avoiding the False Breakout & Algo Flush 💣 Beginner Day Trading Strategies 🍏"
url: https://www.youtube.com/watch?v=uJy9XIJq1cQ
duration_min: 15
teaching_class: howto
topics: [algo-flush, false-breakout, market-makers, high-frequency-trading, circuit-breaker, volatility]
has_rules: false
---

# Avoiding the False Breakout & Algo Flush

## Summary

Explanation of how algorithmic algo flushes occur when large sell orders hit the bid, causing market makers to pull offers and triggering a cascading selloff. Uses PEVV stock as example where a 1-minute candle dropped from $8.25 to $7.40 (halted). Describes role of high-frequency trading algorithms, market makers responding to order imbalance, and circuit breaker halts as circuit-breaker protection.

## Mechanical rules

_None stated._

## Setups and patterns

- **Algo flush pattern** — large sell orders trigger bid disappearance and flush lower [00:06:46-00:07:14]
- **False breakout setup on PEVV** — double top attempt followed by instant drop [00:07:26-00:08:01]

## Indicators, tools, platforms

- **Level 2 market data** — used to filter and view large block orders [00:09:02-00:10:01]
- **Think or Swim platform** — mentioned for Level 2 filtering capabilities [00:07:12-00:09:13]
- **Circuit breaker halt** — automatic 5-minute halt when stock drops 10% in 5 minutes [00:07:15-00:07:20]

## Numbers and thresholds

- [00:07:31-00:07:35] PEVV stock traded at $8.25, dropped to $7.40 in one 1-minute candle (about 1% drop causing halt)
- [00:10:01] First large sell order: 30,141 shares at $8.00, filled at $8.10
- [00:11:04-00:11:07] Second large sell order: 38,925 shares at $8.01

## Claims needing verification

- [00:06:29-00:06:35] Claims PEVV had 34 million shares of volume but still experienced extreme 2-second drop to halt

## Caption quality notes

No significant caption issues detected.
