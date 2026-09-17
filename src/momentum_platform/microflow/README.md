# microflow/ — the 10-second micro pullback, inside the 1-minute candle

The package behind `docs/PLAN-10s-micro-pullback.md`. One module per
responsibility, so a later change touches one file and one test.

**1-minute is the base. 10-second confirms inside a forming momentum
candle.** Not a 10-second strategy.

## Modules

| module | responsibility | status |
|---|---|---|
| `config.py` | every parameter, in one frozen object, each carrying where it came from and whether it was measured | **built** |
| `bars.py` | read 10s candles, aggregate to minutes, assert the two resolutions agree | **built** |
| `spread.py` | the executability gate — is this stop big enough against the spread to be worth taking | **built** |
| `measure.py` | Phase 0 measurements: dip depth against spread, coverage, missing bars | **built** |
| `context.py` | Layer A — the 1-minute state machine. Is this a healthy momentum move? Arms HUNTING, never enters | Phase 1 |
| `timing.py` | Layer B — the 10-second micro pullback inside the forming minute. Fires the trigger, sets the stop | Phase 1 |
| `detector.py` | composes A + B + the gates into setups, and writes them to the ledger | Phase 1 |
| `risk.py` | concurrent-position caps: 3 positions, 3 R of open risk, cash before margin | Phase 2 |

## Contracts between them

```
bars.load(conn, day)        -> {symbol: [Candle]}        10s, ordered, gaps preserved
bars.to_minutes(candles)    -> [Candle]                  the 1m aggregate of those 10s
bars.assert_sync(fine, min) -> None | raises             M3: they describe the same instant

spread.gate(trigger, stop, bid, ask, cfg) -> Verdict     PASS / FAIL / UNKNOWN, with the reason

context.Context(cfg).on_minute(bar, ind)  -> State       IDLE | HUNTING
timing.Timing(cfg).on_tenth(bar, forming) -> Setup|None  the entry, stop and why

detector.Detector(cfg).on_bar(...)        -> [Setup]     what a session produced
```

Every rule returns **why**, never a bare boolean. A gate that cannot say
which condition failed is how a card once showed `FLOAT 3.38M` beside
`float too big` (`.claude/skills/trading-report-design/SKILL.md`).

## Rules for changing anything here

1. A parameter change is a `config.py` change and nothing else. No number
   is written twice.
2. Every value in `config.py` carries `origin` and `evidence_status`.
   `LOCAL_ADDITION` must justify itself in its own text.
3. No module here may place, cancel or amend an order. The order path lives
   in `src/execution/` and a guard test keeps it out of the data packages.
4. Nothing reads the future. Layer B sees closed 10-second candles and the
   forming minute as it stood at that instant, never the finished minute.
