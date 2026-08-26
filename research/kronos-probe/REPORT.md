# Kronos on this tape — a zero-shot probe

```
FEED · minute bars · Alpaca Basic, feed=sip, CONSOLIDATED — the SAME cache
       the parent study ran on (11,429 ticker-months, no refetch)
MODEL · Kronos-small, NeoQuasar/Kronos-small + Kronos-Tokenizer-base
        24,741,376 params · 8 layers · d_model 512 · vocab 1024 x 1024
        ZERO-SHOT. No fine-tuning. Released checkpoints, unmodified.
CODE · Kronos git 67b630e (2026-04-13) · probe git af69c8e · seed 20260826
COMPUTE · 4 CPU cores, no GPU · 1.15 s per rollout, MEASURED, flat from
          4 to 128 rollouts · 174 minutes for both arms
RUN · 2026-08-26

! NOT A TRADING RESULT. This measures whether one model's output carries
  information about outcomes already known. No order, no ticket, no edge
  claim. The strategy under it is negative GROSS of costs and a better
  forecast would not change that.
```

---

## 1. What was asked

`first-pullback-edge` closed negative and left one question open: the
**random** entry population reaches +1 R far more often than the
pattern-selected one — 25.9% vs 14.3%, mean MFE 1.15 R vs 0.78 R
(`first-pullback-edge/reports/final_report.md` §10). That is a question about
the conditional distribution of the next thirty minutes, which is the object
a candlestick foundation model emits.

So: hand Kronos 150 bars, take 30 forward, reduce N sampled paths to
P(+1 R before −1 R), and put it next to what happened.

## 2. What was considered — the funnel

```
PATTERN ARM  3,627 variant-A trades (the study's headline population)
             → 371 drawn seeded-random across eleven years
             → 71 dropped ✗ fewer than 150 same-session bars before the anchor
             → 300 scored · 300 resolved · 26 winners · base rate 8.67%

RANDOM ARM   8,505 scanner-qualified ticker-days
             → 300 random minutes 09:35-11:30, risk = 1 ATR
             → 0 dropped
             → 300 scored · 299 resolved · 131 winners · base rate 43.81%
                (1 'neither' — horizon ran out untouched)
```

The anchor is `setup_ts`, the decision moment, **not** `entry_ts` — a filter
has to be usable before the trigger is touched. No context window crosses a
session boundary; anchors without enough same-session history are dropped and
counted, never padded from the previous day.

**19% of pattern anchors dropped.** Small-cap tape is sparse and 150 bars
back from a 10:15 setup often does not exist inside the session. That is a
selection effect on everything below.

## 3. What the model produced, and what failed

### 3.1 The barrier probability collapsed on the pattern arm

```
✗ p_win  DEGENERATE — 90.33% of anchors exactly 0.0, seven distinct values
                      across 300 anchors
```

Its AUC of 0.5105 is therefore **not** evidence that the model has no signal.
It is a score with almost no variance. Absence of evidence, not evidence of
absence — and a reader who stopped at the summary JSON would have concluded
the opposite.

### 3.2 Why it collapsed — measured, not inferred

| quantity | pattern arm |
|---|---:|
| model's predicted 30-min move, median | **−5.12%** |
| actual tape, median | −1.50% |
| corr(model forecast, **context-window mean**) | **+0.756** |
| corr(model forecast, **what actually happened**) | **−0.041** |
| anchor's z-score inside its own 150-bar window, median | **+2.12σ** |

The model regresses toward the context window's mean. A momentum pullback
sits near the local high *by construction*, so the forecast is structurally
bearish on every anchor in this population. **The bearishness is the
normalisation prior meeting a selected sample — not a forecast.**

### 3.3 The random arm confirms it, and calibrates well

Anchors not selected to sit high in their window (median z **−0.44**):

| | model | actual | gap |
|---|---:|---:|---:|
| P(+1 R before −1 R) | **0.4267** | **0.4381** | **1.1 pts** |
| mean MFE (R) | 2.509 | 2.655 | 0.15 |
| mean MAE (R) | 2.569 | 2.354 | 0.22 |
| fraction of `p_win` exactly 0 | 1.67% | — | — |

`p_win` is no longer degenerate, and the aggregate base rate is close to
right. **Zero-shot, on a tape whose coverage in pre-training is
undocumented, that is a genuine result.**

### 3.4 Ranking, which is what a filter needs

AUC 0.5 = no information. Bootstrapped, 2,000 resamples.

```
in AUC: rank ability only. A well-calibrated model that cannot rank is
useful for sizing a prior and useless as a filter.
```

| arm | score | AUC | 95% CI | source |
|---|---|---:|---|---|
| pattern | `exp_close_r` | 0.6745 | [0.571, 0.778] | kronos |
| pattern | **`dist_from_window_mean_R`** | 0.6443 | [0.533, 0.746] | **free** |
| pattern | `p_win` | 0.5105 | [0.451, 0.557] | kronos ✗ degenerate |
| random | **`risk_pct`** | **0.5683** | [0.501, 0.633] | **free** |
| random | `exp_close_r` | 0.5638 | [0.497, 0.626] | kronos |
| random | `p_win` | 0.5317 | [0.466, 0.598] | kronos |

**Kronos never beats a free statistic.**

- Pattern arm: best Kronos score leads the best model-less one by **+0.030**,
  intervals heavily overlapping, on 26 winners.
- Random arm: best Kronos score **loses by −0.005** to "how wide is the stop
  as a percent of price" — one line of arithmetic, no model, no GPU.

Within either population the CI spans 0.5. There is no ranking signal here.

### 3.5 Pattern vs random, with both confounds controlled

Two confounds, both found and both measured rather than assumed:

| confound | pattern | random |
|---|---:|---:|
| anchor z inside its own window (median) | +2.12σ | −0.44σ |
| session window | all day, **52% afternoon** | 09:35–11:30 only |

The second was inherited from the parent baseline's own rule and would have
flattered the random arm, since the report's time-of-day cut makes
09:30–10:00 the strategy's best bucket. Matching on **both**:

| stage | pattern n | pattern realised | random n | random realised |
|---|---:|---:|---:|---:|
| raw | 300 | 8.67% | 300 | 43.81% |
| 09:35–11:30 only | 104 | 12.50% | 300 | 43.81% |
| **+ overlapping z band** | **46** | **23.91%** | **144** | **40.97%** |

**The parent study's central result survives matching** — random still nearly
doubles the pattern at comparable time of day and comparable height in the
window, though pattern n falls to 46.

The model's own separation does *not* track it. Matched, Kronos assigns
`p_win` 0.016 to pattern and 0.426 to random — a **26× gap where reality
shows 1.7×**. It points the right way and wildly overstates the magnitude,
for the reason in §3.2 rather than from knowledge of the tape.

### 3.6 Predicted candles are not always candles

Nothing in the decoder enforces `high ≥ max(open, close)`. Measured over
1,080 predicted bars:

| check | rate |
|---|---:|
| high < close | 1.11% |
| low > open | 1.20% |
| **high < low** outright | **0.09%** |
| **any inconsistency** | **3.43%** |

Both readings are carried — raw, and after a **monotone** repair that can
only widen a bar to contain its own open and close. `✓ REMEDIATED, and it
changed nothing`: AUC moved 0.5105 → 0.5105 on the pattern arm and
0.5317 → 0.5309 on the random arm. **The invalid bars are real and are not
what drove the result.**

## 4. What this analysis could not check

- **Pre-training coverage is undocumented.** The model card says 45 global
  exchanges without a manifest. Whether sub-$20 US small caps at one-minute
  resolution appear at all is `UNKNOWN`, and it is the most likely
  explanation for §3.2 if the answer is "no".
- **Zero-shot only.** No tokenizer or predictor fine-tuning was run. Kronos'
  own documentation says the tokenizer stage is what adapts to a new domain's
  distribution, so this is a floor on the model's capability, not a ceiling.
- **One model size.** Kronos-small (24.7M). `Kronos-base` (102.3M) untested;
  `Kronos-large` is not open.
- **16 sampled paths** quantises `p_win` to 1/16. Adequate for the random
  arm, and part of why the pattern arm's score is coarse.
- **No holdout discipline.** Anchors are seeded-random across all eleven
  years, not drawn from the parent study's 478-session untouched holdout.
  Nothing here was tuned, so nothing is overfit — but it is not the clean
  test either.
- **Power.** 26 winners on the pattern arm, 46 anchors in the matched
  pattern cell. Detects a large effect, not a small one.
- **Costs never entered.** No spread, slippage, commission, participation or
  halt modelling. Any signal would still owe the ~22.6 bps round trip
  measured earlier in this repo before it meant anything.
- **`fwd_mfe_r` is unconditional** — the excursion over the whole horizon
  whether or not a barrier was hit. It is NOT the parent study's `mfe_r`,
  which stops when the position does. On the same 41 anchors they read
  2.54 R and 0.78 R for that reason alone. Do not put the columns
  side by side.

## 5. Verdict

**NO USABLE SIGNAL — and a real calibration result underneath it.**

Kronos, zero-shot, gives a **well-calibrated unconditional base rate** on
unselected anchors: 42.67% predicted against 43.81% realised, on a tape it
was probably never trained on. That is worth knowing and it is not nothing.

It gives **no ranking ability**. Within either population the AUC interval
spans 0.5, and against free, model-less statistics it wins by +0.030 with
overlapping intervals on one arm and **loses by −0.005** on the other. As a
filter over these setups it is `NO`.

On the pattern population it is worse than uninformative: it regresses to the
context-window mean, which on a momentum-selected anchor is a structurally
bearish forecast, and `p_win` collapses to zero for 90% of anchors. The
apparent between-population separation is that same prior, not knowledge —
26× where reality is 1.7×.

The honest next step, if this is pursued: **fine-tune the tokenizer first**,
because §3.2 is a distribution-mismatch signature, and re-run on the parent
study's untouched holdout. `MANUAL REVIEW` on whether that is worth the
compute — a floor result this flat, from a model whose forecast correlates
0.756 with a one-line statistic, is weak grounds for spending more.

---

```
NO TICKET ISSUED. This probe does not validate spread, executable bid/ask,
fees, halt state, borrow, or any live-market condition. It scores a model's
output against outcomes that are already in the parent study's ledger.
Paper only. An exact implementation is still not an edge.
```
