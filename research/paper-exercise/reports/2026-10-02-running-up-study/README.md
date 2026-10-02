# Running Up tile study — 2026-10-02

Asks why a Running Up row with a small move gets no positive evaluation,
and what the row should show instead. The write-up is
`../2026-10-02-full-report.md` §3.4 and §4.3–4.4.

The study ran in the session scratchpad. Its pickled inputs (`events.pkl`,
`alerts.pkl`) are not committed. Paths that start `/tmp/claude-0/…` inside
these files pointed at that scratchpad.

| file | what it is |
|---|---|
| `analysis_full.txt` | The replay of the live scanner classes over 2,608 days: router outcomes, the cascade verdict at the alert, 30-minute outcomes by move / day change / window / gate, and the best case with a known float and a catalyst. |
| `results.txt` | Train 2016–23 vs test 2024–26 lift tables for 20 features, single-feature AUC, the small-move profile, and the five-feature score by decile with net R. |
| `merge_checks.txt`, `merge_checks2.txt` | The three-feature grade by decile and quintile, per session part, with day-clustered CIs; the dim rules compared. |
| `extra_stats.txt`, `robustness_check.txt` | The under-5% share of moves; score AUC by session part; the broad dim rule. |
| `e1_check.txt` | E1 review: the stamp against the real cascade. A measured float over 20M must stay a lost pillar. |
| `review/c1_check.txt` | C1 review: the RVOL dim, VWAP, price band, and move AUC within each scanner. |
| `review/g1_check.txt`, `review/g1_ci_q5.txt` | G1 review: the grade reproduced, by year and time of day, its downside tail, and net R by quintile. |
| `runup_study.py`, `analyze.py`, `replay_alerts.py`, `merge_checks*.py` | The scripts, as run. |
| `study_result.json` | Synthesis: the diagnosis, ranked changes E1–A5, 12 rejects, the reviews of E1 / C1 / G1, and the code / corpus / measurement maps. |
