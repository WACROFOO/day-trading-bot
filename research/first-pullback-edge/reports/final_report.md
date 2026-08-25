# First Pullback — does it have an edge?

An adversarial ablation of `knowledge-base/tradingview/ross-fp-v4.pine`
(REV `V9.12`) against the brief's 38 requirements.

```
FEED · universe  · Massive (ex-Polygon) grouped daily, free Basic tier
       minute    · Alpaca Basic, feed=sip, CONSOLIDATED — verified 2026-08-25
       cross-check · 28 RTH sessions compared across BOTH feeds: identical
       minute counts, identical session highs and lows, volume within 0.7%.
       ZERO disagreements. (results/provider_verification.json)
✓ pre-market volume present · ✓ delisted names retained in the universe by
  construction · ✓ 1-minute history 2024-09-24 → 2026-08-21

SAMPLE · 7,948 candidate ticker-days · 479 sessions · 2,731 names
         1,837 scanner-qualified ticker-days · 20,248 pullback candidates
         838 trades in variant A across 353 sessions and 945 names
         → the brief's 1,000–3,000 ticker-day target is MET

CODE · git 33d5774 · config sha256 (see run_manifest.json) · seed 20260824
       33 tests pass, all of them about look-ahead and fill ordering
```

**Answer: no. There is no edge here, and the evidence is now strong enough to
say so rather than to plead insufficient sample.** Every variant's 95%
confidence interval lies entirely below zero, in every year, in the untouched
holdout, and a random entry minute on the same tape beats all six.

---

## 1. What was considered — the funnel

| stage | count |
|---|---:|
| universe construction | **grouped daily, one call per DATE** — every ticker that printed |
| candidate ticker-days 2024-09-24 → 2026-08-21 | **7,948** |
| … sessions / distinct names | 479 / 2,731 |
| … after the top-5-gappers-per-session scanner cap | 2,377 |
| … passing the 09:35 ET point-in-time scanner | **1,837** |
| pullback candidates the detector observed (variant A) | **20,248** on 477 sessions, 945 names |
| … armed and filled (realistic costs, pessimistic ambiguity) | **838** |
| stop-limit orders that triggered but could not fill | 2,988 (almost all under *stressed* slippage — see §4) |

The universe is **survivorship-free by construction**, which is the one thing
the earlier Yahoo-based version of this study could not achieve. Grouped daily
returns what actually traded on a date, so a company that gapped in 2025 and
delisted in 2026 appears on its own day and vanishes afterwards with no
special handling. A symbol list — any symbol list — is a list of things that
still exist.

| year | ticker-days | sessions | names |
|---|---:|---:|---:|
| 2024 (from 09-24) | 998 | 69 | 626 |
| 2025 | 3,848 | 250 | 1,798 |
| 2026 (to 08-21) | 3,102 | 160 | 1,447 |

Scanner rules, kept **separate from entry filters** as the brief demands: open
$2–20, gap ≥ 10% vs the previous close, trailing-20-session dollar volume ≥
$250k, reverse-split artefacts excluded (344 flagged), then the top 5 gappers
per session. `scanGates` is `false` in the shipped Pine (line 330), so none of
these is used as a trade gate here either.

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
| confluence: ≥1 support (EMA9 / EMA20 / VWAP / half-dollar, clustered EMAs once) | — | — | ✓ | ✓ | ✓ | **—** | 1577–1585 |
| pullback volume ≤ 0.70 × push volume | — | — | — | ✓ | ✓ | ✓ | 1648 |
| HOD room: trigger ≥ HOD-at-time, or ≥1R headroom | — | — | — | — | ✓ | ✓ | 1860 |
| halt-band veto (LULD tier, fail-closed inside RTH) | — | — | — | — | — | ✓ | 1642, 1652 |
| fast lane / uptrend lane / HOD break-and-retest | — | — | — | — | — | ✓ | 1836–1940, 1315–1362 |
| third-trade half size | — | — | — | — | — | ✓ | 1759 |

**Two ways the requested ladder is not monotone, reported rather than smoothed:**

1. **C is not a rung of the shipped strategy.** `supportCount` exists in the
   Pine but feeds only the display-only quality score (line 1701) — there is
   no confluence gate. It passes **15.3%** of candidates, so D and E inherit
   small samples. A secondary ladder without it is in §5b.
2. **F is not E-plus-something.** Its lanes and retest are extra entry
   *paths* that skip push quality, retracement and pullback volume, so F
   produces **more** trades than E (279 vs 38).

**Declared gap:** the V8.2 LATE JOIN path (Pine 1477–1545) is not implemented.
The repo's own benchmark measured it at **+1 fill in 330 ticker-days**
(`research/momentum-replication/reports/2026-08-pine-v8-benchmark.md`).

---

## 3. Look-ahead controls

| control | how |
|---|---|
| indicators | incremental only; no vectorised pass exists, so no place for bar *i+1* to enter |
| HOD | `max(high)` from session start **through the current bar** |
| RVOL-at-time | today's cumulative volume vs the same-session-minute average over **prior days only** |
| universe | open, previous close, trailing-20 dollar volume **excluding today** |
| scanner timestamp | frozen at 09:35 ET; every trade carries `scan_ts` |
| engine | one strict left-to-right pass, one Snapshot per bar |

Tested, not asserted (`tests/test_lookahead.py`, 33 tests):

```
✓ HOD at bar 20 is 5.25 while the eventual daily high is 9.99
✓ feeding bars 0..k reproduces the first k+1 values of a full pass exactly
✓ the engine's snapshot list never exceeds the bar it was handed
✓ TRUNCATION AUDIT — cut a session at 45/50/55/60 bars and re-run: every
  trade entered before the cut returns with identical entry, price and stop
✓ no entry precedes its own scan timestamp
```

**Still unreconstructable point-in-time, flagged not substituted:** float
(`float_provenance = "unavailable"` on every row), catalyst/news, true spread
(proxy: 25th percentile of recent 1-minute ranges), halt state. **Brief §17's
float cut and all of §18 cannot be produced.** No row is labelled "no
catalyst" — absence of a news feed is not absence of news.

---

## 4. The execution model, and the number that governs everything

**43.0% of variant A's fills are intrabar-ambiguous** — the entry minute
covered both the trigger and the stop, and 1-minute OHLC carries no sequence.
Prior measurements in this repo put it at 25% on 330 ticker-days
(`2026-08-pine-v8-benchmark.md`) and 26% on 250+ megadays
(`research/megaday-study/RESULTS.md`); on 838 fills over two years it is
higher still. This is a structural property of the pattern, not a quirk.

### The execution tax

| cost model | n | expectancy | slippage | commission | median stop | median entry slip |
|---|---:|---:|---:|---:|---:|---:|
| **gross** | 895 | **−0.419 R** | 0.000 R | 0.000 R | 1.99% of price | 0.000% |
| low | 897 | −1.096 R | 0.241 R | 0.193 R | 1.99% | 0.456% |
| **realistic** | 838 | **−1.853 R** | 0.606 R | 0.195 R | 1.96% | 1.088% |
| stressed | **35** | −2.173 R | 0.624 R | 0.124 R | 1.60% | 0.784% |

```
tax in R = (cost as % of price) / (stop as % of price)
         =        1.57%          /        1.96%        ≈ 0.80 R per trade
```

The stop is small because the strategy **caps** it: `maxStopPct = 3.0`
(Pine 406), a number that appears nowhere in the corpus and which
`research/megaday-study/RESULTS.md` §4 measured sitting on the population's
median stop. That study's prediction — widen the cap, cut the tax — replicates
here exactly (§11), and still never reaches zero.

A second tax nobody has written down: sizing uses the slippage-stressed risk
(Pine 1616–1621), `shares = budget / (risk + 2 × 10 ticks)`. On these stops
the $0.20 assumption exceeds the stop itself, so positions are sized to about
a third of the nominal risk budget and the fixed $1/order commission costs
**0.195 R per trade** instead of the ~0.07 R the budget implies.

**The stressed column is not a result, it is a refusal:** only **35 of 838**
entries fill, because modelled slippage breaches the entry limit offset. In a
poor-fill environment this strategy largely does not get executed.

**Exit mix (variant A, realistic):** 544 STOP · **157 STOP_GAP** · 100 T2 ·
32 STOP_AMBIGUOUS · 5 SESSION_FLAT. Nearly one in five exits gaps *through*
the stop and fills at the next open, which is where the missing halt feed
bites hardest — 4 trades carry `halt_flag`, and there is no halt archive to
check the rest against (see `data_acquisition.md` §5).

---

## 5. The ablation

```
Realistic costs · pessimistic ambiguity · Experiment 1 (identical exits for
every variant: stop, T1 at +1R on half, stop to break-even, runner at +2R,
flat at the window edge). 479 sessions, 2024-09-24 → 2026-08-21.
95% CI = day-clustered bootstrap, 5,000 draws, resampling SESSIONS.
```

| Variant | Added rule | Trades | Win % | Avg Win R | Avg Loss R | **Exp. R** | PF | Max DD (R) | 95% CI | Holdout Exp. | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| **A** | First pullback | 838 | 12.9% | +0.68 | −2.27 | **−1.853** | 0.06 | −1553 | [−1.95, −1.76] | −1.884 | **NEGATIVE EDGE** |
| **B** | + VWAP/EMA/MACD | 457 | 13.8% | — | — | **−1.710** | 0.08 | −782 | [−1.84, −1.58] | −1.828 | **NEGATIVE EDGE** |
| **C** | + Confluence | 102 | 19.6% | — | — | **−1.472** | 0.12 | −150 | [−1.72, −1.23] | −1.609 | **NEGATIVE EDGE** |
| **D** | + Pullback volume | 41 | 19.5% | — | — | −1.418 | 0.14 | −58 | [−1.80, −1.03] | — | insufficient sample |
| **E** | + HOD room | 38 | 18.4% | — | — | −1.427 | 0.12 | −54 | [−1.82, −1.03] | — | insufficient sample |
| **F** | Full strategy | 279 | 14.3% | — | — | **−1.704** | 0.08 | −475 | [−1.87, −1.54] | −1.838 | **NEGATIVE EDGE** |

**Every interval lies entirely below zero.** The best variant loses 1.4R per
trade. The profit factor never exceeds 0.14 — for every dollar made, seven to
sixteen are lost.

**Marginal effects.**

| step | trades removed | exp. before | exp. after | Δ exp. |
|---|---:|---:|---:|---:|
| B − A | 381 | −1.853 | −1.710 | **+0.143** |
| C − B | 355 | −1.710 | −1.472 | **+0.238** |
| D − C | 61 | −1.472 | −1.418 | +0.054 |
| E − D | 3 | −1.418 | −1.427 | −0.009 |
| F − E | **−241** (F *adds*) | −1.427 | −1.704 | −0.277 |

Each filter helps a little and costs sample. **None of them, stacked in any
order, gets within 1.4R of break-even.**

### 5b. Secondary ladder — the shipped strategy's own gate order

| Variant | Trades | Win % | Exp. R | 95% CI |
|---|---:|---:|---:|---|
| A | 838 | 12.9% | −1.853 | [−1.95, −1.76] |
| B | 457 | 13.8% | −1.710 | [−1.84, −1.58] |
| B + pullback volume | 212 | 16.5% | −1.576 | [−1.76, −1.39] |
| + HOD room | 183 | 15.8% | −1.607 | [−1.80, −1.41] |
| F | 279 | 14.3% | −1.704 | [−1.87, −1.54] |

### 5c. Gate pass rates over 20,248 observed candidates

```
impulse             100.0%   (definitional — it is the detector)
halt_band            99.6%   rejects almost nothing
hod_room             83.6%
pullback_structure   83.2%
retracement          77.9%   ← barely bites; see §11
risk_structural      64.4%
momentum             60.4%
pb_volume            37.1%
confluence           15.3%   ← by far the most binding
```

---

## 6. Rejected-trade analysis — did the filters remove the right trades?

Variant A's 838 trades split by each gate's verdict, both sides traded under
the identical exit model. **Research only.**

| gate | accepted n / exp. | rejected n / exp. | separation | winners removed | losers removed |
|---|---|---|---:|---:|---:|
| **confluence** | 84 / **−1.468** | 754 / −1.896 | **+0.428** | 91 | 650 |
| **momentum** | 417 / **−1.721** | 421 / −1.984 | **+0.263** | 53 | **364** |
| pb_volume | 396 / −1.805 | 442 / −1.896 | +0.091 | 45 | 389 |
| **hod_room** | 761 / −1.910 | 77 / **−1.297** | **−0.612** | 15 | 60 |
| halt_band | 836 / −1.856 | 2 / −0.897 | — | 0 | 2 |

**A correction to my own earlier reading.** On the 49-trade Yahoo sample,
confluence appeared to separate the *wrong* way (−0.441). At 838 trades it is
the **best** filter in the study (+0.428). The small-sample sign was noise,
and I reported it as a finding at the time. This is what the larger sample was
for.

**HOD room is the one filter that is actively harmful**, consistently: the
77 setups it rejects are the best sub-population anywhere in the study
(−1.297 R, 19.5% win). §11's parameter sweep agrees independently. This
contradicts `research/megaday-study/RESULTS.md` §2, which found the new-high
filter separating *favourably* on n=62 — that study measured MFE on megadays,
this one measures realised R on a general gapper population, and the
populations are not the same.

---

## 7. Filter redundancy (brief §21)

Phi between gate decisions over 20,248 candidates. Largest magnitude **0.31**.

| gate A | gate B | phi | agree % |
|---|---|---:|---:|
| momentum | hod_room | **−0.310** | 45.8% |
| momentum | retracement | +0.211 | 64.4% |
| momentum | risk_structural | −0.208 | 43.3% |
| hod_room | risk_structural | +0.204 | 66.9% |

**The filters are not redundant — two of them are opposed.** Requiring the
full momentum stack pushes selection *toward* setups with less room to the
high of day, because the stack only turns green once price is extended. The
brief's hypothesis (VWAP/EMA/MACD are all one thing) is not what the data
shows.

---

## 8. Cuts

**Time of day, variant A.** `useSessionWindow` defaults FALSE (Pine 314), so
orders arm 09:30–15:58.

| window | trades | win % | exp. R | avg MFE |
|---|---:|---:|---:|---:|
| 09:30–10:00 | 185 | 17.8% | **−1.573** | +0.84 |
| 10:00–10:30 | 48 | 14.6% | −1.828 | +0.96 |
| 10:30–11:30 | 118 | 8.5% | **−2.043** | +0.71 |
| 11:30–16:00 | **487** | 11.9% | −1.916 | +0.75 |
| pre-market | 0 | — | — | — |

**58% of trades are afternoon trades.** The corpus session is 09:35–10:30 with
a hard stop at 11:30 (`PARAMETERS.md` §2). Turning the window on would help —
and would still leave −1.573 R.

Zero pre-market trades despite pre-market volume now being present: the
volume gates (2× a 20-bar baseline, $100k/min) rarely pass on 04:00–09:30
tape, matching the ghost-layer finding in `2026-08-pine-v8-benchmark.md`.

**Stock characteristics, variant A** (n ≥ 30):

| cut | bucket | n | win % | exp. R |
|---|---|---:|---:|---:|
| price | **$2–5** | 422 | 10.4% | **−2.280** |
| price | $5–10 | 251 | 15.5% | −1.480 |
| price | **$10–20** | 142 | 15.5% | **−1.181** |
| gap | 10–20% | 43 | 9.3% | −2.333 |
| gap | 20–50% | 336 | 17.6% | −1.754 |
| gap | 50–100% | 289 | 9.0% | −1.941 |
| gap | >100% | 156 | 12.2% | −1.758 |
| pullback № | 1st | 425 | 12.2% | **−1.966** |
| pullback № | 2nd | 223 | 12.6% | −1.883 |
| pullback № | **3rd+** | 190 | 14.7% | **−1.566** |
| confluence | 0 supports | 754 | 12.1% | −1.896 |
| confluence | **1 support** | 83 | 20.5% | **−1.459** |
| RVOL-at-time | <2 / 2–5 / >5 | 179 / 61 / 426 | — | −1.79 / −1.93 / −1.85 |

Two things worth naming. **The cheapest tier is the worst** — $2–5 loses a
full R more per trade than $10–20, and it is half the sample. And **"first"
is the worst pullback of the three**, which is the setup the strategy is named
after.

**RVOL does not discriminate at all** at this sample size — the three buckets
are within 0.14 R of each other. On the 49-trade sample RVOL >5 looked like
the best feature in the study. It was noise.

**Market-regime cut: NOT PRODUCED.** Two years is not enough distinct regime
to cut on. The four-year daily-proxy version of that question is already
answered in `research/momentum-replication/reports/2026-08-regime-filter.md`:
negative in every year 2022–2026, and the regime is not forecastable at any
lookback.

---

## 9. Holdout and yearly consistency

```
CHRONOLOGICAL SPLIT of 373 traded sessions — never shuffled
  development 167 sessions   validation 94   holdout 112 (opened once)
```

| variant | dev | validation | **holdout** | holdout n |
|---|---:|---:|---:|---:|
| A | −1.899 | −1.728 | **−1.884** | 271 |
| B | −1.703 | −1.555 | **−1.828** | 152 |
| C | −1.352 | −1.443 | **−1.609** | 40 |
| F | −1.766 | −1.420 | **−1.838** | 87 |

**The holdout is 112 sessions and 271 trades for variant A, and it agrees with
development to within 0.02 R.** No parameter was selected on it — the config
was frozen and hashed before the run.

| variant | year | trades | win % | avg win R | avg loss R | exp. R | PF |
|---|---|---:|---:|---:|---:|---:|---:|
| A | 2024 | 116 | 9.5% | +0.62 | −2.46 | −2.143 | 0.04 |
| A | 2025 | 404 | 14.6% | +0.70 | −2.23 | −1.761 | 0.08 |
| A | 2026 | 318 | 11.9% | +0.66 | −2.26 | −1.865 | 0.06 |
| B | 2024/25/26 | 64/211/182 | — | — | — | −1.994 / −1.536 / −1.813 | — |
| F | 2024/25/26 | 44/130/105 | — | — | — | −1.911 / −1.520 / −1.846 | — |

**Negative in every year, for every variant.** There is no good year hiding a
bad one.

---

## 10. Baselines and placebos

Same qualifying ticker-days, same exit ladder, same realistic costs.

| baseline | n | win % | exp. R | PF | avg MFE | 95% CI |
|---|---:|---:|---:|---:|---:|---|
| **variant A as shipped** | 838 | 12.9% | **−1.853** | 0.06 | 0.78 | [−1.95, −1.76] |
| first pullback only | 420 | 12.4% | **−1.961** | 0.05 | 0.82 | [−2.09, −1.84] |
| second pullback only | 208 | 13.0% | −1.869 | 0.07 | 0.74 | [−2.05, −1.69] |
| third pullback and later | 166 | 13.3% | **−1.636** | 0.08 | 0.74 | [−1.82, −1.44] |
| trigger shifted **up** 5 ticks | 376 | 9.3% | −1.963 | 0.05 | 0.66 | [−2.10, −1.83] |
| trigger shifted **down** 5 ticks | 1,732 | 10.9% | −2.334 | 0.05 | 0.84 | [−2.43, −2.24] |
| **random entry, 09:35–11:30, 1-ATR stop** | **9,175** | **28.1%** | **−0.823** | **0.25** | **1.16** | **[−0.86, −0.79]** |

**A random entry minute beats the first pullback by more than a full R.** Not
marginally, not within noise: 9,175 random entries against 838 strategy
entries, non-overlapping intervals, and the random population wins on every
metric — win rate 28.1% vs 12.9%, profit factor 0.25 vs 0.06, average
favourable excursion 1.16 R vs 0.78 R.

The obvious defence — "the random baseline uses a wider stop, so it pays less
tax per R" — was checked on the smaller sample and **fails**: its 1-ATR stop
was a median 1.49% of price against the strategy's 1.73%. It pays *more* tax
per R and still wins.

**This is the study's central result.** The pattern does not merely fail to
add value over a random entry on the same qualifying tape — it destroys value
relative to one. Selecting *for* the first-pullback shape is selecting *for*
worse outcomes.

---

## 11. Parameter sensitivity

Run only after the frozen A–F experiment; each parameter perturbed around its
shipped value, everything else fixed.

**`max_stop_pct` — monotone, no plateau, no spike at the shipped value:**

| cap | A trades | A exp. R | F trades | F exp. R |
|---:|---:|---:|---:|---:|
| 1.5% | 267 | −2.317 | 103 | −2.091 |
| 2.0% | 549 | −2.026 | 184 | −1.959 |
| **3.0% (shipped)** | 838 | −1.853 | 279 | −1.704 |
| 4.5% | 1,018 | −1.719 | 358 | −1.637 |
| 6.0% | 1,069 | −1.676 | 369 | −1.586 |
| 9.0% | 1,076 | **−1.669** | 376 | **−1.568** |

`research/megaday-study/RESULTS.md` §4 predicted this direction before
measuring it, and it replicates on an independent two-year sample. **Widening
the cap reduces the execution tax monotonically and never crosses zero.**
Correcting the single most consequential unsourced parameter in the strategy
makes it less bad by 0.18 R and leaves it losing 1.67 R per trade.

**`min_room_r` (E and F's rule) — tightening it is monotonically worse:**
F at 0.0 R (gate off) −1.630 → 1.0 R shipped −1.704 → 2.0 R −1.772.
Independent confirmation of §6.

**`max_pb_volume_ratio` — looser is better:** F at 0.5 −1.749, shipped 0.7
−1.704, 0.9 −1.651.

**`max_retracement_pct` — inert.** Variant A: −1.852 at 30%, −1.853 at 50%,
−1.845 at 70%. The bound moves the trade count from 283 to 1,118 and moves
expectancy by 0.008 R. `research/megaday-study/RESULTS.md` §1 said the same
from the other direction: median dip depth 39%, p90 49%, *"la borne de
retracement à 50% ne filtre rien"*.

**`reward_multiple` — flat:** −1.849 to −1.856 across 1.5R–4R.

**`min_push_pct` — mildly monotone up:** 3% −1.933 → 8% −1.817.

No parameter shows the spike-at-the-shipped-number signature of curve fitting.
The parameters are not over-tuned; **there is simply no setting of any of them
that reaches positive expectancy.**

---

## 12. Overfitting audit

```
48 strategy parameters affecting universe, entry, stop, sizing or exit
   21 externally sourced · 2 empirically validated · 25 LOCAL HEURISTIC
      (13 flagged [UNTESTED local] or [UNCALIBRATED] by the Pine itself)
→ effective degrees of freedom ≈ 29.8   against 479 independent SESSIONS
```

At 20 sessions this ratio made every conclusion unsupportable. At **479
sessions it is roughly 16 sessions per free parameter**, which is enough to
carry the negative result — and a negative result is in any case the direction
overfitting does not manufacture. You do not accidentally fit your way to
losing 1.85 R per trade across three years and an untouched holdout.

---

## 13. Experiment 2 — F with its own management logic

| | n | win % | exp. R | exits |
|---|---:|---:|---:|---|
| Exp 1, common ladder | 279 | 14.3% | −1.704 | 201 STOP · 39 T2 · 28 STOP_GAP |
| **Exp 2, F's management** | 282 | **6.7%** | −1.581 | **150 BAILOUT** · 87 STOP · 18 T2 |

The breakout-or-bailout rule (out after 2 bars if MFE < 0.5 R) closes **150 of
282** trades and cuts the win rate in half. It slightly *improves* expectancy
(−1.581 vs −1.704) by cutting losses faster — it is a damage-control rule that
works as intended, on a system that should not be running.

---

## 14. Account simulation

$2,000 cash, 2% risk, $2,000 max position, $1/order, realistic costs,
compounding.

| variant | end equity | return | max DD | **ruined** |
|---|---:|---:|---:|:-:|
| A | **−$0.44** | **−100.0%** | −$2,014 | **YES** |
| B | $0.73 | −100.0% | −$2,013 | — |
| C | $229.52 | −88.5% | −$1,770 | — |
| F | **−$0.37** | **−100.0%** | −$2,000 | **YES** |

**Variants A and F destroy the account.** Longest losing streak in A: 39
trades. Worst single day: −20.2 R.

**Daily risk governor (§27): NOT RUN.** The shipped strategy has none — only
third-trade half-size and the 15:58 flat. The overlay is implemented and
switched off. Given the account outcome above it would change *how fast* the
account dies, not whether.

---

## 15. What this analysis still could not check

- **Halts.** 157 of 838 exits gap through the stop; 4 carry `halt_flag`.
  There is no halt archive (the free Nasdaq feed is forward-only —
  `data_acquisition.md` §5), so a LULD pause that reopened below the stop is
  booked at the stop price and **understates** the loss.
- **Intrabar sequence.** 43% of fills are structurally undecidable without
  tick data. All three policies are reported; the choice moves A between
  −0.419 R (gross, pessimistic) and +0.108 R (gross, exclude).
- **True spread.** A range-quartile proxy drives the slippage model, which
  drives the headline. Quotes are a paid endpoint.
- **Float and catalyst.** No point-in-time source. §17's float cut and all of
  §18 are absent, not empty.
- **Before 2024-09.** Two years, not the eight Alpaca could reach — the
  survivorship-free universe depends on Massive's grouped daily, which is
  capped at two years on the free tier.
- **The Pine itself.** `src/setups.py` is a Python port; TradingView is the
  only Pine compiler. State parity is asserted, not proven.
- **The LATE JOIN path**, declared and not implemented.

---

## 16. Answers to the twelve questions

| # | question | answer |
|---|---|---|
| 1 | Does the basic first pullback (A) have positive expectancy? | **No. −1.853 R, CI [−1.95, −1.76], n=838 over 353 sessions.** Negative gross of all costs (−0.419 R). **NEGATIVE EDGE.** |
| 2 | Does VWAP/EMA/MACD improve out-of-sample expectancy? | **Yes, and it does not matter.** +0.143 R on the ladder, +0.263 R accept-vs-reject, 364 losers removed against 53 winners. It moves −1.85 to −1.71. **KEEP — but it is rearranging deck chairs.** |
| 3 | Does confluence add measurable edge? | **It is the strongest filter in the study** (+0.428 R separation, +0.238 R on the ladder) — and it is **not in the shipped strategy** and passes only 15.3% of candidates. **KEEP if the strategy were viable; it is not.** *This reverses my earlier small-sample reading.* |
| 4 | Does low pullback volume add measurable edge? | **Barely.** +0.091 R separation; loosening the threshold improves F monotonically. **UNCERTAIN, lean REMOVE.** |
| 5 | Does requiring room to HOD add measurable edge? | **No — it is harmful.** −0.612 R separation, and tightening it is monotonically worse in the sweep. **REMOVE.** |
| 6 | Does F beat the simpler variants after realistic costs? | **No.** F −1.704 vs C −1.472. F's own management (Exp 2) is −1.581 with a 6.7% win rate. |
| 7 | Which filter removes the most **winning** trades? | **Confluence** — 91 of A's winners (it removes 90% of everything). |
| 8 | Which filter removes the most **losing** trades? | **Confluence** (650). Per unit of damage, **momentum**: 364 losers against 53 winners. |
| 9 | Largest statistically credible improvement? | **Confluence**, +0.428 R with non-overlapping-ish intervals at n=84/754. Credible, and insufficient. |
| 10 | Does it survive stressed slippage? | **The question does not arise: 35 of 838 entries fill.** In a poor-fill environment the strategy is not executable. |
| 11 | Does it survive the untouched holdout? | **It survives it consistently — as a loss.** A: −1.884 R on 271 trades over 112 sessions, within 0.02 R of development. |
| 12 | Genuine edge, or overfitting/noise? | **Neither. It is a genuine negative.** Every CI below zero, every year, the holdout, and a random entry on the same tape beats it by more than 1 R. |

---

## Verdict

**NO EDGE. The First Pullback, as specified in `ross-fp-v4.pine` V9.12, has
negative expectancy on 838 trades across 479 sessions, 945 names and three
calendar years — before costs as well as after.**

Four findings, in descending order of how much they should change what you do:

1. **A random entry minute on the same qualifying tape beats every variant by
   over a full R**, on 9,175 trades, with a *tighter* stop. The pattern is not
   neutral; selecting for it selects for worse outcomes than not selecting at
   all. No filter in the ladder recovers that gap — the best of them closes
   0.4 R of a 1.0 R deficit.

2. **The strategy loses money gross of all costs** (−0.419 R). Execution
   costs then add another 0.8 R of tax, driven by a stop cap that is unsourced
   and sits on the population's median stop. Widening it helps monotonically
   and never reaches zero. **The costs are not the problem; they are the
   amplifier.**

3. **Three of the five filters are worth what they cost, and it changes
   nothing.** Confluence (+0.428) and momentum (+0.263) genuinely separate.
   HOD room actively harms (−0.612). Pullback volume is noise. Stacking the
   good ones gets to −1.47 R.

4. **The account dies.** $2,000 → $0 for variants A and F, 39-trade losing
   streaks, −20 R days.

Two of my own earlier readings were wrong and are corrected above: on 49
trades confluence looked harmful (it is the best filter) and RVOL >5 looked
like the strongest feature (it does not discriminate at all). Both were
small-sample noise reported as findings. That is precisely why the sample was
worth getting.

This lands where every other measurement in this repository has landed:
8,828 symbol-days over 894 sessions with no edge in any year
(`2026-08-regime-filter.md`), an accurate Pine port at −7.66 R and −10.55 R on
330 ticker-days (`2026-08-pine-v8-benchmark.md`), and a 250-megaday study
whose verdict is *"moteur de rejet, pas de génération de signal"*
(`research/megaday-study/RESULTS.md`). Four independent methods, one answer.

**What would be worth testing next is not another filter on this entry.** The
entry is the problem. If anything here is worth pursuing it is the observation
that the *random* population reaches +1 R far more often (28.1% win rate,
1.16 R average MFE) than the pattern-selected one — which says the qualifying
*universe* may hold something the *pattern* is actively selecting away from.

---

```
NO TICKET ISSUED. Paper only. This study did not validate executable
bid/ask, borrow, halt state, float, catalyst, or the Pine's compiled
behaviour. Reproducible from results/run_manifest.json.
```
