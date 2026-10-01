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
| `ablation_live_costs*.txt` | the ten-year ablation at live costs (2026-09-29/30) |
| `2026-09-26-premarket-history.md`, `2026-09-25-full-assessment.md` | earlier assessments |
