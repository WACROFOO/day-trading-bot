# The improvement loop — your trades vs the machine, measured

```
WHY THIS EXISTS · TradingView Paper Trading is a sandbox Pine cannot see:
       the script will never know about a manual trade by itself. Your
       fills enter the repo HERE, and only here. The gap between what you
       traded and what the script signalled is the most valuable data
       this project produces — IF it is logged while the 1m tape still
       exists (Yahoo keeps ~30 days).
DOCTRINE · thresholds move on measurement at n>=30, with the measurement
       committed as a report. Never on one trade, never on feel
       (CLAUDE.md rule 1; the MSGY and score-basket lessons).
```

## The loop, step by step

**1 — Log every trade, same day.** One command per round trip, ET times:

```bash
python3 scripts/trade_log.py add JUNS 2026-08-21 10:01 8.80 10:05 9.40 200 --note "reclaim after deep dip"
python3 scripts/trade_log.py list
```

**2 — Audit: the engine's verdict on each of your trades.**

```bash
python3 scripts/trade_audit.py
```

Fetches each trade's real tape, replays the strategy's decision core
with a trace, and classifies every trade:

| class | meaning | what it feeds |
|---|---|---|
| `MATCHED` | the engine traded within 3 min of you | agreement rate |
| `MISSED · blocked by <gate>` | pattern present, a named gate said no | the gate's miss ledger |
| `OFF-PATTERN` | no push/dip structure at your entry | a candidate NEW setup class |
| `NO-DATA` | tape older than ~30 days | log sooner next time |

**3 — Accumulate.** Nothing changes until a pattern repeats. The
aggregate table at the bottom of the audit is the ledger: which gate
blocks how many of your trades, and what those trades netted.

**4 — Re-measure at n≥30.** When one gate's ledger holds ≥30 profitable
misses, sweep it on real tape with the benchmark harness
(`research/momentum-replication/pine_bench.py` — the same tool that
measured the same-bar policy and the ghost layer): rerun the engine with
the gate relaxed over the accumulated symbol-days and compare ΣR. Write
the result to `research/momentum-replication/reports/`.

**5 — Change the threshold WITH the citation, or keep it WITH the
citation.** Either way the input's tooltip gets the report path. That is
the whole difference between calibration and drift.

**6 — Score the other side too.** MATCHED trades where the engine lost
and you exited better = exit-rule data (the fixed-2R-vs-into-strength
divergence, `research/momentum-replication/reports/2026-08-ispo-stream.md`). OFF-PATTERN winners that
repeat = a new lane candidate, spec'd like the fast lane was (from a
named live case, with its own gates).

## What is automatic and what is deliberately not

Automatic: tape fetch, replay, per-trade verdict, gate ledger,
aggregation — one command. Deliberately manual: logging the trade (only
you know your fills) and changing a threshold (only a committed
measurement may do that). An "automatic" loop that retunes gates on
every trade would overfit to the last winner — that is how the
score-basket died (`research/momentum-replication/reports/2026-08-score-basket.md`: 16/16 against).

## Current state

Journal: 1 trade — XPON 2026-08-24, classified OFF-PATTERN by the audit
(bounce, not a first-pullback). The ledger needs n>=30 before any
threshold moves.

Paper only. The loop improves the tool's honesty and calibration; it
does not create an edge that the 894-session replication says is not
there. If the ledger someday shows otherwise at scale, that will be a
measured finding, and it will be written up like every other one.
