# Next steps

Ordered by what each would actually settle, not by effort.

## 1. Verify the recap dates — cheap, unblocks everything else

Index dates are synthetic below year granularity (`knowledge-base/data/README.md`),
so every engine-vs-trader comparison so far rests on an **inferred** day mapping.
A per-video metadata fetch gives real upload dates.

Until this is done, statements like "he made $22,000 on the session my engine
sat out" are probably right but not proven. Everything in §2 depends on it.

## 2. Calibrate the detector against his actual entries

The recaps name tickers and walk the entries. With dates fixed, each becomes a
labelled example: **did the detector fire where he actually entered?**

That converts "is the pullback detector right?" from argument into measurement,
and it is the question ~18 defect fixes could not settle. It needs no paid data.

Start with the sessions already transcribed — the ZCMD/INM "$40k in 10 minutes"
session and the NCRA/DFNS one — where he narrates entries directly.

## 3. Explain the names he trades that the scanner never sees

ZYBT and CPHI recur across his recaps and never appear in a watchlist here.
Either they should have been selected — a scanner gap — or they failed a pillar,
in which case he trades outside the documented filter. Both answers are
informative and the check is mechanical.

## 4. Sample size

4 trades over 10 sessions cannot support any conclusion. At the observed ~0.4
trades/day, even a full month of free data yields ~8. Distinguishing an edge
from noise needs a few hundred.

This is the paid-data decision in `DATA-SOURCES.md`. Three separate blockers now
point at it: no pre-market volume, no sub-minute bars, and no halt status.
**Do §2 first** — calibrating on free data is what stops a subscription buying a
bigger sample of the wrong thing.

## 5. Unresolved rule readings

Recorded rather than guessed. Each needs evidence, not a decision.

| Question | Where |
|---|---|
| `rate_of_change` — one-shot at 09:35, or continuous? | `reports/2026-07-27-week.md` |
| `MIN_DIP_BARS` on a 1-minute chart | `PARAMETERS.md` §13 |
| Float 20M vs 10M | `PARAMETERS.md` §1 |
| `level_tolerance` | `PARAMETERS.md:127` |

## Not next

**Do not keep tuning the engine.** The P&L sign has moved with nearly every
structural change in this project. Another round produces another number, not
an answer. The engine now matches the documented rules 1:1
(`ENGINE-RULES.md`); further changes need external evidence — §1 and §2 supply
it, more fiddling does not.
