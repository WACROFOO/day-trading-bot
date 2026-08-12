---
name: ticker-verdict
description: Answer "analyze SYM", "SYM analysis now", "what's the play on SYM", "scenarios for SYM", or "best ticker right now" in one fixed format — verdict first, gate table, one reason, one level to watch. Use for any single-name or ranking question during market hours.
---

# Ticker verdict

**Verdict first. Table second. One paragraph third. Nothing else.**

## Rule zero — provenance

**Every price, volume or print cited must appear in a tool output from THIS
turn.** No number from memory, no "the last prints show" unless the prints are
in a fetch you just ran. If a claim needs a number you don't have, fetch it or
drop the claim. A plausible invented print is worse than a missing one —
it poisons trust in every real number around it.

## Always run first

```bash
python3 scripts/tape.py SYM              # VWAP, EMA9/20, MACD, halts, ranges, fade — ONE command, no ad-hoc python
python3 scripts/catalyst_score.py SYM    # 3-channel evidence
```
Plus finviz snapshot (float, shs out, book, cash, 52W high) and the
**split test** below. `tape.py` exists so the tape side is never hand-rolled —
hand-rolled fetches are where invented numbers come from. Thresholds live in
`knowledge-base/strategies/FILTERS.md`; on any conflict with this file,
FILTERS.md wins.

## Gate 5 — the split test is MANDATORY before any reverse-split verdict

The veto's premise is arithmetic: "the gap IS the split". That is only true if
the reported prev close is **unadjusted**. Test it — `split_check()` in
`premarket_stars.py` does exactly this:

```
finviz_prev ÷ yahoo_prev ≈ clean integer (8.00)  → gap is the split → KILL
sources agree (ratio ≈ 1)                        → prev already adjusted
                                                 → the move is REAL → gate
                                                   does NOT fire
```

A split that already settled = tiny new float = the thing this method hunts.
It stays in the answer as **risk context** (compliance shell, offering can
land on a 6-K with no warning) — priced into size, never into the reject.
*MSGY 2026-08-11: rejected on the unfired precondition, ran 2.54 → 5.43.*

---

## Format A — "analyze SYM" (default)

````
## SYM — NO TRADE · 10:58 ET
**One line: the single gate that decided it.**

```
last 6.92  prev 5.72 (+21.0%)   HOD 9.42 @09:43  LOD 6.67
VWAP 8.18   EMA9 6.97   EMA20 7.00
MACD -0.063 / sig -0.085 / hist +0.022
float –(12.6M out)  vol 10.2M  RVOL 30×
```

| gate | | |
|---|---|---|
| price $2–20 | 6.92 | ✅ |
| float <20M | not reported | ⚠️ |
| catalyst today | none | ❌ |
| ≤25% off high | -26.5% | ❌ |
| > VWAP | -15% | ❌ |
| > 9 EMA | below | ❌ |
| MACD +ve & > signal | negative | ❌ |
| vol ≥1M, RVOL ≥1.5× | 10.2M, 30× | ✅ |
| 09:35–11:00 | 11:08, past | ❌ |

**Why:** two sentences. Maximum.

**Watch:** one level that would change the answer. One line.
````

Verdict word: **TRADE / WATCH / NO TRADE**. The nine gate rows never change
shape or order, even when they pass. If TRADE, and only then, add:
```bash
python3 scripts/size.py --entry X --stop Y
```
Stop distance must be survivable on this tape: check the median and max 1-min
range. **A 3¢ stop on a halting stock is fiction** — say so instead of
printing it.

## Format B — "scenarios for SYM"

Format A's header + table, then **at most four** branches, ordered most →
least likely. **No percentages** — invented odds are decorative precision.
Each branch is exactly three lines:

```
### A · Gap fill to 5.72 — most likely
Trigger: LOD 6.67 breaks on rising volume.
Action: nothing. No long below VWAP with negative MACD.
```

## Format C — "best ticker now"

One table, one row per name, ranked. No per-name paragraphs.

| sym | last | vs VWAP | MACD | float | catalyst | verdict |
|---|---|---|---|---|---|---|

Then **one** line naming the best and why, or saying nothing qualifies.
A flat day is a correct answer — say so and stop.

---

## Structural vetoes — one line each, then stop

| finding | line to write |
|---|---|
| split test says gap = split | "The catalyst is the split. Gate 5." |
| 52W high > 20× price | "Split-adjusted history at NNN×." |
| equity line / ATM > market cap | "Can issue N× its market cap at will." |
| foreign private issuer (6-K/20-F) | "Dilution lands on a 6-K — the scorer is blind to it." |
| cash/share > price | "Not a floor. The reason to raise." |

## Self-check before sending — every answer, every time

1. Verdict in the header? 2. Every number traceable to this turn's fetches?
3. Split test actually run, not cited? 4. ≤ 40 lines per name?
5. No method recap, no board summary (unless asked), no percentages on
   scenarios? **Writing these rules was easy; this checklist is where they
   get followed.**

---

Selection only. Replication over 894 sessions was negative expectancy
(`reports/2026-08-regime-filter.md`). Paper.
