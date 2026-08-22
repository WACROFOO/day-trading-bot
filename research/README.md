# research/

Research efforts, one folder per question.

| Folder | Question |
|---|---|
| `momentum-replication/` | Can the documented small-cap momentum strategy be implemented mechanically and does it survive contact with real market data? (The project's main body of work — start at its README; `reports/` holds 27 measurements, cite before re-deriving) |
| `trade-log/` | Which propositions did the tools actually make, and what happened to the ones nobody acted on? `propositions.csv` is the source of truth, `propositions.md` its readable mirror. Written by `scripts/tradelog.py` |
| `megaday-study/` | **Étude terminée.** 250+ megadays en 1 min : anatomie, taux de base, surfaces stop/sortie, protocole gelé et holdout ouvert une fois. Verdict dans `RESULTS.md` — moteur de rejet, pas de génération de signal ; résultat durable : l'échec des backtests était un échec de paramètre (cap de stop à 3 % jamais sourcé). `PLAN.md` = le plan suivi, `data/` = les artefacts |
| `challenge-tickers/` | Which tickers he named per session in the $2,000 challenge recaps, each validated against that day's real tape. `challenge-tickers.csv` is the table; the June–July span is extracted from corpus captions, the Aug 2026 span is titles-only (YouTube bot-gates caption fetch from this host) |
| `trade-journal/` | The OPERATOR's actual fills (TV Paper Trading is invisible to Pine) vs the engine's verdicts — the improvement loop. `journal.csv` written by `scripts/trade_log.py`, audited by `scripts/trade_audit.py` |

Superseded research lives in `../archive/`, not here.
