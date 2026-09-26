# results/ — the edge hunt's record

| File | What |
|---|---|
| `registry.jsonl` | every configuration evaluated on train (and validation for the top five), tagged by run v1 / v2 / v3 |
| `spread_proxy.json` | the spread model: mean quoted spread per cell, fitted on train/validation NBBO moments |
| `quote_moments.csv` | the 1,320 sampled desk fills whose quotes were fetched |
| `f3_symdays.csv` | the 460 symbol-days of ticks (train 150, validation 60, holdout 250) |
| `pm_audit_days.csv` | the 80 sessions audited for pre-market runners missing from the universe |
| `f2_chosen.json` | F2's configuration chosen on train and validation |
| `f2_audit_trainvalid.json` · `f2_audit_holdout.json` | the audit, before and at F2's opening |
| `f2_holdout_output.txt` | the console output of F2's one holdout opening |
| `logs/` | raw output behind every number in `../REPORT.md` |
