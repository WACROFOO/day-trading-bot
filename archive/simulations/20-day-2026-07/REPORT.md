# 17 trading days, 2026-07-09 → 2026-07-31

Forward-only replay of the playbook across a month, with the trade limit raised
from the playbook's 2 to **5** on request.

| | max_trades = 2 | **max_trades = 5** |
|---|---:|---:|
| Trading days | 17 | 17 |
| Trades taken | 12 | **14** |
| Total P&L | −$770.74 | **−$1,037.24** |
| Return on $10,000 | −7.7% | **−10.4%** |
| Win rate | 25.0% | **21.4%** |
| Profit factor | 0.34 | **0.28** |
| Expectancy / trade | −$64.23 | **−$74.09** |
| Max drawdown | −$850.72 | −$1,117.22 |
| Green / red days | 3 / 5 | 3 / 5 |

**Raising the limit to 5 made it worse by $266.50.** Both configurations lose;
the extra trades were −$266.50 in aggregate, because the marginal setups came
after the good ones were already taken.

---

## 17 days, not 20

Yahoo caps 1-minute history at ~30 days, and each day needs a prior session for
its baseline. July 6–8 fell outside usable range. This is 17 trading days.

---

## The data bug that had to be fixed first

The first pass produced watchlists like `FFAI +10,555%`, `GNPX +2,058%`,
`DFNS +12,555%`. Those are not moves.

Yahoo serves 1-minute data in 7-day windows, so a month needs five separate
requests — and **each response is adjusted independently**. When a reverse
split falls inside the month, a day's previous close came from a differently
adjusted response than its open, and the ratio between them was recorded as a
gap. The tell was that anomalies landed exactly on the window boundaries
(Jul 15, 22, 29), not scattered at random.

Every extreme "gap" was a reverse split: VIVK 15.03× (1:15), XPON 12.06×
(1:12), CIIT 9.98× (1:10), TRIB 25.6× (1:25), FFAI 106× (1:150 per Yahoo's
split calendar).

**This also invalidates the watchlist in the earlier single-day report.** FCUV,
which I reported as a +423% gapper and the biggest name of the day, was a 1:5
reverse split. Its intraday move was real, but it should never have been on the
watchlist. Corrected, Friday 2026-07-31 has only CUPR and TCX qualifying, and
neither produced a valid setup — the day is flat, not −$160.96.

**Fix:** gaps are now measured open-vs-previous-close inside a *single* daily
response, so both prices share one adjustment basis. Any symbol-day within 3
trading days of a split is dropped (110 symbols had splits in range), plus a
+200% sanity cap. Intraday execution still uses 1-minute bars, which are
internally consistent within a day — the stitching bug only ever corrupted
comparisons *across* days.

---

## Look-ahead audit

Every day truncated at successive cut-offs and re-run. Any trade entered before
a cut-off must return identical.

```
cut-off     entries<cut   match full run
10:00                 3              YES
10:30                10              YES
11:00                12              YES
11:30                14              YES
full                 14              YES
PASS - no decision changed when future bars were added.
```

---

## Per day (max_trades = 5)

| Day | Names | Setups | Passed | Trades | P&L | Cumulative | Stopped |
|---|---:|---:|---:|---:|---:|---:|---|
| 07-09 | 3 | 19 | 2 | 2 | **+79.98** | +79.98 | |
| 07-10 | 3 | 10 | 1 | 1 | −199.93 | −119.95 | |
| 07-13 | 5 | 54 | 3 | 3 | −383.12 | −503.07 | 3 losses in a row |
| 07-14 | 3 | 8 | 1 | 1 | +0.24 | −502.83 | |
| 07-15 | 2 | 5 | 2 | 2 | **+177.29** | −325.54 | |
| 07-16 | 4 | 38 | 1 | 1 | −91.81 | −417.35 | |
| 07-17 | 2 | 17 | 0 | 0 | 0.00 | −417.35 | |
| 07-20 | 3 | 22 | 3 | 3 | **−558.33** | −975.68 | 3 losses in a row |
| 07-21 | 1 | 11 | 0 | 0 | 0.00 | −975.68 | |
| 07-22 | 5 | 66 | 0 | 0 | 0.00 | −975.68 | |
| 07-23 | 5 | 48 | 1 | 1 | −61.56 | −1037.24 | |
| 07-24 | 5 | 34 | 0 | 0 | 0.00 | −1037.24 | |
| 07-27 | 5 | 47 | 0 | 0 | 0.00 | −1037.24 | |
| 07-28 | 5 | 27 | 0 | 0 | 0.00 | −1037.24 | |
| 07-29 | 5 | 17 | 0 | 0 | 0.00 | −1037.24 | |
| 07-30 | 2 | 3 | 0 | 0 | 0.00 | −1037.24 | |
| 07-31 | 2 | 28 | 0 | 0 | 0.00 | −1037.24 | |

**454 setups evaluated, 14 passed the gate (3.1%).** Nine of 17 days produced no
trade at all — the trade limit was never the binding constraint on 15 of them.

---

## The finding that matters: the 2:1 never happens

Realised R multiple on all 14 trades:

```
-1.00 -1.00 -1.00 -1.00 -1.00 -0.79 -0.60 -0.58 -0.38 -0.33 -0.28  +1.00 +1.00 +1.00
```

**Every winner made exactly +1.00R. Not one made more.** That is not
coincidence, it is the scale-out rule doing arithmetic:

1. Sell half at +2R → banks +1.0R
2. Move the stop to breakeven
3. The remaining half then stops at breakeven → +0.0R
4. **Total: +1.00R, every time**

So the strategy's headline "minimum 2:1" is never realised on a winning trade.
The actual payoff profile is:

| | Value |
|---|---:|
| Average winner | +1.00R |
| Average loser | −0.72R |
| **Break-even win rate needed** | **42.0%** |
| **Actual win rate** | **21.4%** |
| Expectancy | **−0.354R per trade** |

The whole edge argument rests on needing only ~33% accuracy at 2:1. But the
exit rules cap winners at 1R while losers run to −0.72R average, which pushes
the required accuracy to 42% — and the observed rate is half that.

**Losers are smaller than 1R** (−0.72R average) because the break signals
(new low, lost VWAP, MACD negative) fire before the stop on 6 of 11 losses.
Those rules work: they cut losses early. They also cut winners early, and the
breakeven-stop move guarantees the runner contributes nothing.

---

## Why 440 setups were rejected

| Reason | Count |
|---|---:|
| support confluence ≥ 2 | 392 |
| pullback index ≤ 2 | 318 |
| MACD histogram > 0 | 199 |
| stop > $0.20 | 115 |
| pullback volume < impulse volume | 114 |
| price > 9 EMA | 112 |
| pullback 2–3 candles | 20 |

The stop-cap conflict flagged in the single-day report is real but **smaller
than it looked** — 115 of 440 rejections, not the dominant cause. Over a month
the binding constraints are confluence and the pullback counter. Both the
$2–20 price band and the counter reset on losing VWAP mean a trending stock
exhausts its two pullbacks in the first half hour and is then locked out.

---

## Honest limits

1. **17 days, 14 trades.** Far too few to be significant. A −0.354R expectancy
   with n=14 has a confidence interval that comfortably includes zero.
2. **The news pillar was never verified** — all watchlists are 4/5 setups,
   which the playbook itself calls the documented mistake.
3. **Level 2 conditions could not be evaluated at all.** `no_seller_wall` and
   `tape_green` are skipped, so this gate is weaker than the real one.
4. **Float is a market-cap proxy** from a current snapshot, not actual float.
5. **Fills assume $0.02 slippage.** On the observed stops (4–19 cents) that is
   10–50% of the risk budget. Real slippage on these names is likely worse,
   which would make the result worse, not better.
6. **The pullback definition is mine.** "Impulse", "pullback" and the index
   reset on losing VWAP are mechanical choices. Other readings give other
   trades.
7. **Selection still uses a current price/market-cap snapshot** to build the
   candidate pool, with deliberately wide bands to limit the effect.

---

## What I would test next

The 1R cap is the highest-value thing to falsify, because it is a rule change
rather than a parameter tweak:

- Move the stop to breakeven only *after* the second scale, not the first.
- Or scale at +1R and let the remainder run against a trailing stop rather than
  breakeven.

Either would let a winner exceed 1R. With the current rules no winner ever can,
and no win rate available to this strategy makes 1.00R against −0.72R
profitable at 21%.

Reproduce:

```bash
python simulations/20-day-2026-07/scan20.py        # pre-market stats, 2,486 symbols
python simulations/20-day-2026-07/fetch_daily.py   # consistent daily bars
python simulations/20-day-2026-07/run20b.py 2 5    # corrected run, both limits
python simulations/20-day-2026-07/analyze20.py 2 5 # tables above
python simulations/20-day-2026-07/audit20.py       # prove no look-ahead
```
