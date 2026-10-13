# Daily review — 2026-10-13

```
SOURCE · research/daily/2026-10-13/ exported 2026-10-13T13:15:25+00:00 from /Users/ayman.benharara/day-trading-bot/data/journal.sqlite
       · decisions 77 · screener 11 · board 8 · orders 0 · order_events 0 · five_minute 29 · green_run 0 · manual 0 · desk_calls 0 · bars 2521 · board_bars 2521 · log_lines 168
SCORING · refused plans: fill at the trigger if touched within 3 min, A3 trail 1 R, flat 11:30,
          1-minute bars from the desk's own ledger — an UPPER BOUND, no costs, no slippage
! A day is an anecdote. Cohorts decide only at 200 prospective trades, under a preregistered rule.
```

## Funnel — 77 plans armed (54 on loaded history, not counted)

| what happened | plans |
|---|---|
| killed:price | 11 |
| killed:rising | 4 |
| killed:pillars | 4 |
| macd | 2 |
| volume | 1 |
| vwap | 1 |

## Every plan, scored on the day's bars

| ET | symbol | trigger / stop | refused by | if taken (gross R) | how |
|---|---|---|---|---|---|
| 07:54 | BKYI | 4.04 / 3.92 | killed:rising | -0.42 | stop |
| 07:58 | AIXI | 3.14 / 3.09 | killed:pillars | -1.22 | stop |
| 07:59 | FCHL | 1.54 / 1.48 | killed:price | -1.00 | stop |
| 08:00 | SCNI | 2.05 / 1.91 | killed:rising | — | trigger not reached |
| 08:00 | YJ | 2.29 / 2.22 | volume | -0.86 | stop |
| 08:06 | FCHL | 1.55 / 1.49 | killed:price | — | trigger not reached |
| 08:08 | SCNI | 1.84 / 1.77 | killed:price | — | trigger not reached |
| 08:10 | TCRT | 2.22 / 2.13 | macd | -0.66 | stop |
| 08:12 | WBUY | 0.96 / 0.92 | killed:price | — | trigger not reached |
| 08:12 | AIXI | 3.34 / 3.15 | killed:pillars | +1.16 | stop |
| 08:25 | WBUY | 0.98 / 0.95 | killed:price | -0.99 | stop |
| 08:29 | FCHL | 1.27 / 1.24 | killed:price | +0.00 | stop |
| 08:31 | AIXI | 3.27 / 3.15 | killed:pillars | -0.67 | stop |
| 08:33 | TCRT | 1.78 / 1.72 | killed:price | -0.50 | stop |
| 08:38 | BKYI | 3.77 / 3.69 | killed:rising | -0.62 | stop |
| 08:39 | SUGP | 2.01 / 1.97 | vwap | -0.50 | stop |
| 08:40 | YJ | 2.44 / 2.34 | macd | +0.80 | stop |
| 08:42 | SCNI | 1.64 / 1.60 | killed:price | +1.49 | stop |
| 08:45 | AIXI | 3.17 / 3.11 | killed:pillars | -0.38 | stop |
| 08:50 | TCRT | 1.94 / 1.87 | killed:price | -0.14 | stop |
| 08:52 | FCHL | 1.34 / 1.30 | killed:price | +1.27 | stop |
| 08:54 | BKYI | 3.85 / 3.79 | killed:rising | -0.83 | stop |
| 09:08 | TCRT | 1.90 / 1.84 | killed:price | -0.83 | stop |

| refused by | filled if taken | mean gross R | best | worst |
|---|---|---|---|---|
| killed:price | 8 | -0.09 | +1.49 | -1.00 |
| killed:pillars | 4 | -0.28 | +1.16 | -1.22 |
| killed:rising | 3 | -0.62 | -0.42 | -0.83 |
| macd | 2 | +0.07 | +0.80 | -0.66 |
| volume | 1 | -0.86 | -0.86 | -0.86 |
| vwap | 1 | -0.50 | -0.50 | -0.50 |

## The bot's own trades — 0 filled


## Your trades beside the bot — 0 recorded


## Your calls on the desk — 0 recorded

None. The desk's buttons (I took it / I passed / I closed it) write them.

## Cohorts toward their prospective test (all days so far)

| cohort | rule it would test | plans | filled | mean gross R | to go |
|---|---|---|---|---|---|
| warmup_macd | B30 (addendum 2026-10-06b) | 0 | 0 | — | 200 |
| ran_past | RA (addendum 2026-10-06c) | 2 | 2 | -0.41 | 198 |
| before_0700 | W4 (addendum 2026-10-06d) | 1 | 1 | +0.00 | 199 |
| five_min_pb | E1 (addendum 2026-10-06b) | 262 | 82 | +0.54 | 118 |

Gross R before costs: the ten-year tests put costs near 0.27-0.39 R a trade, so a cohort needs a gross mean well above that to matter. Nothing on this page changes a rule.

## Shadow strategies — 0 plans taken today, logged, never traded

Exit: break-even after 1 R, then 2 R; flat 11:30; net of costs at the owner's sizing. The record across days: `python3 scripts/shadow_record.py`.


- S6 (best found): 0 plans taken, 0 filled
- S3 (wider stops): 0 plans taken, 0 filled
