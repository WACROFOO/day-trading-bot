# The trading day — runbook

One command runs the day. This page is what happens around it.

## Once, before the first session

In IBKR Client Portal › Settings › Paper Trading Account, enable sharing
of **real-time market data** with the paper account. Without it IBKR judges
paper fills against delayed prices while decisions are made on live ones;
the morning command measures this and blocks real orders until it reads
`realtime`.

## Before 06:55 ET (12:55 France)

1. Log in to **TWS** (live, read-only data, port 7496).
2. Log in to **IB Gateway** on the **paper** account, port 4002.
3. That is all a human does before the bell. Both logins need 2FA, which
   is why they are not automated.

## 06:55–11:30 ET — one command

```bash
cd ~/day-trading-bot && git pull origin claude/playbook-pullback-explanation-tg5c33
python3 scripts/day.py
```

What it does, in Ross's order (`scripts/day.py`):

| step | what | where the rule lives |
|---|---|---|
| 1 | gap scan → watchlist: STAR then WATCH, rejects named | `scripts/premarket_stars.py` |
| 2 | two probes, once per day: is the paper account on the live tape (`scripts/alignment_probe.py`); does a pre-market stop hold (`scripts/premarket_probe.py`). Both verdicts recorded | `exercise_state` |
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
| `python3 scripts/exercise.py ah-exit ID --confirm` | the after-hours exception: exit-only, records who confirmed |

## Optional: start it for you

`bash scripts/install_daily.sh` installs a macOS launchd agent that runs
`scripts/day.py` at 06:55 ET on weekdays and logs to
`~/Library/Logs/day-trading-bot/`. The two logins above stay yours.
`bash scripts/install_daily.sh --remove` takes it out.

## If something looks wrong

- **Desk shows no plans all morning** → `exercise.py report`: the REJECTS
  block says which gate killed each name. Suppressed is counted, not hidden.
- **`check` returns 1** → stop trading; the log or the code drifted. The
  divergent decisions are listed with recorded vs replayed verdicts.
- **A position after 16:00** → the runner flagged it and printed the
  `ah-exit` command. Nothing sells until you confirm.
- **Probe says `queued`** → pre-market entries are unprotected by design
  (`src/execution/policy.py`); phase C needs your written acceptance in
  `docs/preregistration.md` §5.

*Paper only. Every figure in the reports is selection quality, never edge
(`research/momentum-replication/reports/2026-08-regime-filter.md`).*
