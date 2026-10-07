# Daily review — 2026-10-06

```
SOURCE · research/daily/2026-10-06/ exported 2026-10-07T15:57:57+00:00 from /Users/ayman.benharara/day-trading-bot/data/journal.sqlite
       · decisions 91 · orders 2 · order_events 9 · five_minute 57 · green_run 11 · manual 0 · bars 3841 · log_lines 787
SCORING · refused plans: fill at the trigger if touched within 3 min, A3 trail 1 R, flat 11:30,
          1-minute bars from the desk's own ledger — an UPPER BOUND, no costs, no slippage
! A day is an anecdote. Cohorts decide only at 200 prospective trades, under a preregistered rule.
```

## Funnel — 91 plans armed (42 on loaded history, not counted)

| what happened | plans |
|---|---|
| killed:price | 18 |
| volume | 9 |
| vwap | 7 |
| killed:pillars | 5 |
| killed:rising | 3 |
| ran_past | 2 |
| taken | 2 |
| macd | 1 |
| stop_under_2pct | 1 |
| stop_inside_spread | 1 |

## Every plan, scored on the day's bars

| ET | symbol | trigger / stop | refused by | if taken (gross R) | how |
|---|---|---|---|---|---|
| 07:14 | SDEV | 4.03 / 3.98 | killed:pillars | — | trigger not reached |
| 07:17 | OLOX | 1.62 / 1.59 | killed:price | -0.67 | stop |
| 07:21 | SDEV | 3.93 / 3.84 | killed:rising | -0.55 | stop |
| 07:32 | IPDN | 4.16 / 3.68 | volume | +1.35 | stop |
| 07:35 | NXAT | 1.11 / 0.93 | killed:price | — | trigger not reached |
| 07:46 | JAGX | 6.30 / 6.24 | vwap | +2.50 | stop |
| 07:50 | OLOX | 1.45 / 1.41 | killed:price | -1.00 | stop |
| 07:53 | IPDN | 4.46 / 4.24 | volume | -0.27 | stop |
| 08:00 | NXAT | 0.72 / 0.69 | killed:price | -0.20 | stop |
| 08:01 | IPDN | 5.28 / 4.83 | ran_past | -0.64 | stop |
| 08:05 | OLOX | 1.48 / 1.43 | killed:price | -1.00 | stop |
| 08:09 | AIXI | 3.29 / 3.22 | killed:pillars | -0.63 | stop |
| 08:14 | OLOX | 1.45 / 1.42 | killed:price | -0.33 | stop |
| 08:14 | JAGX | 6.36 / 6.28 | vwap | -0.12 | stop |
| 08:19 | WHLR | 1.29 / 1.27 | killed:price | -0.51 | stop |
| 08:27 | AIXI | 3.36 / 3.24 | killed:pillars | — | trigger not reached |
| 08:40 | JAGX | 6.41 / 6.33 | volume | +0.12 | stop |
| 08:43 | OLOX | 1.43 / 1.39 | killed:price | +2.00 | stop |
| 08:44 | NXAT | 0.77 / 0.74 | killed:price | -0.88 | stop |
| 08:50 | WHLR | 1.18 / 1.14 | killed:price | -1.00 | stop |
| 09:00 | IPDN | 6.26 / 6.04 | ran_past | -0.18 | stop |
| 09:03 | AIXI | 3.23 / 3.17 | killed:pillars | -0.20 | stop |
| 09:10 | NXAT | 0.76 / 0.72 | killed:price | -0.47 | stop |
| 09:14 | IPDN | 6.21 / 6.10 | macd | +0.55 | stop |
| 09:22 | IPDN | 6.51 / 6.32 | taken | -0.68 | stop |
| 09:24 | JAGX | 6.51 / 6.45 | stop_under_2pct | +1.00 | stop |
| 09:40 | JAGX | 6.34 / 6.15 | vwap | +1.11 | stop |
| 09:46 | OLOX | 1.52 / 1.45 | killed:price | — | trigger not reached |
| 09:47 | NXAT | 0.74 / 0.71 | killed:price | — | trigger not reached |
| 09:52 | IPDN | 5.88 / 5.41 | volume | -0.04 | stop |
| 09:56 | AIXI | 2.35 / 2.28 | killed:pillars | +0.04 | stop |
| 10:02 | IPDN | 5.51 / 5.39 | vwap | +2.25 | stop |
| 10:04 | APUS | 6.49 / 5.92 | volume | -0.89 | stop |
| 10:10 | JAGX | 6.49 / 6.34 | volume | -0.27 | stop |
| 10:12 | IPDN | 5.42 / 5.24 | vwap | -1.22 | stop |
| 10:13 | AIFA | 8.21 / 7.84 | stop_inside_spread | +0.03 | stop |
| 10:23 | APUS | 6.98 / 6.54 | volume | -1.00 | stop |
| 10:25 | OLOX | 1.41 / 1.37 | killed:price | +3.75 | stop |
| 10:30 | JAGX | 6.32 / 6.19 | vwap | -0.15 | stop |
| 10:30 | APUS | 6.82 / 6.30 | volume | +0.05 | stop |
| 10:33 | IPDN | 4.80 / 4.71 | killed:rising | -0.78 | stop |
| 10:38 | AIFA | 8.61 / 8.41 | volume | -0.62 | stop |
| 10:38 | OLOX | 1.64 / 1.55 | killed:price | +0.11 | stop |
| 10:46 | APUS | 6.19 / 6.07 | vwap | -0.75 | stop |
| 10:48 | IPDN | 4.42 / 4.31 | killed:rising | -0.82 | stop |
| 10:48 | OLOX | 1.65 / 1.57 | killed:price | -0.62 | stop |
| 10:58 | APUS | 6.36 / 6.19 | taken | -0.65 | stop |
| 11:14 | OLOX | 1.45 / 1.41 | killed:price | -0.87 | stop |
| 11:25 | AIXI | 1.88 / 1.84 | killed:price | — | trigger not reached |

| refused by | filled if taken | mean gross R | best | worst |
|---|---|---|---|---|
| killed:price | 14 | -0.12 | +3.75 | -1.00 |
| volume | 9 | -0.17 | +1.35 | -1.00 |
| vwap | 7 | +0.51 | +2.50 | -1.22 |
| killed:rising | 3 | -0.72 | -0.55 | -0.82 |
| killed:pillars | 3 | -0.26 | +0.04 | -0.63 |
| ran_past | 2 | -0.41 | -0.18 | -0.64 |
| taken | 2 | -0.67 | -0.65 | -0.68 |
| macd | 1 | +0.55 | +0.55 | +0.55 |
| stop_under_2pct | 1 | +1.00 | +1.00 | +1.00 |
| stop_inside_spread | 1 | +0.03 | +0.03 | +0.03 |

## The bot's own trades — 2 filled

- IPDN 153 @ 6.52 → 6.33 · $-29.07 on the fills, -1.00 R · commission $2.02
- APUS 190 @ 6.38 → 6.25 · $-24.70 on the fills, -0.76 R · commission $2.03

## Your trades beside the bot — 0 recorded


## Cohorts toward their prospective test (all days so far)

| cohort | rule it would test | plans | filled | mean gross R | to go |
|---|---|---|---|---|---|
| warmup_macd | B30 (addendum 2026-10-06b) | 0 | 0 | — | 200 |
| ran_past | RA (addendum 2026-10-06c) | 2 | 2 | -0.41 | 198 |
| before_0700 | W4 (addendum 2026-10-06d) | 0 | 0 | — | 200 |
| five_min_pb | E1 (addendum 2026-10-06b) | 52 | 17 | -0.11 | 183 |

Gross R before costs: the ten-year tests put costs near 0.27-0.39 R a trade, so a cohort needs a gross mean well above that to matter. Nothing on this page changes a rule.
