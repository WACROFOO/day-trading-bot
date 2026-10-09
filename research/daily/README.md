# Daily exports and reviews

One folder per trading day, `YYYY-MM-DD/`, written on the owner's Mac by
`scripts/day_export.py` (run by `scripts/day.py` after the 11:30 hard stop and
pushed), then read in the cloud by `scripts/daily_review.py`.

| file | what it is |
|---|---|
| `<day>/screener.csv` | every name the scan returned that day, survivor or reject, with its verdict, reasons, price, gap, float and pre-market volume — the denominator (since 2026-10-09) |
| `<day>/board.csv` | every name the desk's board carried that day: first and last minute, snapshots, verdicts seen, the gate that killed it |
| `<day>/board_bars.csv.gz` | only with `--board-bars`: the desk's own 1-minute bars WITH bid and ask, 04:00-12:00 ET, for every screener and board name |
| `<day>/decisions.csv` | every plan the desk armed, its outcome, refusal reasons, gates, chart values and actuals |
| `<day>/orders.csv`, `<day>/order_events.csv` | what was sent, filled and exited, with commissions |
| `<day>/five_minute.csv`, `<day>/green_run.csv` | the display-only states and the green-run shadow log |
| `<day>/manual_trades.csv` | the owner's trades of the day, copied from `research/trade-journal/journal.csv` (`scripts/trade_log.py add`) |
| `<day>/desk_calls.csv` | the owner's calls from the desk's buttons (took / passed / closed), each with the card the desk showed; the review scores them beside the bot (since 2026-10-08) |
| `<day>/bars.csv` | the desk's 1-minute bars 04:00-12:00 ET for every name with a decision |
| `<day>/day.log` | the bot's log for the day, secrets redacted |
| `<day>/review.md` | the review: every plan scored on the day's bars, by the rule that refused it |
| `cohorts.csv` | the watched cohorts across days (MACD warm-up, run-past entries, before 07:00, 5-minute triggers) toward their 200 prospective trades |
| `shadow.csv` | the shadow strategies' paper track record from 2026-10-09 (`scripts/shadow_record.py`): every plan S6 (the month study's best found) or S3 (its robust core) would take, scored like the bot's fill, exit break-even then 2 R, net of costs. Logged, never traded; read at 30 and 100 trades a strategy |

The review learns, it does not change rules: a cohort reaching 200 trades is
flagged for a preregistered decision (`research/edge-hunt/PREREGISTRATION.md`).

## Days exported

`scripts/day_export.py` adds each new day here when it writes the folder.
`--since DATE --board-bars --push` exports every day with ledger data in one run
(the month study of 2026-10-09).

| day | notes |
|---|---|
| `2026-10-06/` | IPDN 09:22 taken (−1.00 R), APUS 10:58 taken (−0.76 R); uploaded by hand from the Mac |
| `2026-10-07/` | LPCN 07:26 taken; uploaded by hand from the Mac |
| `2026-09-11/` | month export (uploaded from the Mac, 2026-10-09): screener 40 rows, board 8 names, decisions 100, orders 0 |
| `2026-09-14/` | month export (uploaded from the Mac, 2026-10-09): screener 12 rows, board 8 names, decisions 47, orders 0 |
| `2026-09-15/` | month export (uploaded from the Mac, 2026-10-09): screener 36 rows, board 8 names, decisions 63, orders 0 |
| `2026-09-16/` | month export (uploaded from the Mac, 2026-10-09): screener 14 rows, board 8 names, decisions 101, orders 0 |
| `2026-09-17/` | month export (uploaded from the Mac, 2026-10-09): screener 37 rows, board 8 names, decisions 114, orders 0 |
| `2026-09-18/` | month export (uploaded from the Mac, 2026-10-09): screener 90 rows, board 13 names, decisions 132, orders 1 |
| `2026-09-21/` | month export (uploaded from the Mac, 2026-10-09): screener 161 rows, board 17 names, decisions 125, orders 1 |
| `2026-09-22/` | month export (uploaded from the Mac, 2026-10-09): screener 38 rows, board 12 names, decisions 93, orders 3 |
| `2026-09-23/` | month export (uploaded from the Mac, 2026-10-09): screener 54 rows, board 13 names, decisions 141, orders 1 |
| `2026-09-24/` | month export (uploaded from the Mac, 2026-10-09): screener 55 rows, board 15 names, decisions 134, orders 2 |
| `2026-09-25/` | month export (uploaded from the Mac, 2026-10-09): screener 16 rows, board 14 names, decisions 86, orders 2 |
| `2026-09-28/` | month export (uploaded from the Mac, 2026-10-09): screener 6 rows, board 8 names, decisions 61, orders 0 |
| `2026-09-29/` | month export (uploaded from the Mac, 2026-10-09): screener 11 rows, board 8 names, decisions 62, orders 0 |
| `2026-09-30/` | month export (uploaded from the Mac, 2026-10-09): screener 13 rows, board 14 names, decisions 89, orders 1 |
| `2026-10-01/` | month export (uploaded from the Mac, 2026-10-09): screener 20 rows, board 12 names, decisions 52, orders 3 |
| `2026-10-02/` | month export (uploaded from the Mac, 2026-10-09): screener 5 rows, board 8 names, decisions 77, orders 6 |
| `2026-10-05/` | month export (uploaded from the Mac, 2026-10-09): screener 27 rows, board 7 names, decisions 90, orders 0 |
| `2026-10-08/` | month export (uploaded from the Mac, 2026-10-09): screener 25 rows, board 12 names, decisions 108, orders 0 |
