# config/ — the frozen input

One file: `strategy.yaml`.

Every value is transcribed from `knowledge-base/tradingview/ross-fp-v4.pine`
(REV `V9.12`) and carries the line number it came from plus a `provenance`
tag:

| tag | meaning | count |
|---|---|---:|
| `sourced` | traceable to the Warrior corpus | 21 |
| `measured` | set by a measurement in `research/momentum-replication/reports/` | 2 |
| `local` | a local heuristic — 13 of these are flagged `[UNTESTED local]` or `[UNCALIBRATED]` by the Pine itself | 25 |
| `study` | introduced by this study (costs, ambiguity policy, limit offset, minimum stop) — **not the strategy's** | 5 |

`src/param_audit.py` reads those tags and produces
`results/parameter_inventory.csv` and the degrees-of-freedom estimate.

**Nothing in this file was chosen by looking at a result.** The config
SHA-256 in `results/run_manifest.json` is the record; a run whose hash does
not match the one quoted in `reports/final_report.md` is a different
experiment.
