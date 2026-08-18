# Day Trade Dash — what the Momo export reveals about the filters

```
SOURCE · knowledge-base/daytrade-dash/captures/2026-08-18-momo-alerts.csv
         operator's own CSV export from the Warrior platform, high-day-momentum
         alert feed, 2026-08-18 04:02:48 → 05:36:30 ET (94 minutes, pre-market only).
         295 alert rows · 7 distinct symbols · 6 strategy branches.
CROSS-CHECK · continuous 1-minute bars for all 7 names pulled via scripts/tape.py
         the same morning (yahoo), 04:00 → 05:43 ET. The CSV is alert-sampled;
         every timing/threshold test below runs against the continuous bars.
CLEAN-ROOM · no credentials, tokens or private endpoints touched. Server-side
         thresholds remain UNDISCLOSED. Everything here is INFERRED FROM OUTPUT.
! OBSERVED BOUNDS BRACKET A THRESHOLD. THEY DO NOT REVEAL IT.
  "min price seen = 2.48" means the floor is ≤2.48, not that it IS 2.48.
  The one exception is a single-axis exclusion — see finding 2.
```

## The population, and why n is smaller than it looks

295 rows, but a symbol re-alerts continuously and appears under several
branches at once (XOS emits 3 rows at 05:36:30). **The effective sample is
7 symbols**, not 295. Every bound below inherits that.

| sym | float M | price range | vol (max) | rvol daily | chg from close | branches fired |
|---|---:|---|---:|---:|---:|---|
| PFSA | 0.61 | 10.20–12.77 | 2,238,876 | 3637–6876 | 125–182% | FormerMomo, SQ10 |
| WETO | 0.66 | 38.00–38.16 | 172,162 | 28.9 | 54.5–55.2% | VolHunter |
| IPST | 0.69 | 8.51 | 71,823 | **2.13** | 15.2% | FormerMomo |
| SGLY | 0.90 | 6.21–9.83 | 2,466,553 | 5.3–167 | 38–119% | all but MF |
| HCWB | 1.60 | 3.47–3.84 | 37,236 | 120 | 37.7–52.4% | FormerMomo, VolHunter, SQ10 |
| XOS | 8.40 | 3.99–4.07 | 9,148,860 | 1084–1253 | 90.9–94.7% | FormerMomo, LF/HRV, SQ5 |
| WFF | 41.92 | 2.48–2.97 | 5,142,617 | 519–1138 | 22.8–47.0% | **MF/HRV only** |

---

## Finding 1 — "New High" is a hard gate on every branch

`event` is `New High` on **295/295 rows**, across all six branches. Tested
against continuous bars: does the 1-minute bar containing the alert print a
high ≥ every strictly-prior bar's high?

```
alert bars that set a new high of day        293 / 293 measurable   100.0%
baseline: all 1-min bars of these 7 names      31 / 626              5.0%
```

100% against a 5% baseline. This is not an artifact of a rising tape — it is
a precondition. **The six "strategies" are not six scanners; they are six
qualification rules sharing one trigger.** Selection answers *which name*;
the new high answers *when the row appears*.

This is the finding with the most leverage, and it is the one our tooling
does not implement — `./now` and `premarket_stars.py` both rank on gap and
never ask whether the name is printing a new high right now.

## Finding 2 — the Low Float / High Rel Vol branch caps price near $10

**PFSA is a single-axis exclusion, the only clean identification in the file.**
It fired 72 alerts and never once fired `Low Float - High Rel Vol`, despite
beating the branch's observed floor on every measurable axis:

| condition (from what DID fire) | PFSA's best | |
|---|---:|---|
| float ≤ 8.40M | 0.61M | PASS |
| volume ≥ 531,073 | 2,238,876 | PASS |
| daily RVOL ≥ 5.34 | 3,637 | PASS |
| 5-min RVOL ≥ 3,255 | 654,725 | PASS |
| change ≥ 46.3% | 182% | PASS |
| **price ≤ 9.83** | **10.1951** | **FAILS** |

Price is the only axis that excludes it, and the bracket is
**[9.83, 10.1951)** — which contains exactly **$10.00**.

Corroborating, not independent: WETO ($38) also never fires this branch,
though its 169k volume is a second possible cause.

**Per-branch price ceilings therefore differ**, and the low-float branch is
the *tighter* one:

| branch | price ceiling |
|---|---|
| Low Float / High Rel Vol | **≈ $10** (bracketed) |
| Medium Float / High Rel Vol | $20 (stated in the branch's own name) |
| Former Momo | ≥ $12.77 (unbounded above by this data) |
| Low Float Volatility Hunter | ≥ $38.16 — **no cap in evidence** |

## Finding 3 — the float tiers tighten

| tier | prior bound (08-17 snapshot) | this capture |
|---|---|---|
| low-float ceiling | ≥ 5.38M | **≥ 8.40M** (XOS fires low-float branches) |
| medium float includes | 33.39M | **41.92M** (WFF) |

WFF at 41.92M fires **only** the medium branch, never a low-float one. The
low/medium boundary is therefore in **(8.40M, 41.92M]** — still wide, but
both ends moved. Our binary `<20M` cap sits inside that gap, which means it
is neither of his tiers.

## Finding 4 — Former Momo runs the lowest RVOL floor, and it is ≈2

IPST fired `Former Momo Stock` at **daily RVOL 2.13** — the lowest RVOL
anywhere in the file, in the branch the corpus said would have lower
thresholds.

| branch | lowest daily RVOL that fired |
|---|---:|
| **Former Momo** | **2.13** |
| Low Float / High Rel Vol | 5.34 |
| Squeeze 10%/10min | 5.34 |
| Low Float Volatility Hunter | 28.86 |
| Squeeze 5%/5min | 114.78 |
| Medium Float / High Rel Vol | 519.10 |

Two things land at once. The book's ch.10 claim that the Former Runner scan
uses **lower** thresholds is now confirmed from output, not just from prose.
And 2.13 sits just above **2.0** — the book's GR#1 scanner floor, and the
value scanner v2 was already corrected to on 08-17. That correction now has
an observation behind it instead of only a citation.

## Finding 5 — the squeeze thresholds are floors, and are not tight

Measured against continuous bars, low→high inside the trailing window:

| branch | n | min | median | at/above the advertised % |
|---|---:|---:|---:|---|
| Squeeze 5% in 5min | 8 | 8.1% | 9.4% | 8/8 |
| Squeeze 10% in 10min | 111 | 15.0% | 36.5% | 111/111 |

No row contradicts the advertised number, but **no row comes near it either**
— the thresholds are consistent with the names and unidentified by this data.
The alert-sampled CSV alone gives the opposite (and wrong) impression: from
its own price column the 5-min rows compute to a 0.09% median move, because
prices exist only at alert instants. That trap is the reason for the
continuous-bar cross-check.

## Finding 6 — housekeeping facts the export settles

- **`Gap(%)` and `Change From Close(%)` are byte-identical on all 295 rows.**
  Pre-market they are one field printed twice.
- **`Float` is static per symbol** across the session — a stored field, not live.
- **The export carries no news/flame field.** `Symbol / News` holds only
  `https://www.warriortrading.com/quote/<SYM>/`. The flame is rendered in the
  UI and does not survive CSV export, so **this file cannot test the
  red/orange/yellow recency question** from the earlier exchange. Answering
  that still needs a screenshot pair.
- **`Short Interest` is a column we do not have at all** (9,067 → 582,939 here).

---

## Rejected as unidentifiable from this capture

Stated rather than quietly omitted:

- **Every RVOL/volume floor except Former Momo's.** The observed minima are
  set by which of 7 names qualified, not by a boundary being approached.
- **The float tier cut**, beyond the (8.40, 41.92] bracket — no symbol sits
  near it.
- **The price floor.** Minimum seen is 2.48; the 08-17 snapshot already had
  alerts at $1.07, so this adds nothing.
- **Volatility Hunter's defining variable.** It fired on WETO, HCWB, SGLY —
  three names with nothing distinctive in common in these columns. Whatever
  separates it (an ATR or range measure) is not in the export.
- **The 5-min RVOL denominator.** Values reach 654,725%. Unusable until the
  denominator question is answered.

## What to change in this repo

| change | origin | evidence | status |
|---|---|---|---|
| Record low-float ≥8.40M, medium includes 41.92M | OBSERVED | this capture | applied to daytrade-dash/README |
| Former Momo RVOL floor ≈2 confirmed from output | OBSERVED | IPST @2.13 | corroborates the 08-17 scanner v2 change |
| **HOD-as-gate** | OBSERVED, 293/293 vs 5% baseline | strong | **NOT implemented — see below** |
| LF/HRV $10 price ceiling | INFERRED, single-axis | 1 exclusion | **NOT adopted** |

The last two are deliberately not shipped. The HOD gate is the better
finding and the bigger job: it would change `./now` from a ranking of gaps
into an event detector, which is a design change, not a dial. The $10
ceiling rests on **one symbol on one morning** — the inference is clean, but
one clean inference is still n=1, and this repo's standing rule is that a
threshold needs a measurement.

---

## Limitations

- **7 symbols, 94 minutes, one session, pre-market only.** No open, no
  intraday. Branch behaviour after 09:30 is untested here.
- **295 rows are not 295 observations.** A symbol re-alerts every few
  seconds; effective n is 7.
- Observed extrema bracket thresholds. Only PFSA yields a single-axis
  exclusion; every other number in this document is a bracket, not a value.
- **Cross-check bars are yahoo pre-market**, which is thinner and less
  reliable than the platform's own feed. The HOD and squeeze tests inherit
  that. Agreement at 100% and 111/111 makes feed error an unlikely
  explanation, but not an excluded one.
- Server thresholds stay unknowable from the client; the API surface is
  bearer-protected and was not touched.
- Paper only. Knowing how his scanner selects is selection evidence. The
  894-session replication of this strategy class was negative expectancy,
  and reverse-engineering the funnel does not revisit that.
