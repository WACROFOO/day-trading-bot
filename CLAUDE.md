# day-trading-bot

Mechanical replication and honest testing of Ross Cameron's small-cap momentum
strategy. **Paper only** — replication over 894 sessions was negative
expectancy (`research/momentum-replication/reports/2026-08-regime-filter.md`).
Analysis here is selection quality, never a claim of edge.

## Non-negotiable answer rules

1. **Provenance.** Every price, volume, print or indicator value cited must
   appear in a tool output from the same turn. Nothing from memory, nothing
   inferred, nothing "probably around". If the number isn't in a fetch, either
   fetch it or drop the sentence. This outranks completeness.
2. **Verdict first.** Any market question gets the answer in the first line,
   then evidence. Never make the reader hunt.
3. **Low verbosity.** One reason kills a name — name the first failing gate,
   don't tour all nine. No method recaps (rules live in
   `knowledge-base/strategies/FILTERS.md`), no closing board summaries unless
   asked, no invented percentages on scenarios (order them instead).
4. **Match the user's language** (French or English, per message).
5. **Sizing critiques judge risk, not notional.** Risk = shares × stop
   distance. But check the stop is *enforceable*: compare it to the median and
   max 1-min range and to halt history. A tight stop on a halting stock is the
   real finding, not the share count.
6. **Reverse split ≠ veto.** The gate only fires when the split test proves
   the gap IS the split (finviz ÷ yahoo prev close ≈ clean integer —
   `split_check()` in `scripts/premarket_stars.py`). If sources agree, the
   move is real and the shrunken float is a feature. Run the test; don't cite
   it. (MSGY 2026-08-11: rejected without the test, ran 2.54 → 5.43.)
7. **Foreign private issuers (6-K/20-F) are a dilution blind spot.** No S-3 or
   424B tripwire exists for them — check EDGAR by hand and say so in the
   answer.

## Layout

- `knowledge-base/strategies/` — Ross method: `FILTERS.md` (the bible, wins on
  conflict), `PARAMETERS.md`
- `knowledge-base/orderflow-scalping/` — a DIFFERENT trader's futures model.
  **Fully self-contained: never cross-reference it with the Ross material in
  either direction.**
- `scripts/` — `premarket_stars.py` (gap scan), `catalyst_score.py`,
  `premarket_dd.py`, `size.py`
- `research/momentum-replication/reports/` — measurements; cite before
  re-deriving anything
- `.claude/skills/` — `premarket-stars` (morning scan), `ticker-verdict`
  (single-name analysis format), `warrior-corpus` (citations)

## Session

Money window 09:35–11:00 ET, hard stop 11:30 (13:00–17:30 France). The
pre-market 07:00–09:30 ET can contain the whole move (JWEL 2026-08-10).

## Git

Branch `claude/playbook-pullback-explanation-tg5c33`. Never put a model
identifier in commits or pushed files.
