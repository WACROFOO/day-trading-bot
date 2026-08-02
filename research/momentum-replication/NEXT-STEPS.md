# Next steps

Ordered by what each would actually settle, not by effort.

Steps 1–3 are **done** — `reports/2026-07-july-calibration.md`. What they found
rewrote everything below them, so they are kept here with their outcomes rather
than deleted.

## ~~1. Verify the recap dates~~ — done

68 of 73 videos returned a real `upload_date` (5 hit YouTube's bot check). 36
are July uploads with transcripts; 28 map onto a session the bar data covers,
labelling 14 of 17 sessions. Mapping is by publication convention, not by fit.
`data/july_meta.json`, transcripts in `knowledge-base/recaps/`.

## ~~2. Calibrate the detector against his actual entries~~ — done

61 labelled session-ticker pairs. Of every ticker he named that resolves to a
symbol:

| level | of named |
|---|---:|
| in the candidate pool | 100% |
| scanned that session | 97% |
| passed the five pillars | 40% |
| detector found a setup | 97% |
| the engine would have traded it | 5% |

**The detector was not the problem.** ~18 defect fixes went into it and it
finds structure on 97% of what he traded. The losses are the scanner and the
entry rules.

## ~~3. Explain the names he trades that the scanner never sees~~ — done

Charged to a criterion in `diagnostics/pillars.py`. Largest causes: the `$2.00`
price floor (12 of 61 pairs; `PARAMETERS.md:20` records `1.00 also stated`) and
`gap >= 10%`, which is a pre-market test. Lowering the floor to `$1.00` nearly
doubles recall of the names the pillars would accept — 23% → 46% — but produced
**no additional trades**, because the entry rules bind downstream.

---

## ~~4. Make the exit plan deliver the 2:1~~ — done, and it was not the exit

`reports/2026-08-target-and-entries.md`. `min_reward_risk >= 2.0` was
implemented as a pre-entry veto; the spec's own numbers rule that out
(`target_typical` $0.15–0.20 against `stop_typical` $0.08–0.10 is 1–2R, not
"the nearest objective at 2x the stop"), and the measurement is worse than
that: setups passing all 8 gate conditions have a median target 1 of **1.14R**
against 1.79R for setups that fail it. The gate selects names pressed against
their high of day, which is where the nearest objective is closest. The veto
was anti-correlated with the gate behind it and killed 74% of gate-passing
setups. `RR_FILTER` now defaults off.

The realised ratio with the veto gone is **1.52:1** — what the corpus asks for.
Every exit parameter is now implemented as stated and there is no exit-side
explanation left.

## ~~5. The entries~~ — measured: it is timing, not selection

Win rate is **27%** against a claimed 65–75%. At 1.52:1 breakeven is 40%, so
this is an accuracy problem, not a reward:risk one.

It is not the stops. `diagnostics/mae.py`: of the 7 trades stopped at −1R,
**5 never reached target 1 at all**, running −2.50R to −6.70R against the
entry. A wider stop loses more on every one. Median risk is $0.080/share, on
the documented `stop_typical` $0.08–0.10.

It is not the selection either. `diagnostics/excursion.py` replays every setup
forward on both pools:

| pool | setups | reach T1 | median excursion | past −2R |
|---|---:|---:|---:|---:|
| engine watchlist | 406 | 56% | −1.56R | 43% |
| his recap names | 363 | 53% | −1.75R | 46% |

**The same distribution.** Pointing the detector at the stocks he actually
traded produces the same drawdowns. So the scanner fixes from §3 — the price
floor, the gap threshold — change which names it sees and cannot change this.

Stated exactly: target 1 is reached on 56% of setups, but 37% of those dip
past −1R first — the stop — so the documented setup reaches its documented
target without being stopped out on **35%** of its own signals. Breakeven at
the realised 1.52:1 is 40%. The 27% observed over 11 trades is a small sample
landing where the 406-setup measurement says it should.

Both documented distances are implemented correctly ($0.080 stop, $0.160
target, medians). What is wrong is what price does between them. That points at
the trigger: it matches the shape of a micro-pullback at points in a move where
he would not take it. `reports/2026-08-target-and-entries.md`.

## 5b. The streams — a third register, and the timing answer

`reports/2026-08-streams-roundup.md`. The channel's `/streams` tab holds **480
live broadcasts, none of them in the 2,211-video index** (scraped from
`/videos`). **289 of 296 are transcribed — ~1.34M words, 241 hours.** Unlike the teaching
videos and the recaps, a live stream records a decision *before* the outcome.

They are 2021–2023, though (180 of 296 dated files are 2022), and **none fall
in the 2026-07 bar-data window** — so they are evidence about *method*, not a
labelled set the engine can be scored against. The recaps remain the only
calibration set.

**§5 above asked what is wrong with the trigger. The streams answer it:
the micro-pullback he trades is frequently a 10-SECOND pattern.** "10 second"
appears 250 times across 117 of 289 streams; of the "micro pullback" mentions
carrying an explicit timeframe, 19 are 10-second against 59 one-minute. Our
detector runs on 1-minute bars with `MIN_DIP_BARS = 2`, so the shortest dip it
can see is **two minutes**. On a 1-minute chart a 10-second pullback is the
wick of a candle.

Confirmed current, not a 2021 habit: the daily recaps of June–July 2026 use the
phrase in 15 of 68 files, and the teaching corpus in 80 of 257.

That is a mechanical explanation for the −1.56R median excursion, and **it is
not reachable by any parameter setting** — 1-minute bars cannot represent it.
It converts the §6 data decision from "buy more sample" into "buy the
resolution the entry happens at".

Four free corrections were applied from the same source (third pullback → size
reduction, `PRICE_MIN` stays $2.00, float stays 20M, low frequency is not a
bug). Together: 11 trades → 13, −$601.65 → −$588.90. The point of that number
is that it barely moved.

## 6. Sample size

2 trades over 17 sessions cannot support any conclusion, and neither can 11.
At this frequency a full month of free data yields under 20. Distinguishing an
edge from noise needs a few hundred.

This is the paid-data decision in `DATA-SOURCES.md`. **Step 5 first** — the
calibration set now exists, so a subscription would be buying more of a
measurable thing rather than more of an unmeasured one.

## 7. Unresolved rule readings

Recorded rather than guessed. Each needs evidence, not a decision.

| Question | Where | Status |
|---|---|---|
| ~~`min_reward_risk` — entry veto or realised ratio?~~ | §4 above | **settled: realised.** Veto off by default; realised ratio 1.52:1 |
| ~~`price_min` — $2.00 or $1.00?~~ | `PARAMETERS.md:20` | **settled: $2.00.** "cxdc 115 it's a little too cheap" — he rejects above $1 routinely (streams §5) |
| `rate_of_change` — one-shot at 09:35, or continuous? | `reports/2026-07-27-week.md` | still open; costs 10 of 61 pairs as a one-shot |
| ~~`MIN_DIP_BARS` on a 1-minute chart~~ | `PARAMETERS.md` §13 | **settled, and unimplementable on 1-minute data** — he trades 10-second pullbacks (streams §1) |
| ~~Float 20M vs 10M~~ | `PARAMETERS.md` §1 | **settled: 20M.** He traded a 23M float, called 35M "too high" (streams §6) |
| `level_tolerance` | `PARAMETERS.md:127` | still open |

## Not next

**Do not keep tuning the engine on P&L.** The sign has moved with nearly every
structural change in this project, and defect 14 showed the last positive
figure was a look-ahead. There is now a better target than P&L: the 61 labelled
pairs. Change a rule, re-run `diagnostics/calibrate.py`, and see whether the
engine gets closer to what he actually did — that number cannot be moved by an
accounting bug in the exit.

## A caveat that applies to all of the above

**"Named in a recap" is not "traded that session."** Recaps review prior days
and preview watchlists, so the 61 pairs are an upper bound on his trades and
every recall percentage here is a floor. Tightening it means reading the
narration around each mention rather than counting mentions — worth doing
before any of these numbers is treated as precise.
