---
name: trade-review
description: Review the user's pasted trade blotter or P&L — "analyse my trades", "critique my trades today", a pasted broker log, or a position screenshot. Fixed format — blotter table, honest stats, risk judged on stop enforceability not notional, my own calls scored against the outcomes.
---

# Trade review

The blotter is a $100,000 **paper** account on TradingView. Timestamps in
pasted logs are usually France local (ET + 6h in summer) — convert and say so.

## Order of work

1. **Parse** the blotter into one table: ET time, symbol, qty, avg, exit, P&L.
2. **Fetch the tape** for every traded symbol before judging anything:
   `python3 scripts/tape.py SYM1 SYM2 ...` — range distribution, halts,
   per-bar volume. Provenance: no market number in the review that is not in
   this turn's fetches.
3. **Stats**, computed not estimated: win rate, avg win / avg loss, profit
   factor, P&L concentration by symbol.
4. **Risk** — three separate judgements, never conflated:
   - *Risk per trade* = qty × stop distance, as % of account. Judge THIS,
     not notional. 5,000 shares with a real 10¢ stop is $500 risk, period.
   - *Stop enforceability* = stop distance vs `tape.py`'s median/max 1-min
     range and halt history. A 3¢ stop on a halting stock is not $150 of
     risk; it is whatever the reopening print says. This is the honest
     risk number — report both.
   - *Paper slippage* = position ÷ volume of the entry/exit bar. Over ~5% of
     the bar, the fill was fiction; restate the P&L range with 1–2¢ slip.
5. **Window** — flag entries outside 09:35–11:00 ET (11:30 outer edge) as
   off-book. One good day outside the window does not overturn the split of
   his broker statements; say that once, without moralising.
6. **Score my own calls.** If any traded name was analysed in this session,
   put my verdict next to the outcome in a table — including the wrong ones,
   named as wrong, with the specific reasoning error. This section is
   mandatory whenever prior calls exist. A review that grades only the user
   is dishonest.
7. **At most two changes recommended.** Ranked. More than two is noise.

## Tone

Lead with the overall result and the single most important finding. Praise
what was actually good (exits, loss discipline) with the specific prints that
show it. Never inflate an error's importance to seem rigorous, never soften a
real one because the day was green. P&L on paper is the least transferable
output — the decision log is what gets judged.

## Bans

No percentages invented for anything. No board summary. No re-teaching the
method. ≤ 50 lines unless the blotter itself is longer.
