# The desk as a manual decision tool — assessment, 2026-10-08

**Provenance.** Read on 2026-10-08 against commit `fc7c1eb` (code before any
change in this pass): `src/momentum_platform/dashboard/` (`app.js`,
`session_builder.py`, `ibkr_desk.py`, `server.py`), `src/momentum_platform/cascade.py`,
`pullback.py`, `catalyst.py`, `src/momentum_platform/datasources/filings_news.py`, `src/execution/intent.py`,
`runner.py`. The desk was walked on the replay fixture
`fixtures/market_replay/workstation_open_2026-09-01.jsonl` (synthetic, 08:00–10:30 ET),
and the verdict was scored against the two real days exported from the owner's Mac:
`research/daily/2026-10-06/decisions.csv`, `research/daily/2026-10-07/decisions.csv`
and their `bars.csv` (1-minute bars, UTC stamps). `data/journal.sqlite` lives on the Mac
and is not in this repository; those exports are its rows. **No 07:30 replay
exists**: the fixture starts at 08:00 (`scripts/make_replay_fixture.py`), so 07:30
was judged on the 2026-10-06/07 exports instead.

**What was considered.** Every line the per-symbol card draws (header, quote card,
catalyst block, verdict banner, nine chips, plan line, 5-minute line, sizing box),
the feed and health display, and what the bot does with the same plan.

## Gap table

| # | need | today | proposed | effort |
|---|---|---|---|---|
| 1 | one line: decision · the reason that decides · the level to watch | `REVIEW` means "every Layer 1 gate passed — read the chart yourself"; the setup (pullback, trigger, extension) is not in the verdict; the plan line is separate | REVIEW / WATCH / WAIT / NO + one reason + one level, from the cascade **and** the pullback machine, the clock and the halt flag | M |
| 2 | the trigger *before* the break, to have the order ready | a plan appears only after the trigger bar (`pullback.py` freezes at the break) | during a pullback: pending trigger (previous bar's high + 1¢), stop (pullback low − 1¢), size | S |
| 3 | a verdict as fresh as the price | live, `cascade`, `plans` and `fiveMinute` refresh once a minute; the 3-second tick carries frames and metrics only (`app.js` `applySessionTick`) | the card ships in every tick, stamped "as of" | S |
| 4 | gates with values and thresholds, the bot's own | gain, RVOL and pullback volume are recomputed in the browser; VWAP/EMA/MACD too when the cascade stopped early; the news chip passes any headline of any age; every PASS gate carries its kill sentence (`"$6.50 is outside $2.00–20.00."` on IPDN's taken trade) | lamps built server-side from the cascade's gates, the detector and the order math; value + threshold, the reason only when red | M |
| 5 | room overhead | not shown | room to the high of day, the pre-market high and the next half dollar, in R | S |
| 6 | what the bot did with this plan | nothing from the runner reaches the desk | bot line: outcome and refusal text from `decisions`, order and fill from `orders` | M |
| 7 | numbers to type | sizing box: risk + spread, no A10 limit, no commission reserve, no account bound, sizes a withdrawn plan; no copy | order panel from the bot's own arithmetic (moved to `src/momentum_platform/order_math.py`), the runner's A13/A6 checks, the honest stop (`scripts/tape.py`), the halt band (`FILTERS.md`), the pre-market mechanics, one copy-ready line | M |
| 8 | managing a position | nothing | after "I took it": R now, stop, the A3 1R trail, 2R as a reference, sound + notification when a level is crossed | M |
| 9 | catalyst in two lines with a strength word | browser re-grades with a JavaScript copy of the word lists; four to six lines of text; words STRONG/WEAK/NONE/DILUTIVE/UNKNOWN | server read: type, age, STRONG / MODERATE / WEAK + one-line reason, headline clamped to two lines, flags | M |
| 10 | "dated today" | **defect:** the gate reads `meta["tradingDate"]`, which no symbol carries, so any own headline in the 2-day fetch passes the catalyst pillar; the cutoff is the previous *calendar* day, so Friday after-close news is lost on Monday | pass the session's trading date; cutoff 16:00 ET of the previous *trading* day | S |
| 11 | word matching | **defect:** substring, so "window" reads as a market wrap ("dow "), "disorder" as hard news ("order") | whole-word matching | S |
| 12 | foreign filers | **defect:** a 6-K becomes the headline `SEC 6-K · 6-K`, grades WEAK and passes the news pillar; 20-F appears nowhere | an unread filing is UNKNOWN, not news; 6-K/20-F filers flagged as the dilution blind spot (CLAUDE.md rule 7) | S |
| 13 | dilution on file | the desk never reads S-3 / 424B; an ATM is found only in a headline | shelf and takedown filings with their age on the card | M |
| 14 | competing login (10197) | a terminal line; `provider.messages` carries it and the page never shows it; the feed goes STALE silently | red banner naming the cause, with a sound | S |
| 15 | lost AMEX permission (10089/420) | the name silently leaves the page | "dropped — no NYSE American real-time data" list | S |
| 16 | halts | header and quote card; no sound | halt in the verdict line, sound on halt and resume | S |
| 17 | the desk failing to answer | fetch errors swallowed (`.catch(() => {})`) | a banner after repeated failures | S |
| 18 | my calls next to the bot's | nothing; `manual_trades.csv` was empty on both days | "I took it / I passed / I closed it" → ledger → export → daily review | M |

## What the two real days show

Scored on the exported 1-minute bars, live plans only, entry at the trigger
within 3 minutes, +1 R or the stop first, no costs — an upper bound, not P&L.

- **The verdict did not separate the plans.** On 2026-10-06, WAIT plans reached
  +1 R before their stop 8 of 11 times and REVIEW plans 8 of 12. Two days decide
  nothing; the ten-year audit says the same of the gates themselves (no single
  change passed both bar readings, `research/paper-exercise/reports/rules_audit_output_v2.txt`).
  The redesign makes the card honest and actionable; it cannot add an edge.
- **A NO without a level hid a near miss.** SXTC 2026-10-07 08:12, REJECT "25.4% off
  2.72" with the trigger at 2.02. The window reopens at 0.75 × 2.72 = 2.04; the bars
  print 08:13 H 2.18, 08:15 H 2.45. LGCL 09:34, REJECT "38.2% off 4.50"; 09:42 H 4.53.
  The rule held (FILTERS.md gate 4), but the card never said how close the line was.
- **REVIEW while the bot refused.** IPDN 2026-10-06 07:32 read REVIEW with every chart
  gate "yes"; the runner refused on "pullback volume was not lighter than the
  impulse", a check the verdict never reads (10 of the 26 REVIEW rows across both days,
  backfill included, had `volume_ok` 0).
- **The taken trade read fully green.** IPDN 2026-10-06 09:22, REVIEW, TAKEN at 6.51,
  stop 6.32; 09:25 L 6.15, exit −1.00 R. Its own warning — pre-market volume
  30.63M, over the ~1M ceiling — sat below the chips in small type.
- **Two sets of levels.** IPDN 07:53 plan 4.46 / 4.24, and within two minutes the
  5-minute line showed its own 4.56 / 3.96. E1 failed its test (addendum 2026-10-06b);
  a display-only line should not print competing levels.
- **A one-bar spike set "the high".** BIYA 2026-10-07: every plan after 08:32 was
  killed "% off 37.10", a single 08:21 bar; nothing on the card questioned the print.

## Where manual orders meet the desk (point 4)

The desk and the bot share one paper Gateway login (`docs/day-runbook.md`, "One
login, one tape"). On 2026-09-07 a live TWS login took the market data and the
paper session got error 10197 (`docs/STATUS-2026-09-06.md`). One username holds one
session, so the paper username cannot also be logged into TWS or IBKR Mobile.
Practical consequences for typing orders by hand:

- logging the **live** username into TWS or the phone while the desk runs can
  blind the desk (10197) — the new banner says so the moment it happens;
- IBKR's documented route to run both at once is a **second username** on the
  account (Client Portal › Users & Access Rights), which carries its own market-data
  fees — taken from IBKR's knowledge-base article 1719 as reported by a web search
  on 2026-10-08; the page itself refused automated reading, so **verify it in Client
  Portal before relying on it**;
- pre-market, IBKR does not hold a stop: the 2026-09-18 probe got warning 2109 and
  the stop leg could not trigger before 09:30 (`docs/preregistration.md` §5). The
  order panel prints this with every pre-market ticket.

## What this assessment could not check

- 07:30 on the fixture (it starts at 08:00); the real days stand in for it.
- The owner's own trades: none were recorded on 2026-10-06 or 2026-10-07.
- The cascade on the fixture is computed at the end of the replay, so scrubbing
  back shows end-of-day verdicts beside earlier bars (seen at 09:40: WAIT "every
  Layer 1 gate passed" beside a red RVOL chip). Point-in-time replay is not built.
- Any claim that a better card improves results. It is not measured and not claimed.

## Verdict

The desk computes most of what a manual entry needs. It shows it in the wrong
order, refreshes the verdict once a minute while prices refresh every three
seconds, says nothing about the bot, and carries three catalyst defects that also
feed the bot's pillar count. Phase 2 builds rows 1–18 above.
