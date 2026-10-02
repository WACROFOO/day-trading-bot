# Session reports

One file per session day, named by ET date, written by `scripts/day.py`
after the hard stop. Layout follows `.claude/skills/trading-report-design`:
provenance first, funnel with denominators, rejects named with the gate
that killed them, controls in planned R, replay result, limitations last.

Empty until the first live session. A report here from a synthetic fixture
says **SYNTHETIC FIXTURE** in its second line.

## Analyses (not session reports)

| file | what it is |
|---|---|
| `2026-10-01-rules-audit.md` | every operating rule (5, E, F, G) one at a time on ten years, the indicator audit, the defects fixed — verdict: no rule change, one candidate (A15) built OFF |
| `rules_audit_output*.txt`, `rules_audit_results.json`, `indicator_audit_output.txt` | the raw outputs behind it |
| `rules_audit_open_output.txt`, `rules_audit_open_results.json` | addendum 2026-10-01c: three opening-risk candidates (stop vs recent range, opening lockout, plans per name) after the NXL loss — none passes; the first plan of the day is the least-bad cohort but still negative |
| `tick_replay_output.txt`, `tick_replay_results.json` | stage 1 of the tick replay (2026-10-02): the B portfolio's 2,577 gate-passing 2024+ plans filled and exited on SIP prints with the real spread — bars and ticks agree; real costs about 0.40 R a trade |
| `desk_replay_output.txt`, `desk_replay_results.json` | stage 2 (2026-10-02): the same plans armed the way the live desk arms them, mid-minute (median 36 s before the close), gates on the half-formed minute — 243 plans pass only at desk time, 165 only at the close; B is worse at desk time: −0.534 against −0.511 R a trade with real spreads |
| `stage3_output.txt`, `stage3_results.json` | stage 3 + partial exit (2026-10-02, addendum 2026-10-02c) on 648 sessions, real spreads: D −0.542; S3-dip −0.452 (better every year, lower bound −0.004: misses); S3-confirm −0.549; P-half2R −0.529; reported only: P-half1R −0.504 and S3-dip+P2R −0.436 clear the bar but were not preregistered as deciding — switch OFF, prospective. All negative |
| `ablation_live_costs*.txt` | the ten-year ablation at live costs (2026-09-29/30) |
| `2026-09-26-premarket-history.md`, `2026-09-25-full-assessment.md` | earlier assessments |
