# First Pullback — does it have an edge?

An adversarial ablation of `knowledge-base/tradingview/ross-fp-v4.pine`
(REV `V9.12`) against the brief's 38 requirements.

```
FEED · universe 2024-09+ · Massive grouped daily (one call per DATE)
       universe 2016-2024 · Massive historical ticker list x Alpaca
                            multi-symbol daily — both survivorship-free
       minute   · Alpaca Basic, feed=sip, CONSOLIDATED
       cross-check · 28 RTH sessions on BOTH feeds: identical minute counts,
       identical session highs and lows, volume within 0.7%. ZERO disagreements.

SURVIVORSHIP · 12,613 tickers pulled, 6,701 carrying a delisted_utc.
       MORE THAN HALF the universe is companies that no longer exist.

SAMPLE · 25,716 candidate ticker-days · 2,615 sessions · 5,797 names
         2016-02-03 → 2026-08-21 · ELEVEN calendar years
         8,505 scanner-qualified ticker-days · 3,627 trades in variant A
         across 1,453 sessions
         → the brief's 1,000–3,000 ticker-day target is exceeded 3x

CODE · git 70fb29e · seed 20260824 · 33 tests, all look-ahead and fill order
```

**Answer: no. The First Pullback has negative expectancy, and the evidence is
now overwhelming rather than suggestive.** Every variant's 95% confidence
interval lies entirely below zero, in **all eleven years**, in a 478-session
untouched holdout — and a random entry minute on the same tape beats every
variant by 0.8 R.

---

## 1. What was considered — the funnel

| stage | count |
|---|---:|
| tickers in the historical reference list | **12,613** (6,701 delisted) |
| candidate ticker-days 2016-02-03 → 2026-08-21 | **25,716** |
| … sessions / distinct names | 2,615 / 5,797 |
| … after the top-5-gappers-per-session scanner cap | 11,363 |
| … passing the 09:35 ET point-in-time scanner | **8,505** |
| pullback candidates the detector observed (variant A) | ~87,000 |
| … armed and filled (realistic costs, pessimistic ambiguity) | **3,627** |

| year | ticker-days | sessions | names |
|---|---:|---:|---:|
| 2016 | 986 | 215 | 645 |
| 2017 | 1,147 | 245 | 676 |
| 2018 | 1,225 | 247 | 754 |
| 2019 | 1,193 | 249 | 741 |
| **2020** | **4,565** | 252 | 1,822 |
| **2021** | **3,012** | 252 | 1,411 |
| 2022 | 1,891 | 246 | 1,176 |
| 2023 | 1,903 | 247 | 1,176 |
| 2024 | 2,844 | 252 | 1,459 |
| 2025 | 3,848 | 250 | 1,798 |
| 2026 (to 08-21) | 3,102 | 160 | 1,447 |

COVID (2020) and the meme-stock era (2021) are in the sample. This is the
regime variation the brief asks for, and it is real rather than a two-year
slice of one environment.

**The universe is survivorship-free by two independent constructions.** For
2024-09 onward, grouped daily returns what actually traded on a date. Before
that, the full historical ticker list — active *and* delisted, each delisted
row carrying its `delisted_utc` — is screened with multi-symbol daily bars. A
company that gapped in 2019 and delisted in 2021 is screened on the days it
traded and is absent afterwards, with no special handling. The merged table
keeps a `source` column so the two methods stay separable.

Scanner rules, kept **separate from entry filters**: open $2–20, gap ≥ 10% vs
previous close, trailing-20-session dollar volume ≥ $250k, reverse-split
artefacts flagged and excluded, then the top 5 gappers per session (a
discovery cap on a gap known at 09:30, not an entry gate).

---

## 2. What distinguishes A from F

| rule | A | B | C | D | E | F | Pine |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| qualifying impulse (≥5% **and** ≥2 ATR **and** eff ≥0.60 **and** RVOL ≥2 **and** ≥$100k/min) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 878–930, 1645 |
| first pullback, 1–4 bars, ≥1 red | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1646 |
| retracement ≤ 50% of the push | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1647 |
| structural stop + caps (≤3% of price, ≤1.5 ATR, ATR fallback) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1598–1656 |
| trigger = pullback-bar high + 1 tick · stop = pullback low − 1 tick | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1587–1589 |
| close > VWAP **and** > EMA9 **and** EMA9 ≥ EMA20 **and** MACD > 0 **and** hist > 0 | — | ✓ | ✓ | ✓ | ✓ | ✓ | 1580–83, 1649 |
| confluence: ≥1 support (EMA9 / EMA20 / VWAP / half-dollar) | — | — | ✓ | ✓ | ✓ | **—** | 1577–1585 |
| pullback volume ≤ 0.70 × push volume | — | — | — | ✓ | ✓ | ✓ | 1648 |
| HOD room: trigger ≥ HOD-at-time, or ≥1R headroom | — | — | — | — | ✓ | ✓ | 1860 |
| halt-band veto (LULD tier, fail-closed inside RTH) | — | — | — | — | — | ✓ | 1642, 1652 |
| fast lane / uptrend lane / HOD break-and-retest | — | — | — | — | — | ✓ | 1836–1940, 1315–1362 |
| third-trade half size | — | — | — | — | — | ✓ | 1759 |

Two ways the requested ladder is not monotone, reported rather than smoothed:
**C is not a rung of the shipped strategy** (`supportCount` feeds only the
display-only quality score, line 1701 — there is no confluence gate), and
**F is not E-plus-something** (its lanes and retest are extra entry *paths*,
so it produces more trades than E: 1,542 vs 162).

**Declared gap:** the V8.2 LATE JOIN path (Pine 1477–1545) is not
implemented. The repo's benchmark measured it at +1 fill in 330 ticker-days.

---

## 3. Look-ahead controls

| control | how |
|---|---|
| indicators | incremental only; no vectorised pass exists |
| HOD | `max(high)` from session start **through the current bar** |
| RVOL-at-time | cumulative volume vs the same-session-minute average over **prior days only** |
| universe | open, previous close, trailing-20 dollar volume **excluding today** |
| scanner timestamp | frozen at 09:35 ET; every trade carries `scan_ts` |
| engine | one strict left-to-right pass, one Snapshot per bar |

Tested, not asserted (33 tests): HOD-at-time vs eventual daily high · prefix
reproduction · snapshot-list bound · **truncation audit** (cut at
45/50/55/60 bars, every prior trade returns identical) · no entry precedes
its scan timestamp · fill ordering under all three ambiguity policies ·
stop-limit gap-through is a MISS · unknown halt band fails CLOSED.

**Still unreconstructable, flagged not substituted:** float, catalyst/news,
true spread (range-quartile proxy), halt state. **Brief §17's float cut and
all of §18 cannot be produced.** No row is labelled "no catalyst" — absence
of a news feed is not absence of news.

---

## 4. The execution model

**41.4% of variant A's fills are intrabar-ambiguous.** Prior measurements in
this repo: 25% on 330 ticker-days, 26% on 250+ megadays. On 3,627 fills over
eleven years it is 41%. Structural, not a quirk.

| cost model | n | expectancy | slippage | commission | median stop |
|---|---:|---:|---:|---:|---:|
| **gross** | 3,812 | **−0.404 R** | 0.000 R | 0.000 R | 2.01% of price |
| low | 3,803 | −1.055 R | 0.226 R | 0.186 R | 2.01% |
| **realistic** | 3,627 | **−1.741 R** | 0.562 R | 0.186 R | 1.98% |
| stressed | **157** | −1.798 R | 0.649 R | 0.136 R | 1.41% |

Cost ≈ **0.75 R per trade**, on a stop the strategy caps at 3% of price
(Pine 406) — a number nowhere in the corpus, which
`research/megaday-study/RESULTS.md` §4 measured sitting on the population's
median stop.

**The stressed column is a refusal, not a result:** 157 of 3,627 entries
fill, because modelled slippage breaches the entry limit offset.

Ambiguity and cost together, variant A:

| | exclude | optimistic | pessimistic |
|---|---:|---:|---:|
| gross | **+0.118** | −0.053 | −0.404 |
| realistic | −1.217 | −1.414 | **−1.741** |

**The only positive cell in the entire study** is gross-of-all-costs with 42%
of trades discarded. It is also the least defensible one.

**Exit mix (A, realistic):** 2,360 STOP · **677 STOP_GAP** · 471 T2 ·
100 STOP_AMBIGUOUS · 19 SESSION_FLAT. Nearly one in five exits gaps *through*
the stop, which is where the missing halt archive bites.

Trade quality: average winner **+0.712 R**, average loser **−2.197 R**,
realised reward/risk **0.32**. **59.5% are stopped before reaching +0.5 R.**
Longest losing streak **45**. Worst day **−23.8 R**.

---

## 5. The ablation

```
Realistic costs · pessimistic ambiguity · Experiment 1 (identical exits).
2,615 sessions, 2016-02-03 → 2026-08-21.
95% CI = day-clustered bootstrap, 5,000 draws, resampling SESSIONS.
```

| Variant | Added rule | Trades | Sessions | Win % | **Exp. R** | PF | 95% CI | Holdout | Verdict |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| **A** | First pullback | **3,627** | 1,453 | 14.3% | **−1.741** | 0.08 | [−1.79, −1.69] | −1.837 | **NEGATIVE EDGE** |
| **B** | + VWAP/EMA/MACD | 2,428 | 1,140 | 15.2% | **−1.644** | 0.08 | [−1.70, −1.59] | −1.708 | **NEGATIVE EDGE** |
| **C** | + Confluence | 533 | 416 | 17.4% | **−1.497** | 0.10 | [−1.61, −1.38] | −1.440 | **NEGATIVE EDGE** |
| **D** | + Pullback volume | 199 | 169 | 14.1% | **−1.605** | 0.09 | [−1.80, −1.41] | — | **NEGATIVE EDGE** |
| **E** | + HOD room | 162 | 138 | 13.6% | **−1.654** | 0.09 | [−1.88, −1.42] | — | **NEGATIVE EDGE** |
| **F** | Full strategy | 1,542 | 859 | 15.5% | **−1.626** | 0.08 | [−1.70, −1.55] | −1.667 | **NEGATIVE EDGE** |

**Every variant, every interval, entirely below zero.** Profit factor never
exceeds 0.10 — for every dollar made, ten are lost.

| step | trades removed | exp. before | exp. after | Δ |
|---|---:|---:|---:|---:|
| B − A | 1,199 | −1.741 | −1.644 | +0.097 |
| C − B | 1,895 | −1.644 | −1.497 | +0.147 |
| D − C | 334 | −1.497 | −1.605 | **−0.109** |
| E − D | 37 | −1.605 | −1.654 | **−0.049** |
| F − E | −1,380 (F adds) | −1.654 | −1.626 | +0.028 |

The ladder improves by 0.24 R over its first two rungs and then **reverses**.
The best rung is 1.5 R from break-even.

---

## 6. Rejected-trade analysis

Variant A's 3,627 trades split by each gate, both sides traded under the same
exits. **Research only.**

| gate | accepted n / exp. | rejected n / exp. | separation | winners removed | losers removed |
|---|---|---|---:|---:|---:|
| **momentum** | 2,252 / **−1.641** | 1,375 / −1.905 | **+0.264** | 177 | **1,180** |
| confluence | 372 / −1.652 | 3,255 / −1.751 | +0.099 | 456 | 2,736 |
| pb_volume | 1,549 / −1.693 | 2,078 / −1.776 | +0.083 | 271 | 1,774 |
| **hod_room** | 3,096 / −1.819 | 531 / **−1.286** | **−0.532** | 114 | 408 |
| halt_band | 3,619 / −1.740 | 8 / −2.141 | +0.401 | 0 | 8 |

**Momentum is the only filter that clearly earns its place** — 1,180 losers
removed against 177 winners. **HOD room remains the one actively harmful
filter**, and at n=531 rejected that is now solid.

**A second correction to my own reading.** At 838 trades I reported
confluence as the strongest filter (+0.428). At 3,627 it is +0.099 — a
quarter of that. The first reading (49 trades) said it was harmful, the
second (838) said it was the best, the third (3,627) says it is marginal.
**Only the third has the sample to be worth anything.** Two sign-flips on the
way to the answer is exactly why the 11-year run was worth the hours.

---

## 7. Filter redundancy

Largest |phi| across all gate pairs: **0.269** (momentum ↔ hod_room,
negative). The filters are not redundant — momentum and room-to-HOD are
*opposed*, because the momentum stack only turns green once price is
extended. The brief's hypothesis that VWAP/EMA/MACD are one thing is not
what the data shows.

---

## 8. Cuts

**Time of day, variant A** (`useSessionWindow` defaults FALSE, Pine 314):

| window | trades | win % | exp. R | avg MFE |
|---|---:|---:|---:|---:|
| **09:30–10:00** | 877 | **19.5%** | **−1.471** | +0.98 |
| 10:00–10:30 | 303 | 12.5% | −1.799 | +0.67 |
| 10:30–11:30 | 549 | 12.2% | −1.845 | +0.71 |
| **11:30–16:00** | **1,898** | 12.7% | −1.826 | +0.73 |

**52% of trades are afternoon trades**, and the first thirty minutes is the
only bucket meaningfully better than the rest — still at −1.47 R.

Zero pre-market trades despite pre-market volume being present: the volume
gates rarely pass on 04:00–09:30 tape, matching the ghost-layer finding in
`2026-08-pine-v8-benchmark.md`.

**Stock characteristics, variant A** (n ≥ 100):

| cut | bucket | n | win % | exp. R |
|---|---|---:|---:|---:|
| price | **$2–5** | 1,624 | 10.0% | **−2.192** |
| price | $5–10 | 1,223 | 15.1% | −1.471 |
| price | **$10–20** | 693 | **22.1%** | **−1.158** |
| gap | 10–20% | 271 | 16.6% | −1.831 |
| gap | >100% | 552 | 15.0% | −1.601 |
| pullback № | **1st** | 1,822 | 13.3% | **−1.869** |
| pullback № | 2nd | 891 | 14.0% | −1.707 |
| pullback № | **3rd+** | 914 | 16.3% | **−1.519** |
| pullback depth | 20–35% | 1,604 | 15.9% | −1.633 |
| RVOL | <2 / 2–5 / >5 | 543 / 329 / 2,150 | — | −1.73 / −1.69 / −1.75 |

**The cheapest tier is by far the worst** and it is 45% of the sample.
**"First" is the worst pullback of the three** — the setup the strategy is
named after. **RVOL does not discriminate at all** (three buckets within
0.06 R), which is a third correction to an earlier small-sample reading.

---

## 9. Holdout and yearly consistency

```
CHRONOLOGICAL SPLIT of 1,592 traded sessions — never shuffled
  development 716 · validation 398 · holdout 478 (opened once)
```

| variant | dev | validation | **holdout** | holdout n |
|---|---:|---:|---:|---:|
| A | −1.694 | −1.711 | **−1.837** | 1,067 |
| B | −1.591 | −1.672 | **−1.708** | 588 |
| C | −1.507 | −1.526 | **−1.440** | 129 |
| F | −1.532 | −1.761 | **−1.667** | 356 |

**A 478-session, 1,067-trade holdout.** No parameter was selected on it.

| year | trades | win % | avg win R | avg loss R | **exp. R** | PF |
|---|---:|---:|---:|---:|---:|---:|
| 2016 | 84 | 20.2% | +0.57 | −2.04 | **−1.508** | 0.09 |
| 2017 | 167 | 12.6% | +0.72 | −2.13 | **−1.704** | 0.07 |
| 2018 | 174 | 17.8% | +0.72 | −2.19 | **−1.636** | 0.10 |
| 2019 | 215 | 13.5% | +0.72 | −2.20 | **−1.775** | 0.07 |
| 2020 | 478 | 16.3% | +0.73 | −2.18 | **−1.647** | 0.10 |
| 2021 | 628 | 12.6% | +0.77 | −2.11 | **−1.700** | 0.07 |
| 2022 | 422 | 13.0% | +0.70 | −2.23 | **−1.805** | 0.06 |
| 2023 | 350 | 18.0% | +0.70 | −2.26 | **−1.681** | 0.09 |
| 2024 | 387 | 12.1% | +0.70 | −2.25 | **−1.878** | 0.06 |
| 2025 | 404 | 14.6% | +0.70 | −2.23 | **−1.761** | 0.08 |
| 2026 | 318 | 11.9% | +0.66 | −2.26 | **−1.865** | 0.06 |

**Eleven years, eleven losses, in a band of 0.37 R.** Including the two most
favourable small-cap momentum environments in living memory. There is no good
year, no good regime, and no drift — just a stable negative.

---

## 10. Baselines and placebos

| baseline | n | win % | exp. R | PF | avg MFE | 95% CI |
|---|---:|---:|---:|---:|---:|---|
| **variant A as shipped** | 3,627 | 14.3% | **−1.741** | 0.08 | 0.78 | [−1.79, −1.69] |
| first pullback only | 1,800 | 13.4% | **−1.865** | 0.07 | 0.80 | [−1.93, −1.79] |
| second pullback only | 819 | 13.2% | −1.745 | 0.07 | 0.76 | [−1.85, −1.65] |
| third pullback and later | 767 | 15.4% | **−1.568** | 0.08 | 0.74 | [−1.67, −1.47] |
| trigger shifted up 5 ticks | 1,656 | 10.6% | −1.916 | 0.06 | 0.68 | [−1.99, −1.84] |
| trigger shifted down 5 ticks | 7,435 | 12.3% | −2.245 | 0.06 | 0.86 | [−2.30, −2.19] |
| **random entry, 09:35–11:30, 1-ATR stop** | **42,510** | **25.9%** | **−0.940** | **0.22** | **1.15** | **[−0.96, −0.92]** |

**A random entry minute beats the first pullback by 0.80 R**, on 42,510
trades, with intervals nowhere near each other. Random wins on every metric:
win rate 25.9% vs 14.3%, profit factor 0.22 vs 0.08, average favourable
excursion 1.15 R vs 0.78 R.

The wider-stop defence fails — the random baseline's 1-ATR stop is a median
1.49% of price against the strategy's 1.98%. **It pays more tax per R and
still wins.**

**This is the study's central result, and it held from 49 trades to 42,510.**
Selecting for the first-pullback shape selects for worse outcomes than not
selecting at all.

---

## 11. Post-freeze corrections — the one question the ablation raises

**NEW HYPOTHESES, labelled per brief §33.** The frozen A–F experiment is
closed. Everything here was chosen *after* seeing it, is measured on the
*same* data, and therefore cannot confirm itself. What it can answer:
**if every correction this study argues for were applied at once, does the
strategy reach positive expectancy?**

| configuration | n | win % | exp. R | 95% CI | account |
|---|---:|---:|---:|---|---|
| 0 · frozen C (baseline) | 533 | 17.4% | −1.497 | [−1.61, −1.38] | ruined |
| 1 · STOP: cap 3% → 6% | 730 | 20.1% | −1.333 | [−1.43, −1.23] | ruined |
| 2 · CLOCK: arm 09:35–11:30 only | 238 | 18.5% | −1.358 | [−1.52, −1.19] | $0.52 |
| 3 · ROOM: drop HOD-room gate | 533 | 17.4% | −1.497 | — | *no-op: C has no HOD gate* |
| 4 · STOP + CLOCK | 390 | 20.8% | **−1.222** | [−1.35, −1.09] | $0.43 |
| 5 · all three | 390 | 20.8% | **−1.222** | [−1.35, −1.09] | $0.43 |
| 6 · all three on A | 2,233 | 19.0% | −1.427 | [−1.49, −1.37] | $0.36 |
| 7 · all three on F | 1,294 | 21.6% | −1.297 | [−1.37, −1.22] | ruined |

**No. The best fully-corrected configuration is −1.222 R, CI [−1.35, −1.09].**

Fixing the unsourced stop cap, restricting to the corpus session, and
dropping the harmful filter together recover **0.28 R of a 1.5 R deficit**.
Every correction this study can justify, applied simultaneously, leaves the
strategy losing more than a full R per trade with the interval nowhere near
zero.

*(Config 3 is honestly a no-op — variant C's gate list never contained
`hod_room`, so dropping it changed nothing. The HOD-room correction is
genuinely exercised in configs 5 and 7, where F carries the gate: F frozen
−1.626 → all-three-on-F −1.297.)*

---

## 12. Overfitting audit

```
48 strategy parameters · 25 LOCAL HEURISTIC (13 self-flagged in the Pine)
→ effective degrees of freedom ≈ 29.8  against 2,615 independent SESSIONS
```

**88 sessions per free parameter.** At 20 sessions this ratio made every
conclusion unsupportable; here it is not close to binding. And a negative
result is the direction overfitting does not manufacture — you do not fit
your way to losing 1.74 R per trade across eleven years and a 478-session
holdout.

---

## 13. Experiment 2 and the account

F with its own breakout-or-bailout management closes most trades early; it
improves expectancy slightly by cutting losses faster, on a system that
should not be running.

$2,000 cash, 2% risk, compounding, realistic costs: **every variant except D
reaches zero equity.** A: −$1.85. B: −$0.09. C: −$0.18. F: −$0.78.

**Daily risk governor (§27): NOT RUN.** The shipped strategy has none. Given
the above it would change how fast the account dies, not whether.

---

## 14. What this analysis still could not check

- **Halts.** 677 of 3,627 exits gap through the stop; the free Nasdaq feed is
  forward-only, so a LULD pause that reopened below the stop is booked at the
  stop price and **understates** the loss.
- **Intrabar sequence.** 41.4% of fills undecidable without tick data.
- **True spread.** A range-quartile proxy drives the slippage model.
- **Float and catalyst.** No point-in-time source. §17's float cut and all of
  §18 are absent, not empty.
- **Before 2016.** Alpaca's minute history begins there.
- **The Pine itself.** `src/setups.py` is a port; state parity is asserted.
- **The LATE JOIN path**, declared and not implemented.

---

## 15. Answers to the twelve questions

| # | question | answer |
|---|---|---|
| 1 | Does the basic first pullback (A) have positive expectancy? | **No. −1.741 R, CI [−1.79, −1.69], n=3,627 over 1,453 sessions and eleven years.** Negative gross of costs too (−0.404 R). **NEGATIVE EDGE.** |
| 2 | Does VWAP/EMA/MACD improve out-of-sample expectancy? | **Yes, and it is not enough.** +0.097 R on the ladder, +0.264 R accept-vs-reject, 1,180 losers removed against 177 winners. **KEEP.** |
| 3 | Does confluence add measurable edge? | **Marginally: +0.099 R separation, +0.147 R on the ladder.** It is also not in the shipped Pine. **UNCERTAIN — and note this estimate flipped sign twice as the sample grew.** |
| 4 | Does low pullback volume add measurable edge? | **Barely: +0.083 R separation, and −0.109 R on the ladder.** **REMOVE.** |
| 5 | Does requiring room to HOD add measurable edge? | **No — it is harmful.** −0.532 R separation on 531 rejected trades; the rejected population is the best sub-population in the study. **REMOVE.** |
| 6 | Does F beat the simpler variants after realistic costs? | **No.** F −1.626 vs C −1.497. |
| 7 | Which filter removes the most **winning** trades? | **Confluence** — 456 (it removes 90% of everything). |
| 8 | Which filter removes the most **losing** trades? | **Confluence** (2,736). Per unit of damage, **momentum**: 1,180 losers against 177 winners. |
| 9 | Largest statistically credible improvement? | **Momentum**, +0.264 R, and it is credible at this sample. It is also insufficient by a factor of six. |
| 10 | Does it survive stressed slippage? | **157 of 3,627 entries fill.** In a poor-fill environment the strategy is not executable. |
| 11 | Does it survive the untouched holdout? | **It survives it as a loss:** −1.837 R on 1,067 trades over 478 sessions. |
| 12 | Genuine edge, or overfitting/noise? | **Neither. A genuine, stable negative** — eleven consecutive negative years in a 0.37 R band, at 88 sessions per free parameter. |

---

## Verdict

**NO EDGE. The First Pullback as specified in `ross-fp-v4.pine` V9.12 has
negative expectancy on 3,627 trades across 1,453 sessions, 11 calendar years
and a survivorship-free universe in which more than half the tickers no
longer exist — before costs as well as after.**

Five findings, in descending order of consequence:

1. **A random entry minute on the same qualifying tape beats every variant by
   0.80 R**, on 42,510 trades, with a tighter stop and therefore a higher tax
   per R. This held at 49 trades, at 838, and at 42,510. The pattern is not
   neutral — selecting for it selects for worse outcomes than not selecting.

2. **Eleven consecutive negative years in a 0.37 R band**, including 2020 and
   2021. There is no regime in which this works and no year hiding another.

3. **Every correction the study can justify, applied at once, gets to
   −1.222 R.** Widening the unsourced stop cap, restricting to the corpus
   session and dropping the harmful filter recover 0.28 R of a 1.5 R deficit.
   The costs are not the problem; they are the amplifier.

4. **Three of my own earlier readings were wrong and are corrected above.**
   Confluence looked harmful at n=49, best-in-study at n=838, and marginal at
   n=3,627. RVOL >5 looked like the strongest feature at n=49 and does not
   discriminate at all at n=3,627. Each was small-sample noise reported as a
   finding. Two sign-flips on the way to an answer is the case for the sample.

5. **The account dies.** $2,000 → $0 for every variant but one, with
   45-trade losing streaks and −23.8 R days.

This is where every other measurement in this repository has landed:
8,828 symbol-days over 894 sessions with no edge in any year
(`2026-08-regime-filter.md`), an accurate Pine port at −7.66 R and −10.55 R
(`2026-08-pine-v8-benchmark.md`), and a 250-megaday study whose verdict is
*"moteur de rejet, pas de génération de signal"*
(`research/megaday-study/RESULTS.md`). Five independent methods, one answer.

**What is worth testing next is not another filter on this entry.** The one
thing in this study pointing anywhere is that the *random* population reaches
+1 R far more often than the pattern-selected one — 25.9% win rate against
14.3%, mean MFE 1.15 R against 0.78 R, on the same qualifying names. That
says the qualifying **universe** may hold something the **pattern** is
actively selecting away from. Which is a different study, and an honest one
to run next.

---

```
NO TICKET ISSUED. Paper only. This study did not validate executable
bid/ask, borrow, halt state, float, catalyst, or the Pine's compiled
behaviour. Reproducible from results/run_manifest.json.
```
