# reports/

Read in this order. The second is not interpretable without the first.

| File | What |
|---|---|
| `data_quality.md` | **Start here.** The measured feed: 1-minute history reaches 25 days, pre-market volume is zero for every symbol including AAPL and SPY, 6 of 9 delisted tickers 404. Also the corporate-action handling, what is simply absent (quotes, ticks, halts, float, news) and the exact acquisition steps that would remove the blocker |
| `data_acquisition.md` | **The unblocker.** Which free APIs to sign up for, what each one actually fixes, and what none of them fix. Vendor claims quoted with their source page; the halt feed and the Alpha Vantage demo refusal are MEASURED. Short version: one free Massive (ex-Polygon) key clears all three blockers at 2 years of history |
| `final_report.md` | The study: funnel, the A–F rule table, look-ahead controls, the ablation and its marginals, accept-vs-reject per filter, filter overlap, time-of-day and stock-characteristic cuts, holdout, baselines and placebos, parameter sensitivity, the overfitting audit, the account simulation, and answers to the brief's twelve questions. Verdict last |

Both follow `.claude/skills/trading-report-design`: provenance banner first,
funnel before survivors, rejects visible with the reason that fired, a
"could not check" section that is never omitted, verdict at the end.

Headline, so nobody has to read to the bottom to learn it is unreadable at
the top: **insufficient data to answer the question as asked.** The pipeline
that would answer it is built, tested and one API key away from running on
five years instead of twenty sessions.
