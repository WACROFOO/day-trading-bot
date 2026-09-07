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
| `paper-exercise-brief.md` | **the spec for the paper-trading exercise** — platform state, the priors it must be framed by, the decision ledger, and what it cannot check |
| `ASSESSMENT-2026-09-07.md` | **the full review** — what is included, what is left, results so far (none live), how it runs, where the logs are, the improvement loop |
| `STATUS-2026-09-06.md` | **plain-words status** — what works, what is left, what the owner does |
| `day-runbook.md` | **run this** — the one command, what happens around it, the human-only commands |
| `preregistration.md` | the exercise's sample size, stopping rules and failure condition — **PROPOSED until the owner sets the values, before the first order** |

The desk **does not trade**. There is no order path in any module here, and
two tests fail if one appears.

An order path does now exist, deliberately outside that boundary:
`src/execution/` holds the one writable IBKR connection, pointed at a paper
account it refuses to leave. It is a separate package on a separate
connection precisely so the sentence above stays true and provable — a test
fails if any desk module imports it.
