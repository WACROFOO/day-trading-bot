# tests/ — 33 tests, all about being wrong quietly

`python3 -m pytest tests/ -q` from the study root.

| File | Guards |
|---|---|
| `test_lookahead.py` | HOD is the high SO FAR, not the eventual daily high · prefix reproduction (bars 0..k must equal the first k+1 of a full pass) · the engine's snapshot list never exceeds the bar it was handed · **truncation audit** — cut a session at 45/50/55/60 bars and every trade entered before the cut returns identical · no entry precedes its own scan timestamp |
| `test_execution.py` | no-touch is not a fill · a clean touch fills AT the trigger · a gap past the limit is a MISS, not an impossible fill · slippage that breaches the cap is a MISS · the limit offset does not widen with the cost model · participation cap · **fill ordering**: entry-only, stop-only, both-touched, and the policy that decides · an ambiguous bar is never silently a winner |
| `test_setups.py` | pullback numbering 1 / 2 / 3 and the reset on a lower peak · an armed order dies when the next bar trades through the stop · retracement and bar-count invalidation · every gate id present on every candidate · HOD room passes on a new high and fails under a lower high · clustered EMAs count once · LULD band tiers · **unknown halt band fails CLOSED inside RTH** · a sub-tick stop is refused |

Two tests encode findings rather than intentions and say so in their
docstrings: the HOD-room test needs the ATR fallback switched off to be
constructible at all (with it on, a stop too wide for 1R of room is replaced
by a ~1-ATR stop and the gate hands back its pass), and the two-bar pullback
test cannot use a lower second low, because an armed setup whose next bar
trades through the stop is correctly killed.
