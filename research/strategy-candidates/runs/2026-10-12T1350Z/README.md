# 2026-10-12T1350Z — the preregistered five-year run

`python3 scripts/candidates/run.py` on the owner's Mac, git `7163c35`, 803 s (the bar cache was
completed from Alpaca where sessions were missing — "fetch on"). The terminal output was pasted
into the chat; `report.txt` is that output, verbatim. The read-out is `../../RESULTS.md`.

| file | what |
|---|---|
| `report.txt` | the printed report: every configuration on train and validation, the choice, the gate, the diagnosis, the 21 `REG` lines |

Left on the Mac, in `research/strategy-candidates/results/2026-10-12T1350Z/`: `summary.json`,
`trades.csv.gz` (every simulated trade) and `registry.jsonl`. Upload `trades.csv.gz` for any
slice the report does not print.

Filed with a check: the 21 configuration hashes in the `REG` lines equal those the committed
code computes, so the Mac ran exactly the preregistered rules. The `REG` lines are in
`../../registry.jsonl`.
