# Review pack v2 — response to the 2026-09-21 external review

**PROVENANCE** · answers the review of `docs/REVIEW-PACK-2026-09-21.md`
(the original is unchanged except for the wording of four conclusions, item 1
below, and says so at its top) · branch
`claude/playbook-pullback-explanation-tg5c33` · written 2026-09-21 evening ·
work in progress: items are added below as each lands, each with its commit.

## Item 10 — reconciliation with the 894-session negative replication

The review asked what produced the negative result and what in this
exercise is actually different. Read from `research/momentum-replication/reports/`
(nothing re-derived):

**What was measured, and how it failed.** `2026-08-regime-filter.md`: daily
bars, 2,410 symbols, December 2022 to August 2026, 8,828 qualifying
symbol-days over 894 sessions under the same Layer 1 gates (open $2–20, gap
≥ 10 %, no split days). The rule tested was *buy the 09:30 open, exit on a
level or at the close*. Every year is negative on mean open→close (−6.25 %
in 2022 to −1.60 % in 2025; −3.02 % for 2026), 67–78 % of names close red,
and every stop/target cell is negative on the pessimistic bound. The
mechanism the report names: the favourable excursion is a **fat right tail**
(mean MFE +13.76 %, median +5.09 %) against a −10.64 % median drawdown, so a
target close enough to be hit reliably is too small to pay for the losers
and one large enough to matter is hit too rarely. The regime is not
persistent (r ≤ 0.09 at every lookback), so it cannot be timed.

**The cost layer.** `2026-08-pine-v8-benchmark.md`, 330 ticker-days, 20
fills in both engines: at the $2,000 / $20-risk basis commissions are
~18 % of nominal R (a stop-out is two orders = $2 = 10 % of a $20 budget),
and 25 % of fills touched trigger and stop in the same minute — an
ambiguity the daily-bar study could not even see. `2026-08-short-hold.md`:
the median return is negative at every holding period from 5 minutes to the
close, and entering before the open is worse than entering at it in every
pairing.

**The entry layer.** `2026-07-july-calibration.md`: of 61 session-ticker
pairs he named, 100 % were in the pool, 31 % passed the five pillars and 3
survived the entry rules — the universe is not the problem; the gates and
the entry are where the method is lost. `2026-08-target-and-entries.md`:
the 2:1 reward veto was anti-correlated with the chart gate (setups that
passed the gate had *closer* targets), and the losses were entries, not
tight stops.

**What is different here, stated without claiming it is enough.** This
exercise enters on a first pullback on the desk's own 1-minute tape after a
confirmed move, with a structural stop, inside 09:30–11:30, on names the
cascade passed at that minute — the intraday method the daily-bar study
explicitly says it could not represent ("this does not show that the
strategy fails — it shows that the daily-bar version of it fails"). It also
records the NBBO at every decision and fill, so the same-bar ambiguity and
the spread cost are measured rather than assumed. That is the whole of the
difference. It removes one stated blocker of the replication (no intraday
data); it does not remove the tail-versus-median structure, the commission
toll at $20 risk, or the negative median at every horizon, and six
compromised sessions with zero fills do not overturn a 894-session result.
Until the failure condition in `docs/preregistration.md` §4 is evaluated at
phase D on realised R, the standing verdict is the replication's.

