# 2026-10-12T1512Z-quotes — the real-quote cost check

`python3 scripts/candidates/requote.py` on the owner's Mac, git `8512a1e` (amendment 2026-10-12c
committed before it ran). The terminal output was pasted into the chat; `report.txt` is its
report, verbatim. The read-out is `../../COST-CHECK.md`.

From the progress lines pasted with it: the trades were rebuilt from the cached bars in 3 s
(743 sessions); 803 distinct trades were re-priced in 2,211 s with 2,640 print requests and
1,245 quote requests to Alpaca's SIP feed.

| file | what |
|---|---|
| `report.txt` | the decision (Δ = Q − proxy on S2 G20·hod·close), where the proxy errs, every configuration under Q |

Left on the Mac, in `research/strategy-candidates/results/2026-10-12T1512Z-quotes/`:
`requoted.csv.gz` (every trade with its real fills, spreads and quote ages) and
`cost_check.json`; the run also wrote the verdict at the top of that git-ignored results folder,
where `run.py --lead S2W` reads it. The committed copy is `../../cost_check.json` (values as
printed, 3 decimals).

One line of the report is void: "our shares above the displayed bid size: 425" compared shares
with sizes Alpaca reported in round lots for those years (until 2025-11-03). The code now
converts; see `../../COST-CHECK.md` §5.
