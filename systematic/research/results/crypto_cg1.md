# Gate CG1: frozen crypto rule, backtest before the hold-out

Run 2026-11-25. Rule `crypto-primary-v1` (frozen_rules.json, revision 2). BTC/USD Bitstamp daily closes to 2024-11-30. Cost 0.12% per unit traded (2× test: 0.24%). Cash 0%, no contributions, no tax. Criteria are in `scripts/crypto_cg1.py`, fixed before the first run.

**Verdict: PASS.** A (drawdown halving): pass; B (deflated Sharpe 1.000, N = 10): pass; C (2× costs): pass.

| Window | Strategy CAGR / Sharpe / max DD | Buy-and-hold CAGR / Sharpe / max DD | DD ratio | Turnover/yr |
|---|---|---|---|---|
| W1 2015-2020 | 42.6% / 1.67 / -30.2% | 112.5% / 1.38 / -83.4% | 0.36 | 3.8 |
| W2 2021-2023 | 13.6% / 0.82 / -20.9% | 12.9% / 0.51 / -76.7% | 0.27 | 5.5 |
| W3 Jan-Nov 2024 (reported only) | 49.0% / 1.79 / -14.0% | 134.7% / 1.84 / -26.2% | 0.53 | 7.5 |
| Full 2015 - Nov 2024 | 34.1% / 1.48 / -30.2% | 78.1% / 1.17 / -83.4% | 0.36 | 4.7 |

- **2× costs (full period):** 33.3% / 1.45 / -30.6%, against buy-and-hold Sharpe 1.17.
- **C1 benchmark, 200-day (full period):** 75.3% / 1.30 / -67.5%, turnover 5.5/yr.
- **Same rule on ETH/USD** (2018-08 → 2024-11-30): 20.2% / 1.07 / -19.8%, against buy-and-hold 47.8% / 0.89 / -79.3%.
- **Max drawdown in EUR** (USDC leg converted at FRED EUR/USD): -27.4%, against the −30% pain limit.

In-sample for the literature (2015–2023) and already partly seen by the research replication; the forward record from 26 Nov 2026 is the true out-of-sample test.
