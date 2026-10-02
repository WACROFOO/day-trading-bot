# Adversarial reviews of the execution proposals (M1–M5)

Each file is one reviewer's re-run of one proposal; the verdicts and notes are
in `../study_result.json` under `verdicts`, the summary in
`../../2026-10-02-full-report.md` §3.3.

| file | proposal | verdict |
|---|---|---|
| `m1_race_output.txt` | M1 stop of last resort | survives — built in e58a9d2 |
| `m1_race_head_repro.py`, `m1_short_invisible_repro.py` | M1 | the double sale and the invisible short at 92c404d (scratch; no longer reproduces) |
| `m2_output.txt` | M2 Fixed vs Tiered | refuted as stated; second-order |
| `m3_output.txt` | M3 half at +1 R | refuted on a trade-through fill |
| `m4_report_output.txt`, `m4_sigma_output.txt` | M4 trigger method | pin survives (built); the print band is refuted |
| `m5_output.txt` | M5 A6 at the fire | refuted |
