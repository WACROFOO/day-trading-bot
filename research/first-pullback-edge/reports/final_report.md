# First Pullback — does it have an edge?

An adversarial ablation of `knowledge-base/tradingview/ross-fp-v4.pine`
(REV `V9.12`), run against the brief's 38 requirements.

```
FEED · Yahoo chart v8, unauthenticated · 1-minute · pre/post requested
       MEASURED 2026-08-24 from this container (results/data_quality.json)
! 1-MINUTE HISTORY REACHES 25 DAYS. 30 days back returns HTTP 422.
! PRE-MARKET VOLUME IS ZERO FOR EVERY SYMBOL, AAPL AND SPY INCLUDED.
! 6 OF 9 DELISTED TICKERS PROBED RETURN 404 — the universe is
  survivorship-biased and it cannot be repaired from this feed.
→ The brief asks for 1,000-3,000 ticker-days across multiple years.
  The intraday ablation below runs on 20 SESSIONS and 49 TRADES at its
  widest rung. Read every number in this document as a pipeline
  demonstration, not as an expectancy estimate.

CODE · git 1033875 · config sha256 d224b4e5… · seed 20260824 · py 3.11.15
       33 tests pass (tests/), all of them about look-ahead and fill order
```

Read `data_quality.md` first. It is the constraint that shapes everything here.

---

## 1. What was considered — the funnel

| stage | count | source |
|---|---:|---|
| symbol pool (current Nasdaq/NYSE/AMEX listings) | **6,742** | `data/symbol_pool.json` |
| **candidate ticker-days 2022-09-01 → 2026-08-21** | **8,152** | `data/candidate_days.parquet` |
| … over sessions / distinct names | 976 / 2,295 | same |
| … falling inside the obtainable 1-minute window | **349** | `2026-07-28 → 2026-08-21` |
| … passing the 09:35 ET point-in-time scanner | **218** | `data/scanned_ticker_days.parquet` |
| pullback candidates observed by the detector (variant A) | **670** | on 20 sessions, 119 names |
| … passing variant A's gates | 254 | `data/rejected_setups.parquet` |
| … filled (realistic costs, pessimistic ambiguity) | **49** | `data/trades.parquet` |

The daily layer **meets** the brief's sample target: 8,152 ticker-days is
above the 1,000–3,000 band, across four calendar years and two obvious
regimes. The intraday layer, which is where A–F actually live, does not and
cannot.

| year | ticker-days | sessions | names |
|---|---:|---:|---:|
| 2022 (from 09-01) | 263 | 74 | 222 |
| 2023 | 1,085 | 240 | 657 |
| 2024 | 1,933 | 252 | 937 |
| 2025 | 2,801 | 250 | 1,311 |
| 2026 (to 08-21) | 2,070 | 160 | 1,059 |

Scanner rules, stated as the brief demands and kept **separate from entry
filters**: open price $2–20, gap ≥ 10% vs the previous close, trailing
20-session dollar volume ≥ $250k, split-artefact days excluded. The intraday
layer re-qualifies at 09:35 ET on bars printed up to that minute only.
`scanGates` is `false` in the shipped Pine (line 330), so none of these is
ever used as a trade gate here either.

---

## 2. What distinguishes A from F

| rule | A | B | C | D | E | F | Pine line |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| qualifying impulse (≥5% **and** ≥2 ATR **and** eff ≥0.60 **and** RVOL ≥2 **and** ≥$100k/min) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 878–930, 1645 |
| first pullback, 1–4 bars, ≥1 red | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1646 |
| retracement ≤ 50% of the push | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1647 |
| structural stop + caps (≤3% of price, ≤1.5 ATR, ATR fallback, shares ≥1) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1598–1656 |
| trigger = pullback-bar high + 1 tick · stop = pullback low − 1 tick | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1587–1589 |
| close > VWAP **and** close > EMA9 **and** EMA9 ≥ EMA20 **and** MACD > 0 **and** hist > 0 | — | ✓ | ✓ | ✓ | ✓ | ✓ | 1580–1583, 1649 |
| confluence: ≥1 support (EMA9 / EMA20 / VWAP / half-dollar, EMAs clustered count once) | — | — | ✓ | ✓ | ✓ | **—** | 1577–1585 |
| pullback volume ≤ 0.70 × push volume | — | — | — | ✓ | ✓ | ✓ | 1648 |
| HOD room: trigger ≥ HOD-at-time, or ≥1R of headroom | — | — | — | — | ✓ | ✓ | 1860 |
| halt-band veto (LULD tier, fail-closed inside RTH) | — | — | — | — | — | ✓ | 1642, 1652 |
| fast lane / uptrend lane / HOD break-and-retest | — | — | — | — | — | ✓ | 1836–1940, 1315–1362 |
| third-trade half size | — | — | — | — | — | ✓ | 1759 |

**Two ways the requested ladder is not monotone, both reported rather than
smoothed:**

1. **C is not a rung of the shipped strategy.** `supportCount` exists in the
   Pine but feeds only the display-only quality score (line 1701). There is
   no confluence gate. C therefore tests a filter the operator does not run —
   and it passes only **14.2%** of candidates, which collapses D and E to
   n=1. A secondary ladder without it is reported in §5b.
2. **F is not E-plus-something.** Its lanes and the HOD retest are extra
   entry *paths* that skip push quality, retracement and pullback volume, so
   F can produce **more** trades than E. It did: 20 vs 1.

**Not implemented, and therefore not measured in F:** the V8.2 LATE JOIN path
(Pine 1477–1545). Justification is a measurement, not convenience — the
repo's own benchmark found it added **+1 fill in 330 ticker-days**
(`research/momentum-replication/reports/2026-08-pine-v8-benchmark.md`, V8.2
addendum). It is the one declared gap between F and the shipped script.

---

## 3. Look-ahead controls

| control | how |
|---|---|
| indicators | incremental only. No vectorised pass over a day exists in `src/indicators.py`, so there is no place for bar *i+1* to enter |
| HOD | `max(high)` from session start **through the current bar**. Never the eventual daily high |
| RVOL-at-time | today's cumulative volume vs the same-session-minute average over **prior days only** |
| gap | today's open (or the 09:35 last price) vs the **previous** close |
| universe | daily layer reads open, previous close and trailing-20 dollar volume **excluding today**. Today's high, close, volume and range are never read |
| scanner timestamp | frozen at 09:35 ET; every trade carries `scan_ts` and an entry can never precede it |
| engine | one strict left-to-right pass, one Snapshot per bar |

Tested, not asserted (`tests/test_lookahead.py`):

```
✓ HOD at bar 20 is 5.25 while the eventual daily high is 9.99
✓ feeding bars 0..k reproduces the first k+1 values of a full-day pass exactly
✓ the engine's snapshot list never exceeds the bar it was handed
✓ TRUNCATION AUDIT — cut the session at 45/50/55/60 bars, re-run: every
  trade entered before the cut returns with identical entry, price and stop
✓ every recorded setup's hod_at_time equals max(high) over bars 0..i
✓ no entry precedes its own scan timestamp
```

**Fields that could not be reconstructed point-in-time, flagged rather than
substituted:** float (`float_provenance = "unavailable"` on every row),
catalyst/news (no timestamped feed), true spread (proxy: 25th percentile of
recent 1-minute ranges), halt state (missing minutes flagged, not resolved).
**Brief §17's float cut and §18's catalyst analysis cannot be produced.** No
row is labelled "no catalyst" — absence of a news feed is not absence of news.

---

## 4. Execution model, and the one number that governs everything

```
COSTS · commission $1/order (matches Pine line 6, cash_per_order)
        slippage = slip_ticks + spread_mult x (spread_est / 2)
                              + atr_mult x ATR x participation
        participation cap 2% of the printed minute
        gross / low / realistic / stressed, all four reported
AMBIGUITY · a bar covering trigger AND stop carries no sequence information.
        Flagged, then resolved under an explicit policy. All three reported.
```

**Ambiguous entry bars: 30.6% of variant A's fills.** Two independent prior
measurements in this repo put it at 25% (`2026-08-pine-v8-benchmark.md`, 330
ticker-days) and 26% (`research/megaday-study/RESULTS.md`, 250+ megadays).
Three measurements, same number. This is a structural property of 1-minute
OHLC on this universe, not a quirk of one sample.

### The execution tax — the finding that dominates every table below

| cost model | n | expectancy | slippage | commission | median stop | median entry slip |
|---|---:|---:|---:|---:|---:|---:|
| gross | 51 | **−0.274 R** | 0.000 R | 0.000 R | 1.74% of price | 0.000% |
| low | 51 | −1.027 R | 0.284 R | 0.220 R | 1.74% | 0.447% |
| **realistic** | 49 | **−1.775 R** | 0.701 R | 0.224 R | 1.73% | 1.034% |
| stressed | **4** | −0.517 R | 0.650 R | 0.139 R | 1.71% | 0.817% |

Read the identity, which is `research/megaday-study/RESULTS.md` §4 reproduced
on a different sample:

```
tax in R = (spread + slippage, as % of price) / (stop, as % of price)
         =            1.356%                  /        1.73%        = 0.79 R per trade
```

The stop is small **because the strategy caps it**: `maxStopPct = 3.0`
(Pine 406), a value that appears nowhere in the corpus. The sibling study
measured the population's median stop at **3.02%** — the cap is sitting on
the median, removing 51% of setups and locking every backtest into the regime
where the execution tax per R is highest. This study did not set out to
confirm that and confirms it anyway.

**A second, smaller tax nobody has written down.** Sizing uses the
slippage-stressed risk (Pine 1616–1621): `shares = budget / (risk + 2 × 10
ticks)`. On these stops the $0.20 assumption is larger than the stop itself,
so the position is sized to roughly **a third of the nominal risk budget** —
and the fixed $1/order commission then costs **0.224 R per trade** instead of
the ~0.07 R the $40 budget implies. The V8 header discloses a 10–15% drag;
measured here it is 22%.

**The stressed column is not a good result.** Its `−0.517 R` comes from
**4 fills**: under stressed slippage the modelled cost breaches the entry
limit offset and ~90% of entries are simply **MISSED**. That is the honest
reading — *in a poor-fill environment this strategy largely does not get
filled*, which is information, not performance.

---

## 5. The ablation

```
Realistic costs · pessimistic ambiguity · Experiment 1 (identical exits for
every variant: stop, T1 at +1R on half, stop to break-even, runner at +2R,
flat at the window edge). 20 sessions, 2026-07-28 → 2026-08-21.
95% CI = day-clustered bootstrap, 5,000 draws, resampling SESSIONS.
```

| Variant | Added rule | Trades | Win % | Avg Win R | Avg Loss R | **Exp. R** | PF | Max DD (R) | 95% CI | Holdout Exp. | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| **A** | First pullback | 49 | 16.3% | +0.77 | −2.27 | **−1.775** | 0.12 | −86.97 | [−2.24, −1.32] | −1.37 | INSUFFICIENT SAMPLE |
| **B** | + VWAP/EMA/MACD | 26 | 26.9% | — | — | **−1.351** | 0.20 | −35.25 | [−2.05, −0.74] | −1.01 | INSUFFICIENT SAMPLE |
| **C** | + Confluence | 3 | 0.0% | — | — | **−1.828** | 0.00 | −5.48 | [−2.02, −1.71] | −2.02 | INSUFFICIENT SAMPLE |
| **D** | + Pullback volume | 1 | 0.0% | — | — | **−1.744** | 0.00 | −1.74 | degenerate | — | INSUFFICIENT SAMPLE |
| **E** | + HOD room | 1 | 0.0% | — | — | **−1.744** | 0.00 | −1.74 | degenerate | — | INSUFFICIENT SAMPLE |
| **F** | Full strategy | 20 | 20.0% | — | — | **−1.585** | 0.10 | −31.71 | [−2.40, −0.88] | −1.26 | INSUFFICIENT SAMPLE |

Every confidence interval lies **entirely below zero**. That is not evidence
of a negative edge at the level the brief would accept — the sample is far
too small and the cost model is uncalibrated — but nothing in this table
points upward.

**Marginal effects.**

| step | trades removed | exp. before | exp. after | Δ exp. | DD improved? | CI narrower? |
|---|---:|---:|---:|---:|:-:|:-:|
| B − A | 23 | −1.775 | −1.351 | **+0.424** | yes (−87 → −35) | no (0.92 → 1.31) |
| C − B | 23 | −1.351 | −1.828 | **−0.477** | yes, by deletion | degenerate |
| D − C | 2 | −1.828 | −1.744 | +0.083 | degenerate | degenerate |
| E − D | 0 | −1.744 | −1.744 | 0.000 | — | — |
| F − E | **−19** (F *adds* trades) | −1.744 | −1.585 | +0.159 | worse (−1.7 → −31.7) | — |

### 5b. Secondary ladder — the shipped strategy's own gate order

C, D and E are degenerate because of a gate the operator does not run. Repeat
the ablation without it:

| Variant | Trades | Win % | Exp. R | 95% CI |
|---|---:|---:|---:|---|
| A | 49 | 16.3% | −1.775 | [−2.24, −1.32] |
| B | 26 | 26.9% | **−1.351** | [−2.05, −0.74] |
| B + pullback volume | 17 | 17.6% | −1.722 | [−2.39, −1.09] |
| + HOD room | 17 | 11.8% | −1.819 | [−2.49, −1.20] |
| F (adds lanes, retest, halt band, half-size) | 20 | 20.0% | −1.585 | [−2.40, −0.88] |

Same shape: the momentum stack is the only rung that moves expectancy up, and
everything after it moves it back down while shrinking the sample.

### 5c. What the gates actually do — pass rates over 670 observed candidates

```
✓ impulse              100.0%   (definitional — it is the detector)
✓ halt_band            100.0%   REJECTED NOTHING in 670 candidates
  pullback_structure    76.0%
  retracement           74.9%   ← the 50% bound barely bites; see §11
  risk_structural       72.5%
  hod_room              85.2%
  momentum              54.5%   ← the binding one
  pb_volume             45.4%
✗ confluence            14.2%   ← collapses the sample by itself
```

---

## 6. Rejected-trade analysis — did the filters remove the right trades?

Variant A's 49 trades, split by each gate's verdict, both sides traded under
the identical exit model. **Research only.**

| gate | accepted n / exp. | rejected n / exp. | separation | winners removed | losers removed |
|---|---|---|---:|---:|---:|
| **momentum** | 23 / **−1.398** | 26 / **−2.108** | **+0.710** | 2 | **24** |
| confluence | 4 / −2.180 | 45 / −1.739 | **−0.441** | 8 | 37 |
| pb_volume | 36 / −2.007 | 13 / −1.133 | **−0.874** | 3 | 10 |
| hod_room | 44 / −1.963 | 5 / −0.116 | **−1.847** | 3 | 2 |
| halt_band | 49 / −1.775 | 0 / — | — | 0 | 0 |

Reading, with the sample sizes attached:

- **momentum is the only filter whose accepted population beats its rejected
  population.** It removed 24 losers against 2 winners. The CIs still overlap
  ([−2.05, −0.71] vs [−2.63, −1.66]).
- **confluence, pullback volume and HOD room all separate the wrong way** on
  this sample, and §11's parameter sweep independently agrees for the last
  two: loosening either threshold improves expectancy monotonically. HOD room's rejected trades are the best sub-population in the
  whole study (−0.12 R, 60% win) — but n=5, and this **contradicts** the
  sibling megaday finding that the new-high filter separates *favourably*
  (median MFE 2.04 R vs 1.35 R, n=62, `research/megaday-study/RESULTS.md` §2).
  Two studies, opposite signs, both under-powered. **UNCERTAIN.**
- **halt_band vetoed nothing in 670 candidates.** Its purpose is to refuse a
  stop wider than the LULD band; after the 3% cap and the ATR fallback, no
  stop is ever that wide. It is inert in this configuration.

---

## 7. Filter redundancy (brief §21)

Phi coefficients between gate decisions, 670 candidates. The largest
magnitude anywhere is **0.33**.

| gate A | gate B | phi | agree % |
|---|---|---:|---:|
| momentum | risk_structural | **−0.327** | 37.5% |
| momentum | hod_room | **−0.313** | 42.1% |
| hod_room | risk_structural | +0.262 | 74.2% |
| momentum | pb_volume | −0.196 | 39.9% |

**The filters are not redundant — but two of them are actively opposed.**
Requiring the full momentum stack pushes selection *toward* setups with wider
stops and *less* room to the high of day, because the stack only turns green
once price is extended. The brief's hypothesis (VWAP, EMA and MACD all just
measure short-term momentum, so one would do) is not what the data shows;
what it shows is that momentum and room-to-HOD are fighting each other.

---

## 8. Cuts (brief §§16–17)

**Time of day, variant A.** The shipped default is `useSessionWindow = false`
(Pine 314), so orders are armed 09:30–15:58.

| window | trades | win % | exp. R | avg MFE |
|---|---:|---:|---:|---:|
| 09:30–10:00 | 9 | 33.3% | **−0.715** | +1.20 |
| 10:00–10:30 | 3 | 33.3% | −1.277 | +0.97 |
| 10:30–11:30 | 10 | 20.0% | −1.335 | +1.02 |
| **11:30–16:00** | **27** | **7.4%** | **−2.346** | +0.82 |
| pre-market | 0 | — | — | — |

**More than half of variant A's trades are afternoon trades, and they are the
worst population in the study.** The corpus session is 09:35–10:30 with a
hard stop at 11:30 (`PARAMETERS.md` §2). The same conclusion was reached from
the other direction by the repo's ghost-layer measurement: 31 afternoon
signals over 11 days summed to **−9.47 R** hypothetical
(`2026-08-pine-v8-benchmark.md`, V8.1 rerun). **Turning the session window on
is the single largest lever visible in this study, and it is a default, not a
discovery.**

Zero pre-market trades is a data fact, not a strategy fact: pre-market volume
is zero on this feed, so the volume gates can never pass before 09:30.

**Stock characteristics, variant A** (buckets with n≥5 only):

| cut | bucket | n | win % | exp. R | reaches +1R |
|---|---|---:|---:|---:|---:|
| price | $2–5 | 24 | 8.3% | **−2.340** | 29% |
| price | $5–10 | 14 | 28.6% | −1.158 | 57% |
| price | $10–20 | 10 | 20.0% | −1.167 | 40% |
| gap | 10–20% | 6 | 16.7% | −1.112 | 50% |
| gap | 20–50% | 18 | 16.7% | −1.631 | 39% |
| gap | 50–100% | 13 | 30.8% | −1.421 | 46% |
| gap | **>100%** | 9 | **0.0%** | **−2.764** | 33% |
| RVOL-at-time | <2 | 8 | 0.0% | −2.059 | 25% |
| RVOL-at-time | **>5** | 14 | **50.0%** | **−0.885** | 57% |
| pullback depth | <20% | 9 | 11.1% | −1.331 | 44% |
| pullback depth | 35–50% | 22 | 18.2% | −2.012 | 41% |
| pullback number | 1st | 35 | 17.1% | −2.032 | 34% |
| pullback number | 2nd | 12 | 8.3% | −1.356 | 42% |

The cheapest tier and the biggest gaps are the worst; genuine relative volume
is the best single discriminator in the table. **Float and catalyst cuts are
absent — the data does not exist. See §3.**

**Market-regime cut (strong/weak momentum environment, high/low volatility):
NOT PRODUCED.** Twenty consecutive sessions in one month contain no regime
variation to cut on. The four-year regime question is already answered
elsewhere on 8,828 symbol-days: buy-the-open on gappers is negative in every
year 2022–2026 and the regime is not forecastable at any lookback from 5 to
60 sessions (`research/momentum-replication/reports/2026-08-regime-filter.md`).

---

## 9. Holdout and yearly consistency

```
CHRONOLOGICAL SPLIT of 19 traded sessions — never shuffled
  development 8 sessions  2026-07-27 → 2026-08-06
  validation  5 sessions  2026-08-07 → 2026-08-13
  holdout     6 sessions  2026-08-14 → 2026-08-21   (opened once)
```

| variant | dev | validation | **holdout** | holdout n |
|---|---:|---:|---:|---:|
| A | −2.095 | −1.669 | **−1.370** | 14 |
| B | −1.936 | −0.863 | **−1.010** | 6 |
| F | −2.586 | −0.804 | **−1.262** | 3 |

**A six-session holdout is not a holdout.** No parameter was selected on it —
the config was frozen and hashed before the run — but three trades cannot
confirm or refute anything, and the "improvement" from development to holdout
is a two-week drift in one direction, not evidence of stability.

**Yearly consistency and walk-forward: NOT PRODUCED.** One month of intraday
data contains no years to compare and `walk_forward_folds()` correctly returns
`[]` rather than manufacturing folds. `results/yearly.csv` exists and holds a
single row per variant, all of it 2026.

---

## 10. Baselines and placebos (brief §§24–25)

Same qualifying ticker-days, same exit ladder, same realistic costs.

| baseline | n | win % | exp. R | 95% CI |
|---|---:|---:|---:|---|
| **variant A as shipped** | 49 | 16.3% | **−1.775** | [−2.24, −1.32] |
| first pullback only (`pullback_number == 1`) | 35 | 17.1% | −2.032 | [−2.55, −1.55] |
| second pullback only | 10 | 10.0% | −1.311 | [−1.96, −0.46] |
| third pullback and later | 2 | 0.0% | −1.943 | [−3.38, −0.50] |
| trigger shifted **up** 5 ticks | 16 | 25.0% | **−1.161** | [−1.81, −0.63] |
| trigger shifted **down** 5 ticks | 113 | 8.8% | −2.597 | [−2.92, −2.33] |
| **random entry, 09:35–11:30, 1-ATR stop** | **1,090** | 24.9% | **−0.993** | **[−1.13, −0.87]** |

Two results here are uncomfortable and are reported because they are:

1. **A random entry minute beats the first pullback on this tape.** −0.99 R
   against −1.78 R, with a 22× larger sample. The obvious defence — "the
   random baseline uses a wider stop, so it pays less tax per R" — was
   checked and **fails**: the random baseline's 1-ATR stop is a median
   **1.49%** of price against the strategy's **1.73%**. It pays *more* tax per
   R, not less, and still wins.
2. **Restricting to the *first* pullback is worse than not restricting**
   (−2.03 vs −1.78), and the *second* pullback is the best of the three. The
   sibling megaday study found the same non-separation from the other side —
   "par numéro de dip : le 1er et le 2e se valent"
   (`research/megaday-study/RESULTS.md` §5bis).

An arbitrary +5-tick shift of the trigger also outperforms the trigger the
strategy actually uses. A rule whose exact level can be moved five cents in a
direction chosen at random and improve is not a level the market respects on
this sample.

---

## 11. Parameter sensitivity (brief §23)

Run only after the frozen A–F experiment. Each parameter perturbed around its
shipped value, everything else fixed. Variant A, realistic costs.

**`max_stop_pct` — monotone, no plateau, no spike at the shipped value:**

| cap | trades | exp. R | 95% CI |
|---:|---:|---:|---|
| 1.5% | 26 | −2.157 | [−2.79, −1.49] |
| 2.0% | 39 | −1.952 | [−2.54, −1.48] |
| **3.0% (shipped)** | 49 | −1.775 | [−2.24, −1.32] |
| 4.5% | 56 | −1.757 | [−2.17, −1.36] |
| 6.0% | 59 | **−1.672** | [−2.07, −1.29] |
| 9.0% | 59 | −1.672 | [−2.07, −1.29] |

The direction predicted by `research/megaday-study/RESULTS.md` §4 replicates
exactly — widening the cap reduces the execution tax and improves expectancy
monotonically, flattening above ~6% where the ATR fallback takes over. **It
never crosses zero.** Correcting the unsourced parameter makes the strategy
less bad, not profitable. That is the same conclusion the sibling study
reached: *"Le corriger ne produit pas un edge — il révèle la loterie qui
était dessous."*

**`min_push_pct` — monotone the other way:** 3% → −1.908 (n=71), 5% shipped →
−1.775 (n=49), 8% → −1.409 (n=17). A stronger impulse requirement helps and
keeps helping; the shipped value is not a local optimum, which is evidence
*against* it having been fitted.

**`max_retracement_pct`:** A: 30% → −1.533 (n=21), 50% shipped → −1.775
(n=49), 70% → −1.796 (n=69). On F the gradient is steeper: 30% → −1.045
(n=9), 70% → −1.781 (n=29). The shipped 50% bound sits mid-range and barely
bites — 74.9% of candidates pass it. This is
`research/megaday-study/RESULTS.md` §1 again: median dip depth 39%, p90 49%,
*"la borne de retracement à 50% ne filtre rien"*.

**`min_room_r` (variant E and F's rule) — tightening it makes things worse,
monotonically.** On variant A the parameter is inert because A does not carry
the gate; on F:

| required room | trades | exp. R | 95% CI |
|---:|---:|---:|---|
| 0.0 R (gate off) | 23 | **−1.361** | [−2.24, −0.63] |
| 0.5 R | 23 | −1.491 | [−2.34, −0.75] |
| **1.0 R (shipped)** | 20 | −1.585 | [−2.40, −0.88] |
| 1.5 R | 19 | −1.728 | [−2.43, −1.11] |
| 2.0 R | 19 | −1.728 | [−2.43, −1.11] |

Independent corroboration of §6: the HOD-room gate rejects the better trades
on this sample. It still contradicts the megaday study's n=62 result, so the
verdict stays **UNCERTAIN**, but now two different tests inside this study
point the same way.

**`max_pb_volume_ratio` (variant D and F's rule) — looser is better:** on F,
0.5 → −1.863 (n=15), **0.7 shipped → −1.585** (n=20), 0.8 → −1.451 (n=22),
0.9 → −1.524 (n=23). Same direction as its accept/reject split.

**`reward_multiple` — flat.** A: −1.771 / −1.775 / −1.786 / −1.803 / −1.762
across 1.5R–4R. F: −1.597 → −1.533, mildly better at higher targets. The 2R
profit target is not a fitted optimum, which is the good news in this table.

**`max_stop_pct` on F is NOT monotone** (best at 2.0%, −1.502) where on A it
is. With 10–25 trades per cell that difference is noise, and it is recorded
rather than interpreted.

**`max_pullback_bars`, `min_efficiency`, `fallback_atr_mult`:** flat-to-noisy
neighbourhoods, no spike at the shipped value.

No parameter shows the spike-at-the-shipped-number signature of curve
fitting. The problem is not that the parameters are over-tuned; it is that
none of them reaches positive expectancy anywhere in its neighbourhood.

---

## 12. Overfitting audit (brief §22)

```
48 strategy parameters affecting universe, entry, stop, sizing or exit
   21  externally sourced rule      (traceable to the corpus)
    2  empirically validated        (the $2,000 account basis)
   25  LOCAL HEURISTIC              (13 flagged [UNTESTED local] by the Pine itself)
    5  study parameters             (costs, ambiguity policy, limit offset)
→ effective degrees of freedom ≈ 29.8   (results/degrees_of_freedom.json)
```

Against **20 independent sessions**. Trades inside one session are not
independent observations of a parameter choice, so the comparison that matters
is 29.8 knobs against 20 sessions — roughly one and a half free parameters per
independent observation. **No out-of-sample conclusion of any kind is
supportable at that ratio**, in either direction.

Parameters most likely to have been introduced after looking at individual
trades, flagged on their own evidence:

| parameter | value | why flagged |
|---|---|---|
| `max_stop_pct` | 3.0 | nowhere in the corpus; sits on the measured population median (3.02%) |
| `max_pullback_bars` | 4 | the Pine's own comment reads `[local, was 3]` — a value that moved |
| `min_efficiency` | 0.60 | `[UNTESTED local]` |
| `min_dollar_volume` | 100,000 | `[UNTESTED local]` |
| `minimum_mfe_r` | 0.5 | `[UNTESTED local]`, and the bailout it drives closed 14 of F's 20 trades |
| `scanMinRVOL` | 2.0 | `[UNCALIBRATED]` in the Pine's own label |

---

## 13. Experiment 2 — F with its own management logic

Identical entries, F's own exits (breakout-or-bailout: out after 2 bars if
MFE < 0.5 R, or on a close below entry inside 2 bars).

| | n | win % | exp. R | exits |
|---|---:|---:|---:|---|
| Exp 1, common ladder | 20 | 20.0% | −1.585 | 12 STOP · 5 T2 · 3 STOP_GAP |
| **Exp 2, F's management** | 20 | **0.0%** | **−1.885** | **14 BAILOUT** · 3 STOP_GAP · 3 STOP |

The bailout closed 14 of 20 trades and **took every winner with it** — the
five trades that reached +2 R under the common ladder were bailed out before
they got there. On 20 trades this is an observation, not a verdict, but the
mechanism is legible: a 2-bar / 0.5 R patience threshold on a 1-minute chart
of a stock whose median favourable excursion is +0.94 R will exit most
positions during normal noise.

---

## 14. Account simulation (brief §26)

$2,000 cash account, 2% risk, $2,000 max position, $1/order, realistic costs,
compounding.

| variant | end equity | return | max DD | trades |
|---|---:|---:|---:|---:|
| A | $1,173 | **−41.3%** | −$835 (−41.6%) | 49 |
| B | $1,600 | −20.0% | −$408 | 26 |
| F | $1,628 | −18.6% | −$382 | 20 |

R performance and dollar performance are separate facts and are kept
separate. Neither is an estimate of anything at n=49 over 20 sessions.

**Daily risk governor (brief §27): NOT RUN.** The shipped strategy has no
governor — only the third-trade half-size rule and the 15:58 flat. The
overlay is implemented (`_governor_stop` in `src/backtest.py`, configured in
`config/strategy.yaml`) and switched off, because a with/without comparison
on 20 sessions where the median session carries 2–3 trades cannot separate
"the governor helped" from "the governor deleted trades". It runs the moment
the sample supports it.

---

## 15. What this analysis could not check

- **Anything before 2026-07-28 intraday.** The feed stops at 25 days. This is
  the whole limitation; everything else is downstream of it.
- **The pre-market session**, which is where the source says the move often
  is — 07:00 named 78 times against 36 for 09:30 across his July recaps
  (`research/momentum-replication/reports/2026-07-challenge.md`). Zero
  pre-market volume on this feed makes it unmodellable.
- **Delisted names.** 6 of 9 probed return 404. Direction of the resulting
  bias is unquantified.
- **Intrabar sequence.** 30.6% of fills are structurally undecidable without
  tick data.
- **Halts.** One trade carries `halt_flag`; there is no halt/resume feed to
  confirm or deny any of them.
- **Float and catalyst.** No point-in-time source. Brief §17's float cut and
  all of §18 are absent, not empty.
- **True spread.** A range-quartile proxy drives the slippage model, and the
  slippage model drives the headline. An error here moves every number in §5.
- **The Pine itself.** `src/setups.py` is a Python port. TradingView is the
  only Pine compiler; state parity is asserted, not proven.
- **The LATE JOIN path**, declared and not implemented (§2).
- **Yearly, walk-forward, regime.** One month of data.

---

## 16. Answers to the twelve questions

| # | question | answer |
|---|---|---|
| 1 | Does the basic first pullback (A) have positive expectancy? | **No evidence that it does.** −1.775 R, CI [−2.24, −1.32], n=49 over 20 sessions. Gross of all costs it is still −0.274 R. **NO DEMONSTRATED EDGE — insufficient sample.** |
| 2 | Does VWAP/EMA/MACD improve out-of-sample expectancy? | **Directionally yes, inconclusively.** +0.424 R, the only rung that moves up, and the only filter whose accepted set beats its rejected set (+0.710 R separation, 24 losers removed against 2 winners). CIs overlap. **UNCERTAIN, lean KEEP.** |
| 3 | Does confluence add measurable edge? | **No — it separates the wrong way** (−0.441 R) and passes only 14.2% of candidates. It is also **not in the shipped strategy**. **REMOVE / do not add.** |
| 4 | Does low pullback volume add measurable edge? | **Not on this sample, twice over.** The accept/reject split separates −0.874 R (rejected trades outperformed), and loosening the threshold on F improves expectancy monotonically (0.5 → −1.863, shipped 0.7 → −1.585, 0.8 → −1.451). **UNCERTAIN, lean REMOVE — n=13 rejected.** |
| 5 | Does requiring room to HOD add measurable edge? | **Contradictory.** Two tests inside this study say no — separation −1.847 R, and tightening the requirement on F is monotonically worse (gate off −1.361 → 2R −1.728). The sibling megaday study found the *opposite* on n=62 (median MFE 2.04 R vs 1.35 R). **UNCERTAIN — needs the bigger sample to settle.** |
| 6 | Does F beat the simpler variants after realistic costs? | **No.** F −1.585 R vs B −1.351 R. F's own management logic (Exp 2) is worse still at −1.885 R with a 0% win rate. |
| 7 | Which filter removes the most **winning** trades? | **Confluence** — 8 of A's winners. |
| 8 | Which filter removes the most **losing** trades? | **Confluence again** (37), but it removes almost everything. Per unit of damage, **momentum**: 24 losers against 2 winners. |
| 9 | Largest statistically credible improvement? | **None is statistically credible at this sample size.** The largest point estimate is the momentum stack, +0.424 R on the ladder / +0.710 R on the accept-reject split, CIs overlapping throughout. |
| 10 | Does it survive stressed slippage? | **The question does not arise: under stressed slippage ~90% of entries are never filled.** Four fills survive. |
| 11 | Does it survive the untouched holdout? | **The holdout is 6 sessions and 3–14 trades. It cannot answer.** All variants stay negative in it. |
| 12 | Genuine edge, or overfitting/noise? | **Neither is demonstrated.** ~30 effective degrees of freedom against 20 independent sessions makes any out-of-sample claim unsupportable. What *is* established is narrower and does not depend on the sample: the pattern is negative **before costs**, a random entry on the same tape beats it, and the execution tax at the shipped stop cap is ~0.8 R per trade. |

---

## Verdict

**INSUFFICIENT DATA TO ANSWER THE QUESTION AS ASKED, and the pipeline that
would answer it is built, tested and ready.**

Three things are established and do not depend on the small sample:

1. **The blocker is 1-minute history, and it is one API key wide.** 25 days
   is what this environment can reach. `PolygonProvider` is wired for 5 years
   with extended-hours volume and delisted retention; §7 of `data_quality.md`
   has the three tests to run before paying and the exact commands after.
2. **The execution tax is structural, not incidental.** At the shipped 3%
   stop cap — an unsourced number sitting on the population's median stop —
   costs consume ~0.8 R per trade, and widening the cap improves expectancy
   monotonically without ever reaching zero. Two independent studies in this
   repo now say the same thing.
3. **Nothing in this study points upward.** Gross of all costs, variant A is
   negative. A random entry minute on the same qualifying tape beats it. An
   arbitrary five-tick shift of the trigger beats it. The afternoon trades
   that make up more than half the sample lose −2.35 R each, and the session
   window that would delete them is a default switch, not a discovery.

That is consistent with everything else measured in this repository: 8,828
symbol-days over 894 sessions with no edge in any year
(`2026-08-regime-filter.md`), an accurate Pine port at −7.66 R and −10.55 R
on 330 ticker-days (`2026-08-pine-v8-benchmark.md`), and a 250-megaday study
whose own verdict is *"moteur de rejet, pas de génération de signal"*
(`research/megaday-study/RESULTS.md`).

**The next step is data, not another rule.** Re-running this exact pipeline on
five years of consolidated minute bars is a single command and a $29
subscription, and it would move the sample from 49 trades to something in the
thousands. Until then the correct statement is the one the brief asked for
verbatim: **there is insufficient evidence of positive expectancy.**

---

```
NO TICKET ISSUED. Paper only. This study did not validate executable
bid/ask, borrow, halt state, float, catalyst, or the Pine's own compiled
behaviour. Every figure above is reproducible from results/run_manifest.json
(git 1033875, config sha256 d224b4e5…, seed 20260824).
```
