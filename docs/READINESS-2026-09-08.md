# Readiness review — 8 September 2026

Written for the owner before the first open-market session, in plain words.
Every statement about the software was checked by running its tests today;
every fix below has a test that pins it. Nothing about real markets is
claimed, because the platform has still not run through an open market.

**Basis.** Branch `claude/playbook-pullback-explanation-tg5c33`. Eight
independent readers went through the desk, the diary (the ledger), the
trader program (the runner), the pre-market and after-hours paths, the
grading (actuals), the pre-registration gates and the one-command day.
They returned 90 distinct findings. Each was then checked by hand against
the code, and the ones that were real were fixed in two rounds. The rest
are listed at the end with the reason they were not.

---

## 1. Today's plan, and what mode it runs in

The exercise is in **phase A**: the trader program **logs only**. It sizes
every armed plan, runs every refusal, writes the outcome, and places
**nothing**. Phase A stays until five sessions **and** forty decisions are
in the diary, every decision replays, and the paper session has been
measured on the real-time tape (`docs/preregistration.md` §3;
`scripts/day.py` `gates_for_advance`). Nothing can be bought today by any
path: `place_bracket` is not reachable in LOG_ONLY mode
(`src/execution/runner.py`).

That means the two things that matter today are (a) the desk sees the real
tape on the paper login and (b) the diary fills with decisions that are
true to what the desk saw. Both are what the Round A fixes were about.

## 2. Round A — the recording path (what today depends on)

| # | what was wrong | why it mattered today | fixed in |
|---|---|---|---|
| A1 | the feed reported STALE when trades paused for a minute, even while quotes ticked | the desk would have declared the feed dead on a quiet name and stopped journaling | `src/momentum_platform/datasources/ibkr_stream.py` `check()` |
| A2 | when the live connection failed, the desk silently fell back to the synthetic fixture and kept "trading" it | a whole morning of decisions on fake bars, labelled live | `src/momentum_platform/dashboard/server.py` `--ibkr-required` (exit 3 instead) |
| A3 | the first ten seconds of a minute were written as the whole minute and never replaced | every stored bar was a fragment; the grading would have scored fragments | `src/journal/ledger.py` `record_bars` (fuller aggregate wins) |
| A4 | a decision first written as STALE stayed STALE even when the same plan later evaluated clean | the diary kept the worse verdict forever | `record_decision` (STALE upgrades, nothing else changes) |
| A5 | the bid/ask stamped on a decision came from the bar being rebuilt, not the newest one | the recorded NBBO could be minutes old | `session_builder.py` newest-bar rule |
| A6 | "catalyst today" accepted a 48-hour window and market-roundup headlines | Layer 1 gate 5 passed on stale or generic news | `session_builder.py` `_catalyst_today` (since 16:00 ET yesterday, roundups excluded) |
| A7 | news was fetched once at start-up | a name that got its headline at 08:00 stayed "no catalyst" | `ibkr_desk.py` refresh every 120 s |
| A8 | halts were never recorded on the live path | Layer 1 gate 7 could not fire | `ibkr_desk.py` writes `halts` from the ticker's halted flag |
| A9 | Layer 2 pullback-volume was computed but never enforced | a TRADE-mode entry could go on rising pullback volume | `runner.py` `_act` (refuses; LOG_ONLY records the refusal too) |
| A10 | the diary was committed once at the end of the loop | a crash left resting orders with no diary row and the decision PENDING, to be placed again | `runner.py` commit per decision |
| A11 | a risk-gate lock flipped the runner to LOG_ONLY, which also switched off fill sync, the monitored stop and the flatten | the day-lock disabled the exits | `scripts/exercise.py` `entries_enabled=False` only |
| A12 | phase A required sessions **or** decisions | phase A could end after five thin sessions | `day.py` both required, as §3 says |
| A13 | a holiday counted as a session; a rerun counted twice | phase A could be left on days that taught nothing | `day.py` `after_close` (no bars = not counted; `last_session_date`) |
| A14 | a runner crash took the desk (the recorder) down | the diary stopped when the trader stumbled | `day.py` runner restart, up to 5; `exercise.py` retry loop |
| A15 | the replay tool wrote into the production diary | a replay could pollute the exercise's own record | `exercise.py replay` requires `--db` |
| A16 | grading used bars from later days, and an untriggered plan scored −1R | controls were wrong in both directions | `src/journal/actuals.py` same-day bars, `trigger_hit`; `controls.py` excludes untriggered |
| A17 | the gap scan's candidates were not recorded | the funnel's first stage was invisible | `day.py` records `candidates` |

## 3. Round B — the trading path (not reachable today; needed before phase B)

| # | what was wrong | fixed in |
|---|---|---|
| B1 | a partial fill was treated as a full one; the monitored stop would have sold `shares` and gone short the difference | `ibkr_trader.py` `sync()` records `filled_qty`; `runner.watch_stops` sells what was filled |
| B2 | the monitored stop wrote the LIMIT price as the exit price the moment it was sent | a sent sell is now `ExitPending`; the fill, read back by its own order id, closes the row at the real price |
| B3 | the hard-stop flatten sold at the broker and left the diary rows open ("stuck" forever) | the flatten's sells are recorded as `ExitPending` per position and confirmed by the next sync |
| B4 | the after-hours exit closed the row at the limit price | `exercise.py ah-exit` waits up to ten seconds for the fill, otherwise leaves the row `ExitPending` |
| B5 | the fill time was the runner's poll time | the broker's own stamp from the trade log |
| B6 | the runner's quote-freshness test looked at when the desk wrote the quote, which the desk rewrites every rebuild | the quote's own timestamp must be recent too (`ledger.quote_source`) |
| B7 | the test double used order-type strings IBKR never sends (`LIM`, `STO`), so the exit-leg lookup by type was never really exercised | `tests/test_real_trader_path.py` uses `LMT`, `STP`, `MKT` |
| B8 | the paper-account guard was tested on the helper, not on the real connect path | `tests/test_audit_fixes.py` drives `connect()` against a fake live account: refused, socket closed |
| B9 | the launchd installer did not set `IBKR_PORT`, so an automated start would have pointed the desk at TWS | `scripts/install_daily.sh` sets `IBKR_PORT=4002` |

## 4. Findings judged NOT real, and why

- *"the gap scan's volume floor kills names before Layer 1 sees them"* — the
  scan's `discover()` applies the floor as a discovery filter, which is what
  `knowledge-base/strategies/SCANNERS.md` says the scanner layer is: a
  discovery layer, never a gate. Nothing is suppressed that the cascade
  should have judged; it was never a candidate.
- *"the after-close session count uses the UTC date"* — bars are stored in
  UTC and the session ends at 11:30 ET, 15:30 UTC, the same calendar day.
  Harmless; left as is.
- *"the pre-market probe's `held` verdict is inferred, not evidenced"* —
  true, and already stated where the verdict is printed: the probe's own
  `held` line says "still verify a real fill before trusting it with size"
  (`scripts/premarket_probe.py`), and `docs/preregistration.md` §5 makes
  phase C's bracket shape depend on `protected` being confirmed by
  read-back. Not a code change; a rule the owner reads before phase C.

## 5. Tests

`python3 -m pytest tests` on this branch, today: every test passes except
one that is on the baseline list (`BASELINE-2026-09-06.md`:
`test_ibkr_stream.py::test_read_only_connect_skips_the_startup_account_sync_when_ib_async_offers_it`).
One browser test, `test_live_ui.py::test_the_verdict_card_renders_the_servers_cascade_not_its_own_score`,
failed in the full run and passed alone. The cause was found and fixed: the
new-trading-day test's cleanup restored the clock but not the minute bars
the rollover had dropped, so every later test in that module saw an empty
tape. A test-isolation gap, not a defect in the desk; the module passes. `research/kronos-probe/tests` is not collected
(needs `torch`, as the baseline says).

## 6. What the owner does today

`docs/day-runbook.md` is the page. In short: TWS out, Gateway in on paper,
move the rehearsal diary aside, preflight on port 4002 from 07:00 ET, then
`IBKR_PORT=4002 python3 scripts/day.py` at 12:55 France. After 17:30 France:
`exercise.py report`, `check`, `review`, `state`. One more, any time the
Gateway is up: `python3 scripts/restart_probe.py` proves a restarted runner
finds its orders at the broker by permanent id; it has not been run yet.

## 7. Still open, honestly

- **The strategy has not been shown to have edge.** The 894-session
  replication was negative (`research/momentum-replication/reports/2026-08-regime-filter.md`).
  Everything here measures selection quality.
- **Pre-market stops** rest or do not rest depending on the probe verdict.
  A `held` verdict is read back from IBKR's order status, not proven by a
  fill (`scripts/premarket_probe.py`); a `queued` verdict means phase C
  waits for the owner to accept amendment A1 (`docs/preregistration.md` §5).
- **Layer 2's REVIEW verdict** needs VWAP, 9 EMA and MACD from real bars.
  Until a live session has produced one REVIEW, the TRADE path's entry
  condition is untested on real data.
- **One live login** is the design since today. If IBKR's data-sharing
  setting has not taken effect, the day still runs and records, but
  `paper_data` will not read `realtime` and phase A cannot end.

*Paper only. Every figure in the reports is selection quality, never edge.*
