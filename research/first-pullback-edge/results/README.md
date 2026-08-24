# results/ — analysis tables

Written by `run.py report`, `run.py sensitivity` and `run.py placebo`.
`run_manifest.json` is the reproducibility record: git commit, config
SHA-256, study period, cost assumptions, seed.

| File | Brief section | What |
|---|---|---|
| `summary.csv` | §13, §35 | the A–F headline: trades, win rate, expectancy, PF, drawdown, 95% CI, verdict |
| `summary_secondary.csv` | §19 | the same ladder without the confluence rung the shipped strategy does not contain |
| `ablation.csv` / `ablation_secondary.csv` | §19 | B−A, C−B, D−C, E−D, F−E marginals with CI widths |
| `rejected_trades.csv` | §20 | accepted vs rejected expectancy per gate, winners/losers removed |
| `filter_overlap.csv` | §21 | phi between every pair of gate decisions |
| `cost_sensitivity.csv` | §28 | gross / low / realistic / stressed × the three ambiguity policies |
| `holdout.csv` + `splits.json` | §7 | chronological development / validation / holdout |
| `yearly.csv` | §15 | one row per variant-year. **Single year — the minute window is one month** |
| `regime.csv` | §16 | time-of-day buckets |
| `characteristics.csv` | §17 | price, gap, pullback depth, pullback number, push size, RVOL, confluence |
| `sensitivity.csv` | §23 | each parameter perturbed around its shipped value |
| `baselines.csv` | §24, §25 | random entry, pullback number, shifted triggers |
| `account_simulation.csv` | §26 | $2,000 cash account, compounding |
| `parameter_inventory.csv` + `degrees_of_freedom.json` | §22 | every parameter classified by provenance; ~29.8 effective DoF |
| `data_quality.json` | §29 | the measured provider probes |
| `provider_verification.json` | §29 | output of `run.py verify` — the five decisive checks against whatever key is present |
| `*_run.log` | — | stage logs, kept so a funnel count can be traced |

**Not produced, and why:** walk-forward folds (one month of intraday data),
market-regime buckets (no regime variation in 20 consecutive sessions),
float and catalyst cuts (no point-in-time source). Each is stated as absent
in `../reports/final_report.md` rather than silently omitted.
