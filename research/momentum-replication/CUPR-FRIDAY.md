# CUPR, 2026-07-31 — full extraction, mock trading, and what each loss teaches

```bash
python pipeline/cupr_friday.py    # extract + find setups
python pipeline/cupr_mock.py      # mock-trade them all, diagnose losses
```

## Candles extracted

| Frame | Pre | Regular | After | Total | With volume |
|---|---:|---:|---:|---:|---:|
| 1m | 9 | 172 | 60 | 241 | 171 |
| 2m | 8 | 122 | 49 | 179 | 122 |
| 5m | 7 | 64 | 34 | 105 | 64 |
| **10s** | — | — | — | — | **unavailable** |

10-second bars could not be obtained: Yahoo rejects every sub-minute interval,
Nasdaq's `realtime-trades` returns zero rows for a past date, and
`extended-trading` is a live snapshot rather than history. No keyless
trade-level source is reachable. Pre-market bars exist but carry **zero
volume**, consistent with the API-wide limitation.

## The day

| | |
|---|---|
| Pre-market | 2.93 → 3.27 |
| Open | **3.28** (09:30) |
| High of day | **5.77** (10:26) — **+75.9%** from open |
| Low of day | 2.50 (11:42) |
| Close | 2.93 — **−10.7%** from open |
| After-hours | 2.92 → 2.93 |

Minutes 10:16–10:24 have no bars at all — a halt, immediately before the spike
to 5.77 on 195,821 shares.

---

## Finding 1 — the 2-bar minimum blinds the detector to the fastest move

Every dip during the run to the high was **exactly one bar long** (dip runs:
`[1, 1]`). The detector requires two.

| Minimum dip | Setups on the day | Setups during the 09:30–10:30 run |
|---:|---:|---:|
| 2 bars | 13 | 3 |
| 1 bar | 21 | 5 |

`PLAYBOOK.md:99` does say "2–3 candles" — but that reading assumes the
1-minute chart is the finest one available, and it is not. The source also
reads a **10-second chart**, on which a 1-minute pause *is* a 2–3 candle
pullback. The 2-bar minimum is therefore a 1-minute artifact, not the rule, and
it removes setups precisely where the move is fastest.

This is the concrete cost of the missing 10-second data: not fill precision, but
whole setups.

---

## Mock trades — all 21 setups taken, gate ignored

Taking gate-rejected setups is what the strategy forbids. It was done here to
see what the gate was right about. **No setup scored 6/6**, so every trade below
was one the strategy would have declined.

21 taken, 5 winners, **+$18.64** total.

## Finding 2 — the gate gradient is monotonic

| Gate score | n | Winners | Total | Mean |
|---|---:|---:|---:|---:|
| 5 of 6 | 5 | 2 | **+$45.59** | **+1.54R** |
| 4 of 6 | 7 | 1 | −$25.99 | +0.38R |
| 3 or fewer | 9 | 2 | −$0.96 | −0.13R |

Outcome improves monotonically with gate score. That is exactly the
falsification test `PARAMETERS.md` §12 step 3 prescribes, and it **passes** —
the first evidence in this project that the entry conditions capture setup
quality rather than merely reducing trade count. n=21 on one symbol on one day,
so it is weak evidence, but it points the right way and it is the first time it
has.

---

## What each loss teaches

16 losses. Grouped by cause rather than listed one by one.

### Lesson 1 — VWAP is the single most protective rule

**13 of 16 losses failed `price > VWAP`.** Almost every losing trade was taken
below VWAP. Nothing else in the gate comes close as a predictor of a loss on
this day. Of the three losses that were above VWAP, two failed on volume and
one on MACD.

### Lesson 2 — a stop inside the spread is not a stop

Five losses had a stop narrower than the estimated spread — 09:51 ($0.020 stop
vs $0.050 spread), 10:58 ($0.015 vs $0.078), 12:06, 13:39 ($0.001 vs $0.010),
14:09 ($0.002 vs $0.010). These cannot survive; noise alone closes them. The
spread floor (`PARAMETERS.md:161`) exists for exactly this and correctly
rejected all five.

### Lesson 3 — most losses died instantly

11 of 16 were stopped within **1–2 bars**. Entering into a dip that had not
finished, on a stock no longer trending, gives the trade no room at all.

### Lesson 4 — the target logic breaks after the stock rolls over

Every trade after 10:55 shows `T1 = 5.77` — the high of day. Once CUPR had
collapsed to the $2.80s, a target at 5.77 is unreachable, yet it satisfies the
2:1 filter trivially because it is so far away. **The reward:risk check is
passed by an impossible target.**

The documented target is a *retest* of the high of day, which presupposes the
stock is still near it. Nothing currently enforces that. This is the same
concern the removed `front side of the move` condition was groping at — it was
correctly removed from the gate as invented, but the underlying problem is real
and lives in the target, not the gate.

### Lesson 5 — the winners came from the run, the losses from the fade

The five winners cluster 09:48–10:14 and 11:46/15:40. Everything taken between
10:55 and 14:09 — after the high, on the way down — lost. The strategy's own
prime window (09:35–10:30) and its VWAP rule both point at the same thing, and
this day is a clean illustration of why.

---

## What this changes

Nothing in the engine yet. Three candidates fall out, in order of evidence:

1. **`MIN_DIP_BARS` is a 1-minute artifact.** Exposed as a constant in
   `engine/sim.py` so it can be tested rather than assumed. Properly resolving
   it needs 10-second data.
2. **The target must be reachable.** A high-of-day target should require the
   price to still be near that high, or the 2:1 filter is decorative.
3. **The gate earns its keep.** The monotonic gradient is the first positive
   result for it; worth re-testing across the 17-day window before relying on
   it.

Weak-evidence warning stands throughout: one symbol, one session, 21 mock
trades, none of which the strategy would actually have taken.
