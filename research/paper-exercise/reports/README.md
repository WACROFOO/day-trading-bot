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
| `ablation_live_costs*.txt` | the ten-year ablation at live costs (2026-09-29/30) |
| `2026-09-26-premarket-history.md`, `2026-09-25-full-assessment.md` | earlier assessments |
