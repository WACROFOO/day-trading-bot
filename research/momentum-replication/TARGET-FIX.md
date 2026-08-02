# Target fix, and what TCX says about it

## The defect

The first target was `max(high_of_day, measured_move)` — the **furthest**
structural objective. On CUPR 2026-07-31 every trade after 10:55 carried a
target of $5.77, the high of day, while price sat in the $2.80s. Unreachable —
and it satisfied the 2:1 reward:risk filter *trivially because it was so far
away*. **The filter was passed by an impossible target.**

## The fix

The first target is the **nearest** structural objective above the entry. Both
candidates are documented — a retest of the high of day (5 videos) or a measured
move equal to the pole height (`small-cap-momentum-bull-flag.md`) — and the
source describes the first target as typically 15–20 cents away, i.e. near.

```python
objectives = [x for x in (hod, pullback_low + pole) if x and x > entry]
t1 = min(objectives) if objectives else 0
rr_ok = (t1 - entry) >= 2 * risk
```

---

## Does the fix work? The direct test

The fix is meant to make the 2:1 filter discriminate. It does — on both symbols
the trades the filter would **skip** lose money, and the trades it **allows**
make money:

| | TCX | CUPR |
|---|---|---|
| Target reachable at 2:1 (allowed) | n=58, **+$3,139.31** | n=10, **+$5.15** |
| Target not 2:1 (skipped) | n=20, **−$409.91** | n=11, **−$16.00** |

Before the fix the filter separated nothing, because every distant target
passed it. This is the clean result: **the fix does what it was supposed to do,
on both symbols, in the same direction.**

---

## Does the gate gradient replicate? No.

CUPR suggested outcome improved monotonically with gate score. **TCX does not
reproduce that**, and the honest reading is that the CUPR result was thin.

Mean R by gate score:

| Gate score | CUPR (n) | CUPR mean | TCX (n) | TCX mean |
|---|---:|---:|---:|---:|
| 6 of 6 | — | — | 1 | +1.82R |
| 5 of 6 | 5 | +0.31R | 16 | +16.23R |
| 4 of 6 | 7 | +0.03R | 24 | +3.07R |
| 3 or fewer | 9 | −0.47R | 37 | +5.39R |

CUPR is monotonic (+0.31 → +0.03 → −0.47). TCX is not: the ≤3 bucket (+5.39R)
beats 4-of-6 (+3.07R). Two symbols, opposite answers.

Two further reasons not to lean on TCX's numbers:

- **TCX trended all day** — open $11.10, close $15.43, +39%, finishing near its
  high. Almost any long trade made money, so the sample is biased toward
  winners regardless of setup quality.
- **Mean R is inflated by tiny stops.** The +16.23R average in the 5-of-6
  bucket comes from trades whose risk-per-share was a couple of cents; a normal
  move is then dozens of R. R is not comparable across trades with wildly
  different stop widths, and this is where that bites.

So: the target fix is supported. The gate-quality claim from CUPR is **not**
replicated and should be treated as withdrawn pending a proper multi-day test.

---

## What the TCX losses teach

23 losses. The recurring causes, in order of frequency:

1. **`pullback index <= 2` fails in nearly every loss.** TCX trended all
   morning without losing VWAP, so the counter climbed to #7, #8 and kept
   going. Every late-morning setup was structurally disqualified. Whether that
   is the rule protecting the account or the counter-reset reading being wrong
   is still open — it is listed as an unresolved parameter in `OBSERVATIONS.md`.
2. **"Entered at/near the high of day"** — 7 losses. Buying the top of the leg
   rather than a dip inside it.
3. **Stops inside the spread** — 7 losses, e.g. 10:17 ($0.120 stop vs $0.128
   spread), 11:06 ($0.040 vs $0.069), 13:43 ($0.020 vs $0.030). Same lesson as
   CUPR: these cannot survive noise, and the spread floor correctly rejects
   them.
4. **Died in 1–2 bars** — 11 losses.

`price > VWAP`, the dominant loss predictor on CUPR, barely appears on TCX —
because TCX held above VWAP nearly all day. That is consistent rather than
contradictory: VWAP separated winners from losers on the day it was
informative.

---

## Engine-level effect

17-day window, all-symbol:

| | Before fix | After fix |
|---|---:|---:|
| Trades (max 5) | 20 | **6** |
| P&L | −$1,104.94 | **+$817.95** |

Look-ahead audit passes at every cut-off. Friday 2026-07-31 is still 0 trades;
`target < 2:1` now appears as a rejection reason there (4 setups), which is the
filter doing its job rather than being satisfied by an impossible number.

**n=6.** The sign has now moved with every structural change in this project.
The target fix is justified by the mechanism and by the filter-separation test,
not by this P&L, and the P&L should not be quoted as a result.
