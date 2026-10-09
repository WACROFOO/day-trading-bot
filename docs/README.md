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
| `AUDIT-RESPONSE-2026-09-08.md` | **the outside review, checked against the code** — six findings confirmed and fixed the same day, the measurement points, the five decisions only the owner can make |
| `REVIEW-PACK-2026-09-08.md` | **for an outside reviewer** — the whole exercise in one self-contained page, with the questions to ask |
| `READINESS-2026-09-08.md` | **the pre-session review** — 90 audit findings judged by hand, the 26 fixed (recording path, then trading path), the ones refused and why, what is still open |
| `ASSESSMENT-2026-09-07.md` | **the full review** — what is included, what is left, results so far (none live), how it runs, where the logs are, the improvement loop |
| `STATUS-2026-10-08.md` | **start the next session here** — where things stand after 8 October: the F9 result, the desk as a manual decision tool (card, order panel, catalyst, Time & Sales, layout), the owner's decisions, what is not verified live yet, the open list, how to run |
| `STATUS-2026-09-06.md` | **plain-words status** — what works, what is left, what the owner does |
| `desk-assessment-2026-10-08.md`, `desk-assessment-2026-10-08/` | **the desk as a manual decision tool** — the gap table, the evidence from 2026-10-06/07, what was built, and before/after screenshots of the card |
| `desk-grid-audit-2026-10-09.md`, `desk-grid-audit-2026-10-09/` | **the desk, grid by grid** — the owner's 04:34 ET screenshot numbered by zone: what each element serves, what Ross uses (his scanners, charts, Level 2, the tape), keep / trim / cut per element, what is missing — and what was applied the same day, with after screenshots and the Level 2 costs |
| `day-runbook.md` | **run this** — the one command, what happens around it, the human-only commands |
| `preregistration.md` | the exercise's sample size, stopping rules and failure condition — **PROPOSED until the owner sets the values, before the first order** |

The desk **does not trade**. There is no order path in any module here, and
two tests fail if one appears.

An order path does now exist, deliberately outside that boundary:
`src/execution/` holds the one writable IBKR connection, pointed at a paper
account it refuses to leave. It is a separate package on a separate
connection precisely so the sentence above stays true and provable — a test
fails if any desk module imports it.
