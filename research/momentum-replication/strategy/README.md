# Strategy documents — moved

The canonical strategy documents live in **`../../../knowledge-base/strategies/`**
and nowhere else:

| File | What it is |
|---|---|
| `PARAMETERS.md` | Numeric spec with `n=` evidence counts; §13 lists known misreading traps — **read it before implementing anything** |
| `PLAYBOOK.md` | The same rules as an execution sequence |
| `PLAYBOOK_V2.md` / `STRATEGY_V2.md` | GENERATED from the claims DB (`scripts/pipeline/13_render_v2_docs.py`) — never hand-edit |
| `STRATEGY.md` | Prose description |
| `PLATFORM.md` | Broker/platform notes (hotkeys, order types) |
| `small-cap-momentum-bull-flag.md` | The pattern in isolation |

This folder used to carry copies, made when this package was prepared as a
self-contained handoff. The copies drifted — PARAMETERS.md here was 397 lines
while the canonical one had grown to 639, including §13's misreading traps and
every stream-derived correction. A stale spec next to the engine is worse than
no spec: it is the exact mechanism behind HISTORY.md defect #20. Deleted; one
copy of the truth.
