# The 2:1 veto, settled — and what it was hiding

Follow-on from `2026-07-july-calibration.md`, which left one live question:
`min_reward_risk >= 2.0` is the largest single rejection reason in the engine
(66), the corpus reads it as a realised ratio rather than a pre-entry veto, and
removing it made expectancy worse. Something had to give.

## The arithmetic was already in the spec

`PARAMETERS.md` §6 and §8, two rows apart:

| | |
|---|---|
| `target_typical` | ~$0.15–0.20 per share |
| `stop_typical` | ~$0.08–0.10 per share |
| `stop_max_distance` | <= $0.20 per share |

A target of $0.15–0.20 against a stop of $0.08–0.10 is **roughly 2R at the
typical values and 1R at the cap** — and nowhere near the "nearest structural
objective at least 2× the stop" the veto was enforcing. The same document
specifies both, so they cannot both be right.

## Measured, not argued

`diagnostics/target_r.py` — distance from entry to the nearest structural
objective, across every setup in the 17-day window:

| | p25 | median | p75 | reach 2R |
|---|---:|---:|---:|---:|
| every setup (n=406) | 1.00R | 1.79R | 3.09R | 46% |
| **passing all 8 gate conditions (n=31)** | **0.67R** | **1.14R** | **2.19R** | **26%** |

In dollars the median distance to target 1 is **$0.160/share** — the middle of
the documented `target_typical` $0.15–0.20. The detector's target is right.

The second row is the finding. **Setups that pass the gate have *closer*
targets than setups that don't** — median 1.14R against 1.79R. That is not
noise, it is mechanical: the gate demands price above VWAP, above the 9 EMA,
MACD positive and confluence at support, which selects names pressed up against
their own high of day, which is exactly where the nearest objective is closest.

So the veto was anti-correlated with the gate sitting behind it. **The stronger
the setup by the documented criteria, the more certainly the veto killed it** —
74% of gate-passing setups rejected for failing to clear a bar the strategy's
own typical target does not clear either.

`RR_FILTER` now defaults **off**. 2:1 is measured as a realised ratio over
trades, which is how every citation states it. `RR_FILTER=1` restores the veto.

## What that exposed

| | trades | winners | total | expectancy | realised P/L ratio |
|---|---:|---:|---:|---:|---:|
| veto ON | 2 | 50% | +$357.54 | +0.89R | 2.79:1 |
| **veto OFF (now default)** | **11** | **27%** | **−$601.65** | **−0.27R** | **1.52:1** |

The realised ratio is 1.52:1 — respectable, and the thing the corpus actually
asks for. The win rate is 27% against a claimed 65–75%, and at 1.52:1 the
breakeven is 40%. **The strategy is failing on accuracy, not on reward:risk.**

## Bad entries, not tight stops

Two shapes, opposite fixes. `diagnostics/mae.py` replays every trade forward
from its entry bar to the end of the window — deliberately looking past the
engine's own exit, since that is the question — and records the worst
excursion before target 1.

| day | sym | in | $/sh | engine | worst before T1 | T1 reached |
|---|---|---|---:|---:|---:|---|
| 07-09 | RPGL | 09:36 | 0.12 | −1.00 | −2.92R | no |
| 07-09 | RPGL | 10:05 | 0.04 | +0.65 | 0.00R | 10:06 |
| 07-13 | SKYQ | 09:47 | 0.10 | −1.00 | −1.30R | 09:54 |
| 07-13 | EHGO | 11:25 | 0.03 | −0.00 | −0.00R | no |
| 07-14 | SHPH | 09:38 | 0.29 | −1.00 | −3.90R | no |
| 07-15 | ERNA | 09:37 | 0.46 | −1.00 | −6.70R | no |
| 07-22 | ADVB | 10:24 | 0.62 | +0.55 | 0.00R | 10:25 |
| 07-22 | ADVB | 11:22 | 0.33 | +2.79 | 0.00R | 11:25 |
| 07-23 | ADVB | 10:07 | 0.67 | −1.00 | 0.00R | 10:08 |
| 07-27 | BIYA | 10:24 | 0.18 | −1.00 | −2.50R | no |
| 07-27 | BIYA | 11:22 | 0.07 | −1.00 | −4.29R | no |

**Of the 7 trades stopped at −1R, 5 never reached target 1 at all**, and they
ran −2.50R, −2.92R, −3.90R, −4.29R and −6.70R against the entry. A wider stop
loses more on every one of them. The stops are not the problem, and they are
not mis-set either: the engine's median risk is **$0.080/share**, sitting on
the documented `stop_typical` $0.08–0.10.

Target 1 was reachable on 5 of 11 trades; the engine won 3. So the exit rules
cost about two trades — worth fixing, but a second-order effect. **The other
six are entries into stocks that simply went down.**

One of the two is a tie-break, not a defect: ADVB 07-23 hit its stop and its
target on the *same bar* (10:08). Intrabar order is unknowable from 1-minute
data, and the engine assumes the stop filled first. That is the conservative
choice and it should stay.

## Selection or timing? Timing.

The engine enters names that fall 3–7R and he does not — so is the detector
being handed the wrong stocks, or is it entering the right stocks at the wrong
moment? The recap labels separate the two, and the test is the same forward
replay pointed at a different pool.

`diagnostics/his_mae.py` ran it on gate-clearing trades and produced 11 per
side: target 1 reached on 64% of his names against 45% of watchlist names,
median excursion −1.25R against −1.30R. Directionally kinder, statistically
nothing — 7 trades against 5.

The gate is what makes that sample small, and the gate is not what is being
tested. `diagnostics/excursion.py` drops it and measures **every** setup:

| pool | setups | reach T1 | median | p25 | p10 | past −2R |
|---|---:|---:|---:|---:|---:|---:|
| engine watchlist | 406 | 56% | −1.56R | −3.44R | −5.92R | 43% |
| **his recap names** | **363** | **53%** | **−1.75R** | **−3.86R** | **−7.78R** | **46%** |
| both (overlap) | 123 | 59% | −1.76R | −3.46R | −5.25R | 44% |

**They are the same distribution.** Point the detector at the stocks he
actually traded and it produces the same drawdowns it produces on the
watchlist — marginally worse, if anything. 60 watchlist name-days against 61 of
his, 20 shared.

So **selection is not the problem, and fixing the scanner cannot fix this.**
The price floor and the gap threshold from the July calibration change which
names the detector sees; they do not change what happens after it fires.

(The gate-restricted split of the same table runs 31/23/5 setups and points the
other way. It is underpowered and should not be read.)

## Where this leaves it

The geometry the corpus describes and the geometry the detector produces do not
match, and this is the sharpest statement of the gap the project has:

| | corpus | measured |
|---|---|---|
| stop | low of the pullback candle, ~$0.08–0.10 | $0.080 median — matches |
| target 1 | ~$0.15–0.20 | $0.160 median — matches |
| what price does after the trigger | reaches target more often than not | **median −1.56R first, 43% past −2R** |

Both distances are right. What is wrong is the path between them, and it can be
stated exactly. Target 1 *is* reached, on 56% of setups. But of the 228
watchlist setups that reach it, **37% dip past −1R on the way** — that is the
stop, so those targets are only reached by a trade that has already been
closed:

| pool | setups | reach T1 | of those, dipped past −1R first | **clean to target** |
|---|---:|---:|---:|---:|
| engine watchlist | 406 | 56% | 37% | **35%** |
| his recap names | 363 | 53% | 42% | **31%** |

**35%.** The strategy as documented — the documented trigger, the documented
stop under the pullback low, the documented first target — reaches its target
without first being stopped out on about a third of its own setups. At the
realised 1.52:1 the breakeven is 40%. The observed 27% win rate over 11 trades
is a small sample landing where a well-powered 406-setup measurement says it
should.

That is the whole result, and it is not a bug this time. Every parameter is
implemented as written and the arithmetic still does not close.

The gap has to be in the trigger. The detector fires on the first candle
making a new high after a qualifying dip, which is what the corpus says; the
setups it finds pass the documented structure tests; and they are still, about
half the time, in front of a collapse. The likely reading is that it is
matching the *shape* of a micro-pullback at points in a move where he would not
take it — and no scanner change, stop change, or target change reaches that.

**This is where the free-data sample stops being the limit and starts being the
question.** 406 setups is enough to say the two pools behave alike. It is not
enough to characterise which pullbacks within them are the survivable ones,
which is the next thing worth knowing.

## Reproduce

```bash
cd research/momentum-replication
python diagnostics/target_r.py     # how far target 1 is, in R
python diagnostics/trades.py       # the 17-day run, with the realised ratio
RR_FILTER=1 python diagnostics/trades.py
python diagnostics/mae.py          # bad entries or tight stops?
python diagnostics/his_mae.py      # the same test on his names (n=11/side)
python diagnostics/excursion.py    # the same test without the gate (n=406/363)
```
