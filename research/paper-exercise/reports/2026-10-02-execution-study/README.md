# Execution-cost study — 2026-10-02

Asks where a trade's cost goes on the real tape, and which order-handling
changes could cut it. The write-up is `../2026-10-02-full-report.md` §3.3 and §4.1–4.2.

The study ran in the session scratchpad. Its pickled inputs (the plan cache
and the stage-1 tick outcomes under the gitignored `data/cache/`) are not
committed. Paths that start `/tmp/claude-0/…` inside these files pointed
at that scratchpad.

| file | what it is |
|---|---|
| `cost_decomposition_output.txt` | 1,873 filled gate-passing trades split into commission, half-spreads, entry fill and exit slippage. Cut by session, price, stop %, spread ÷ stop, shares, exit kind and year. Covers the exit-slippage tail, fill statistics, A6 on the real spread, and Fixed vs Tiered commission. |
| `proposals_output.txt` | Tape tests of the proposals: (A) post-trigger drift, (B) resting STP LMT exits, (C) A6 on the real spread, (D) entry cap = trigger, (E) Tiered all-in. |
| `proposals2_output.txt` | Cost by session with off-market-flagged exits removed; drift tails. |
| `open_cross_output.txt` | Pre-market fills still held at 09:30 and what happened to them. |
| `cost_decomp.py`, `exec_props.py`, `exec_props2.py` | The scripts behind those outputs, as run. |
| `study_result.json` | Synthesis: ranked proposals M1–M9, eight rejects, adversarial reviews of M1–M5, and the code / IBKR / cost / corpus maps. |
| `review/m1_race_output.txt` | M1: the enforce race under stop-limit exits. |
| `review/m1_race_head_repro.py`, `review/m1_short_invisible_repro.py` | M1: the double sale and the invisible short, reproduced at 92c404d. They are scratch scripts, renamed from `test_*` so pytest never collects them; at today's code they no longer reproduce. |
| `review/m2_output.txt` | M2: Fixed vs Tiered by take fee, at $40 and $20 risk. |
| `review/m3_output.txt` | M3: the half-at-+1 R target under five fill rules — refuted. |
| `review/m4_report_output.txt`, `review/m4_sigma_output.txt` | M4: exit-trigger rules re-simulated — the band is refuted; the triggerMethod pin survives. |
| `review/m5_output.txt` | M5: A6 at the fire — refuted. |
