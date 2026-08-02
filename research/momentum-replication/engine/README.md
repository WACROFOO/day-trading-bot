# engine/ — the implementation under test

| File | What |
|---|---|
| `sim.py` | The strategy itself: account rules, indicators (VWAP, EMAs, MACD), `PullbackTracker` (swing structure + halt handling), `confluence()`, `evaluate()` (the entry gate), and every strategy constant. Env-switchable readings are flagged inline with the evidence for each |
| `engine20.py` | The execution loop: `run_day()` — minute-interleaved across symbols, one open position, scale-out ladder, halts, forced flat at the 11:30 cutoff. Also the switchable models: `RR_FILTER`, `RE_ENTRY`, `SCALE_IN` |

Contracts that everything downstream relies on:

- **Forward-only.** At minute T the engine has seen bars up to T and nothing
  else.
- **Intrabar ambiguity resolves against the trader** — including on the entry
  bar (defect #19) and on gap-through stops.
- **`run_day` is the single execution path.** Nothing may re-derive the gate
  or re-implement the loop (defects #15, #20 were exactly that). Diagnostics
  call it; they do not imitate it.

The rule-by-rule mapping to the spec, with citations, is `../ENGINE-RULES.md`.
