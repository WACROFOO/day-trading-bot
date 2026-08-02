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
