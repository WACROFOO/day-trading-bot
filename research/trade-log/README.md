# Trade-proposition ledger

Every call this system makes, taken or not — because a broker statement
cannot show the reject that ran.

```
python3 scripts/tradelog.py add --sym IPST --source pine-strategy \
    --verdict TRIGGER-SET --entry 7.46 --stop 7.30 --target 7.78 --shares 1249
python3 scripts/tradelog.py measure --id 20260817-IPST-01   # tape -> mfe/mae/counterfactual
python3 scripts/tradelog.py report                          # the scoreboard
python3 scripts/tradelog.py md                              # rebuild the readable mirror
```

**Log the proposition when it is made, not after the outcome is known.**
Hindsight rewrites verdicts silently; a timestamped row cannot be edited by
memory. `measure` must run the SAME DAY — Yahoo's 1-minute history expires,
and a row measured late is flagged `UNMEASURABLE` rather than guessed.

`propositions.csv` is the source of truth. `propositions.md` is generated.

Analysis: `research/momentum-replication/reports/2026-08-wrong-trades.md`.
Rule: nothing gets tuned on fewer than ~10 measured instances.
