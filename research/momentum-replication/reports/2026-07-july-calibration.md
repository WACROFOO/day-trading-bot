# July calibration — the engine measured against his actual trades

**Status:** first external measurement in this project. Every earlier report
scored the engine against itself.

## What made it possible

The channel index carries synthetic dates below year granularity, so every
engine-vs-trader comparison so far rested on an inferred day mapping. A
per-video metadata call returns the true `upload_date`. 68 of 73 videos
returned one (5 hit YouTube's bot check); 36 are July uploads with transcripts,
and 28 map onto a session the bar data covers.

| | |
|---|---|
| bar data | 2026-07-09 .. 2026-07-31, 17 sessions |
| July videos with real dates + transcripts | 36 |
| mapped onto a covered session | 28 |
| before the bar data starts (07-01..07-08) | 8 |
| sessions carrying at least one video | 14 of 17 |
| session-ticker pairs named | 61 |

Session mapping is by publication convention, never by which fits better: a
recap is posted after the close, so a weekday upload is that session and a
weekend upload is the Friday before. `Watch List for MONDAY` videos are
previews and map **forward**.

## The five levels

Of every ticker a recap names, how far does the engine get? Levels 4 and 5 are
evaluated for **every** named ticker with bar data, not only ones that reached a
watchlist — otherwise a scanner miss would hide a detector miss behind it.

| level | count | of named |
|---|---:|---:|
| named in a recap | 81 | 100% |
| in the candidate pool | 63 | 78% |
| scanned that session | 61 | 75% |
| **passed the five pillars** | **25** | **31%** |
| detector found a setup | 61 | 75% |
| **the engine would have traded it** | **3** | **4%** |

The 18-point gap at level 1 is caption noise, not universe misses: 18 tokens
never resolved to a symbol. Of the 63 that did, **every one was in the pool**
and 61 were scanned. Widening the universe would fix nothing.

Two levels collapse, and neither is the part that had absorbed the most work:

- **the scanner** drops 3 of every 5 names he traded
- **the entry rules** drop 58 of the 61 that reach them
- **the detector is not the bottleneck** — it finds structure on 61 of 63

## Why the scanner drops them

`diagnostics/pillars.py` re-runs the scanner's own criteria over those 61
pairs and charges each to the **first** one that fails.

| first criterion to fail | pairs | % |
|---|---:|---:|
| gap >= 10% | 21 | 34% |
| rate_of_change <= 0 at 09:35 | 10 | 16% |
| *passed everything* | 10 | 16% |
| open >= $2.00 | 6 | 10% |
| gap <= 200% (split artifact guard) | 4 | 7% |
| open <= $20 | 4 | 7% |
| float <= 20M | 1 | 2% |
| ranked outside the top 5 by gap | 1 | 2% |
| no daily bar / inside a split buffer | 4 | 7% |

Charged unconditionally rather than first-fail, the `$2.00` floor blocks 12 of
the 61 — and `PARAMETERS.md:20` records `1.00 also stated` in the same row, so
it was never a settled number. Measured against the recap labels
(`diagnostics/sweep.py`):

| price_min | names/day | his names on watchlist | of those, ones the pillars accept |
|---:|---:|---:|---:|
| 2.00 | 5 | 20 (33%) | 3 (23%) |
| 2.00 | 10 | 21 (34%) | 4 (31%) |
| **1.00** | **5** | **23 (38%)** | **6 (46%)** |
| 1.00 | 10 | 24 (39%) | 7 (54%) |

The floor is the dominant lever; the top-N cutoff barely matters. **But
lowering it produced no additional trades** — 61 watchlist symbols instead of
47, same 2 trades, same P&L. Whatever is binding sits downstream.

### The 21 that never gapped

`gap >= 10%` measures the open against the previous close: a **pre-market**
test. Only 6 of those 21 rose 10%+ from the open intraday, so this is not
mostly a scanner-timing problem — most are names discussed in a recap without
being traded that session. Which is the honest caveat on this whole study:
**"named in a recap" is not "traded that session."** Recaps review prior days
and preview watchlists. The 61 is an upper bound on his trades, so every
recall percentage here is a floor.

## What actually binds: the entry rules

`diagnostics/lost.py` replays each accepted pair alone, so the daily trade
limit cannot bind. Rejections across all of them:

| reason | count |
|---|---:|
| **target < 2:1** | **66** |
| MACD histogram > 0 | 52 |
| price > 9 EMA | 43 |
| pullback index <= 2 | 38 |
| support confluence >= 2 | 24 |
| price > VWAP | 24 |
| pullback_volume < impulse_volume | 17 |
| stop tighter than spread | 16 |
| not resumed lower after a halt | 11 |

### `min_reward_risk` is being read as something the corpus never says

`min_reward_risk >= 2.0` (`PARAMETERS.md:177`, n=37) is implemented as a
**pre-entry veto**. Every citation behind it is retrospective and aggregate:

- *"~2:1 profit-to-loss ratio **achieved**"* — `Wsq8zdtCcis` [02:58]
- *"Profit-loss ratio **this week**: 46:1"* — `8eLtork_M50` [04:26]
- *"Profit/loss ratio **for month**"* — `hLtPtEVBBBQ` [14:34]
- *"$500 **average** winners, 61% accuracy"* — `bvy1pyzTrG4` [00:56]
- *"Trade 2:1 minimum. **If accuracy around 65%**, this ratio ensures
  profitability"* — `4t3GDiAXW18` [40:07]

`PARAMETERS.md` §9 uses it the same way — `avg_win`/`avg_loss` inside an
expectancy formula. A ratio of averages is produced by the **exit** plan, not
by refusing entries. It also collides with the setup it filters: a
micro-pullback enters just under the high of day, so the nearest objective is
cents away while the stop is the depth of the dip. Requiring 2× of that
rejects the entry the strategy is built on.

**Removing the veto is not the fix either.** `RR_FILTER=0`, 17 sessions:

| | trades | winners | total | expectancy | realised P/L ratio |
|---|---:|---:|---:|---:|---:|
| veto ON (current) | 2 | 1 (50%) | +$357.54 | +0.89R | 2.79:1 |
| veto OFF | 11 | 3 (27%) | −$601.65 | −0.27R | 1.52:1 |

Frequency rises 5×, expectancy goes negative. The reading is right and the
consequence is that **the exit plan has to deliver the 2:1 the entry veto was
faking**. Target 1 is currently the *nearest* structural objective; when that
sits under 2R, half the position books a sub-1R gain and the rest goes to
breakeven. That is the next thing to fix, and it is a target question, not an
entry question.

## A look-ahead defect, found here, that was producing the profit

The forced close of a position still open at the 11:30 cutoff read
`sorted(bars)[-1]` — **the last bar of the session, 15:59** — and stamped it
`11:29`. The engine was pricing exits four and a half hours after it was
allowed to look.

It was not marginal. It was the largest number in the study:

| trade | with the bug | after the fix |
|---|---:|---:|
| EHGO 2026-07-13 (flat at 11:30) | −$1,275.68 (−6.38R) | −$0.00 |
| ADVB 2026-07-22 (the biggest winner) | +$833.28 (+4.17R) | +$557.52 (+2.79R) |
| **17-day total, veto ON** | **+$633.30** | **+$357.54** |
| 17-day total, veto OFF | −$1,601.57 | −$601.65 |

The previously reported *"week of 07-20: +8.33% on the account"* was this
trade. That week's real figure is +5.58%.

Fixed in `engine/engine20.py`: flatten at the last bar **before** `HARD_STOP`,
at that bar's close, never worse than the resting stop, stamped with the real
minute.

## And one in the measurement itself

The first version of `calibrate.py` re-derived the entry gate as "every
`GATE_CONDITION` holds" and so silently omitted the 2:1 and spread tests
`run_day` applies on top. It reported **14** pairs the engine would trade where
the engine trades **3**. It now calls `run_day` directly. Anything that
restates the engine will drift from it.

## Bottom line

Three findings, in order of how much they change:

1. **The universe and the detector are exonerated.** Every ticker he named that
   resolved to a symbol was in the pool and scanned, and the detector found
   structure on 97% of them. Work spent there was spent in the wrong place.
2. **The scanner and the entry rules are where the strategy is being lost**,
   and the two largest single causes are both parameters the corpus does not
   settle: the `$2.00` price floor (`1.00 also stated`) and `min_reward_risk`
   read as an entry veto rather than a realised ratio.
3. **The engine still has no measured edge.** 2 trades at +0.89R or 11 at
   −0.27R over 17 sessions is not a result either way. What this study bought
   is that the next change can be aimed, and checked against 61 labelled pairs
   instead of against itself.

## Reproduce

```bash
cd research/momentum-replication
python diagnostics/calibrate.py     # the five levels
python diagnostics/pillars.py       # which criterion rejects them
python diagnostics/sweep.py         # price floor and top-N, against the labels
python diagnostics/intraday.py      # were the non-gappers moving intraday?
python diagnostics/lost.py          # gate said yes, engine still passed
python diagnostics/trades.py        # the 17-day run, trade by trade
RR_FILTER=0 python diagnostics/trades.py
PRICE_MIN=1.0 python diagnostics/calibrate.py
```
