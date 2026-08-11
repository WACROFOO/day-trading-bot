---
name: ticker-verdict
description: Answer "analyze SYM", "SYM analysis now", "what's the play on SYM", "scenarios for SYM", or "best ticker right now" in one fixed format — verdict first, gate table, one reason, one level to watch. Use for any single-name or ranking question during market hours.
---

# Ticker verdict

**Verdict first. Table second. One paragraph third. Nothing else.**

Three question shapes, three formats below. Never mix them, never add sections.

---

## Always do first

```bash
python3 scripts/premarket_dd.py SYM      # bars, VWAP, EMA9/20, MACD, halts
python3 scripts/catalyst_score.py SYM    # 3-channel evidence
```
Plus finviz snapshot for float / shares out / book / cash / 52W high.
**State the ET time in the header.** Never answer from stale numbers.

---

## Format A — "analyze SYM" (default)

````
## SYM — NO TRADE · 10:58 ET
**One line: the single gate that decided it.**

```
last 6.79  prev 5.72 (+18.7%)   HOD 9.42 @09:43 → -27.9%
VWAP 8.19   EMA9 6.93  EMA20 7.06
MACD -0.139 / sig -0.114 / hist -0.0247
float –(12.6M out)  vol 10.1M  RVOL 30×
```

| gate | | |
|---|---|---|
| price $2–20 | 6.79 | ✅ |
| float <20M | not reported | ⚠️ |
| catalyst today | none | ❌ |
| ≤25% off high | -27.9% | ❌ |
| > VWAP | -17% | ❌ |
| > 9 EMA | below | ❌ |
| MACD +ve & > signal | fails both | ❌ |
| vol ≥1M, RVOL ≥1.5× | 10.1M, 30× | ✅ |
| 09:35–11:00 | 10:58 | ✅ |

**Why:** two sentences. Maximum.

**Watch:** one level that would change the answer. One line.
````

Verdict word is one of **TRADE / WATCH / NO TRADE**. Gate rows are always
those nine, always that order, even when they pass — a fixed table is
readable at a glance, a bespoke one is not.

If it says TRADE, and only then, add:
```bash
python3 scripts/size.py --entry X --stop Y
```

## Format B — "scenarios for SYM"

Format A's header + table, then **at most four** branches. Each is exactly
three lines: name and odds, the trigger, the action.

```
### A · Gap fill $5.72 · ~50%
Trigger: lost $7.00 on rising volume, MACD crossed down.
Action: nothing. No long below VWAP with negative MACD.
```

Odds are your estimate — label them as such once, not per branch.
Order by probability. Never write a fifth.

## Format C — "best ticker now"

One table, one row per name, ranked. No per-name paragraphs.

| sym | last | vs VWAP | MACD | float | catalyst | verdict |
|---|---|---|---|---|---|---|

Then **one** line naming the best and why, or saying nothing qualifies.
A flat day is a correct answer — say so and stop.

---

## Hard rules

- **Verdict in the header.** Never make the reader hunt for it.
- **One reason kills.** Name the first failing gate; don't list all nine failures in prose.
- **Fundamentals only if they change the verdict.** Book value, cash/share and
  P/B are not day-trade reasons. Mention them only as a *risk* (cash/sh above
  the price = offering fuel) or skip them.
- **No method recap.** The rules live in `knowledge-base/strategies/FILTERS.md`.
  Don't re-teach them in the answer.
- **No closing summary of the whole board** unless asked.
- **Total answer ≤ 40 lines.** If it's longer, cut prose, never data.

## Structural vetoes — state as one line, then stop

| finding | line to write |
|---|---|
| reverse split effective today | "The catalyst is the split. Gate 5." |
| 52W high > 20× price | "Split-adjusted history at NNN×." |
| equity line / ATM > market cap | "Can issue N× its market cap at will." |
| foreign private issuer (6-K/20-F) | "Dilution lands on a 6-K — the scorer is blind to it." |
| cash/share > price | "Not a floor. The reason to raise." |

---

Selection only. Replication over 894 sessions was negative expectancy
(`reports/2026-08-regime-filter.md`). Paper.
