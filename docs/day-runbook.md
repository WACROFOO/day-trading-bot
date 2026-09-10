# The trading day — runbook

One command runs the day. This page is what happens around it.

## Once, before the first session

In IBKR Client Portal › Settings › Paper Trading Account, enable sharing
of **real-time market data** with the paper account. Without it IBKR judges
paper fills against delayed prices while decisions are made on live ones;
the morning command measures this and blocks real orders until it reads
`realtime`.

## Is the market open?

The command checks the NYSE calendar (`src/momentum_platform/holidays.py`)
and refuses to start on a weekend or holiday, naming which. 7 September
2026 was Labor Day; the chain ran all morning on a stale feed before this
check existed.

## One login, one tape (the design since 8 September)

On 7 September the paper session was refused market data with IBKR error
10197, *"No market data during competing live session"*: a live TWS login
holds the subscriptions and the paper Gateway cannot share them while TWS
is logged in. The alignment probe reports this as `competing`.

The fix is a single login. The **desk reads and the executor writes on the
same paper session** (port 4002, `IBKR_PORT=4002`). The desk connection
stays read-only; only the executor's connection may write. Decisions and
orders then share one tape by construction, and the alignment probe runs in
single-login mode.

## Before 06:55 ET (12:55 France)

1. Once, in Client Portal › Settings › Account Settings › Paper Trading
   Account: share real-time market data subscriptions with the paper
   account. Log the Gateway out and back in afterwards. (Done 7 September.)
2. **TWS logged out.** Log **IB Gateway** in on the **paper** account,
   port 4002. That is the only login; it needs 2FA, which is why it is not
   automated.
3. First trading day only, or after any rehearsal: move the rehearsal
   ledger aside so the exercise starts from a clean file. The rehearsals of
   7 September wrote decisions and orders into it that are not sessions.
   ```bash
   cd ~/day-trading-bot && git pull origin claude/playbook-pullback-explanation-tg5c33
   mv data/journal.sqlite data/journal-rehearsals-2026-09-07.sqlite
   ```
4. Prove the paper session has the tape (from 07:00 ET, when bars exist):
   ```bash
   IBKR_PORT=4002 python3 scripts/ibkr_preflight.py
   ```
   Wants `market data type 1` and five-second bars arriving. If it shows
   type 3 (delayed) or no bars with TWS out, the sharing setting has not
   taken effect: the day still runs, but `paper_data` will not read
   `realtime` and the phase gate keeps orders off.

## 06:55–11:30 ET — one command

```bash
IBKR_PORT=4002 python3 scripts/day.py
```

What it does, in Ross's order (`scripts/day.py`):

| step | what | where the rule lives |
|---|---|---|
| 1 | gap scan → watchlist: STAR then WATCH, rejects named; its finviz floats are handed to the desk so Layer 0 and Layer 1 agree on float | `scripts/premarket_stars.py` → the daily float file under `data/` |
| 2 | two probes, once per day: is the paper account on the live tape (`scripts/alignment_probe.py`, single-login mode); does a pre-market stop hold (`scripts/premarket_probe.py`, at 07:00 ET). Both verdicts recorded | `exercise_state` |
| 3 | desk starts on the watchlist, journaling every rebuild | `JOURNAL_DB` → `src/journal/ledger.py` |
| 4 | runner starts in the phase's mode (A = log only) | `docs/preregistration.md` §3 |
| 5 | hard stop 11:30: runner flattens (TRADE mode) | `PARAMETERS.md` §2 · `src/execution/intent.py` |
| 6 | actuals, replay check, controls, report, sessions_done += 1 | one file per day in `research/paper-exercise/reports/` |

Leave it running. `Ctrl-C` stops both processes cleanly. Missed the
morning? Run the same command after 11:30 and it does step 6 only.

Browser desk: `http://127.0.0.1:8787`. The bottom-right verdict is the
server's cascade word; a killed name reads `suppressed · KILLED` on the
Entry line, never `ARMED`.

## Human-only commands

| command | when |
|---|---|
| `python3 scripts/exercise.py state` | where the exercise is |
| `python3 scripts/exercise.py report` | today's funnel, rejects, controls, replay |
| `python3 scripts/exercise.py check` | replay check alone; exit 1 on any divergence |
| `python3 scripts/exercise.py advance` | move to the next phase — refuses and lists blockers unless every gate is clear |
| `python3 scripts/exercise.py stuck` | any filled, un-exited position |
| `python3 scripts/exercise.py review` | everything so far across sessions: what kills, what is refused, verdicts, fills, controls, replay, today's risk lock |
| `python3 scripts/exercise.py ah-exit ID --confirm` | the after-hours exception: exit-only, records who confirmed |
| `python3 scripts/exercise.py accept-a1 --confirm` | records YOUR acceptance of amendment A1 (pre-market entries with no stop at the broker). Never set by code; read §5 of the pre-registration first |
| `python3 scripts/exercise.py retag-backfill --before 2026-09-08T08:06 --confirm` | one-off correction: tags the decisions recorded before the backfill tag existed (the morning of 8 September, armed on history loaded at 08:06) as backfill; dry run without `--confirm` |
| `python3 scripts/day.py --settle 2026-09-09` | the after-close block for a past day the hard stop never reached (the Mac slept, Ctrl-C): grading from the ledger's bars, replay, report, session counted once |
| `IBKR_PORT=4002 python3 scripts/backfill_tape.py 2026-09-09` | when the desk stopped early: fetches that day's 1-minute bars from IBKR (read-only) for the names decided on, resets the 'no tape' gradings, grades again. Then `--settle` |
| `IBKR_PORT=4002 python3 scripts/day.py --probe-orders` | the only way the day command runs the pre-market stop probe, which places and cancels an unfillable paper bracket. Off by default: an observational day dispatches nothing order-shaped |

## Optional: start it for you

`bash scripts/install_daily.sh` installs a macOS launchd agent that runs
`scripts/day.py` at 06:55 ET on weekdays with `IBKR_PORT=4002` and logs to
`~/Library/Logs/day-trading-bot/`. The Gateway login stays yours.
`bash scripts/install_daily.sh --remove` takes it out.

## If something looks wrong

- **Desk shows no plans all morning** → `exercise.py report`: the REJECTS
  block says which gate killed each name. Suppressed is counted, not hidden.
- **`check` returns 1** → stop trading; the log or the code drifted. The
  divergent decisions are listed with recorded vs replayed verdicts.
- **A position after 16:00** → the runner flagged it and printed the
  `ah-exit` command. Nothing sells until you confirm.
- **`exercise.py stuck` shows a row with status `ExitPending`** → a sell was
  sent (monitored stop, hard-stop flatten or `ah-exit`) and its fill has not
  been read back yet. The next runner sync closes it at the real fill price;
  if the runner is gone, check the position in the Gateway.
- **The runner restarted mid-morning** → it adopts its open orders from the
  ledger and matches them at the broker by IBKR's permanent id. An order
  whose acknowledgement was never saved is found by its reference (the
  decision id on every leg) or marked `UNRESOLVED` for you; it is never sent
  again. Nothing is placed twice, whatever the restart count.
- **A `start UNRESOLVED intent` or `RECONCILE` line in the runner output** →
  the ledger and the broker disagree about a position. New entries are
  blocked until you look: `exercise.py stuck`, then the Gateway's order and
  position windows.
- **`phase A: the exercise is log-only — --trade is refused`** → the
  runner will not trade before `exercise.py advance` has moved the exercise
  to phase B. This holds at the execution boundary, not only in the day
  command.
- **`another runner already holds …lock`** → a runner is already attached to
  this ledger. Two would claim the same decision; the second refuses.
- **Probe says `queued`** → pre-market entries are unprotected by design
  (`src/execution/policy.py`); phase C needs your written acceptance in
  `docs/preregistration.md` §5.

*Paper only. Every figure in the reports is selection quality, never edge
(`research/momentum-replication/reports/2026-08-regime-filter.md`).*
