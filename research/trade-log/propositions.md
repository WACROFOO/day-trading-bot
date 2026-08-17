# Trade propositions — readable mirror

```
Generated from propositions.csv by scripts/tradelog.py md.
The CSV is the source of truth. Outcome columns are MEASURED
from tape.py, never typed from memory.
```

| id | ts ET | sym | source | verdict | entry/stop/target | room R | taken | outcome | counterfactual | error class |
|---|---|---|---|---|---|---|---|---|---|---|
| 20260817-IPST-01 | 2026-08-17 10:50 | IPST | pine-strategy | TRIGGER-SET | 7.46/7.30/7.78 | — | yes | LOSS | -1.00 (stop 7.30 touched 10:55, before target 10:58) | NONE |
| 20260817-TRUG-01 | 2026-08-17 10:25 | TRUG | pine-strategy | TRIGGER-SET | 1.7801/1.7300/1.8803 | 0.4 | no | NOT-TAKEN | -1.00 (10:28 low 1.56 < stop) | PRESENTATION |
| 20260817-TRUG-02 | 2026-08-17 10:25 | TRUG | chat | NO | —/—/— | — | yes | LOSS | — | ANTICIPATION |
| 20260811-MSGY-01 | 2026-08-11 10:26 | MSGY | chat | NO | —/—/— | — | no | NOT-TAKEN | + ran 4.39 -> 5.43 (+24%) | SELECTION |
| 20260814-WETO-01 | 2026-08-14 09:20 | WETO | now-board | REVIEW | —/—/— | — | no | NOT-TAKEN | -1.00 (opened 10.65, low 9.70 in bar one) | VARIANCE |
| 20260814-ONFO-01 | 2026-08-14 10:31 | ONFO | now-board | WATCH | 4.00/—/— | — | yes | WIN | + reclaimed 4.00 at 10:56, printed 5.57 by 11:03 (+39%) | NARRATION |
| 20260814-HHS-01 | 2026-08-14 10:04 | HHS | now-board | NO | —/—/— | — | no | NOT-TAKEN | pinned 4.2-4.5 all session | NONE |
| 20260813-FGI-01 | 2026-08-13 10:52 | FGI | chat | REVIEW | 11.45/10.80/— | — | yes | WIN | + ran to 19.93 by 12:37 | NONE |
| 20260812-WYHG-01 | 2026-08-12 10:58 | WYHG | chat | NO | —/—/— | — | no | NOT-TAKEN | - continued to 5.26 by 08-14 | NONE |
| 20260811-TDIC-01 | 2026-08-11 11:08 | TDIC | chat | NO | —/—/— | — | yes | LOSS | — | NONE |

## Error taxonomy

- **SELECTION** — wrong vehicle — it should never have been on the board
- **EXECUTION** — right vehicle, wrong moment / size / exit
- **PRESENTATION** — the information was present but invisible
- **DATA** — the information was genuinely absent
- **NARRATION** — the tool was right, the human summary was wrong
- **ANTICIPATION** — the operator acted before the trigger — no proposition existed at that price
- **VARIANCE** — the rule fired correctly; the outcome was simply unfavourable
- **NONE** — no error — correct call, correct outcome

Paper only. Selection evidence, not edge.
