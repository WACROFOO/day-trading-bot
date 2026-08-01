# Observations

Measurements from the current implementation. Facts and where they came from —
no interpretation beyond what the numbers state.

Regenerate any of these with the command shown.

---

## 1. What the source reports

From the corpus (`../../scripts/search.py`), self-reported and unaudited:

| Claim | Source |
|---|---|
| ~68.5% win rate over 10+ years, 32,000 trades | `Wsq8zdtCcis` [28:01] |
| 69.3% over 166 trades in one 7-day period | `Wsq8zdtCcis` [1:25] |
| 76% accuracy on the first/second pullback pattern | `SmSOboqGPgs` [12:14] |
| ~2:1 average profit-to-loss ratio | `Wsq8zdtCcis` [2:58] |
| Trades taken per day | 2 (playbook limit); recaps typically show 2–5 |

`STRATEGY_V2.md` §3 notes the stated win rate and reward:risk imply roughly
+3.2% per day, which is implausibly high. The claims are unverified.

---

## 2. What the implementation produces

17 trading days, 2026-07-09 → 2026-07-31, $10,000 account.

```bash
python pipeline/run20b.py 2 5
python diagnostics/analyze20.py 5
```

| | max_trades=2 | max_trades=5 |
|---|---:|---:|
| Trades | 3 | 3 |
| Total P&L | +$128.70 | +$128.70 |
| Expectancy | +0.717R | +0.717R |

| Day | Sym | In | Out | Hold | Entry | Stop | R | Exit |
|---|---|---|---|---:|---:|---:|---:|---|
| 07-23 | NEUP | 09:40 | 09:51 | 11m | 3.78 | 3.75 | +3.17 | trailing stop |
| 07-28 | EHGO | 10:12 | 10:13 | 1m | 2.44 | 2.38 | −1.00 | stop hit |
| 07-28 | EHGO | 10:22 | 10:26 | 4m | 2.46 | 2.42 | −0.02 | MACD negative |

n=3. One trade exceeds the total P&L; without it the result is negative. The
two trade limits give identical output because the limit never binds.

---

## 3. The largest measured discrepancy

**Trade frequency: 0.18 per day. The source describes ~2 per day.**

The implementation is roughly an order of magnitude more selective than the
behaviour it is modelling. This is the discrepancy that makes the P&L
uninterpretable — the sample is small because the gate is narrow, not because
the market offered nothing.

```bash
python diagnostics/loo.py
```

835 candidate setups are detected across the 17 days. 5 satisfy every entry
condition simultaneously. The entry gate is a conjunction of 9 boolean
conditions with these individual pass rates:

| Condition | Passes | Setups passing everything if this one is dropped |
|---|---:|---:|
| pullback volume < impulse volume | 79% | 8 |
| price > 9 EMA | 74% | 5 |
| MACD histogram > 0 | 63% | 5 |
| price > VWAP | 61% | 5 |
| support confluence ≥ 2 | 60% | 8 |
| front side of the move | 52% | 9 |
| pullback index ≤ 2 | 50% | 9 |
| pullback 2–4 candles | 46% | 9 |
| pullback holds 50% of leg | 36% | 8 |

Distribution of conditions failed per setup: the median setup fails 3–4 of 9.
Dropping any single condition still leaves under 10 passing out of 835.

The product of the individual rates is ~0.6%, which matches the observed
0.18 trades/day. For reference, 2 trades/day at 835 setups would require the
joint pass rate to be ~4%.

---

## 4. Setup geometry

```bash
python diagnostics/probe.py
```

Distance from the pullback low to each reference level, as a percentage of
price, measured across ~300 detected setups. Positive means the dip stopped
above the level.

| Level | Median signed distance | Dip stopped above it |
|---|---:|---:|
| 9 EMA | −1.23% | 13% of setups |
| 20 EMA | −0.48% | 42% |
| VWAP | +3.07% | 89% |

Confluence hit counts across setups: 20 EMA 38, 9 EMA 35, whole/half dollar 26,
VWAP 21, 200 MA 7.

---

## 5. Timing

```bash
python diagnostics/probe2.py
```

60 symbol-days on the watchlists. Bars, setups, and time spent below VWAP:

| Window | Bars | Setups | Below VWAP |
|---|---:|---:|---:|
| 09:30–10:00 | 1,534 | 186 | 57% |
| 10:00–10:30 | 1,590 | 257 | 56% |
| 10:30–11:30 | 3,182 | 402 | 68% |

The source describes the prime window as 09:30–10:30 with most of the edge
there.

---

## 6. Watchlist behaviour

```bash
python diagnostics/probe3.py
```

Of 60 watchlist symbol-days, **35 (58%) close below their opening price** by
11:30. Median run from open to high is +13.6%; median open to 11:30 is −3.9%.

Individual examples span the range — VEEE on 07-13 opened $12.20, reached
$29.19 (+139%) and held +99% at 11:30; LVLU on 07-14 opened $9.77 and was
−19% by 11:30.

---

## 7. Pillar-count gradient

```bash
python diagnostics/gradient.py
```

`PARAMETERS.md` §12 step 3 prescribes this test: if the entry conditions capture
setup quality, results should improve monotonically as more of them are
required.

| Min pillars required | Trades | Win % | P&L | Exp R |
|---:|---:|---:|---:|---:|
| 9 | 3 | 33.3 | +128.70 | +0.717 |
| 8 | 22 | 40.9 | +703.35 | +0.446 |
| 7 | 52 | 36.5 | +608.23 | +0.320 |
| 6 | 69 | 39.1 | +404.31 | +0.156 |
| 5 | 72 | 37.5 | −453.16 | +0.334 |

Expectancy per trade declines as the requirement is relaxed from 9 to 6, which
is the direction the test predicts; total P&L and the 5-pillar row do not follow
it. Sample sizes are small and the rows are not independent.

---

## 8. Exit attribution

```bash
python diagnostics/diag.py
```

Identical entry signals under three exit regimes, used to separate entry quality
from exit quality. Re-run this after any change to either.

---

## Open parameters

Values the corpus does not state, which therefore cannot be set from evidence:

| Parameter | Status |
|---|---|
| `level_tolerance` | `PARAMETERS.md:127` — "unstated", sweep 0.1–0.5% of price, floor at spread width |
| pullback index reset | No rule stated for when "first or second pullback" restarts counting. Two readings are implemented and switchable (`PULLBACK_RESET` in `engine/sim.py`); they currently produce identical results |
| front-side definition | "Front side of the move" is not quantified in the corpus |
| spread | No quote data; estimated from bar ranges |

`diagnostics/sweep.py` sweeps the first two together.
