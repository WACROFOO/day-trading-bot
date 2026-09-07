# Full assessment — 7 September 2026

Written for the owner, in plain words. Every statement about the software
was checked by running it on this date. Every statement about the strategy
is cited to a file in this repo. Nothing about real markets is claimed,
because the platform has not yet run through an open market.

**Basis.** Branch `claude/playbook-pullback-explanation-tg5c33` at the end
of this review; the automated tests run today (counts at the bottom); one
replay of the synthetic ten-stock fixture through the complete chain; one
live run on a holiday morning (7 September, Labor Day) that exercised every
connection against the real broker with the market closed.

---

## 1. What the platform is, in one picture

```
gap scan ──► desk watches ──► rule-checker ──► pullback detector
                                   │                  │
                                   ▼                  ▼
                            written to the DIARY at that instant
                                   │
                        trader program reads the diary
                        ├─ refuses (with the reason)
                        ├─ logs only            ← phase A, where we are
                        └─ places entry + stop together   ← phase B, later
                                   │
                    fill, exit, and the screen price at the fill
                                   │
                    grader adds what the stock did next
                                   │
                    honesty check re-runs every decision
```

The desk and the trader never talk to each other. They talk through the
diary (a database file). That one design choice is what makes the whole
thing auditable: nothing can be traded that was not first written down
with everything that was known at that moment.

---

## 2. What is included and working

Grouped by what it does for you. "Proof" is a test that runs on every
change, or a live result you saw yourself.

### Finding the stock (Ross's Layer 0 and Layer 1)

| piece | plain meaning | proof |
|---|---|---|
| Gap scan | before the open, finds the stocks gapping up and throws out the ones that break his first rules, naming why | ran live on 7 Sept: nine rejects named, one survivor |
| Rule-checker (the cascade) | the eight kill rules from `knowledge-base/strategies/FILTERS.md`: price band, float under 20M, a catalyst or a live theme, not faded more than 25%, not a split gap, not a fund, penny ticks, no buyout. First failure is final; anything unknown fails closed | 37 tests |
| Float handoff | the scan's real float (finviz) is handed to the desk, so the desk no longer kills good names on a shares-outstanding upper bound | live-chain test; found on 7 Sept (WETO armed on a 22M bound) |
| Feed-health rule | if the price feed goes stale, delayed or dies, every verdict is STALE and nothing is armed | 4 tests; found on 7 Sept |
| Market calendar | the day refuses to start on a weekend or NYSE holiday and says which | 3 tests; found on 7 Sept |

### Deciding to enter (Layer 2 and the setup)

| piece | plain meaning | proof |
|---|---|---|
| Pullback detector | impulse of at least two green bars and 2%, a one-to-four bar pullback on lighter volume, entry when a bar breaks the previous bar's high, stop under the pullback low, target at 2× the risk. Plans freeze and never repaint | existing tests |
| **Chart gates (new today)** | above VWAP, holding the 9 EMA, MACD positive and above its signal, computed from the desk's own bars. **Until today these were never computed on the live path**, so the best verdict a stock could get was WATCH and real orders would never have checked the chart | 3 tests; the fixture now produces a REVIEW |
| **REVIEW required for a real order (new today)** | the trader program places nothing unless every chart gate is green. Log-only records the others so the funnel shows how many pullbacks the chart turned away | test |
| Verdict on screen | the bottom-right card shows the server's word and the gate that killed the name; a killed stock reads "suppressed · KILLED", never "ARMED" | 2 browser tests |

### Placing the order safely

| piece | plain meaning | proof |
|---|---|---|
| Paper only | refuses any account that is not a paper account; there is no switch to turn this off and a test fails if one is added | test; confirmed live on `DUR339781` |
| Entry and stop together | the stop is attached in the same transmission; a failure part-way sends nothing | live smoke test 6 Sept |
| Sizing from your risk only | shares = your stated dollar risk ÷ (entry − stop). Never from buying power | test |
| Window | no new entries after 11:30 ET; exits always allowed | test |
| Same tape | no order leaves unless the desk has a quote for that stock fresher than 30 seconds | test |
| **Daily risk gate (new today)** | reads the diary: locks the day after 3 consecutive losses, or −3 R, or 6 entries. Once locked stays locked, survives a restart. **Until today the live trader ran with no risk gate at all** | 3 tests |
| Pre-market path | only in phase C, only in the shape the broker test dictates; with a `queued` verdict the runner itself is the stop and the position is marked unprotected by name | 8 tests |
| After-hours | a position still held after 16:00 is flagged for you and never sold by the program; the exit command records who confirmed | 7 tests |

### Recording and grading (the backtest)

| piece | plain meaning | proof |
|---|---|---|
| The diary | every plan, taken or not, with the price, quote, news, float and every gate at that instant; written once even though the desk rebuilds every few seconds; **now saved to disk** (until 7 Sept it never was, so the trader would have read nothing) | 18 tests + live-chain test |
| Every candidate, not just trades | the whole board is snapshotted so the denominator exists at every stage | test |
| Both risk numbers | planned risk (entry − stop) and realised risk (fill − stop). The research found realised ran 1.5× planned | test |
| Screen price at fill | bid and ask at the instant of each fill, so a paper fill can be judged plausible or not | test |
| **Exits recorded (new today)** | a filled stop or target now closes the trade in the diary with its price and reason. Until today only entries were ever synced, so no P&L existed | test |
| **Never-filled entries (new today)** | at the hard stop an entry that never filled becomes NOT_FILLED, not a trade | test |
| **Restart recovery (new today)** | a restarted trader adopts the diary's open orders instead of forgetting them | 2 tests |
| The grader | for every decision, refused ones included: what the stock did over 5, 15, 30, 60 minutes and to the stop, whether the stop or target was hit and which first | 10 tests |
| Controls | the strategy against hold-to-close and enter-at-bar-close on the same rows, in the same units | test |
| Honesty check | re-runs every decision from what was stored and confirms the same verdict; any divergence blocks advancing | 5 of 5 on the fixture |
| The one-command day | scan → probes → desk → trader → hard stop → grading → report → session count, with the stop probe at 07:00 and holidays not counted | 14 tests; ran live 7 Sept |
| **Cumulative review (new today)** | `exercise.py review`: sessions, what kills most, what the executor refuses most, verdict mix, fills, controls, replay, today's risk state | test |

---

## 3. Results so far — accurately

**There are no market results.** The platform has not run through an open
market. Anyone showing you a P&L from it today would be inventing it.

What exists is plumbing evidence:

| measurement | value | meaning |
|---|---|---|
| synthetic fixture: symbols → plans → killed → allowed | 10 → 5 → 3 → 2 | the funnel has a denominator at every stage |
| kills by gate | catalyst 2, float 1 | the rejects are named with the rule that fired |
| verdicts at the plan | REJECT 3 · WAIT 1 · **REVIEW 1** | REVIEW is now reachable — proof the chart gates are live |
| honesty check | 5 of 5 reproduce | the diary can reproduce its own decisions |
| controls (planned R, n=5, synthetic) | strategy 0.20 · hold 2.54 · random 2.88 | the comparison runs; the numbers mean nothing (invented stocks) |
| live broker, holiday | both logins, both probes, desk, trader, scan all connected and behaved | the chain works against the real broker |
| automated tests | see footer | |

---

## 4. What is remaining

In the order it will happen.

| item | who | when |
|---|---|---|
| Client Portal: share real-time market data with the paper account | you, once | before Tuesday |
| Decide the login setup: single paper login (recommended) or both | you | Tuesday morning; the runbook has both recipes |
| Set the pre-registration numbers (`docs/preregistration.md`): risk per trade, sessions before real orders, trades before judging, what counts as failure | you | before the first real order |
| First real session, log only | the day command | Tuesday |
| Five honest log-only sessions | the day command | this week and next |
| Broker answers: does a stop hold pre-market; does the paper account see the tape | the probes, automatic | Tuesday |
| Leave log-only mode | `exercise.py advance`, only when every gate is clear | after the five sessions |
| Real paper orders, regular hours only | phase B | then |
| Pre-market entries | phase C, shape set by the probe | after 30 trades |
| Read-out against the pre-registered failure condition | phase D, once, at 60 trades | weeks away |
| One pre-existing screen bug (LIVE/STALE badge repaint) | me | cosmetic, no trading effect |
| Theme detection ("sympathy" plays) | not built | the rulebook allows a live theme to stand in for a catalyst; nothing detects one, so such names are killed on "no catalyst" |
| Level 2 / tape | never automatable here | shown as a manual check on the card |

---

## 5. How it runs automatically

One human command per trading morning, or none with the installer:

```
python3 scripts/day.py                 # or IBKR_PORT=4002 python3 scripts/day.py, single login
```

Everything else is the machine: scan, probes, desk, trader in the mode the
phase dictates, hard stop, grading, report, session count. Phase changes
are the one thing a human must type (`exercise.py advance`), and the
machine refuses unless every pre-registered gate is met. `docs/day-runbook.md`
is the page to keep open.

## 6. Where the logs are

| what | where |
|---|---|
| the diary (every decision, order, fill, exit, quote, bar, halt) | `data/journal.sqlite` — not committed |
| one report per session day | `research/paper-exercise/reports/` |
| the exercise's state (phase, sessions, probe verdicts, risk lock) | inside the diary, read with `exercise.py state` |
| the cumulative view | `exercise.py review` |
| the terminal, live | one line per decision as it happens |

## 7. The backtesting loop for continuous improvement

1. **Every session grades itself.** After the hard stop, every decision —
   taken, refused, killed, unfilled — gets what the stock did next. The
   report names each reject with the gate that fired.
2. **Every session checks itself.** The honesty check re-runs every decision
   from the stored inputs. A divergence means the diary or the code drifted,
   and it blocks the phase from advancing until fixed.
3. **The cumulative review says where to look.** Which gate kills most,
   which refusal dominates, how many pullbacks the chart turned away, how
   the strategy stands against the free baselines on its own names.
4. **What may change and what may not.** Plumbing and data quality may be
   fixed at any time (the float source was one such fix). The rulebook's
   thresholds and the detector's logic are frozen until the phase-D
   read-out (`docs/preregistration.md` §7). Tuning them on paper fills is
   forbidden by name, because paper fills are optimistic and tuning on them
   amplifies the error.
5. **Regression protection.** `BASELINE-2026-09-06.md` records the known
   failures and the fingerprint; the test suite runs on every change.

## 8. What this exercise cannot tell you, even when it all works

Whether the strategy makes money — the prior research over 894 sessions
says it did not (`research/momentum-replication/reports/2026-08-regime-filter.md`).
Whether a paper fill would have happened for real. What happens in a
trading halt. Anything about a different month.

---

## Footer — the numbers behind this report

- Automated tests, non-browser: **553 passed, 1 failed** — the failure is the pre-existing one recorded in the baseline
- Browser verdict tests (Chromium): **3 passed** — the card shows the server's word, never PASS, and names every non-passing gate
- Known pre-existing failures, recorded in `BASELINE-2026-09-06.md`: two
- Live sessions through an open market: **zero**
- Real orders placed: **zero**
