# His recaps vs my simulation, week of 2026-07-27

Source: `knowledge-base/recaps/`. Day mapping inferred from ticker overlap plus
the recaps' own numbering ("day 26", "day 27") — **not** from the index dates,
which are synthetic below year granularity.

| Session | His recap | He traded | My engine |
|---|---|---|---|
| Mon 07-27 | "Record Breaking Green Day!" (day 26) | EDBL, LGHL, DFNS | 2 trades, **+$114.69** |
| Tue 07-28 | "Biggest Red Day…" (day 27) | DFNS, INLF, LGHL, BIYA | 1 trade, −$64.72 |
| Wed 07-29 | "Taiwan Stock … up 177%" | NCRA, DFNS | **0 trades** |
| Thu 07-30 | — | — | 0 trades |
| Fri 07-31 | — | — | 0 trades |

---

## 1. Selection is validated

Every ticker he names was independently on a watchlist my pipeline built from
the five pillars: DFNS, INLF, EDBL, LGHL, NCRA, AMIX, STFS, BIYA, VIVK — plus
CJMB, JEM and ADVB from the wider 17-day lists.

This is the first independent confirmation of any part of the pipeline against
his actual behaviour. **The scanner works.** Whatever is wrong is downstream of
selection.

## 2. The day I sat out is the day he made money

On the Taiwan session he finished **up ~$22,000** in his main account. My engine
took **zero trades**.

He also states he **lost $1,200 on DFNS** that same day, and on NCRA that he
"wasn't sure enough … where I took my first trade". So the winning day contained
losing trades and hesitancy — consistent with the documented strategy rather
than with a perfect read.

## 3. Halts — an unmodelled event, on exactly that day

From the recap: "we had AMIX that halted, STFS that halted, and there was
another one that halted".

The bars corroborate it precisely, 09:30–11:30:

| Symbol | Missing minutes | Longest gap |
|---|---:|---|
| STFS | 18 | **9 min from 09:38** |
| AMIX | 4 | 4 min from 09:36 |
| NCRA | 4 | 4 min from 11:18 |
| VIVK | 0 | — |
| GMM | 0 | — |

**The engine has no concept of a halt.** It treats a gap in the minute series as
though nothing happened: the pullback tracker carries state straight across it,
the indicators skip the missing period, and a halt-resumption gap can look like
an ordinary bar-to-bar move. The corpus treats halts as a first-class event —
`PARAMETERS.md` records 46 claims about them, and there is a named
"dip and rip on halt resumption" setup (`2kMgCjsmFzY` 02:39) — none of which is
implemented.

Two of the five names on the 07-29 watchlist halted in the first ten minutes.
That is the session my engine produced 46 setups and zero trades on.

## 4. Scale differs

The recaps run two accounts in parallel: a $2,000 small-account challenge and a
main account where figures like "up about $247,000" and "down $32,384.82"
appear. The simulation models a single $10,000 account, so P&L is not comparable
in magnitude — only behaviour is.

On the Record Green Day he notes he traded EDBL in the main account "but not in
the small account", so even he does not take every setup in every account.

---

## What this changes

**Confirmed:** the five-pillar scanner selects the right stocks. The earlier
week-audit conclusion — that the watchlist was contaminated with faders — still
holds for Monday/Wednesday/Thursday, but it is now clear the *names* were right
even when their behaviour was not.

**New defect, evidenced:** halt handling is absent, and its absence is
concentrated on the one session in this week where he made significant money.
Whether modelling halts would have produced trades is untested — the point is
that the engine currently cannot represent an event the source treats as a
core setup.

**Still open:** the day mapping is inferred, not certain. Confirming it needs
the recap dates verified individually rather than taken from the synthetic
index, which is a per-video metadata fetch.
