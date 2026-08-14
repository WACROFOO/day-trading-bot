# Audit: "ROSS First Pullback V3" Pine strategy (ChatGPT-authored)

```
SOURCE AUDITED · knowledge-base/tradingview/ross-fp-v3.pine (archived) ·
received 2026-08-14 · audited against FILTERS.md, PARAMETERS.md, the
2026-08 parameter audit, the score-basket measurement and the 2023 book.
NOT RUN: TradingView backtests — this container has no TV runtime. Every
claim below is static analysis plus this week's tape.py measurements.
The slippage-sensitivity table is therefore a PROTOCOL, not a result.
```

## Universe considered

Every input, gate, state transition and execution property of V3 —
32 inputs, 7 gates, 7 states, 2 order paths. Verdicts: 9 MATCHES ·
4 DIVERGES · 2 MISSING · 6 LOCAL_ADDITION.

## Divergence table

| rule | V3 | source says | verdict |
|---|---|---|---|
| MACD gate | `value>0 and hist>0` | *"positive and above the signal line"* (PARAMETERS §723). hist>0 ⟺ above signal, value>0 ⟺ positive | **MATCHES** — checked, not assumed |
| VWAP gate | input, **default OFF** | Layer 2: `price > vwap` required at entry | **DIVERGES** → V4 default ON |
| EMA9 gate | input, **default OFF** | Layer 2: `price > ema9` required | **DIVERGES** → V4 default ON |
| Session | **"NO time-of-day filter"** (header, as a feature) | measured window 07:00–11:00, 11:30 hard stop; his broker-split profit curve starts 07:00; after hours measured not profitable | **MISSING** → V4 session input, default ON |
| Quality score | 0–100 + A+/A/B/C grades | score-basket: similar score lost **16/16** vs equal weight, anti-predictive above 50 | **DIVERGES** → grades removed, number demoted to display-only with the caveat printed on the dashboard |
| Entry timing | stop-entry armed at CLOSE of a confirmed pullback bar | intrabar entry at the break of the previous red candle's high | **DIVERGES — documented, NOT changed** (see below) |
| Trigger definition | prev pullback bar high + buffer | *"first candle to exceed the previous red candle's high"* | MATCHES |
| One red candle suffices | `redPullbackBars >= 1` | *"one red candle is enough"* | MATCHES |
| Retracement ≤50% | default 50 | his tolerance zone | MATCHES |
| Pullback volume < push volume | ratio ≤0.70 | *"the dip comes on lighter volume"* | MATCHES |
| Breakout-or-bailout | 2 bars to prove ≥0.5R MFE | immediate-resolution principle is SOURCE; the 0.5R/2-bar numbers are not | MATCHES in kind, **LOCAL_ADDITION in numbers** (flagged UNTESTED) |
| 2:1 planned R:R | input, default OFF | book GR#5 "generally minimum 2:1" as a plan; audit: realised best-month 1.42, never a pre-entry veto | MATCHES (off-by-default is the audited reading) |
| Pullback #3 | duration >3 bars → **REJECT** | *"3rd pullback: reduce size, don't skip"* — and that rule is about pullback NUMBER, which V3 doesn't track at all | **DIVERGES + MISSING** → V4 counts setups/day, halves size from the 3rd; duration cap kept as flagged local, loosened to 4 |
| Halt bands | absent | book: prior close <$0.75→15¢, $0.75–3→20%, >$3→10%, fixed all session. A stop wider than the band cannot be honoured | **MISSING** → V4 computes the band, warns, and (toggle, default ON) vetoes |
| minEfficiency 0.60 | gate | no corpus source | LOCAL_ADDITION → flagged UNTESTED in the input label |
| minDollarVolume $100k/min | gate | closest source is "1M+ session shares" — different object | LOCAL_ADDITION → flagged |
| breakoutBufferTicks | 1 tick | no source (he buys the break, no stated offset) | LOCAL_ADDITION → flagged |
| slippage=1, commission 0.01% | strategy() | measured 1-min median ranges this week: 0.23–0.83 on the names this targets | **DIVERGES from reality** → V4 default slippage 10 ticks |

## The one divergence deliberately NOT fixed

**Bar-close arming vs intrabar entry.** Fixing it means arming intrabar,
which multiplies the repaint surface (the script itself admits intrabar
ordering cannot be reconstructed historically). Cost of keeping it: when the
first red candle completes and the break happens within the *next* bar, V3
fills correctly; when the break happens late in the arming bar itself, V3
misses that leg entirely. On fast tape (FGI's 10:51 leg took one bar) this
misses real entries. Accepted trade-off: **backtests stay trustworthy;
live-signal users must know the tool is one bar late by construction.**
Recorded here rather than silently — the design pack's withdrawal rule.

## Honesty-of-backtest findings

1. **Halt fills.** TV fills a stop order AT the stop price. MSGY's 10:02
   halt on 08-13 reopened +15% higher; WETO halted 5 times on 08-14. Any V3
   backtest on these names books exits that did not exist. No Pine fix —
   V4 prints it in the LIMITS row; the report reader must discount.
2. **Slippage sensitivity — PROTOCOL (not run here).** Re-run the identical
   backtest at slippage 1/5/10/20/25 ticks. Measured context: median 1-min
   range 0.23–0.83 this week → 1 tick is fiction, 10 is charitable, 20–25
   approximates halting names. **If the P&L sign flips across this sweep —
   and on 2R targets with 25¢ stops it plausibly does — the strategy has
   no demonstrated edge at realistic friction.**
3. **Repaint surface.** Trustworthy: everything keyed on
   `barstate.isconfirmed` (state machine, arming, bailout). Not
   reconstructable historically: the intrabar ARMED-cancel and
   `calc_on_order_fills` re-entry timing. Live behaviour will diverge from
   backtest around exactly the fast bars that matter most.
4. **Scope.** Pine sees one chart: the entire Layer 0/1 cascade (float,
   catalyst, split test, dilution, buyout) lives outside. V4 says so in its
   header and dashboard. This tool *triggers*; it must never *select*.

## What changed in V4 (one theme per commit)

| change | origin | evidence_status |
|---|---|---|
| VWAP+EMA defaults ON | SOURCE (FILTERS Layer 2) | SOURCED |
| session window 07:00–11:30 ET, default ON, OFF prints a warning | SOURCE (broker split, book ch.3) | SOURCED |
| setups/day counter, half size from 3rd | SOURCE rule, LOCAL mapping (setup-count proxies pullback-number) | REASONED_NOT_MEASURED |
| grades removed; score display-only with printed caveat | MEASURED (score-basket 16/16) | SOURCED |
| halt-band computation + warn + veto toggle | SOURCE (book halt table); prevDayClose taken from last print incl. AH — documented approximation | REASONED_NOT_MEASURED |
| vocabulary: ARMED→TRIGGER SET, LONG→IN TRADE, REJECT→NO, "BREAK X = LONG"→"Trigger X — confirm on chart", LIMITS row added | design pack | N/A |
| slippage default 1→10 ticks | measured 1-min ranges | REASONED_NOT_MEASURED |

Not changed: state machine, bailout logic, impulse detection (best parts —
prompt's own constraint), 2:1 default-off, bar-close arming (above).

## Limitations of this audit

No TradingView runtime here: nothing was backtested, the slippage table is
a protocol for the operator, and Pine v6 compilation of V4 is unverified —
paste it into the Pine editor and report compile errors back. And the
standing sentence, which no audit overturns: **nothing here establishes
profitability — the repo's own 894-session replication of this strategy
class was negative expectancy. A green backtest on optimistic fills is a
description of the fill model, not of the edge.**
