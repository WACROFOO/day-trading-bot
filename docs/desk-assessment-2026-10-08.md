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

## What was built (Phase 2, same day)

| rows | built | where |
|---|---|---|
| 1, 2, 4, 5 | the decision card: REVIEW / WATCH / WAIT / NO + the reason + the level (the trigger, the VWAP to reclaim, the line that puts a faded name back inside 25 %), the setup in words with the last plan's outcome, every gate as a lamp with value beside threshold, room overhead as information | `src/momentum_platform/decision_card.py`, `src/momentum_platform/dashboard/cards.py`; `pullback.py` gained read-only `pending()` and `progress()` |
| 3 | the cards ride every live tick, only the changed ones; an "as of" stamp; a scrubbed replay says the card is the newest read | `ibkr_desk.py` `_changed_cards`; `app.js` |
| 6 | the bot line: refused and why in plain words (the raw text on hover), armed, in, out | `journal.ledger.bot_view`, `decision_card.bot_line` |
| 7 | the order panel from the bot's own arithmetic, moved to `src/momentum_platform/order_math.py` and re-exported unchanged by `execution.intent` (a test checks they are the same objects): copy-ready line, A10 limit, A18 size, account bound, the runner's A13/A6 checks, the honest stop (`scripts/tape.py`'s rule), the halt band, the pre-market mechanics | `order_math.ticket` |
| 8 | "I took it" switches the card to the position: stop, 1 R trail (A3), 2 R, R and $ now; a sound, a notification and a flash when a level is crossed | `order_math.position`, `app.js` `watchCards` |
| 9, 13 | the catalyst in two lines: grade + reason, the headline clamped, type · age · source, flags (offering today, a 424B in 30 days, a shelf, a foreign filer, the split test). The same read in `scripts/catalyst_score.py` | `catalyst.card_read`; rules with origins in `knowledge-base/strategies/CATALYST.md` |
| 10, 11, 12 | the three catalyst defects fixed; recorded in `docs/preregistration.md` §5 because they move the bot's pillar count | `session_builder.py`, `catalyst.py` |
| 14–17 | a banner for a competing login (10197) and for names dropped for want of a data permission; halts and resumes sound; a desk that stops answering is said | `ibkr_desk.health`, `app.js` `renderDeskAlerts` |
| 18 | the three buttons write `manual_decisions`; the export carries `desk_calls.csv`; the review scores each call beside the bot | `server.py` POST routes (JSON only, owner key), `day_export.py`, `daily_review.py` |
| — | a real day can be replayed at any minute | `scripts/fixture_from_export.py` |
| — | the owner's layout call: the decision card takes the simulated Level 2's slot (Level 2 to the tray, still labelled); off REVIEW the order itself says "not now — WAIT: the reason" | `app.js` `DEFAULT_LAYOUT` (layout v9), `renderTicket` |
| — | the owner's two risk calls: copy arms on REVIEW only, and a hand order is sized on the owner's own risk or not at all (no fallback to the bot's paper risk) | `app.js` `copyArmed`, `src/momentum_platform/dashboard/cards.py` `_risk` |
| — | the real Time & Sales: IBKR tick-by-tick `Last` + `BidAsk` for the selected name, each print's side read against the quote that stood, 60-s and 10-s facts, big prints, gaps and refusals said on the tape; the decision card carries its one-line summary. Facts, never a gate | `src/momentum_platform/tape.py`, `src/momentum_platform/datasources/ibkr_tape.py`, `ibkr_desk.py`, `/api/v1/tape`, `/api/v1/focus` |
| — | the owner's "act as a pro trader" pass: find / see / decide — scanners and the Five Pillars check left; the charts under a two-line header that took the quote card's facts; the decision card (now holding the catalyst) over the Time & Sales right; the risk box above the order, the buttons beside it | `app.js` (layout v10), `index.html`, `styles.css` |

Tests: `tests/test_desk_card.py` (46), plus the rewritten card tests in
`tests/test_dashboard.py` and `tests/test_live_ui.py`, and the desk-calls loop in
`tests/test_daily_loop.py`. The full suite runs 1,051 tests with the browser
tests no longer skipped (Playwright installed against the preinstalled Chromium).

## More, ranked — each marked measured or opinion

| # | suggestion | basis |
|---|---|---|
| 1 | Export each day's references (previous close, 20-day volume, the time-of-day profile), headlines, quotes and halts, so any minute replays faithfully. Without the RVOL baseline every replayed name read NO on "missing rvol" | measured today (the first replay of 2026-10-06/07) |
| 2 | ~~Give the decision card the slot the **simulated** Level 2 card holds by default; the order panel needs height~~ — done the same day on the owner's word | opinion — a layout choice, the owner's |
| 3 | Compute the card point-in-time when a replay is scrubbed, instead of saying it is the newest read | opinion; the look-ahead itself is measured (the 09:40 screenshots) |
| 4 | Measure gate 4 from the pre-market high as FILTERS.md states, or amend FILTERS.md: the code uses the session high, so a one-bar spike (BIYA 37.10) or a regular-hours high moves the 25 % line. A preregistered test decides | measured in the code; the effect is not measured |
| 5 | Decide whether the pillar count should use the 5× scanner dial (A5's choice) or the 1.5× trade floor FILTERS.md calls the gate | opinion; a test decides |
| 6 | A second IBKR username for manual orders, so they never blind the desk | IBKR documentation via a web search, not verified here |
| 7 | The company name: IBKR's contract carries none (`longName` lives on the contract details), so the card cannot print it | measured in the code |

## Level 2 — the owner's question, same day

"Do we need a Level 2 analysis layer?" What the repository holds on it, read
the same day:

| question | what the files say | source |
|---|---|---|
| where it sits in his method | the last step before execution, and a veto: *"if I pulled up the level two and all I saw were sellers or I saw a huge sell order on the ask would I've taken the trade absolutely not level two is that final step"* | `4syXgXshgsc` [00:50:13] |
| can he trade without it | *"could I trade without level two? I could, but my accuracy would be lower because I would miss some of the signals"* | `_9za7jNDPQc` [00:44:38] |
| how often it is his stated reason | 7 % of his trades | `research/ross-trades/REPORT.md` |
| near a live entry | 17 % of entry utterances against 7 % of random text (2.5×) | `research/momentum-replication/reports/2026-08-streams-roundup.md` §9 |
| what of it can be encoded | 63 % of his Level 2 / tape instructions name nothing concrete; of the rest, only seller-wall detection needs the book — *"tick and quote data cover most of it"* | `knowledge-base/strategies/PARAMETERS.md` §10 |
| can it be tested here | *"Level 2 history — does not exist in any source available here"* | `research/edge-hunt/PREREGISTRATION.md` |
| is it mastered | the course chapters on it (Basics 9 and 10, Strategies & Scaling 6) are outside the mastered chapters 1–6 | `knowledge-base/warrior-support/trading-questions/19000135531-understanding-level-2.md` |
| what real depth costs here | Nasdaq TotalView is *"the Nasdaq book, not all US venues"*; IBKR needs TotalView-OpenView plus an API add-on, and allows 3 depth symbols at a time on the default 100 lines | `CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/platform-rebuild-audit.md`; IBKR's documentation as reported by a web search on 2026-10-08 — the pages refuse automated reading, so verify in Client Portal |
| what a real tape costs here | IBKR's tick-by-tick Time & Sales runs on the Level 1 subscription the desk already uses, 5 symbols at a time on 100 lines | IBKR's documentation as reported by the same search — not verified here |

**Answer (opinion, not measured): not a scored layer.** There is nothing to
calibrate a Level 2 score against, and most of what he reads on it is
unspecified. What the desk lacks is the raw tape and book in front of the
owner's eyes at the trigger, which he places last before the order. In order:

1. a second IBKR username, so TWS's own book and tape run beside the desk —
   needed for manual orders anyway (see point 4 above);
2. a real Time & Sales strip on the desk: no new licence, and it covers the
   "green on the tape" read — **built the same day** on the owner's word;
3. depth on the desk only after the licence, showing one fact — the largest
   offer between the trigger and the next half dollar, with its size on his
   own scale (*"15,000 and up starts to become more significant. Above 100,000
   is a huge seller"*, `knowledge-base/warrior-blog/tools-platforms/spotting-breakouts-with-level-2.md`)
   — and never as a gate: displayed orders can be spoofed, and when they are he
   stops trusting that stock's book (`q5DRctM5C-Q` [00:22:36]).

The bot can use none of it: a rule on a book this repository has never
recorded cannot be tested.

## Risks that remain

| risk | how it bites | what limits it now | still open |
|---|---|---|---|
| a WATCH / WAIT card shows a copyable buy line | a stop-limit staged while a gate is red can fill while it is still red — an entry the bot would refuse (IPDN 2026-10-06 07:32: trigger 4.16 under the VWAP 4.17) | the order panel says "not now — WAIT: below the VWAP 4.17" above the line, and **copy arms on REVIEW only** (owner's call, same day) | closed |
| the order is sized on the bot's paper risk until you type yours | a manual share count from a figure set for the paper exercise | **no share count until the owner types a risk** (owner's call, same day) | closed |
| a print's side is only as good as the quote it is read against | a stale quote reads a print on the wrong side; with `BidAsk` refused the quote is IBKR's sampled Level 1 | the tape's source line says which quote it reads, and the note calls the Level 1 read an Approximation | — |
| the tape shares IBKR's tick-by-tick allowance (5 streams on 100 lines, as reported) | TWS windows open on the same login can use it up; the desk's request is then refused | the card reads ERROR with IBKR's reason (10190) — never an empty tape that looks quiet | — |
| no stop at the broker before 09:30 | a pre-market entry is protected by the owner's eyes only | every pre-market ticket says so (probe 2026-09-18, warning 2109) | — |
| a stop inside the noise or wider than the halt band | stopped by an ordinary 1-minute range, or halted straight through the stop | red checks on the ticket (rule 5) | — |
| the position view is what was typed | the desk reads no fills or positions; a mistyped fill or a forgotten "I took it" means wrong trail alerts, or none | — | read positions from IBKR read-only (no order path needed) |
| alerts need the page open | a level crossed while the tab sleeps, or with sound and notifications blocked, passes unannounced | — | — |
| one IBKR username for the desk and hand orders | logging in elsewhere blinds the desk (10197) | a red banner names it | a second username — verify in Client Portal |
| the catalyst grade reads headlines only | a promotional headline with a hard word grades STRONG | the headline is always on the card | — |
| the bot's pillar count moved | names whose only catalyst was stale or an unread filing are now killed; the effect on results is not measured | recorded in `docs/preregistration.md` §5 | read it at the next review |
| replay look-ahead | a scrubbed replay shows the newest card | the card says so | a point-in-time card (row 3 above) |
| the same author audited and built | the new tests share the builder's assumptions | a separate review agent read the tape and layout diff the same day and confirmed 13 defects — another name's refusal pinned on the focus tape, unreported prints written into the desk's last price, a locked quote read as buying, a refused quote stream that could never fall back, focus requests for a name already left, no re-request after a competing login, among them; each fixed with a test | a human read of the diff |
| a clearer card read as an edge | legibility feels like reliability; no configuration tested so far has positive expectancy | the verdict below says so | — |

## What this assessment could not check

- 07:30 on the fixture (it starts at 08:00); the real days stand in for it.
- The owner's own trades: none were recorded on 2026-10-06 or 2026-10-07.
- The cascade on the fixture is computed at the end of the replay, so scrubbing
  back shows end-of-day verdicts beside earlier bars (seen at 09:40: WAIT "every
  Layer 1 gate passed" beside a red RVOL chip). Point-in-time replay is not built.
- Any claim that a better card improves results. It is not measured and not claimed.

## Verdict

Before: the desk computed most of what a manual entry needs but showed it in the
wrong order, refreshed the verdict once a minute while prices refreshed every
three seconds, said nothing about the bot, and carried three catalyst defects
that also fed the bot's pillar count. After: one card answers what to do now,
why, at what price, with the bot's own order and the bot's own answer beside it,
and the owner's calls are scored next to the bot's. None of it is evidence of an
edge: no configuration tested so far has positive expectancy, and the card makes
the method legible, not profitable.
