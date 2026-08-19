# External review brief — ross-fp-v4.pine (revision V5.4)

Copy everything below the line into ChatGPT, then paste the full Pine file
after it. The brief is written so the reviewer attacks the failure classes
this project has actually shipped, instead of re-lecturing on documented
trade-offs.

---

## PROMPT

You are auditing a TradingView Pine Script v6 **strategy** (~1,300 lines) for
correctness. Be adversarial: your job is to find what breaks, not to summarise
what works. I will paste the full source after this brief.

**Context in one paragraph.** This is a mechanical replication of Ross
Cameron's small-cap momentum strategy — first-pullback and high-of-day-retest
entries on 1-minute charts of low-float gappers, paper trading only. It is one
component of a larger repo; stock selection happens outside it. The repo's own
894-session backtest of this strategy class was negative expectancy, so nobody
is claiming edge — the script's job is to be an *accurate* implementation of
stated rules, with honest display.

**Architecture you need to know before reading:**

- A confirmed-bar state machine: IDLE → IMPULSE → PULLBACK → ARMED → LONG,
  plus INVALID/DONE. Transitions only on `barstate.isconfirmed`.
- Entries are `strategy.entry(..., stop=trigger)` stop orders;
  `calc_on_every_tick=true` so fills happen intrabar once armed.
- THREE arming paths that share the state machine:
  1. **Formal**: full gate chain (push quality, retracement ≤50%, pullback
     volume, momentum, risk caps).
  2. **Fast lane**: any red candle closing while state ∈ {IMPULSE, PULLBACK}
     + momentum gates → arm at red high + buffer.
  3. **Uptrend lane**: any red candle in ANY non-armed state when MACD, EMA9
     and VWAP are all bullish (hard-coded) → arm.
  Lanes 2–3 deliberately skip the quality gates; they respect stop-size caps,
  a halt-band veto (RTH only), and a high-of-day room guard (trigger at/above
  HOD, or ≥1R of room below it).
- An ATR-fallback stop: when the candle-low stop exceeds `maxStopPct` or
  `maxStopATR`, the stop is substituted with `trigger − 1×ATR` instead of
  rejecting the setup.
- Exits: bracket (structural stop + 2R target) plus a "breakout-or-bailout"
  rule (exit if <0.5R MFE within 2 bars, or close below entry early).
- A dashboard table (14 rows, some gated by `dashFull`) and level plots.

**Bugs this codebase has actually shipped — hunt for more of the same class:**

1. *Forward references* (CE10272): top-level identifier used above its
   assignment. We lint for this but the linter is homemade.
2. *Non-const plotshape args* (CE10123).
3. **Zombie states**: an order was cancelled intrabar while the state stayed
   ARMED, showing a stale trigger 0.70 below price for 20 minutes. Patched
   three ways (lanes now set `pullbackLastBar`; cancel → INVALID; a staleness
   guard abandons ARMED when `close > trigger + ATR`). **Audit whether other
   cancel/transition paths can still desynchronise the order book from the
   state machine** — this is the highest-value target.
4. *Sentinel leaks*: `f_safeDiv` fallbacks of ±999 reached the display once.
5. *na-propagation*: comparisons against possibly-na vars silently false.

**Specific questions, in priority order:**

1. **Order/state desync.** Enumerate every `strategy.entry` / `strategy.cancel`
   call site against every state transition. Is there any path where an order
   exists with state ≠ ARMED/LONG, or state = ARMED with no working order?
   Include: fill happening on the same tick as an intrabar cancel; the retest
   path arming; `setupsToday` incrementing on arms that never fill.
2. **Repainting & lookahead.** The HOD tracking, the retest `brokenHOD`
   capture, `request.security` calls (daily RVOL, prior close, 5-min volume) —
   any repaint on historical vs realtime bars? Any `lookahead` hazard? Will
   backtest results systematically differ from live behaviour, and where?
3. **Intrabar semantics.** With `calc_on_every_tick=true`: do the lanes'
   confirmed-bar arming plus intrabar fills behave identically on historical
   bars (where ticks don't exist)? Flag every place backtest fills are
   optimistic relative to live.
4. **The state machine itself.** Draw the actual transition graph from the
   code. Find unreachable states, transitions that skip cleanup (vars from a
   previous setup surviving into the next), and any path where `pullbackBars`,
   `pushPeak`, `pullbackLow` etc. carry stale values.
5. **Double-counting / duplicate orders.** Same order id "Long" used by
   formal path and lanes. Can two paths arm in one script execution and
   produce conflicting stop levels or duplicated `setupsToday` increments?
6. **The dashboard.** Any cell that can display a value inconsistent with the
   state (the class of bug users actually notice). Table index bounds vs
   `dashFull` gating.
7. **Pine v6 pitfalls** we may have missed: `var` init timing, ternary type
   unification, `na` in bool contexts, series-vs-simple mismatches in inputs
   feeding `request.security`.

**What NOT to spend effort on** (documented, deliberate, or out of scope):
the strategy's profitability; the choice of thresholds (they are inputs, and
tuning them is measured elsewhere); the quality-score being display-only;
style/naming; the fact that selection (float, catalyst, dilution) is outside
the script; Pine having no per-cell multi-colour (known display limitation).

**Output format:** a numbered list of findings, each with (a) severity
CRITICAL / MAJOR / MINOR, (b) the exact line or code excerpt, (c) a concrete
failure scenario — inputs/state → wrong behaviour, (d) a minimal fix. If you
verify a suspected bug is NOT real, say so explicitly with the reasoning —
refuted findings are as valuable as confirmed ones. End with the three
findings you would fix first and why.

---

## SUMMARY OF THE FILE (for the reviewer's orientation)

| section | approx. content |
|---|---|
| header + inputs | 8 input groups: impulse, pullback, momentum, session, scanner criteria (display-only mirror of the Day Trade Dash pillars), retest, structure, risk, execution (incl. fast/uptrend lanes, ATR fallback, HOD room guard), display |
| context calcs | EMA9/20, VWAP (anchor selectable), MACD 12/26/9, ATR, halt-band width from prior close (15¢/<$0.75, 20%/$0.75–3, 10%/>$3 — veto RTH-only), HOD tracking, broken-HOD retest detection, daily/5-min RVOL via `request.security` |
| state machine | confirmed-bar; impulse detector scans a lookback window for the best candidate leg; retest path can enter PULLBACK directly with synthesised push metrics |
| gates | push quality, pullback count/retracement/volume, momentum, risk (with ATR-fallback stop substitution), session (soft by default), scanner (display-only by default), halt band |
| arming | formal block at bar close; fast/uptrend lanes at red-candle close; all place `strategy.entry("Long", stop=...)`; staleness + intrabar-retracement guards cancel |
| management | bracket exit at structural stop / 2R target; breakout-or-bailout within first bars; MFE tracking |
| display | 14-row table (9 in compact mode), per-criterion ✓/✗ with row-level all-met colouring, plan row with T1(half)/T2 ladder, level plots, event markers |

**Revision history relevant to review:** V4.8.1 fixed a shipped forward
reference; V4.9.1 fixed shipped non-const `plotshape` sizes; V5.0 added the
retest entry + HOD tracking; V5.1 added the fast lane; V5.2 the uptrend lane
+ ATR-fallback stop; V5.3 fixed the zombie-ARMED bug (three-part fix);
V5.4 added the lanes' HOD room guard. Each fix came from a live failure, which
is why the review brief emphasises finding the *next* member of each class.
