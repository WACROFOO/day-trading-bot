# Daily review — 2026-10-12

```
SOURCE · research/daily/2026-10-12/ exported 2026-10-13T13:15:25+00:00 from /Users/ayman.benharara/day-trading-bot/data/journal.sqlite
       · decisions 105 · screener 0 · board 12 · orders 5 · order_events 44 · five_minute 86 · green_run 18 · manual 0 · desk_calls 0 · bars 3725 · board_bars 4091 · log_lines 339
SCORING · refused plans: fill at the trigger if touched within 3 min, A3 trail 1 R, flat 11:30,
          1-minute bars from the desk's own ledger — an UPPER BOUND, no costs, no slippage
! A day is an anecdote. Cohorts decide only at 200 prospective trades, under a preregistered rule.
```

## Funnel — 105 plans armed (38 on loaded history, not counted)

| what happened | plans |
|---|---|
| killed:rising | 27 |
| killed:price | 18 |
| killed:pillars | 6 |
| taken | 5 |
| volume | 5 |
| ema9 | 2 |
| stale | 1 |
| vwap | 1 |
| macd | 1 |
| after_cutoff | 1 |

## Every plan, scored on the day's bars

| ET | symbol | trigger / stop | refused by | if taken (gross R) | how |
|---|---|---|---|---|---|
| 07:15 | MNDR | 2.35 / 2.05 | stale | -0.67 | stop |
| 07:16 | NCPL | 1.52 / 1.47 | killed:price | -0.40 | stop |
| 07:19 | MEDS | 3.54 / 3.44 | killed:rising | -0.10 | stop |
| 07:22 | MNDR | 2.71 / 2.50 | taken | -0.81 | stop |
| 07:25 | YMAT | 2.82 / 2.71 | killed:rising | -0.91 | stop |
| 07:31 | MNDR | 2.36 / 1.99 | volume | -0.81 | stop |
| 07:36 | YMAT | 2.86 / 2.79 | killed:rising | +0.16 | stop |
| 07:50 | CTNM | 12.91 / 12.89 | killed:pillars | -35.00 | stop |
| 07:51 | LNKS | 1.30 / 1.26 | killed:price | — | trigger not reached |
| 07:52 | MNDR | 2.19 / 2.01 | volume | +0.39 | stop |
| 07:54 | YMAT | 2.75 / 2.66 | killed:rising | -0.67 | stop |
| 07:56 | MEDS | 3.28 / 3.24 | killed:rising | -0.79 | stop |
| 08:04 | CTNM | 10.01 / 9.90 | killed:pillars | -9.64 | stop |
| 08:09 | MNDR | 2.29 / 2.14 | taken | -0.63 | stop |
| 08:11 | MEDS | 3.56 / 3.45 | vwap | -0.91 | stop |
| 08:15 | YMAT | 2.80 / 2.74 | killed:rising | -1.83 | stop |
| 08:16 | LNKS | 1.29 / 1.25 | killed:price | -0.75 | stop |
| 08:24 | MNDR | 2.59 / 2.39 | taken | -0.15 | stop |
| 08:25 | YMAT | 2.80 / 2.74 | killed:rising | -1.00 | stop |
| 08:36 | NCPL | 1.47 / 1.44 | killed:price | -1.00 | stop |
| 08:37 | LNKS | 1.27 / 1.24 | killed:price | -1.00 | stop |
| 08:45 | YMAT | 2.69 / 2.62 | killed:rising | +3.29 | stop |
| 08:49 | GIXI | 6.51 / 6.32 | killed:rising | — | trigger not reached |
| 08:53 | CLWT | 2.23 / 2.12 | volume | — | trigger not reached |
| 09:03 | GIXI | 5.78 / 5.64 | killed:rising | -0.93 | stop |
| 09:04 | MNDR | 2.35 / 2.23 | taken | -0.17 | stop |
| 09:09 | LNKS | 1.28 / 1.24 | killed:price | +0.27 | stop |
| 09:11 | CLWT | 2.10 / 2.02 | killed:rising | +0.12 | stop |
| 09:12 | YMAT | 2.74 / 2.70 | killed:rising | -1.00 | stop |
| 09:19 | NCPL | 1.49 / 1.46 | killed:price | -1.00 | stop |
| 09:29 | GIXI | 6.09 / 5.82 | killed:rising | +0.30 | stop |
| 09:36 | MNDR | 3.36 / 3.10 | taken | -1.06 | stop |
| 09:38 | YMAT | 2.21 / 2.13 | killed:rising | +1.37 | stop |
| 09:38 | CLWT | 2.29 / 2.12 | volume | -0.82 | stop |
| 09:38 | NCPL | 1.56 / 1.49 | killed:price | -0.93 | stop |
| 09:40 | LNKS | 1.49 / 1.41 | killed:price | -1.25 | stop |
| 09:42 | SKYA | 2.42 / 2.36 | killed:pillars | +0.52 | stop |
| 09:49 | NCPL | 1.55 / 1.51 | killed:price | -0.50 | stop |
| 09:51 | CLWT | 2.17 / 2.04 | killed:rising | -0.20 | stop |
| 09:56 | SKYA | 2.58 / 2.52 | killed:pillars | -0.52 | stop |
| 09:56 | GIXI | 5.74 / 5.44 | killed:rising | +1.40 | stop |
| 10:00 | MNDR | 3.09 / 3.02 | macd | +1.00 | stop |
| 10:00 | YMAT | 2.09 / 2.04 | killed:rising | -0.82 | stop |
| 10:03 | SKYA | 2.57 / 2.49 | killed:pillars | +0.13 | stop |
| 10:11 | CLWT | 2.07 / 1.99 | killed:rising | -0.38 | stop |
| 10:12 | DAIC | 2.01 / 1.95 | killed:rising | -0.36 | stop |
| 10:17 | GIXI | 6.78 / 6.76 | killed:rising | -0.50 | stop |
| 10:19 | LNKS | 1.42 / 1.37 | killed:price | -0.80 | stop |
| 10:20 | YMAT | 2.14 / 2.08 | killed:rising | +1.54 | stop |
| 10:24 | MNDR | 4.53 / 4.51 | ema9 | +23.58 | stop |
| 10:35 | NCPL | 1.69 / 1.62 | killed:price | — | trigger not reached |
| 10:35 | LNKS | 1.30 / 1.25 | killed:price | +2.60 | stop |
| 10:39 | DAIC | 1.94 / 1.90 | killed:price | +1.02 | stop |
| 10:44 | CLWT | 2.08 / 2.03 | killed:rising | — | trigger not reached |
| 10:54 | DAIC | 2.04 / 2.01 | killed:rising | -3.09 | stop |
| 10:56 | LNKS | 1.46 / 1.40 | killed:price | +0.16 | stop |
| 10:59 | MNDR | 4.18 / 4.00 | ema9 | +2.28 | stop |
| 10:59 | GIXI | 7.16 / 6.82 | killed:rising | — | trigger not reached |
| 11:01 | SKYA | 2.63 / 2.60 | killed:pillars | -1.00 | stop |
| 11:05 | CLWT | 1.81 / 1.75 | killed:price | +0.03 | stop |
| 11:05 | YMAT | 3.25 / 3.08 | killed:rising | +0.06 | stop |
| 11:09 | DAIC | 2.00 / 1.97 | killed:price | -1.00 | stop |
| 11:15 | MNDR | 4.60 / 4.44 | volume | +2.13 | stop |
| 11:23 | YMAT | 3.08 / 2.97 | killed:rising | -2.09 | stop |
| 11:24 | DAIC | 2.04 / 2.01 | killed:rising | +2.51 | flat 11:30 |
| 11:24 | MNDR | 5.28 / 4.92 | after_cutoff | -0.97 | stop |
| 11:25 | CLWT | 1.78 / 1.74 | killed:price | +1.03 | flat 11:30 |

| refused by | filled if taken | mean gross R | best | worst |
|---|---|---|---|---|
| killed:rising | 24 | -0.16 | +3.29 | -3.09 |
| killed:price | 16 | -0.22 | +2.60 | -1.25 |
| killed:pillars | 6 | -7.59 | +0.52 | -35.00 |
| taken | 5 | -0.56 | -0.15 | -1.06 |
| volume | 4 | +0.22 | +2.13 | -0.82 |
| ema9 | 2 | +12.93 | +23.58 | +2.28 |
| stale | 1 | -0.67 | -0.67 | -0.67 |
| vwap | 1 | -0.91 | -0.91 | -0.91 |
| macd | 1 | +1.00 | +1.00 | +1.00 |
| after_cutoff | 1 | -0.97 | -0.97 | -0.97 |

## The bot's own trades — 5 filled

- MNDR 166 @ 2.70 → 2.53 · $-28.22 on the fills, -0.81 R · commission $2.01
- MNDR 222 @ 2.29 → 2.20 · $-19.98 on the fills, -0.60 R · commission $2.23
- MNDR 173 @ 2.60 → 2.60 · $+0.00 on the fills, +0.00 R · commission $2.01
- MNDR 266 @ 2.36 → 2.37 · $+2.66 on the fills, +0.08 R · commission $2.67
- MNDR 137 @ 3.37 → 3.28 · $-12.33 on the fills, -0.35 R · commission $2.01

## Your trades beside the bot — 0 recorded


## Your calls on the desk — 0 recorded

None. The desk's buttons (I took it / I passed / I closed it) write them.

## Cohorts toward their prospective test (all days so far)

| cohort | rule it would test | plans | filled | mean gross R | to go |
|---|---|---|---|---|---|
| warmup_macd | B30 (addendum 2026-10-06b) | 0 | 0 | — | 200 |
| ran_past | RA (addendum 2026-10-06c) | 2 | 2 | -0.41 | 198 |
| before_0700 | W4 (addendum 2026-10-06d) | 1 | 1 | +0.00 | 199 |
| five_min_pb | E1 (addendum 2026-10-06b) | 233 | 72 | +0.64 | 128 |

Gross R before costs: the ten-year tests put costs near 0.27-0.39 R a trade, so a cohort needs a gross mean well above that to matter. Nothing on this page changes a rule.

## Shadow strategies — 16 plans taken today, logged, never traded

Exit: break-even after 1 R, then 2 R; flat 11:30; net of costs at the owner's sizing. The record across days: `python3 scripts/shadow_record.py`.

| strategy | symbol | armed | trigger / stop | stop % | filled | exit | net R | the bot |
|---|---|---|---|---|---|---|---|---|
| S6 | MNDR | 09:36 | 3.36 / 3.10 | 7.7 | yes | stop | -1.22 | TAKEN |
| S3 | MNDR | 09:36 | 3.36 / 3.10 | 7.7 | yes | stop | -1.22 | TAKEN |
| S3 | YMAT | 09:38 | 2.21 / 2.13 | 3.6 | yes | stop | -1.50 | SUPPRESSED |
| S3 | CLWT | 09:38 | 2.29 / 2.12 | 7.4 | yes | stop | -1.24 | REFUSED |
| S3 | CLWT | 09:51 | 2.17 / 2.04 | 5.8 | yes | stop | -1.40 | SUPPRESSED |
| S3 | GIXI | 09:56 | 5.74 / 5.44 | 5.2 | no | opened over the A10 cap | — | SUPPRESSED |
| S6 | SKYA | 10:03 | 2.57 / 2.49 | 3.1 | yes | trail | -0.52 | SUPPRESSED |
| S3 | SKYA | 10:03 | 2.57 / 2.49 | 3.1 | yes | trail | -0.52 | SUPPRESSED |
| S3 | CLWT | 10:11 | 2.07 / 1.99 | 3.9 | yes | stop | -1.62 | SUPPRESSED |
| S3 | DAIC | 10:12 | 2.01 / 1.95 | 3.0 | yes | stop | -1.80 | SUPPRESSED |
| S3 | YMAT | 10:20 | 2.14 / 2.08 | 3.0 | no | opened over the A10 cap | — | SUPPRESSED |
| S6 | MNDR | 10:59 | 4.18 / 4.00 | 4.3 | yes | target | +1.77 | REFUSED |
| S3 | MNDR | 10:59 | 4.18 / 4.00 | 4.3 | yes | target | +1.77 | REFUSED |
| S3 | GIXI | 10:59 | 7.16 / 6.82 | 4.8 | no | — | — | SUPPRESSED |
| S3 | YMAT | 11:05 | 3.25 / 3.08 | 5.4 | yes | stop | -1.25 | SUPPRESSED |
| S3 | MNDR | 11:15 | 4.60 / 4.44 | 3.5 | no | opened over the A10 cap | — | REFUSED |

- S6 (best found): 3 plans taken, 3 filled · net +0.009 R a trade · total +0.0 R · wins 1/3 · days up 1/1 · one position +0.0 R over 3
- S3 (wider stops): 13 plans taken, 9 filled · net -0.977 R a trade · total -8.8 R · wins 1/9 · days up 0/1 · one position -3.9 R over 6
