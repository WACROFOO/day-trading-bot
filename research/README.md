# research/

Research efforts, one folder per question.

| Folder | Question |
|---|---|
| `momentum-replication/` | Can the documented small-cap momentum strategy be implemented mechanically and does it survive contact with real market data? (The project's main body of work — start at its README; `reports/` holds 27 measurements, cite before re-deriving) |
| `trade-log/` | Which propositions did the tools actually make, and what happened to the ones nobody acted on? `propositions.csv` is the source of truth, `propositions.md` its readable mirror. Written by `scripts/tradelog.py` |
| `megaday-study/` | **Étude terminée.** 250+ megadays en 1 min : anatomie, taux de base, surfaces stop/sortie, protocole gelé et holdout ouvert une fois. Verdict dans `RESULTS.md` — moteur de rejet, pas de génération de signal ; résultat durable : l'échec des backtests était un échec de paramètre (cap de stop à 3 % jamais sourcé). `PLAN.md` = le plan suivi, `data/` = les artefacts |
| `challenge-tickers/` | Which tickers he named per session in the $2,000 challenge recaps, each validated against that day's real tape. `challenge-tickers.csv` is the table; the June–July span is extracted from corpus captions, the Aug 2026 span is titles-only (YouTube bot-gates caption fetch from this host) |
| `first-pullback-edge/` | Does the First Pullback have a positive edge, and which filters contribute? A six-variant ablation (A basic → F full) of `ross-fp-v4.pine` with point-in-time universe, look-ahead tests, cost/ambiguity models. **Verdict: NO EDGE** over 25,716 survivorship-free gapper-days 2016-2026 — every variant negative in every year and in an untouched holdout; a random entry minute beats every variant. `first-pullback-edge/reports/final_report.md` |
| `edge-hunt/` | Is any version of the bot — Ross's rules or new hypotheses stated as such — positive after costs on data it never saw? Holdout-guarded: train 2016-2022, validation 2023, holdout 2024-2026 opened once per family, five-part adoption rule. `PREREGISTRATION.md` first (written before any run), then `REPORT.md` |
| `kronos-probe/` | Does an open-source candlestick foundation model (Kronos) carry information about first-pullback outcomes? **Verdict: no usable ranking signal.** Calibrated in aggregate on unselected anchors (0.4267 predicted vs 0.4381 realised) but never beats a one-line context statistic; its forecast correlates 0.756 with the context-window mean and −0.041 with the outcome. `REPORT.md` first, then `EXTERNAL_BRIEF.md` |
| `paper-exercise/` | The live IBKR paper exercise itself, as opposed to the historical studies above: `reports/` holds the per-session read-outs and the analyses built on the ledger. Pre-registered in `docs/preregistration.md`; the ledger is `data/journal.sqlite` |
| `trade-journal/` | The OPERATOR's actual fills (TV Paper Trading is invisible to Pine) vs the engine's verdicts — the improvement loop. `journal.csv` written by `scripts/trade_log.py`, audited by `scripts/trade_audit.py` |

Superseded research lives in `../archive/`, not here.
