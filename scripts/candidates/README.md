# scripts/candidates/ — the strategy candidates' runner

Protocol: `research/strategy-candidates/PREREGISTRATION.md`. Tests: `tests/test_candidates.py`.

```bash
python3 scripts/candidates/run.py                  # the preregistered run — on the Mac (bars + keys)
python3 scripts/candidates/run.py --source daily   # smoke test on research/daily/ — plumbing, not evidence
python3 scripts/candidates/run.py --sample 30      # plumbing on 30 sessions a split — opens nothing
```

| Module | What |
|---|---|
| `data.py` | the universe (candidate_days.csv, reverse splits removed), the history cache read session by session and fetched where missing, the exported desk days for the smoke test; `SymbolDay` with its 04:00 VWAP |
| `rules.py` | the entries — S1 afternoon fade, S2 crowded-gapper fade, L1 real-time new-high dip, L3 the reference through the desk's own detector — and the family table |
| `sim.py` | one long exit manager (shorts run on mirrored prices), the live cost model split into commission / spread / borrow, the random-entry baseline |
| `protocol.py` | the registry, the holdout ledger (once per family, across the Mac's and the committed ledger), the one-position portfolio, the seven adoption criteria |
| `diagnose.py` | why a configuration fails: the decomposition, the slices, the rule-based reading, the leads |
| `run.py` | the run: train and validation for every configuration, the choice on train, the gate, the holdout only behind a passed gate, the report and its files |
