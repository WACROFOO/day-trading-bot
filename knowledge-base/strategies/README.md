# strategies/ — the canonical strategy documents

The single authoritative home of the strategy spec. Copies elsewhere have
been removed after one drifted (see
`research/momentum-replication/strategy/README.md`).

| File | What it is | Edit? |
|---|---|---|
| `PARAMETERS.md` | The numeric spec. Every rule with an `n=` evidence count. **§13 lists the misreading traps** — an implementation attempt produced ~20 defects and not one was a wrong number here; all were misreadings §13 now documents | by hand |
| `PLAYBOOK.md` | The same rules as a step-by-step execution sequence | by hand |
| `STRATEGY.md` | Prose description of the strategy | by hand |
| `PLAYBOOK_V2.md` | Beginner-oriented playbook, with citations | **GENERATED** — `scripts/pipeline/13_render_v2_docs.py` |
| `STRATEGY_V2.md` | Parameter distributions, conflicts flagged | **GENERATED** — same script |
| `PLATFORM.md` | Broker/platform mechanics: hotkeys, order types | by hand |
| `small-cap-momentum-bull-flag.md` | The core pattern in isolation | by hand |

Reading order for a newcomer: `STRATEGY.md` → `PLAYBOOK_V2.md` →
`PARAMETERS.md` (§13 first). To verify any rule against the tape:
`python scripts/search.py "<phrase>"`.
