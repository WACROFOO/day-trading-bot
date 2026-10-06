# Daily exports and reviews

One folder per trading day, `YYYY-MM-DD/`, written on the owner's Mac by
`scripts/day_export.py` (run by `scripts/day.py` after the 11:30 hard stop and
pushed), then read in the cloud by `scripts/daily_review.py`.

| file | what it is |
|---|---|
| `<day>/decisions.csv` | every plan the desk armed, its outcome, refusal reasons, gates, chart values and actuals |
| `<day>/orders.csv`, `<day>/order_events.csv` | what was sent, filled and exited, with commissions |
| `<day>/five_minute.csv`, `<day>/green_run.csv` | the display-only states and the green-run shadow log |
| `<day>/manual_trades.csv` | the owner's trades of the day, copied from `research/trade-journal/journal.csv` (`scripts/trade_log.py add`) |
| `<day>/bars.csv` | the desk's 1-minute bars 04:00-12:00 ET for every name with a decision |
| `<day>/day.log` | the bot's log for the day, secrets redacted |
| `<day>/review.md` | the review: every plan scored on the day's bars, by the rule that refused it |
| `cohorts.csv` | the watched cohorts across days (MACD warm-up, run-past entries, before 07:00, 5-minute triggers) toward their 200 prospective trades |

The review learns, it does not change rules: a cohort reaching 200 trades is
flagged for a preregistered decision (`research/edge-hunt/PREREGISTRATION.md`).
