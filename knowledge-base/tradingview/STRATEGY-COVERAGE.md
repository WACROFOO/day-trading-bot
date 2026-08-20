# ROSS FP — what the script covers, what it cannot, and how to read it

```
SCOPE · ross-fp-v4.pine revision V9.4, 2026-08-20. Written after the
        operator's step-back request on live MMA + the Top Gainers export.
SOURCES · the script itself; PARAMETERS.md; FILTERS.md; AUDIT-RESPONSE-V6.md;
        research/momentum-replication/reports/ (measured findings cited
        by path). Nothing below is asserted from memory.
STATUS · paper only. The repo's own 894-session replication of this
        strategy was NEGATIVE expectancy
        (research/momentum-replication/reports/2026-08-regime-filter.md).
        This document explains a tool, not an edge.
```

## The setup, in plain words

The script trades ONE pattern long: a small-cap already moving up hard,
its **first orderly dip**, entered on the **break back above the dip's
last red candle**. Everything on screen serves that sequence:

1. **A push** — ≥5% or ≥2 ATR within ≤6 one-minute bars, moving
   efficiently (≥0.60 of the path is net progress), on ≥2× local volume.
   State: `MOVE UP`.
2. **A dip** — 1–4 bars, keeping more than half the push (≤50%
   retracement), on lighter volume than the push. State: `DIP FORMING`.
3. **The trigger** — a stop-buy one tick above the last red candle's
   high. Placed at bar close when every gate is green (`ORDER SET`),
   filled intrabar on the break.
4. **The exits, fixed at entry** — stop under the dip low (or an
   ATR-substitute when the candle-low stop is fiction), half sold at
   +1R, stop to break-even, remainder at 2R. If the break stalls —
   two bars without follow-through or a close back under entry — it
   bails at market. No averaging down, no second position (pyramiding=0).

Four ways into the same trade: the formal path above; the **fast lane**
(any red candle inside a valid structure — the EHGO case); the **uptrend
lane** (red candle + MACD/EMA/VWAP all green in any state — the YJ case);
the **HOD break-and-retest** (broken high holds as support). A **late
join** catches a dip that formed while the machine was busy with the
previous trade (the CDTG case). All lanes share the same stops, sizing,
session window and vetoes.

**Decision order on the dashboard:** VERDICT (one of BUY / WAIT / NO /
MANAGE, always present) → PLAN (the three levels) → SIZE (shares, $
position vs equity, risk) → CLOCK (market phase vs the 07:00–11:30
arming window — two different clocks) → SETUP (is THIS dip tradeable)
→ TREND (is the tape behind it) → HIGH OF DAY (front side or back side)
→ STOCK FIT (is this even the right stock — selection, not timing).

## What is implemented (and where it came from)

| piece | source |
|---|---|
| Impulse/pullback thresholds | PARAMETERS.md; local additions labelled `[UNTESTED local]` in the inputs |
| Entry above the red-candle high, no waiting for the next bar | operator directive (EHGO), V5.1 |
| Stop under the dip low; ATR fallback on wide candles | daytrade-dash/README.md (measured 1-min ranges) |
| Halt-band enforceability veto | FILTERS.md rule: a stop wider than the LULD band cannot be honoured |
| T1 half at +1R, break-even, 2R runner | DAILY-ROUTINE-FR.md exit policy |
| Breakout-or-bailout | corpus rule, V4 |
| 2% risk sizing, $50 flat beginner path, third-trade half-size | PARAMETERS.md §7 (n=125) |
| 07:00–11:30 hard window, boundary flatten, last-bar no-arm | PARAMETERS.md §2; V8 re-audit |
| Ghost signals when only the clock refuses | operator directive (CDTG), V7.3 |
| 4-pillar selection display + 2+ hits rule | 2026-08-18 export (MEASURED, 299/299 New-HOD); KSPN yg5E_mqGFGg @00:16:47 |
| Execution honesty: varip cancel latches, exactly-once fills, pre-staged exits, ambiguity counting | external audit + re-audit, AUDIT-RESPONSE-V6.md |

## What the script CANNOT do — the limits, each with its receipt

1. **It cannot see the 10-second pattern.** His micro-pullback is often
   a sub-minute event; a 1-minute detector structurally misses it —
   MEASURED, `research/momentum-replication/reports/2026-08-streams-roundup.md`.
   The fast lane narrows this gap; it does not close it.
2. **It cannot read float.** TradingView exposes no float field to Pine.
   Float must be typed (`scripts/chart_card.py <export.csv> SYM` prints
   it from a Top Gainers export). An untyped float shows `?` and the
   pillar fails closed — that is honesty, not a bug.
3. **Its RVOL is not Warrior's RVOL.** The chart computes a TradingView
   same-time proxy (cumulative volume today ÷ average cumulative volume
   at this minute). Warrior's "Rel Vol Daily Rate" uses their own
   denominator (MMA 2026-08-20: Warrior 7,744×, proxy ~4,911× — same
   direction, different number). The chip is labelled ᵗ for this reason.
   Comparing them as if equal is the error.
4. **It cannot handle halts.** No ticks = no cancels, no exits; backtest
   fills walk through gaps a live order would never get (MSGY resumed
   +15% from its halt, 2026-08-14). Disclosed, unsolvable from Pine.
5. **It sells at fixed R, he sells into strength.** Halt-level and
   extension exits are a documented divergence
   (`research/momentum-replication/reports/2026-08-ispo-stream.md`);
   the repo's own exit policy is the
   2R ladder, and that is what runs.
6. **No news, no catalyst, no dilution, no Level 2, no spread.** The
   whole Layer-0/1 reject cascade (split test, S-3/shelf, buyout
   pinning, executable size) lives outside the chart — `./now --scan`
   and by hand. The script is a Layer-2 trigger tool; it qualifies
   nothing (header scope exclusion).
7. **No multi-day levels.** Prev close and the current day's/pre-market
   high are drawn; older daily S/R is not computed. Intraday pivots (2
   per side) are the S/R fan.
8. **Long only, one position, no adds** — by design (pyramiding=0).
9. **Backtest numbers are not portable.** Same-bar trigger+stop bars are
   unknowable from OHLC — counted and flagged on LIMITS; on real tape
   25% of fills hit this
   (`research/momentum-replication/reports/2026-08-pine-v8-benchmark.md`).
10. **The strategy itself has no measured edge.** 894 sessions negative;
    the benchmark's own 11 days: −7.7R to −10.6R. The tool's job is
    discipline and visibility, not prediction.

## What V9.4 changed after the step-back

| complaint | change |
|---|---|
| "no strong clean S/R" | the S/R fan is BACK on the always-on layer (V9 had over-cleaned it into diagnostics): 2 levels each side + prev close, plus the **pre-market high** as a new first-class line |
| "stop/target too narrow" | the hypothetical (no-setup) stop is now STRUCTURAL — under the 5-bar swing low, never tighter than 1 fallback-ATR — and the 2R target widens with it. Live setups already used the dip low |
| "float and rvol not correct" | they were not wrong — they were *unknowable* (float) and *a different measure* (RVOL). `scripts/chart_card.py` bridges the export to the inputs; the chips colour from measured values while gates stay fail-closed |

Paper only. An accurate implementation is still not an edge.
