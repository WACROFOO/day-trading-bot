# 2026-07-31, start to finish, multi-timeframe

```bash
python pipeline/friday.py          # cached bars
NO_CACHE=1 python pipeline/friday.py
```

**Result: 15 setups, 0 passed the gate, 0 trades.** Four setups scored 8/9 —
each failed by exactly one condition.

---

## Timeframes: what was obtainable

The corpus uses three, for three different jobs:

| Frame | Job | Source |
|---|---|---|
| 5-minute | setup context | `BFH-0N8S-IA` [08:04] |
| 1-minute | the entry trigger | `PARAMETERS.md:144` |
| 10-second | "zoom-in for micro pullback patterns" | `HMaTY5-x2N0` [11:30] |

**10-second bars could not be obtained.** Yahoo rejects every sub-minute
interval outright:

```
1s, 5s, 10s, 15s, 30s  ->  "not supported. Valid intervals: [1m, 2m, 5m, 15m, ...]"
1m -> 961 bars   2m -> 481   5m -> 193
```

Building them needs trade-level data, which no keyless source reachable here
provides. Per the corpus the 10-second chart is a zoom for placing an entry
inside a 1-minute candle rather than a separate signal generator, so its
absence costs fill precision, not setups. **But see the spread finding below —
on this day that distinction is less comfortable than it sounds.**

Fetched for the day: 1m, 2m and 5m, pre-market and session.

| Sym | 1m pre | 1m session | 2m session | 5m session |
|---|---:|---:|---:|---:|
| CUPR | 9 | 232 | 171 | 98 |
| TCX | 40 | 395 | 250 | 118 |

---

## The chain

| Stage | Result |
|---|---|
| Candidate pool | 2,486 symbols (price + market-cap filtered) |
| Pre-market records for the day | 1,542 |
| Passing all five pillars | **2** |

| Sym | Gap | Open | RVOL (first 5 min) |
|---|---:|---:|---:|
| CUPR | +23.3% | $3.28 | 45.2× |
| TCX | +14.4% | $11.10 | 17.6× |

---

## Every setup the day produced

| Sym | Time | Leg low | Leg high | Dip | Bars | # | Score | Failed on |
|---|---|---:|---:|---:|---:|---:|---:|---|
| CUPR | 09:40 | 3.27 | 3.57 | 3.36 | 2 | 1 | 6/9 | volume; 50%-of-leg |
| CUPR | 09:48 | 3.20 | 3.44 | 3.36 | 2 | 1 | 7/9 | VWAP; MACD |
| CUPR | 10:05 | 3.36 | 3.49 | 3.38 | 2 | 2 | 7/9 | confluence; MACD |
| CUPR | 10:55 | 3.02 | 3.59 | 3.25 | 4 | 1 | 5/9 | front side; confluence |
| CUPR | 11:14 | 3.10 | 3.26 | 3.19 | 2 | 1 | 6/9 | front side; confluence |
| **TCX** | **09:50** | 11.10 | 13.57 | 12.87 | 2 | 1 | **8/9** | **support confluence** |
| **TCX** | **09:56** | 12.87 | 14.27 | 13.53 | 3 | 2 | **8/9** | **pullback volume** |
| TCX | 10:01 | 13.53 | 14.27 | 13.68 | 2 | 3 | 7/9 | index; MACD |
| TCX | 10:04 | 13.68 | 14.27 | 13.27 | 2 | 4 | 7/9 | index; MACD |
| TCX | 10:15 | 13.27 | 14.27 | 13.51 | 3 | 5 | 6/9 | volume; index |
| TCX | 10:22 | 13.51 | 14.27 | 13.34 | 3 | 6 | 5/9 | index; confluence |
| **TCX** | **10:33** | 13.34 | 14.27 | 13.67 | 3 | 7 | **8/9** | **index (#7)** |
| TCX | 10:57 | 14.18 | 14.75 | 14.35 | 4 | 1 | 7/9 | 50%-of-leg; MACD |
| **TCX** | **11:16** | 14.35 | 14.98 | 14.38 | 2 | 2 | **8/9** | **MACD** |
| TCX | 11:25 | 14.38 | 14.98 | 14.64 | 2 | 3 | 6/9 | volume; index |

Aggregate rejections: MACD 10, stop tighter than spread 8, index 6, pullback
volume 4, confluence 4, 2:1 target 3, VWAP 3, 50%-of-leg 2, front side 2,
9 EMA 1.

---

## What actually happened

TCX opened $11.10 and closed the session **+36.4%**. The engine found 10 setups
on it, four scoring 8/9, and took none. The first — 09:50, first pullback of
the day, leg $11.10 → $13.57, a clean 2-candle dip to $12.87 — failed on
support confluence alone.

CUPR opened $3.28, ran to $5.77, and closed at $2.93.

---

## The finding that matters: structure below the noise floor

**8 of 15 setups were rejected because the stop was tighter than the estimated
spread.** The stop is the distance from the trigger to the pullback low, so
this says the micro-pullback structure on these names is roughly one spread
wide at 1-minute granularity.

That reframes the missing 10-second data. It is not only about fill precision:
at this granularity the pullback low cannot be located finely enough to sit a
stop against it. The source uses the 10-second chart precisely because the
structure is small — the zoom is not cosmetic.

The spread itself is estimated from the tightest quartile of 1-minute ranges,
because no quote data is available. A feed with real quotes would replace an
estimate with a measurement here, and it is the single input this day was most
sensitive to.

---

## Verification

A trade-level look-ahead audit is vacuous on a day with no trades, so setup
detection was audited instead — a setup detected before a cut-off must be
identical when later bars are absent.

```
cut-off   setups<cut   identical?
10:00              4   YES
10:30              9   YES
11:00             12   YES
11:30             15   YES
full              15   YES
PASS - setup detection is forward-only.
```

---

## The 5-minute frame

Fetched and available, deliberately **not** wired into the entry gate. Its
corpus support is a single claim (n=1); adding a tenth hard condition on that
basis would be inventing a rule rather than restoring one. `friday.py` reports
the 5-minute state at each entry and measures what a 5-minute trend filter
would have changed — on this day there were no trades, so it changed nothing,
and the question stays open rather than being answered by assumption.

---

## Honest reading

One session, two qualifying names, zero trades. That is not evidence the
strategy is wrong; it is one day in which nothing cleared a 9-condition gate.

The informative part is the shape of the near-misses. Four setups at 8/9, on
the name that ran +36%, failing on four *different* conditions — support
confluence, pullback volume, pullback index, MACD. No single rule is standing
in the way. That is the same pattern the 17-day leave-one-out showed, and it is
consistent with either a gate still slightly too strict or a genuinely
selective strategy having a quiet day. **One session cannot distinguish those
two, and this file does not claim to.**
