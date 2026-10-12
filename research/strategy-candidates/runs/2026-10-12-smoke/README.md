# 2026-10-12-smoke — the plumbing check, not evidence

`python3 scripts/candidates/run.py --source daily --out research/strategy-candidates/runs/2026-10-12-smoke`,
run on 2026-10-12 before the commit that added the runner, on the 20 exported desk days of
`research/daily/` (2026-09-11 → 10-08: 136 symbol-days "train" to 10-01, 41 "validation"
after; 04:00-12:00 bars, previous closes as exported). These days lie outside the
preregistered five years, so the run reads nothing the real test will use.

What it shows: the runner goes end to end — entries, exits, costs, the random baseline, the
diagnosis, the registry lines — and every family fails for lack of trades (best 23 against
the 100 train trades required), as it must on 20 days. No number here says anything about
the candidates.

| file | what |
|---|---|
| `report.txt` | the printed report |
| `summary.json` | every configuration's statistics |
| `trades.csv.gz` | every simulated trade, before the one-position rule |
| `registry.jsonl` | the run's own registry lines, marked `"smoke": true` — not in `../../registry.jsonl` |
