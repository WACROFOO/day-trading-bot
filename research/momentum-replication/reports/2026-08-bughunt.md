# Bug hunt: four mechanical defects, one of which was strangling the engine

A line-by-line re-read of `sim.py` and `engine20.py`, with every suspicion
quantified against the 17 sessions before being called a bug. Four survived.
Numbered continuing `HISTORY.md`.

## 17. A missing minute was treated as a halt, and the veto it armed was sticky

The worst of the four. Two defects compounding:

**False positives.** Any ≥5-minute print gap was a "halt". On a quiet name,
minutes with no prints are routine — CUPR 2026-07-31 shows **eighteen** such
gaps through one afternoon with **159–2,744 shares** trading around them. The
real halts in the same window (ZCMD and ADVB on 07-22, both genuinely halted
repeatedly) have **63k–3.1M shares** on the adjacent bars. Two orders of
magnitude of clean separation, because a volatility halt is *triggered by*
heavy one-directional trading. The detector now requires halt-scale volume
around the gap (`HALT_MIN_ADJ_VOLUME`, default 25k, mid-band).

**Stickiness.** When the bar after a gap closed lower, `halted_down` was set —
and stayed set until some *later* gap happened to close higher. The corpus
rule ("stock halted going down typically resumes lower", `FN-uqfbEVKw`
[19:03]) is a caution about the **resumption**, not a verdict on the session.
One quiet stretch that drifted a cent could veto every setup for hours. The
flag now clears when the stock prints a new session high — the direct
falsification of "resumed lower".

**Measured effect.** 16 of ~60 watchlist name-days carried fake-halt gaps.
`'not resumed lower after a halt'` — previously 11 rejections in the
gate-passing replay, 9 on JZXN alone — has vanished from the rejection table.
And the July calibration's final level moved more than everything else this
project has changed combined:

| of every ticker he named | before | after |
|---|---:|---:|
| detector found a setup | 75% | 74% |
| **the engine would have traded it** | **3 of 81 (4%)** | **18 of 81 (22%)** |

Six times closer to his actual behaviour, on the labelled set, from one fix.

## 18. Impulse volume contained the pullback it was compared against

`impulse_volume()` averaged `ind.bars[-12:]` — a window that **includes the
dip bars themselves** (and, early in the session, pre-market bars). So
`pullback_volume < impulse_volume` compared the dip partly to itself, and
marginal cases were decided by noise: ADVB 07-22 10:24 passed by **481
shares** (201,810 vs 202,291). Excluding the dip flips 12 of 171 setup
verdicts (8 fail→pass, 4 pass→fail). ADVB 10:24 — previously a booked winner —
now correctly fails: its dip traded as heavily as its impulse.

## 19. The entry bar was exempt from the stop

`sim.py`'s header promises *"intrabar ambiguity is always resolved against the
trader"*. Every bar honoured that except one: the entry bar. A position opened
at minute T was first evaluated at T+1, so a trigger bar whose own low broke
the stop was silently held. BIYA 07-27 11:22 entered at $3.77 with the stop at
$3.70 on a bar whose low was **$3.66**. One of 13 trades in the sample — and it
booked roughly the same loss a bar later, so the P&L effect here was nil — but
a contract violation is a contract violation. The entry bar is now tested, and
stop fills on any bar that *opens* below the stop now fill at the open (zero
instances in the sample; the optimism existed, the data never exercised it).

## 20. Dead code carrying already-fixed defects

- `sim.simulate()` — the original single-day runner. Nothing imported it, and
  it still contained defect #3 (`t1 = entry + 2R`) and defect #4 (the
  any-lower-low exit) — both "fixed in the current code" per HISTORY. A stale
  engine inside the engine's module is how fixed defects come back. Deleted.
- A second copy of the trigger logic in `PullbackTracker.update`, drifted from
  the real one (it built setups **without the halt flag**). Statically
  unreachable, dynamically confirmed: 0 of 1,362 setups. Deleted.

## What the run looks like now

| | trades | winners | total | expectancy | realised P/L |
|---|---:|---:|---:|---:|---:|
| before this hunt | 13 | 31% | −$588.90 | −0.26R | 1.32:1 |
| **after (veto off)** | **15** | **20%** | **−$852.85** | **−0.43R** | 1.87:1 |
| after (veto on) | 4 | 25% | +$334.05 | +0.00R | 7.48:1 |

The P&L got **worse**. That is the expected direction: defect 17 was
suppressing trades (so its fix admits more of the strategy's real, losing
entries), 18 was passing a marginal winner, and 19 was holding through a
touched stop. Every prior fix that made the number *better* deserved
suspicion; these make the measurement honest instead.

The excursion distributions that anchor `2026-08-target-and-entries.md` are
unchanged (412 setups vs 406, same medians), so its conclusions stand — the
entries are still late, and the resolution argument in
`2026-08-streams-roundup.md` §1 is untouched.

The number that actually improved is the one this project should be steering
by: **agreement with his labelled trades, 4% → 22%**, from
`diagnostics/calibrate.py` — exactly the metric `NEXT-STEPS.md` §"Not next"
says to optimise instead of P&L.

## Reproduce

```bash
cd research/momentum-replication
python diagnostics/trades.py          # the 17 sessions, current rules
python diagnostics/calibrate.py       # agreement with his named trades
python diagnostics/lost.py            # rejection table (halt veto now absent)
```
