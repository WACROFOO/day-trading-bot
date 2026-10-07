# Daily review — 2026-10-07

```
SOURCE · research/daily/2026-10-07/ exported 2026-10-07T15:57:58+00:00 from /Users/ayman.benharara/day-trading-bot/data/journal.sqlite
       · decisions 107 · orders 1 · order_events 12 · five_minute 100 · green_run 2 · manual 0 · bars 3790 · log_lines 272
SCORING · refused plans: fill at the trigger if touched within 3 min, A3 trail 1 R, flat 11:30,
          1-minute bars from the desk's own ledger — an UPPER BOUND, no costs, no slippage
! A day is an anecdote. Cohorts decide only at 200 prospective trades, under a preregistered rule.
```

## Funnel — 107 plans armed (37 on loaded history, not counted)

| what happened | plans |
|---|---|
| killed:rising | 34 |
| killed:price | 27 |
| killed:pillars | 3 |
| vwap | 2 |
| volume | 2 |
| before_0700 | 1 |
| taken | 1 |

## Every plan, scored on the day's bars

| ET | symbol | trigger / stop | refused by | if taken (gross R) | how |
|---|---|---|---|---|---|
| 06:56 | LPCN | 2.98 / 2.88 | before_0700 | +0.00 | stop |
| 07:00 | MTEN | 1.35 / 1.30 | killed:price | — | trigger not reached |
| 07:00 | MI | 1.64 / 1.61 | killed:price | -1.00 | stop |
| 07:07 | BIYA | 2.44 / 2.38 | vwap | -0.16 | stop |
| 07:12 | LPCN | 3.23 / 3.10 | volume | -0.46 | stop |
| 07:21 | NCPL | 1.34 / 1.32 | killed:price | — | trigger not reached |
| 07:21 | BIYA | 2.38 / 2.33 | vwap | +0.00 | stop |
| 07:26 | LPCN | 3.67 / 3.55 | taken | +1.41 | stop |
| 07:29 | SXTC | 1.91 / 1.85 | killed:price | +0.83 | stop |
| 07:38 | MTEN | 1.19 / 1.14 | killed:price | — | trigger not reached |
| 07:47 | MI | 1.52 / 1.47 | killed:price | — | trigger not reached |
| 07:53 | MTEN | 1.23 / 1.20 | killed:price | -1.00 | stop |
| 07:54 | LPCN | 3.62 / 3.52 | volume | — | trigger not reached |
| 07:56 | NCPL | 1.30 / 1.28 | killed:price | -1.00 | stop |
| 07:59 | SXTC | 2.04 / 2.00 | killed:rising | — | trigger not reached |
| 08:11 | SDEV | 3.30 / 3.26 | killed:pillars | -0.75 | stop |
| 08:12 | SXTC | 2.02 / 1.99 | killed:rising | +2.01 | stop |
| 08:17 | MTEN | 1.24 / 1.21 | killed:price | -1.00 | stop |
| 08:18 | MI | 1.58 / 1.55 | killed:price | +4.34 | stop |
| 08:19 | SXTC | 4.20 / 3.42 | killed:rising | — | trigger not reached |
| 08:28 | SDEV | 3.27 / 3.21 | killed:pillars | +0.34 | stop |
| 08:29 | LPCN | 2.72 / 2.65 | killed:rising | +0.14 | stop |
| 08:29 | NCPL | 1.30 / 1.26 | killed:price | -0.25 | stop |
| 08:32 | BIYA | 3.61 / 3.25 | killed:rising | -0.75 | stop |
| 08:34 | MTEN | 1.32 / 1.18 | killed:price | +0.43 | stop |
| 08:34 | SXTC | 2.40 / 2.23 | killed:rising | -1.34 | stop |
| 08:38 | LPCN | 2.76 / 2.70 | killed:rising | +1.33 | stop |
| 08:40 | MI | 1.62 / 1.53 | killed:price | +3.11 | stop |
| 08:42 | BIYA | 3.34 / 3.12 | killed:rising | -1.27 | stop |
| 08:46 | SXTC | 2.31 / 2.21 | killed:rising | -1.00 | stop |
| 08:52 | SXTC | 2.29 / 2.21 | killed:rising | -0.13 | stop |
| 08:59 | LPCN | 2.85 / 2.74 | killed:rising | +0.36 | stop |
| 09:01 | MI | 1.77 / 1.68 | killed:price | -0.67 | stop |
| 09:19 | SXTC | 2.85 / 2.67 | killed:rising | -0.62 | stop |
| 09:20 | BIYA | 2.18 / 2.06 | killed:rising | — | trigger not reached |
| 09:21 | LGCL | 2.65 / 2.47 | killed:rising | -0.67 | stop |
| 09:25 | MI | 1.65 / 1.61 | killed:price | +0.03 | stop |
| 09:30 | BIYA | 2.21 / 2.08 | killed:rising | -1.08 | stop |
| 09:34 | LGCL | 2.80 / 2.59 | killed:rising | +0.95 | stop |
| 09:36 | SXTC | 3.07 / 2.69 | killed:rising | — | trigger not reached |
| 09:41 | NCPL | 1.42 / 1.38 | killed:price | — | trigger not reached |
| 09:45 | BIYA | 2.08 / 2.00 | killed:rising | — | trigger not reached |
| 09:47 | MI | 1.70 / 1.60 | killed:price | — | trigger not reached |
| 09:52 | LPCN | 2.60 / 2.52 | killed:rising | -1.00 | stop |
| 09:54 | BIYA | 2.08 / 1.96 | killed:rising | +1.50 | stop |
| 09:54 | MTEN | 1.21 / 1.16 | killed:price | -0.62 | stop |
| 09:55 | MI | 1.71 / 1.66 | killed:price | — | trigger not reached |
| 10:00 | SXTC | 2.35 / 2.22 | killed:rising | -0.54 | stop |
| 10:03 | LGCL | 3.28 / 3.12 | killed:rising | -0.50 | stop |
| 10:13 | LGCL | 3.35 / 3.19 | killed:rising | — | trigger not reached |
| 10:15 | NCPL | 1.34 / 1.31 | killed:price | -0.32 | stop |
| 10:22 | MI | 1.57 / 1.53 | killed:price | -1.00 | stop |
| 10:23 | LPCN | 2.46 / 2.42 | killed:rising | -0.75 | stop |
| 10:27 | NEOG | 11.91 / 11.76 | killed:pillars | — | trigger not reached |
| 10:29 | LGCL | 3.23 / 3.15 | killed:rising | +0.87 | stop |
| 10:33 | SXTC | 2.24 / 2.19 | killed:rising | — | trigger not reached |
| 10:44 | MTEN | 1.11 / 1.06 | killed:price | -0.79 | stop |
| 10:45 | LPCN | 2.26 / 2.22 | killed:rising | -0.64 | stop |
| 10:45 | NCPL | 1.43 / 1.40 | killed:price | -0.68 | stop |
| 10:45 | MI | 1.56 / 1.52 | killed:price | — | trigger not reached |
| 10:47 | SXTC | 2.10 / 1.99 | killed:rising | -0.95 | stop |
| 10:55 | BIYA | 2.05 / 2.01 | killed:rising | -0.75 | stop |
| 11:09 | BIYA | 1.96 / 1.89 | killed:price | -1.00 | stop |
| 11:11 | LGCL | 2.61 / 2.53 | killed:rising | -0.12 | stop |
| 11:13 | MTEN | 1.11 / 1.08 | killed:price | -0.99 | stop |
| 11:13 | SXTC | 2.03 / 1.98 | killed:rising | +0.80 | stop |
| 11:15 | MI | 1.58 / 1.55 | killed:price | — | trigger not reached |
| 11:24 | BIYA | 2.06 / 2.01 | killed:rising | -0.60 | stop |
| 11:29 | LGCL | 2.61 / 2.54 | killed:rising | — | trigger not reached |
| 11:31 | SXTC | 2.24 / 2.14 | killed:rising | — | trigger not reached |

| refused by | filled if taken | mean gross R | best | worst |
|---|---|---|---|---|
| killed:rising | 25 | -0.19 | +2.01 | -1.34 |
| killed:price | 18 | -0.09 | +4.34 | -1.00 |
| vwap | 2 | -0.08 | +0.00 | -0.16 |
| killed:pillars | 2 | -0.21 | +0.34 | -0.75 |
| before_0700 | 1 | +0.00 | +0.00 | +0.00 |
| volume | 1 | -0.46 | -0.46 | -0.46 |
| taken | 1 | +1.41 | +1.41 | +1.41 |

## The bot's own trades — 1 filled

- LPCN 266 @ 3.67 → 3.83 · $+42.56 on the fills, +1.33 R · commission $2.68

## Your trades beside the bot — 0 recorded


## Cohorts toward their prospective test (all days so far)

| cohort | rule it would test | plans | filled | mean gross R | to go |
|---|---|---|---|---|---|
| warmup_macd | B30 (addendum 2026-10-06b) | 0 | 0 | — | 200 |
| ran_past | RA (addendum 2026-10-06c) | 2 | 2 | -0.41 | 198 |
| before_0700 | W4 (addendum 2026-10-06d) | 1 | 1 | +0.00 | 199 |
| five_min_pb | E1 (addendum 2026-10-06b) | 150 | 41 | -0.10 | 159 |

Gross R before costs: the ten-year tests put costs near 0.27-0.39 R a trade, so a cohort needs a gross mean well above that to matter. Nothing on this page changes a rule.
