# tradingview/ — our Pine implementations

Two different instruments. Confusing them is the most common error here: one
answers WHICH NAME, the other answers WHEN.

| file | what it is |
|---|---|
| `ross-fp-v4.pine` | **THE STRATEGY.** First-pullback entry logic — impulse, pullback, trigger, stop, target, halt-band veto, high-of-day room. Revision in the `REV` constant and on the dashboard (the `//@version=6` line is the Pine LANGUAGE version, not ours) |
| `ross-style-scanner-v2.pine` | **THE SCANNER.** Clean-room approximation of the Day Trade Dash branches; scores the four measurable pillars and exposes 11 Pine Screener columns. Holds no position, has no opinion on entry |
| `ross-fp-v3.pine` | archived predecessor, kept for the audit trail |
| `reverse-split-flag.pine` | standalone split-detection helper |
| `SCANNER-V2-PLAYBOOK.md` | how to operate the scanner: the three modes, the denominator problem, the eleven columns |
| `STRATEGY-COVERAGE.md` | what the strategy script covers, what it structurally cannot (float, halts, 10-second patterns, Warrior RVOL parity), and how to read the dashboard |

**Before pushing any edit:** `python3 scripts/pine_check.py <file>` — catches
top-level forward references (CE10272) and non-const `plotshape` arguments
(CE10123), the two classes that have actually shipped broken from here. It is
a lint, not a compiler; TradingView is the only authority.

Audits and divergence tables live in
`research/momentum-replication/reports/2026-08-pine-v3-audit.md` and
`knowledge-base/daytrade-dash/README.md`.

Paper only. A green dashboard is not an edge.
