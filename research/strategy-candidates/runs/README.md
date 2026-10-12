# runs/ — the reports of every run, one folder each

A run on the Mac writes `research/strategy-candidates/results/<run>/` (git-ignored); its
report comes back by paste or upload and is filed here, and its `REG` lines are appended to
`../registry.jsonl`. Nothing in a folder here is edited after it is filed.

| run | what | evidence? |
|---|---|---|
| `2026-10-12-smoke/` | `scripts/candidates/run.py --source daily` on the 20 exported desk days (177 symbol-days, 04:00-12:00 bars), run before the commit that added the runner: every family fails for lack of trades (best 23 < 100 train trades). Files: `report.txt`, `summary.json`, `trades.csv.gz`, `registry.jsonl` | **no** — plumbing only, outside the five years, nothing opened or registered |
