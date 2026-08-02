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

## 4. Make the exit plan deliver the 2:1 — the live question

`min_reward_risk >= 2.0` is implemented as a pre-entry veto and it is the
single largest rejection reason (66). The corpus does not support that reading:
every citation is retrospective and aggregate (`achieved`, `this week`, `for
month`, `$500 average winners`), and `PARAMETERS.md` §9 uses it as
`avg_win`/`avg_loss` inside an expectancy formula. A ratio of averages comes
from the exit plan.

Removing the veto is **not** the fix on its own:

| | trades | winners | total | expectancy | realised P/L ratio |
|---|---:|---:|---:|---:|---:|
| veto ON | 2 | 50% | +$357.54 | +0.89R | 2.79:1 |
| veto OFF | 11 | 27% | −$601.65 | −0.27R | 1.52:1 |

Target 1 is the *nearest* structural objective. When that sits under 2R, half
the position books a sub-1R gain and the remainder goes to breakeven — the
same capping defect as `HISTORY.md` #3, arriving by a different route. The
question is what target 1 should be when the high of day is only cents away:
skip the scale-out, use the measured move, or trail from the start. Three
readings, all testable against the same 61 pairs.

## 5. Sample size

2 trades over 17 sessions cannot support any conclusion, and neither can 11.
At this frequency a full month of free data yields under 20. Distinguishing an
edge from noise needs a few hundred.

This is the paid-data decision in `DATA-SOURCES.md`. **Step 4 first** — the
calibration set now exists, so a subscription would be buying more of a
measurable thing rather than more of an unmeasured one.

## 6. Unresolved rule readings

Recorded rather than guessed. Each needs evidence, not a decision.

| Question | Where | Status |
|---|---|---|
| `min_reward_risk` — entry veto or realised ratio? | §4 above | evidence says realised; the replacement exit rule is open |
| `price_min` — $2.00 or $1.00? | `PARAMETERS.md:20` | $1.00 nearly doubles recall of his names; no P&L effect yet |
| `rate_of_change` — one-shot at 09:35, or continuous? | `reports/2026-07-27-week.md` | still open; costs 10 of 61 pairs as a one-shot |
| `MIN_DIP_BARS` on a 1-minute chart | `PARAMETERS.md` §13 | still open |
| Float 20M vs 10M | `PARAMETERS.md` §1 | 20M in use; blocks 9 of 61 unconditionally |
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
