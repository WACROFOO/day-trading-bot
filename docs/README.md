# docs/

Design notes and operating guides for the momentum workstation.

| File | What |
|---|---|
| `solution-review-2026-09-03.md` | **start here** — what the desk is, what it is not, how to read every element on screen |
| `daily-operating-guide.md` | the operator's day |
| `ibkr-streaming-design.md` | the IBKR read-only data path: clients 27/28, BarStore, health states |
| `alpaca-setup.md` · `windows-setup.md` | getting the feeds and the launcher running |
| `wiring-market-data.md` | how a data source reaches the screen |
| `dashboard-plan.md` · `design-handoff.md` | the dashboard's plan and its handoff notes |
| `shared-desk.md` | owner and viewer keys; two browsers on one desk |

The desk **does not trade**. There is no order path in any module here, and
two tests fail if one appears.
