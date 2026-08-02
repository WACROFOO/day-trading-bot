# What he spotted that the engine didn't — two weeks, 07-20 to 07-31

44 tickers named across 13 recaps. **10 were on a watchlist here** (ADVB, AMIX,
BIYA, CJMB, DFNS, EDBL, ERNA, INM, STFS, ZCMD). **34 were not.** Those 34 split
into four causes, three of which are decisions I made rather than rules he
broke.

---

## Cause 1 — the $2 price floor. The largest single exclusion.

`PARAMETERS.md:20` states `price_min >= 2.00` with **n=144**, and records in the
same row that **"1.00 also stated"**. I resolved that conflict to $2. He trades
below it, repeatedly, and those are the biggest movers he names:

| Ticker | Day | Open | Gap | RVOL | Verdict |
|---|---|---:|---:|---:|---|
| **ZYBT** | 07-20 | $1.26 | **+82%** | enormous | price + float |
| **LGHL** | 07-29 | $1.20 | +12% | **66×** | **price only** — passed everything else |
| LABT | 07-30 | $1.99 | +1% | 0.2× | price |
| CPHI | 07-24 | $1.78 | −4% | 6.6× | price |
| IQST | all 10 days | ~$1.05 | flat | <2× | price |

**LGHL on 07-29 is the cleanest miss in the dataset**: +12% gap, 66× relative
volume, 0.9M shares outstanding — it satisfied gap, volume and float, and was
rejected solely for trading at $1.20 instead of $2.00.

The corpus states both thresholds. Neither is wrong; picking $2 is a choice, and
this is what the choice costs.

## Cause 2 — my +200% gap guard, which is not a documented rule

| Ticker | Day | Gap | RVOL | Rejected by |
|---|---|---:|---:|---|
| **LABT** | 07-22 | **+249%** | 16,186× | `gap > 200%` — **my invention** |

The guard exists to catch reverse-split artifacts (see `HISTORY.md` defect 1),
and it does. But LABT's +249% was a real move, and the guard has no basis in
`PARAMETERS.md`. This is a false positive from a heuristic I added to fix a data
bug, and it is the only ticker in this study excluded purely by a rule the
source does not contain.

## Cause 3 — the 20M float ceiling

| Ticker | Shares out | Named in |
|---|---:|---|
| ZYBT | 47.4M | 3 recaps |
| CPHI | 43.0M | 3 recaps |

`PARAMETERS.md:26` gives `float_max <= 20M` with "10M preferred, 5M ideal" — and
records the value as **disputed** (18 statements for 20M, 16 for 10M). Both of
these are more than double the ceiling. Either the ceiling is wrong, or float
is not the binding criterion for him, or — most likely — my market-cap-over-price
proxy is not float. Actual float is usually far smaller than shares outstanding.

**This is a measurement problem as much as a threshold problem.** The proxy
cannot distinguish a 47M-share company with a 3M float from one with a 47M
float.

## Cause 4 — he trades setups this engine does not implement

| Ticker | Day | Gap | What it was |
|---|---|---:|---|
| CPHI | 07-22 | **−64%** | not a gap-up at all |
| ZYBT | 07-21 | **−46%** | not a gap-up at all |

A stock down 64% on the day cannot enter a long momentum scan, and should not.
He named these anyway — as reversals, second-day plays, or short squeezes on
prior movers. `PARAMETERS.md` §1 defines a **gap-up momentum** universe; these
are different setups from the same watchlist, and the engine implements only the
one.

## Cause 5 — never in the candidate pool

SLND, VIBK, INHD, ATAI, DJT, DWAC and others never entered the 2,486-symbol
pool, which is filtered on price and market cap from a current snapshot. DJT and
DWAC are large caps he mentions as market context rather than trades. The rest
are genuine pool gaps.

Several apparent tickers — BIWAY, BIY, INFL, INLX, INFS, MIT — are caption
garbling of BIYA and INLF, not real symbols.

---

## Summary

| Cause | Documented? | Fixable? |
|---|---|---|
| $2 price floor | **conflict in source** ($2 and $1 both stated) | test $1 as the floor |
| +200% gap guard | **no — my invention** | narrow it, or replace with split-calendar checks only |
| 20M float ceiling | disputed in source; **proxy is not float** | needs real float data |
| Reversal / short-squeeze setups | out of scope by design | separate strategy |
| Pool gaps | — | widen the pool |

**Two of the five are mine, not his.** The +200% guard has no source basis at
all, and the $2 floor resolves a documented conflict in the direction that
excludes the most active names he trades.

The float proxy is the one that cannot be fixed by choosing differently — it
needs a real float feed, which is now a fourth item on the paid-data list
alongside pre-market volume, sub-minute bars and halt status.

## The cheap test

Re-run both weeks with `price_min = 1.00` (the corpus's other stated value) and
the gap guard relaxed, and see whether ZYBT, LGHL and LABT appear. That is a
parameter the source explicitly offers, not a tuning knob — and unlike a P&L
comparison it has a falsifiable prediction: **those three names should show up.**

---

# Test result — prediction 2 of 3 confirmed

Re-ran both weeks with `PRICE_MIN=1.00` (the corpus's other stated value) and
the gap guard relaxed to 400%.

```bash
WEEK=07-22 PRICE_MIN=1.0 GAP_CAP=400 WATCH_NAMES=20 python pipeline/week.py 2
```

| Predicted | Result |
|---|---|
| **LABT** | **appears** — 07-22 at +249% |
| **LGHL** | **appears** — 07-27 at +124%, 07-29 at +12% |
| **ZYBT** | **still absent** — prediction wrong |

**ZYBT is blocked by the float ceiling, not the price floor.** Its
shares-outstanding proxy is 47.4M against a 20M ceiling. I listed float as a
separate cause and should have predicted ZYBT would stay out; the prediction was
sloppy, and the test caught it.

## Everything else the lower floor recovers

The $1 floor plus the relaxed guard widens the watchlists substantially — the
07-22 list goes from 3 names to 10 (adding LABT +249%, INLF +46%, KUST +22%,
SNTG, CRIS, HIHO, MGIH), and 07-30 adds YAAS at +390%, which the 200% guard had
been discarding as a suspected split artifact.

## But none of them trade

Neither LGHL nor LABT survives to a trade, and both weeks return **exactly the
same P&L as before** (+$833.28 and −$199.98). The one-shot rate-of-change check
removes all three:

| Name | Day | Open | 09:34 | Change |
|---|---|---:|---:|---:|
| LABT | 07-22 | 6.50 | 5.70 | **−12.3%** |
| LGHL | 07-27 | 2.05 | 2.03 | −0.9% |
| LGHL | 07-29 | 1.20 | 1.18 | −1.8% |

All three were **below their opening price at 09:35**, so the filter drops them
for the day.

## What this actually settles

The price floor and the gap guard were real exclusions and are now switchable
with the corpus's own alternative value. But they were not the binding
constraint — **the one-shot rate-of-change reading is**, and it is the same
unsettled question flagged in `2026-07-27-week.md`.

That reading now blocks two things at once: the faders it was added to remove,
and the biggest movers he actually traded. LABT opened at $6.50, was down 12% by
09:35, and he named it anyway. A continuously-running scanner would re-alert it
when it turned; a one-shot 09:35 gate cannot.

**This raises the priority of resolving that reading above the price floor.** It
is now the single largest divergence between this engine and his behaviour, and
`NEXT-STEPS.md` §5 lists it as unresolved rather than decided.
