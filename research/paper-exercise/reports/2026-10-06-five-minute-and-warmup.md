# The green run on the 5-minute chart (E1) and the MACD warm-up (B30) — 2026-10-06

```
DATA   · Alpaca SIP 1-minute bars, 04:00-16:00 ET, pre-market volume included (data/cache/history, gitignored)
       · 2,608 sessions 2016-02-03 → 2026-08-21 · 24,831 gapper symbol-days (open $2-20, gap ≥ 10 %, reverse splits dropped)
RULES  · preregistered: research/edge-hunt/PREREGISTRATION.md, addendum 2026-10-06b, commit 8434ce2,
         committed with scripts/five_minute.py BEFORE its first run
ENGINE · scripts/rules_audit.py: B's plans, A10 fill (cap +0.3 %), A3 trail 1 R, flat 11:30, costs "live"
         ($40 risk, $2,000 cap, spread proxy + 1 ¢ a side), one position, B's daily limits; bar readings A and C
OUTPUT · five_minute_output.txt (the decision) · five_minute_check_output.txt (a diagnostic written AFTER the
         run, deciding nothing) · five_minute_results.json
! 2024-2026 has been read for other rules many times; it is a fresh holdout for these two only.
! The universe is chosen on the 09:30 gap: pre-market entries carry hindsight. Regular hours are shown apart.
```

Paper only. No claim of edge.

## 1 · The question

The owner, 2026-10-06: *"adapt handling the green upternding 1 min bars without a proper pullback in the one minute chart."*
The desk's detector needs a red 1-minute candle, so a straight green run arms nothing. The method's answer is the 5-minute chart:
*"the one minute is fine what's the first five minute candle to make a new high it'll be over 65 so your entry is 65 your stop is the low at 60"* (`Xdw5azEqs6o` [00:12:38]).
His own warning goes with it: names that go *"from you know 7 to 14 on without a five minute pullback"* and then *"it just Fades back down"* (`t-_T5MTl1FI` [00:34:09]).

**E1** buys the first 5-minute candle to make a new high, in the owner's case only. That case is a run of ≥ 4 green 1-minute candles to a new high of day inside the 5-minute impulse.
- The setup is the detector's own rules on clock-aligned 5-minute candles.
- The stop-limit rests during the candle after each pullback candle, at its high + 1 ¢. The break is bought intrabar.
- The stop sits at the pullback low − 1 ¢.
- The live gates are read at each placement.

**B30** allows a B plan whose only red gate is a MACD the desk cannot compute yet (fewer than 35 one-minute bars since 04:00).

## 2 · What was considered, and what each rule refused

```
291,291 E1 placements · 32,173 in the owner's case · 438 pass every rule · 179 trades (reading A)
```

| first rule that refused it | owner's-case placements |
|---|---|
| outside 07:00-11:20 | 11,075 |
| price outside $2-20 | 647 |
| below VWAP | 4,930 |
| below the 9 EMA | 8,841 |
| MACD not positive and above signal | 4,702 |
| pullback volume not lighter | 1,194 |
| more than 25 % off the high | 0 |
| stop < 2 % of price (A13) | 244 |
| stop < 4× the spread (A6) | 102 |
| **pass every rule** | **438** |

A placement is one order on one pullback candle; a setup can re-place up to four times. One position at a time, the daily limits and the fill leave 179 trades (`five_minute_check_output.txt` §4).

## 3 · E1 — fails at stage 1, both readings

Net R a trade after costs. A trade's own costs decide: E1's stops are wide (median 4.95 % on train), so its costs run 0.265 R a trade on train against 0.389 R on B's (gross minus net, same output).

| period | reading | n | gross | net | regular hours, net | lower bound (net) |
|---|---|---|---|---|---|---|
| train 2016-2022 | A | 96 | −0.028 | **−0.293** | −0.170 (n 66) | −0.464 |
| | C | 96 | −0.032 | **−0.297** | −0.177 (n 66) | −0.469 |
| gate 2023 | A / C | 14 | +0.191 | −0.095 | −0.061 (n 8) | — |
| holdout 2024-2026 | A | 69 | +0.277 | +0.042 | −0.109 (n 40) | −0.205 |
| | C | 67 | +0.309 | +0.073 | −0.061 (n 38) | −0.180 |

Stage 1 needed: n ≥ 200, net > 0 with its lower bound > 0, regular hours > 0, and a beat over random. **Every condition fails, in both readings.** Stage 2 fails too.

The holdout's positive net rests on the pre-market trades: regular hours are negative there as well. On 67-69 trades its lower bound is −0.18 to −0.21.

**Reported, deciding nothing** (`five_minute_output.txt`):
- **E1 without the owner's-case condition:** train net −0.266 (A, n 433), holdout −0.317.
- **VWAP as the only chart gate:** train −0.366 (n 858), holdout −0.281.
- **B ∪ E1 against B:** holdout −0.472 vs −0.477 (A) and −0.466 vs −0.475 (C). The day-paired lower bound is −0.010 / −0.005: adding E1 does not help.
- **By 5-minute pullback count:** 1st −0.215 (n 13), 2nd −0.152 (n 35), 3rd+ −0.141 (n 131).

### Why it fails — the move is over before the entry

The random-entry baseline read **+0.405 R gross** against E1's −0.028. That was checked for a defect before being reported (`five_minute_check_output.txt`, written after the run):

| random entries, gross R, reading C | pre-market | 09:30-10:30 | 10:30-11:30 |
|---|---|---|---|
| any symbol-day of the 2016-2022 universe (800 drawn), stop 5 % | +0.140 | −0.079 | −0.062 |
| the windows of B's trades | +0.286 | +0.170 | +0.212 |
| the windows of E1's trades | +0.435 | +0.370 | +0.573 |
| **E1's windows, BEFORE the E1 order** | **+0.875** | **+0.750** | **+1.254** |
| E1 itself | −0.266 | +0.071 | +0.101 |

With no conditioning, being long in regular hours loses. The same windows read positive around any setup, because the stock was moving there. E1's 5-minute pullback comes after the run: being long earlier in the same window earned +0.75 to +1.25 R, while the first 5-minute candle to make a new high earned about nothing.
**The green run is the profit, and a 5-minute pullback entry buys after it.** This agrees with his warning above, and with the 2026-10-05 finding that the 10-second entry "comes 1–3 minutes later and higher" than his (`2026-10-05-ross-recent-and-execution/README.md` §2).

## 4 · B30 — passes the preregistered rule; the trades it adds lose

4,577 B plans armed inside the warm-up had MACD as their only red gate among price, VWAP, 9 EMA, MACD and volume: pre-market 2,734, 09:30-10:30 1,789, 10:30-11:30 54. The stop floor, the spread rule, the window and one position still apply to them in B30.

| reading | period | B: n · net · total | B30: n · net · total |
|---|---|---|---|
| A | train 2016-2023 | 2,246 · −0.411 · −923.6 R | 2,520 · −0.387 · **−975.1 R** |
| | holdout | 1,492 · −0.477 · −712.2 R | 1,587 · −0.451 · **−715.8 R** |
| C | train 2016-2023 | 2,231 · −0.436 · −973.0 R | 2,506 · −0.407 · **−1,020.4 R** |
| | holdout | 1,479 · −0.475 · −701.9 R | 1,573 · −0.444 · −698.6 R |

**The rule passes in both readings:**
- the mean is better in train and in the holdout, and in 2 of 3 years;
- there are at least 200 holdout trades;
- the paired lower bound is +0.003 (A) and +0.007 (C).

**What it adds: 519 trades (A) / 514 (C), gross +0.054 / +0.048 but net −0.262 / −0.268 each.** The mean per trade rose because the added trades lose less than B's average, not because they pay. Total R is worse in three of the four cells. A rule judged on mean R per trade admits exactly this, and the preregistration did not guard against it.

## 5 · What was done with it

| | before | now |
|---|---|---|
| a straight green 1-minute run | the card read "no plan — no confirmed first pullback yet" | the card and `scripts/watch.py` read **EXTENDED**; once a 5-minute candle pauses, **5-MIN PB** with its trigger and stop. Display only, no order (`src/momentum_platform/five_minute.py`, ledger table `five_minute_states`) |
| E1 as an order | — | never (it failed stage 1) |
| a plan inside the MACD warm-up | refused, "MACD unknown" | still refused. The reason now names the warm-up ("the MACD needs 35 one-minute bars and the desk held N (warm-up; B30 candidate, OFF)") so `exercise.py missed` can score these plans prospectively. `runner.B30_WARMUP_MACD = False` |

## 6 · What this could not check

- Five-minute candles were built from 1-minute bars. A fill and a stop inside the same minute are ordered by the two bar readings, not by the tape.
- The desk's MACD starts at 04:00. His platform carries earlier days' bars. The cache holds no previous-day bars for most names, so B30 is "allow when unknown", not "compute it as he does".
- No float, no news, no halts, no Level 2. The pillar count does not run on history.
- 179 E1 trades in ten years: the owner's case is rare once the live gates apply. The no-condition and VWAP-only variants (433 and 858 train trades) say the same thing.
- The random-baseline diagnostic was written after the result was seen. It decides nothing; it explains.

## 7 · Verdict

**The 5-minute answer to a green 1-minute run does not pay on ten years of this universe:** train net −0.29 R a trade, 0.43 R gross below random entries in the same windows (lower bound −0.61). The move it waits out is the move that paid.
- The desk now says EXTENDED instead of nothing; that is all it does.
- **B30 is handed to the owner OFF.** It passes the per-trade rule, but the trades the warm-up blind spot hides lose 0.26 R each after costs.

**My call, scored:** the 2026-10-05 summary proposed "handle green runs the way Ross says to: wait for the first 5-minute candle to make a new high" as the adaptation. **Refuted on the train years in both readings.**
