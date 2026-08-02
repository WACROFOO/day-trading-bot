# tests/

| File | Covers |
|---|---|
| `test_paper_trading.py` | `src/paper_trading/` — broker fills, risk rules, ledger arithmetic |
| `test_scanner.py` | The five-pillar scanner |

Run: `python -m pytest tests/`

The research harness under `research/momentum-replication/` is deliberately
not covered here — its correctness is argued by its diagnostics and the
defect log (`HISTORY.md`), which is the record of what unit tests would have
had to catch.
