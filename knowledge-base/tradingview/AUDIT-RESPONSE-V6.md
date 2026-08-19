# V6 — response to the external adversarial audit

```
AUDIT · ChatGPT, against commit 05e9826 (V5.4), 2026-08-19.
        5 critical, 14 major, 1 minor, 13 refuted suspicions.
VERDICT ON THE AUDIT · substantially correct. The central finding — that
        Pine rolls ordinary `var` state back between realtime executions
        while orders persist, so V5.3's zombie fix un-fixed itself one tick
        later — is right, and it invalidates the mental model several of my
        intrabar patches were built on. Every finding was verified against
        the source before acting; three fixes diverge from the auditor's
        suggested remedy, each with the reason below.
STATUS  · every finding addressed in V6.0 or explicitly disclosed as a
        platform limit. NOT COMPILED — TradingView remains the only compiler,
        and the regression list at the end is manual until it is scripted.
```

| # | sev | finding | action in V6 |
|---|---|---|---|
| 1 | CRIT | intrabar cancel state rolls back; zombie returns | `varip intrabarCancelled` latch (reset on `barstate.isnew`), the ONLY varip in the script by design; intrabar state writes demoted to display; the close execution commits a durable INVALID; every arming path checks the latch |
| 2 | CRIT | same-minute entry+exit vanishes | lifecycle keyed to monotonic `strategy.closedtrades` vs `handledClosedTrades`; flat → DONE + cancel; position remaining → T1-partial detection. Fires correctly regardless of what the var state rolled back to |
| 3 | CRIT | realtime cancel absent from history | cannot be reproduced historically (no historical ticks; `isconfirmed` always true). Mitigated: fills on bars whose low touched the stop are labelled **AMBIGUOUS SEQ** on the chart rather than silently trusted. Backtests must be read with those flags. *Diverges from the auditor's "exclude such bars" — exclusion silently deletes fills too; a visible flag keeps the count honest* |
| 4 | MAJ | `calc_on_order_fills` re-runs confirmed logic with final OHLC | turned OFF (bracket now lands one tick late live / next bar historical — disclosed), plus a `lastSignalBar` once-per-bar latch as belt-and-braces |
| 5 | CRIT | no session/day/halt expiry | new-day and session-boundary block: cancels pending orders, invalidates setups, flattens positions at the session edge when the hard window is on. Halts stay unsolvable from Pine (no ticks = no cancel) — disclosed, not papered over |
| 6 | CRIT | formal NO overwritten by uptrend arm same-execution | uptrend lane arms from clean IDLE only, `bar_index > stateStartBar`, `not eventInvalid`, `not intrabarCancelled` |
| 7 | MAJ | `setupsToday` counts trigger revisions | counter moved to the FILL detector; half-size rule reads prior fills (`>= 2` = third fill) |
| 8 | MAJ | lanes leave incoherent setup records | `KIND_FAST` / `KIND_UPTREND` added; lanes initialise pullback fields; uptrend lane nulls the push record so retracement math reads na instead of a sentinel; retest kind can no longer leak onto lane entries |
| 9 | MAJ | lanes bypass advertised-hard controls | lanes now enforce session, post-fallback ATR cap, dollar cap, user-enabled scanner veto, and FAIL-CLOSED halt band (na inside RTH = veto, both paths) |
| 10 | MAJ | daily `security()` merge delayed on history | switched to the documented stable pattern: `[expr[1]]` offset WITH `lookahead_on` — offset removes the future leak, lookahead removes the merge delay |
| 11 | MAJ | `brokenHOD` ratchets; wick breaks; no expiry | episode model: first CLOSE-confirmed break freezes the level; episode ends on retest consumption, 2 confirmed closes below, or age > `retestMaxAgeBars` (30, input); live setups keep a frozen `setupRetestLevel` copy; the plot draws the frozen copy |
| 12 | MAJ | retest fabricates a red candle | honest count (`close < open ? 1 : 0`); the pullback gate accepts `KIND_RETEST` without a red candle explicitly — the pattern's definition, not a falsified counter |
| 13 | MAJ | day volume omits the first bar | rollback-safe accumulator: `dayVolCum := isfirst or newDayBar ? volume : dayVolCum + volume` |
| 14 | MAJ | sizing ignores declared slippage | `slipPerShare = 2 × 10 ticks`; both paths size on `risk + slipPerShare`, so the modelled worst case fits the budget. `SLIP_TICKS` must be kept equal to the `strategy()` argument (Pine cannot read it back — noted in-source) |
| 15 | MAJ | synthetic fill ordering; optimistic bailout | `immediately=true` removed (bailout fills next tick/bar). Bar Magnifier is a chart/plan setting Pine cannot force — disclosed in-source. Ambiguity labelling from finding 3 covers the conflicting-levels case |
| 16 | MAJ | dashboard promises a ladder the code doesn't run | the code now runs the ladder: `T1` exit (50% at entry+1R), `RUNNER` (remainder at 2R), runner stop → break-even once the T1 partial is detected via the closed-trades counter. Detection lags one tick live / one bar historical — conservative, disclosed |
| 17 | MAJ | `liveEval` scope; LIVE tag dropped | LIVE tag re-appended to the verdict (it was computed and orphaned in the V5.3 compression). Full confirmed-snapshot mode NOT built: with `calc_on_every_tick` the preview layer is inherently live, and freezing only the dashboard would misrepresent the working orders. The input's honest scope (pullback-low preview) is documented |
| 18 | MAJ | dashboard contradicts state | INVALID/DONE get explicit verdict branches (no more "CHART OK" beside a red NO); GATES row now includes MOM/RR/SCAN and its colour IS `hardGatesOK`; unknown float renders `F?` not `F✓`; lower-high claims require a live impulse (`hodComparable`); abandoned plans are wiped when the cancel commits |
| 19 | MAJ | sentinels leak; `f_safeDiv` na numerator | numerator validated; every ±999 fallback in R/risk metrics replaced with na + explicit na-handling in gates; `f_rr` renders na as an em dash |
| 20 | MIN | inconsistent revision strings; double retest marker | title/alerts/REV unified on V6; generic TRG marker excludes `KIND_RETEST` |

## Where V6 diverges from the audit's remedies

1. **F3**: flag ambiguous historical fills instead of excluding them. Exclusion
   is also a distortion — it deletes real fills the live logic would have
   taken. A visible AMBIGUOUS SEQ label keeps the row and the doubt.
2. **F16**: implemented the ladder rather than downgrading the display,
   because the ladder is the repo's documented exit policy
   (`DAILY-ROUTINE-FR.md`), so the display was right and the code was behind.
3. **F17**: no full snapshot mode. Freezing the dashboard while the order
   book stays live would manufacture a new class of display-vs-reality
   disagreement — the exact defect class this audit is about.

## Regression list (from the audit, tracked manually until scripted)

The auditor's 20 regression cases are accepted as the test plan. None can run
in this repo (no TradingView runtime); they are executed by hand on the chart:
1–2 intrabar cancel persistence + same-minute round trip · 3 one fill = one
alert · 4–5 no same-bar re-arm after NO/exit · 6 trigger revisions count once
· 7–8 session/day expiry · 9 halt = unprotected gap, disclosed · 10 lane
record completeness · 11 lane risk controls · 12 ambiguous bars flagged ·
13 HTF stable across reload · 14 first-bar volume · 15 dashboard = tester
exits · 16 liveEval scope documented · 17 per-state verdicts · 18 unknown ≠
pass · 19 no sentinel reaches a string · 20 slippage-aware sizing.

Paper only. An accurate implementation is still not an edge.
