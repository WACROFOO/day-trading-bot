# day-trading-bot

Mechanical replication and honest testing of Ross Cameron's small-cap momentum
strategy. **Paper only** — replication over 894 sessions was negative
expectancy (`research/momentum-replication/reports/2026-08-regime-filter.md`).
Analysis here is selection quality, never a claim of edge.

## Routing — which skill answers what

| question looks like | use |
|---|---|
| "stars of the pre-market", "what's gapping" | skill `premarket-stars` |
| "analyze SYM", "scenarios", "best ticker now" | skill `ticker-verdict` |
| "analyse my trades", pasted blotter/P&L | skill `trade-review` |
| "plan du jour", "je fais quoi maintenant" | skill `trading-day` |
| "what does Ross say/teach/do about X" | skill `warrior-corpus` |
| pre-market/after-hours orders, sessions, fills | skill `extended-hours` |
| writing a standalone report/playbook/write-up | skill `trading-report-design` |

**Media rule:** chat answers are verdict-first (rule 2 below). Standalone
documents follow `trading-report-design`: provenance first, verdict last,
rejects visible, limitations footer. Same goal, two media.

The skills carry **format**; thresholds and rules live in
`knowledge-base/strategies/FILTERS.md`, which wins every conflict. Fix a rule
there first, then check whether a skill repeats it.

## Non-negotiable answer rules

1. **Provenance.** Every price, volume, print or indicator cited must appear
   in a tool output from the same turn. The tape side comes from
   `python3 scripts/tape.py SYM` — never hand-rolled fetch code, which is
   where invented numbers come from. No fetch, no claim. Outranks
   completeness.
2. **Verdict first.** Any market question gets the answer in the first line.
3. **Low verbosity.** One reason kills a name. No method recaps, no closing
   board summaries unless asked, no invented percentages — order scenarios
   by likelihood instead.
4. **Match the user's language** (French or English, per message).
5. **Sizing critiques judge risk, not notional** — and stop *enforceability*
   against `tape.py`'s range/halt output. A tight stop on a halting stock is
   the finding, not the share count.
6. **Reverse split ≠ veto.** Run the split test (`split_check()` /
   finviz ÷ yahoo prev close); the gate fires only when the ratio is a clean
   integer. Sources agreeing = real move, shrunken float = feature.
   (MSGY 2026-08-11: rejected untested, ran 2.54 → 5.43.)
7. **Foreign private issuers (6-K/20-F) are a dilution blind spot** — no
   S-3/424B tripwire. Check EDGAR by hand and say so.
8. **Score my own calls.** Any review of outcomes must put my session verdicts
   next to what happened, wrong ones named as wrong.

## Layout

- `knowledge-base/strategies/` — Ross method. `FILTERS.md` is the bible;
  `PARAMETERS.md` the numeric spec
- `knowledge-base/orderflow-scalping/` — a DIFFERENT trader's futures model.
  Self-contained: never cross-reference it with the Ross material, either way
- `./now [SYM…]` — the standard terminal report: market phase (pre-market /
  open / after-hours), countdown to the next boundary, then the `tape.py`
  workup of the watchlist (`./now --set SYM SYM`, `./now --scan` pre-market)
- `scripts/` — `tape.py` (intraday workup), `now.py` (phase report),
  `premarket_stars.py` (gap scan), `catalyst_score.py`, `premarket_dd.py`
  (pre-market shape), `size.py`, `corpus.py` (corpus search)
- `research/momentum-replication/reports/` — 23 measurements; cite before
  re-deriving anything

## Session

Money window 09:35–11:00 ET, hard stop 11:30 (13:00–17:30 France). The
pre-market 07:00–09:30 ET can contain the whole move (JWEL 2026-08-10).
Blotter timestamps are usually France local = ET + 6h in summer.

## Git

Branch `claude/playbook-pullback-explanation-tg5c33`. Never put a model
identifier in commits or pushed files.
