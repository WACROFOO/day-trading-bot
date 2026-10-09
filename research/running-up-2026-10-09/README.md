# Running Up filters on the recorded days — 2026-10-09

Asks what the Running Up tile catches and misses on the twenty days the desk
recorded (`research/daily/<day>/board_bars.csv.gz`, 2026-09-11 … 2026-10-08),
before and after the four discovery filters of
`src/momentum_platform/scanners/running_up_filters.py`, false alarms included.
Discovery only: the filters never gate the bot, and both guards below say so
on every day.

| file | what it is |
|---|---|
| `measure.py` | the measurement: replays each day through the desk's own session builder, scores every scanner and the tile as shown against one ground truth fixed before scoring. Its docstring states every definition and every Approximation |
| `results.txt` | its output, unedited: `python3 research/running-up-2026-10-09/measure.py > research/running-up-2026-10-09/results.txt` (about 45 s) |

What `results.txt` says, in its own numbers:

- **Ground truth** (an Approximation, not his numbers): a RUN is ≥ 10 % from
  a low to a high within ≤ 10 minutes, low $2–20, high 07:00–11:30 ET,
  ≥ 50,000 shares — 523 RUNs on 104 of 214 name-days.
- **The tile as shown, before → after:** RUNs caught 389 → 439 of 523;
  name-days 98 → 101 of 104; first alert 5.0 → 3.0 minutes after the run's
  low (median); false alarms 210 → 312, the same 16 % of in-window alerts.
- **Every day** catches as many RUNs after as before or more; every day has as
  many false alarms or more (`## per day`).
- **The desk, both tiles:** 416 → 456 RUNs caught; RUNs with no alert anywhere
  near them 41 → 11, nine of the eleven a single one-minute bar (low and high
  in the same minute — a replay feeds one price a minute, its close).
- **Per trigger:** `pct_in_n` (5 % off the 5-minute low) carries the filters —
  413 RUNs alone; `vol_surge` 246; `new_hod` 101 at the worst false-alarm rate
  (24 %); `halt_resume` 20 RUNs from 27 alerts, 3 false.
- **False alarms, why:** the filters' 151 split into 49 moves under 5 %
  (`vol_surge`/`new_hod` fire smaller by design), 59 moves that started under
  $2 (the alert is in the band, its low was not), 43 moves under 10,000 shares
  (the filters set no share floor, as the method sets none pre-market).
- **Guards, all 20 days:** plans, cascade verdicts and card words identical
  with the filters silenced; every alert row the desk's own scanners showed
  identical with the filters silenced.

Two things this measurement found in the desk, both fixed in the same commit:

1. The recorded bars fill an untraded minute with a zero-volume row, so a halt
   is a run of empty minutes, not a gap. The first run counted 0 halts; 70 are
   inferred now (`measure.py`, `inferred_halts`).
2. The router files same-name alerts of one moment under the first scanner to
   fire. Filed under `running_down`, which has no tile, an alert showed on no
   tile at all — 13 rows, among them BENF 2026-09-23 09:40, the halt-resume
   alert. The Running Up tile now lists such a row (`app.js`, `loggedAlerts`).

Not measured: live ticks (the replay sees closes, so one-minute wicks are
invisible to it), the official halt feed (halts here are inferred from the
bars), news (every name's catalyst reads UNKNOWN in the replay).
