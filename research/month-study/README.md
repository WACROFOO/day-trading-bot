# month-study/ — our screeners' last month, from the flexible strategy to the solid one

The owner, 2026-10-09: take every name our screeners showed in the last
month, run our strategy on it loose and then stricter, and find the
combination that would have made money — for a paper track record that
measures accuracy going forward.

| file | what |
|---|---|
| `PREREGISTRATION.md` | written before any run: universe (the ledger's screener, board and decision names, 2026-09-08..10-08), data, the two arming regimes, the levers, the greedy ladder, the holdout week, the random-entry check, what counts as a CANDIDATE |
| `../../scripts/month_study.py` | the run: universe from `research/daily/<day>/` (screener, board, decisions), SIP bars, the engine's plans in both regimes, three cost models, the ladder, the checks; writes `results.json` here |

| `REPORT.md` | **the result: no combination made money in both the 15 selection sessions and the held-out week.** The best found (stop ≥ 3 % + price + regular hours + VWAP + pullback volume + still rising, break-even exit) read +0.41 R a trade on 31 trades and −0.73 on its 7 holdout trades. What held in both periods is a direction: wider stops, the price band, regular hours — losing 0.16–0.25 R a trade against the bot's 0.88–1.69 |
| `output.txt`, `results.json` | the preregistered run's printout and every table |
| forward record (`../../src/momentum_platform/shadow.py`, `../../scripts/shadow_record.py`) | from 2026-10-09 the best found (S6) and its robust core (S3) are judged on every plan the desk arms and scored like the bot's fill — logged, never traded — into `../daily/shadow.csv`; the test this month could not give |
| `exploratory.json` (`../../scripts/month_study_explore.py`) | read after the verdict, chose nothing: each greedy step on the holdout, the best found's trades by name |
