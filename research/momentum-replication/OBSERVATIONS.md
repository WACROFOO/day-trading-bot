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

---

## Update — two further defects (independent review)

Found by an independent review of this package, verified here against the code
and reproduced on the cached data.

**14. The pullback index counted things the source does not call pullbacks.**
`PullbackTracker.update` incremented `self.index` (sim.py:214, 253) on *any*
dip that resolved upward, while the 2–4 candle test lived in `evaluate()`
(sim.py:286). A 1-bar pause was therefore rejected as an entry but had already
consumed one of the two pullbacks allowed by `PARAMETERS.md:89`, and had
rebased `leg_low` — moving the leg origin used by the 50%-of-leg test. The
first genuine flag of a move was routinely numbered #3+ and rejected.
*Fix:* only 2–4 candle dips emit a setup, advance the index, or rebase the leg.
A single pause bar is part of the impulse; a 5–6 bar consolidation is a base.

**15. A 6%-of-price stop cap that appears in no source document.**
`sized_ok` required `risk_per_share <= 0.06 * entry`. The corpus bound is
absolute — `stop_max_distance <= $0.20` (`PARAMETERS.md:159`) — and
`PLAYBOOK.md:166` says a wider stop is sized down, not skipped, which the
sizing formula already does. The only 6% in the source is the **daily account
loss limit** (`PLAYBOOK.md:56`), a different quantity. Being relative it cut
both ways: on a $2.44 stock it skipped stops past $0.15, tighter than the $0.20
the source allows. *Fix:* removed. The spread floor (`PARAMETERS.md:161`)
remains as the only sizing rejection.

### Measured effect

| | Before | After |
|---|---:|---:|
| Setups detected | 835 | 416 |
| Passing all 9 conditions | 6 | 14 |
| Trades (17 days) | 3 | 10 |
| Trades per day | 0.18 | 0.59 |
| P&L | +$128.70 | −$541.58 |

Look-ahead audit passes at every cut-off after the change.

The leave-one-out profile is now flat — dropping any single condition yields
14–27 passing out of 416, with no choke point:

| Condition | Pass % |
|---|---:|
| pullback 2–4 candles | 100% |
| pullback volume < impulse | 78% |
| pullback holds 50% of leg | 77% |
| pullback index ≤ 2 | 71% |
| price > 9 EMA | 65% |
| MACD histogram > 0 | 62% |
| support confluence ≥ 2 | 61% |
| price > VWAP | 54% |
| front side of the move | 52% |

`pullback 2–4 candles` is now 100% by construction — the tracker cannot emit
anything else — so it is a redundant check rather than a filter.

### Correction to §3 above

§3's statement that "dropping any single condition still leaves under 10
passing out of 835" was **stale**. Re-measured on the pre-fix engine it was 24
for the index rule, not ≤9 — that rule was already the identifiable choke
point, and §3 understated it. The figures in §3 were recorded before defects
12–13 landed; the 1-minute source window also rolls, so setup counts drift a
little between runs.

### Status

Frequency is now 0.59 trades/day against ~2 in the source. The order-of-
magnitude selectivity is gone; the residual difference includes scope the
harness does not cover — it trades 09:35–11:30 only, while the source also
trades 07:00–09:30 pre-market (`PARAMETERS.md:71`), and it scans the top-5
gappers rather than the whole market.

P&L is −$541.58 on 10 trades. Per the ground rules in `README.md` this is not
a result: n=10, and the sign has now flipped three times across implementation
changes on identical data.

---

## Update — pre-flight before deciding on paid data

Two scope gaps were named in §"Status" as the difference between the harness
(0.59 trades/day) and the source (~2/day). Both were tested.

### Pre-market window: blocked by the data, not by the code

`PARAMETERS.md:71` puts the session start at 07:00 ET with limit orders only,
and 38 corpus claims reference pre-market activity. Measured across the
watchlist symbols:

```
symbol-days with pre-market bars: 198
pre-market bars total: 20,848   with non-zero volume: 0 (0%)
bars at/after 07:00 ET: 11,108  (56 per symbol-day)
```

**Not one pre-market bar in 20,848 carries volume.** Price data exists; volume
does not. That makes three of the nine entry conditions unevaluable before
09:30 — VWAP cannot be computed without volume, the
`pullback_volume < impulse_volume` filter has no inputs, and relative volume
cannot be measured.

Trading the window anyway would mean running a 6-condition gate pre-market and
a 9-condition gate after the open, then adding the two trade counts together.
That produces a higher number with no defensible meaning, so it was not done.
The window remains unimplemented, blocked on a data source that carries
pre-market volume.

### Watchlist width: already saturated

`MAX_NAMES` (now `WATCH_NAMES`) capped each day's watchlist at 5. Raising it:

| Cap | Distinct symbols | Trades | P&L |
|---:|---:|---:|---:|
| 5 | 47 | 10 | −$541.58 |
| 10 | 55 | 12 | −$332.02 |
| 20 | 55 | 12 | −$332.02 |

10 and 20 are identical, because the cap was never the binding constraint —
the five-pillar filter is. Names qualifying per day across the 17 sessions:

```
9, 8, 7, 6, 6, 5, 5, 4, 3, 3, 3, 3, 2, 2, 2, 2, 1   (mean 4.2/day)
```

Only 7 of 17 days ever reached the old cap of 5. The market did not offer more
qualifying names in this window; widening recovers 8 extra symbol-days and 2
extra trades, and there is nothing further to recover.

Look-ahead audit passes at every cut-off with the wider watchlist.

### Where that leaves the frequency gap

| | Trades/day |
|---|---:|
| Before the last two defect fixes | 0.18 |
| After them | 0.59 |
| After widening the watchlist | **0.71** |
| Source | ~2 |

The order-of-magnitude selectivity is gone. The remaining ~3x is not reachable
on this data: the largest single component is the pre-market session, which is
unusable for want of volume, and the rest would need a market-wide scanner
rather than a 2,486-symbol pool.

**This was the pre-flight test for whether paid data is worth buying.** It
answers yes on the specific ground that the missing frequency is a data
limitation rather than a detector defect — the widening experiment shows the
detector is no longer the constraint on candidate supply.

### Efficiency note

1-minute bars are now cached to `data/bars_cache/` (one file per symbol, ISO
timestamps, atomic writes). A run went from 20.3s to 1.4s with identical
output. `NO_CACHE=1` bypasses it. Yahoo's 1-minute history is a rolling ~30-day
window, so the cache will age out of usefulness once these dates fall outside
it — it is a run-to-run accelerator, not an archive.
