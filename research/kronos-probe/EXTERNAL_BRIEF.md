# External review brief — small-cap momentum, and a candle foundation model that didn't help

**Purpose of this document.** It is a self-contained handoff for an outside
reviewer with no access to the repository. Every number needed to critique
the work is inline. The specific questions are in §7 — that is what the
review is actually for.

**Standing bias request:** we are trying to *disprove* our own work. If a
result here looks like a finding, the most useful thing you can do is explain
why it is an artifact. Two of the three "findings" in the parent study were
already overturned by our own larger samples.

---

## 0. TL;DR for the reviewer

1. We mechanically replicated a well-known retail day-trading strategy
   ("First Pullback" on small-cap momentum gappers) over 11 years and found
   **negative expectancy in every year, and negative gross of all costs**.
2. Worse: a **random entry minute on the same stocks beats the strategy by
   0.80 R**. Selecting for the pattern selects for *worse* outcomes than not
   selecting at all. That is the interesting result and we do not have a
   mechanism for it.
3. We then tested **Kronos**, an open-source candlestick foundation model, as
   a possible filter. Zero-shot it is **well calibrated in aggregate** (42.67%
   predicted vs 43.81% realised) but has **no ranking ability**, and it loses
   to a one-line statistic.
4. Its forecast correlates **+0.756 with the context window's mean** and
   **−0.041 with what actually happened**. We think this is a normalisation
   artifact. We want that diagnosis attacked.

---

## 1. The strategy under test

Small-cap momentum, US equities, intraday. Ported mechanically from a
2,774-line TradingView Pine script (`ross-fp-v4.pine`, REV V9.12) to Python,
parameter by parameter, with each value tagged by the Pine line it came from.

**Universe (point-in-time, survivorship-free):**
- open price $2–20, gap ≥ 10% vs previous close
- trailing-20-session dollar volume ≥ $250k
- reverse-split artifacts flagged and excluded
- top 5 gappers per session (a discovery cap on a gap known at 09:30, not an
  entry gate)

**Entry (variant A, the basic form):**
- a qualifying impulse: ≥5% **and** ≥2 ATR **and** efficiency ≥0.60 **and**
  RVOL ≥2 **and** ≥$100k/min
- first pullback, 1–4 bars, at least one red
- retracement ≤ 50% of the push
- trigger = pullback-bar high + 1 tick; stop = pullback low − 1 tick
- structural stop with caps: ≤3% of price, ≤1.5 ATR, ATR fallback

Variants B–F add: VWAP/EMA9/EMA20/MACD stack (B), support confluence (C),
pullback volume ≤0.70× push volume (D), HOD room (E), LULD halt-band veto
plus extra entry lanes (F).

---

## 2. Data and method

| | |
|---|---|
| Minute bars | Alpaca Basic, `feed=sip`, **consolidated**, 2016–2026 |
| Universe | Massive/Polygon grouped-daily (2024-09+) and historical ticker list × Alpaca multi-symbol daily (pre-2024) |
| Survivorship | 12,613 tickers pulled, **6,701 carrying a delisted date** — more than half the universe no longer exists |
| Cross-check | 28 shared RTH sessions on both feeds: identical minute counts, identical session highs/lows, volume within 0.7%, **zero disagreements** |
| Sample | 25,716 candidate ticker-days · 2,615 sessions · 5,797 names · **11 calendar years** including 2020 COVID and 2021 meme-stock |
| Qualified | 8,505 ticker-days pass the 09:35 ET point-in-time scanner |
| Trades | 3,627 in variant A across 1,453 sessions |

**Look-ahead controls** (33 tests, all about this):
- indicators are incremental only; no vectorised pass over a day exists
  anywhere in the codebase
- HOD = `max(high)` from session start **through the current bar**
- RVOL-at-time = cumulative volume vs the same-session-minute average over
  **prior days only**
- universe screening uses open, previous close, trailing-20 dollar volume
  **excluding today**
- scanner frozen at 09:35 ET; every trade carries its `scan_ts`
- **truncation audit**: cut the day's bars at 45/50/55/60 and every prior
  trade returns identical

**Execution model:**
- stop-limit entry; a gap through the limit books as MISSED, not filled
- four cost scenarios: gross / low / realistic / stressed
- ambiguity policy: a bar containing both trigger and stop is scored
  **pessimistically** (loss) — with OHLC only there is no evidence for the
  favourable ordering. ~25% of fills touch trigger and stop in the same
  minute.
- participation cap, LULD halt bands, fail-closed on unknown band inside RTH

**Splits:** chronological, never shuffled — development 716 sessions,
validation 398, **untouched holdout 478** (opened once). No parameter was
selected on the holdout.

---

## 3. Result: the strategy has negative expectancy

### 3.1 Headline

| variant | trades | win % | exp. R | PF | 95% CI |
|---|---:|---:|---:|---:|---|
| A (basic first pullback) | 3,627 | 14.3% | **−1.741** | 0.08 | [−1.79, −1.69] |
| **random entry, 09:35–11:30, 1-ATR stop** | **42,510** | **25.9%** | **−0.940** | **0.22** | **[−0.96, −0.92]** |

CIs are day-clustered bootstrap — we resample **sessions**, not trades,
because trades within a session are not independent.

**A random entry minute beats the first pullback by 0.80 R**, with intervals
nowhere near each other. Random wins on every metric: win rate 25.9% vs
14.3%, profit factor 0.22 vs 0.08, mean favourable excursion 1.15 R vs 0.78 R.

The wider-stop defence fails: the random baseline's 1-ATR stop is a median
**1.49% of price** against the strategy's **1.98%**. It pays more execution
tax per R and still wins.

### 3.2 Every year, both good regimes included

| year | trades | win % | exp. R |
|---|---:|---:|---:|
| 2016 | 84 | 20.2% | −1.508 |
| 2017 | 167 | 12.6% | −1.704 |
| 2018 | 174 | 17.8% | −1.636 |
| 2019 | 215 | 13.5% | −1.775 |
| **2020** | 478 | 16.3% | −1.647 |
| **2021** | 628 | 12.6% | −1.700 |
| 2022 | 422 | 13.0% | −1.805 |
| 2023 | 350 | 18.0% | −1.681 |
| 2024 | 387 | 12.1% | −1.878 |
| 2025 | 404 | 14.6% | −1.761 |
| 2026 (to 08-21) | 318 | 11.9% | −1.865 |

Eleven years, eleven losses, in a band of 0.37 R. No good year, no good
regime, no drift. Holdout (478 sessions, 1,067 trades): **−1.837**.

### 3.3 Cuts that should matter and don't

| cut | bucket | n | win % | exp. R |
|---|---|---:|---:|---:|
| price | $2–5 | 1,624 | 10.0% | **−2.192** |
| price | $10–20 | 693 | 22.1% | −1.158 |
| pullback № | **1st** | 1,822 | 13.3% | **−1.869** |
| pullback № | 3rd+ | 914 | 16.3% | −1.519 |
| RVOL | <2 / 2–5 / >5 | 543/329/2,150 | — | −1.73 / −1.69 / **−1.75** |
| time | 09:30–10:00 | 877 | 19.5% | −1.471 |
| time | 11:30–16:00 | 1,898 | 12.7% | −1.826 |

Notes we find uncomfortable and are reporting anyway:
- **"First" is the worst of the three pullbacks** — the setup the strategy is
  named after.
- **RVOL does not discriminate at all** (three buckets within 0.06 R), despite
  being the strategy's headline filter.
- The cheapest tier is by far the worst and is 45% of the sample.
- Filter redundancy: largest |phi| across all gate pairs is 0.269
  (momentum ↔ HOD-room, **negative** — they are opposed, because the momentum
  stack only turns green once price is already extended).

Applying every correction the study can justify, **all at once**, reaches
−1.222 R. Still negative.

**The strategy is negative gross of all costs.** This is not an execution
problem.

---

## 4. The open question we cannot answer

> The **random** population reaches +1 R far more often than the
> pattern-selected one — 25.9% vs 14.3%, mean MFE 1.15 R vs 0.78 R, on the
> *same qualifying names*, in the *same session window*.

So the qualifying **universe** appears to hold something the **pattern** is
actively selecting away from. We do not have a mechanism. Candidate
explanations we have considered and not resolved:

1. The pattern fires *after* the impulse, i.e. it systematically buys
   extension. The negative momentum↔HOD-room correlation (−0.269) is
   consistent with this.
2. The structural stop is tighter than the noise it sits in, so the pattern
   population is stopped out by microstructure rather than by being wrong.
3. Selection on a *visible* pattern selects for crowding, and the crowd is
   the exit liquidity.
4. Some artifact in our own detector that we have not found.

**We want (4) attacked hardest.**

---

## 5. Kronos probe — what we did and what happened

### 5.1 The model

[Kronos](https://github.com/shiyu-coder/Kronos) — "first open-source
foundation model for financial candlesticks (K-lines)", AAAI 2026, MIT
licence. Two stages: a Binary Spherical Quantization tokenizer compresses
`[open, high, low, close, volume, amount]` per bar into two hierarchical
token streams (coarse `s1`, fine `s2` conditioned on `s1`), then a
decoder-only transformer over those tokens with RoPE and additive temporal
embeddings (`minute, hour, weekday, day, month`).

We used **Kronos-small**, zero-shot, unmodified: 24,741,376 params, 8 layers,
d_model 512, 8 heads, s1/s2 = 10 bits each → 1024 × 1024 vocab, max context
512. Code at commit `67b630e`.

### 5.2 Design

- context **150 bars**, horizon **30 bars**, **16 sampled paths** per anchor
- anchor = the strategy's `setup_ts` (the decision moment, before the trigger
  is touched) — not the entry
- **no context window crosses a session boundary.** Anchors without 150
  same-session bars are dropped and counted, never padded from the previous
  day. 19% of pattern anchors dropped for this.
- we **keep the sample axis**. Kronos' shipped `predict()` ends on
  `preds = np.mean(preds, axis=1)`, which averages OHLC paths in price space —
  the mean of N paths has a lower high and a higher low than any single path,
  destroying exactly the quantity we measure. We replicate each anchor N times
  in the batch dimension and call with `sample_count=1` so their mean becomes
  a no-op. *(Verified by test that the N copies are genuinely independent
  samples — otherwise every probability would be 0 or 1 and nothing would
  complain.)*
- reduction: walk each path bar by bar, first touch of entry ± 1R using the
  **predicted high and low**, ambiguous bar → loss (matching the backtest's
  policy)
- ground truth: the same rule applied to the forward tape

**Two arms:**

| arm | anchors | n |
|---|---|---:|
| pattern | the strategy's own setups | 300 |
| random | random minute 09:35–11:30 on a qualifying ticker-day, risk = 1 ATR | 300 |

Compute: 4 CPU cores, no GPU. **1.15 s per rollout, flat from 4 to 128
rollouts** — the cores saturate at batch 4, so batching bought nothing. 174
minutes total.

### 5.3 Results

**Random arm — calibration is good:**

| | model | actual |
|---|---:|---:|
| P(+1R before −1R) | **0.4267** | **0.4381** |
| mean MFE (R) | 2.509 | 2.655 |
| mean MAE (R) | 2.569 | 2.354 |

**Pattern arm — the score collapses:**

- `p_win` was **90.33% exactly zero**, seven distinct values across 300
  anchors. Its AUC of 0.5105 is therefore *absence of evidence*, not evidence
  of absence.
- the model predicts **−5.12% median** over 30 minutes on essentially every
  anchor; the tape did −1.50%
- **corr(model forecast, context-window mean) = +0.756**
- **corr(model forecast, what actually happened) = −0.041**
- these anchors sit at a median **+2.12σ** inside their own 150-bar window,
  because a momentum pullback is near the local high by construction

**Our diagnosis:** the model regresses toward the context window's mean. Under
Kronos' normalisation (per-window z-score, clip ±5), a selected anchor near
the top of its window produces a structurally bearish forecast. It is a
prior meeting a selected sample, not a forecast.

### 5.4 Ranking — the control that matters

AUC 0.5 = no information. Bootstrapped, 2,000 resamples.

| arm | score | AUC | 95% CI | source |
|---|---|---:|---|---|
| pattern | `exp_close_r` | 0.6745 | [0.571, 0.778] | Kronos |
| pattern | **`dist_from_window_mean_R`** | 0.6443 | [0.533, 0.746] | **free** |
| pattern | `p_win` | 0.5105 | [0.451, 0.557] | Kronos (degenerate) |
| random | **`risk_pct`** | **0.5683** | [0.501, 0.633] | **free** |
| random | `exp_close_r` | 0.5638 | [0.497, 0.626] | Kronos |
| random | `p_win` | 0.5317 | [0.466, 0.598] | Kronos |

"free" = computable from the context window with no model. `risk_pct` is
literally `100 * stop_distance / price`.

**Kronos never beats a free statistic.** +0.030 with overlapping intervals on
one arm; **−0.005 on the other**.

### 5.5 Confounds we found and controlled

| confound | pattern | random |
|---|---:|---:|
| anchor z inside its own window (median) | +2.12σ | −0.44σ |
| session window | all day, **52% afternoon** | 09:35–11:30 only |

Matching on both:

| stage | pattern n | pattern win% | random n | random win% |
|---|---:|---:|---:|---:|
| raw | 300 | 8.67% | 300 | 43.81% |
| 09:35–11:30 only | 104 | 12.50% | 300 | 43.81% |
| **+ overlapping z band** | **46** | **23.91%** | **144** | **40.97%** |

The parent study's central result survives matching. **The model's separation
does not track it**: matched, Kronos says 0.016 vs 0.426 — a **26× gap where
reality shows 1.7×**.

### 5.6 Code-level findings in Kronos itself

Read-only scan, commit `67b630e`:

- **Causal by construction.** `is_causal=True` is hard-coded in every
  self-attention block (`model/module.py:349`), including the *tokenizer's*
  encoder. No look-ahead by design. Good.
- Training normalisation is lookback-only (`finetune/dataset.py:112`). No leak.
- **Predicted candles are not always valid candles.** Nothing enforces
  `high ≥ max(open, close)`. Measured over 1,080 predicted bars: **3.43%
  internally inconsistent**, 0.09% with `high < low` outright. We applied a
  monotone repair (widen only). **It changed nothing** — AUC 0.5105 → 0.5105,
  0.5317 → 0.5309.
- **No KV cache** (`model/kronos.py:436`) — every generated bar re-runs the
  full stack over the whole context. This is the entire compute bill.
- Train/inference mask mismatch in the `s2` cross-attention:
  `is_causal = self.training` (`module.py:387`) — causal while training,
  non-causal at eval. No actual leak in the rolling loop, but the layer is
  evaluated under a mask it wasn't trained under.
- Latent crash: self-attention passes both `attn_mask` and `is_causal=True`
  to `F.scaled_dot_product_attention` (`module.py:345-350`), which PyTorch
  rejects. Survives only because every call site passes `padding_mask=None`.
- Their own downstream never uses predicted high or low —
  `finetune/qlib_test.py:277-281` builds every signal from close alone. So our
  use of the predicted high/low is untested upstream.
- Pre-training corpus coverage is **undocumented**: "45 global exchanges", no
  manifest. Whether sub-$20 US small caps at 1-minute resolution appear at all
  is unknown, and is the most likely explanation for §5.3 if the answer is
  "no".

---

## 6. A separate, earlier measurement (context for §7)

Before Kronos we asked whether minute candles carry usable sequence
information at all, treating them as a discrete language.

*(Measured on our cached bars this session; scratch analysis, not committed —
treat as indicative, not audited.)*

- 1,378,652 candles across 4,000 sessions, 36-symbol alphabet
  (direction × body size × range), held out **by session**
- conditional entropy: order 0 = 4.4721 bits/candle; **order 2 = 4.3190
  (−3.42%, the peak)**; order 3 = 4.5667 (**worse than no context**);
  order 5 = 5.0458 (much worse)
- beyond ~2 candles of context, a count-based model does worse out of sample
  — it was memorising 331,776 contexts
- next-candle direction, flat candles excluded: **56.86%** on 552,834 held-out
  candles vs a **50.28%** majority baseline (+6.59 pts)
- attribution: **lag-1 autocorrelation ρ = −0.124**; mean next-minute return
  −7.69 bps after an up candle vs +5.09 bps after a down candle
- that 12.78 bps spread against a **~22.6 bps proxy round-trip cost** =
  **0.565×**. The signal is the bid-ask bounce and is smaller than the cost of
  capturing it.

Caveat we are aware of: a count-based order-N model failing at order 3+ does
**not** imply a transformer will fail — it failed by memorisation, which is
what a learned model is built to avoid.

---

## 7. What we want from you

Ordered by how much we think it matters.

### Q1 — Is the mean-reversion diagnosis right, and is it fixable?
Our claim: Kronos' per-window z-score normalisation, applied to an anchor
sitting at +2σ in its own window, produces a structurally bearish forecast
that is a prior rather than information. Evidence: corr 0.756 with window
mean, −0.041 with outcome.
**Is there a normalisation or conditioning scheme that removes this without
feeding the model out-of-distribution inputs?** (Longer context? Return-space
inputs? Anchoring on last price instead of window mean? Does any of that
break the pre-training match?)

### Q2 — Is a barrier probability the right reduction of a generative candle model?
We reduce N sampled OHLC paths to P(touch +1R before −1R) using predicted
high/low. Alternatives we considered but did not test: quantile forecasts of
the 30-bar high/low, CRPS/pinball loss on those, expected shortfall, or
simply not using a path model at all.
**Is there a better-posed target?**

### Q3 — Is our evaluation statistically sound?
We use rank AUC with tie-correction, bootstrapped 2,000×. But our anchors are
**not independent** — multiple anchors share a session. The parent study uses
day-clustered bootstrap; the probe's AUC CIs do **not** cluster by day.
**How much does that overstate our precision, and what is the right
correction here?**

### Q4 — Are the free baselines strong enough to be a fair test?
We beat Kronos with `dist_from_window_mean_R` and `risk_pct`. A skeptic could
say we picked weak baselines to make a null look decisive, or that we
p-hacked the baseline by trying several.
**What baseline would you demand?**

### Q5 — Is fine-tuning worth it, and what would success look like?
Kronos' docs say the tokenizer stage is what adapts to a new domain's
distribution. Our §5.3 looks like a distribution mismatch.
**Given a floor result this flat, is tokenizer fine-tuning a reasonable next
spend, and what pre-registered success criterion should we set before
starting?** (We want the criterion fixed in advance so we cannot move it.)

### Q6 — Is there a better-suited model?
Chronos, TimesFM, Moirai, Lag-Llama, TimeGPT, PatchTST. Most are univariate
or point-forecast oriented; we need a joint OHLC path to answer a barrier
question.
**Is there one that fits this shape better, or is the shape itself wrong?**

### Q7 — The real question: why does random beat the pattern?
See §4. This is the finding we care about and cannot explain. **What
mechanism would produce a visible chart pattern that systematically selects
worse-than-random outcomes on the same names, in the same window?** And what
test would distinguish a real mechanism from a bug in our detector?

### Q8 — What did we get wrong?
Anything above. We would rather find it here than believe it.

---

## 8. What this work did NOT check

- No fine-tuning of any kind — zero-shot only. Floor, not ceiling.
- One model size (24.7M). Kronos-base (102.3M) untested; Kronos-large not open.
- 16 sampled paths quantises the probability to 1/16.
- The probe's anchors are seeded-random across all 11 years, **not** drawn
  from the parent study's untouched holdout. Nothing was tuned, so nothing is
  overfit — but it is not the clean test either.
- Power: 26 winners on the pattern arm; 46 anchors in the matched pattern
  cell. Detects a large effect, not a small one.
- Costs never entered the Kronos probe at all.
- No quote data anywhere in the free tier — spread is a proxy throughout.
- Foreign private issuers (6-K/20-F) are a dilution blind spot: no S-3/424B
  tripwire exists for them.

---

```
Paper only. No live capital, no order ever placed from any of this.
The strategy is negative gross of costs; a better forecast would not
change that. Everything above is selection quality, never a claim of edge.
```
