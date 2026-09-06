# fixtures/market_replay/

Recorded market sessions, one JSON object per line, replayed so the desk can
be exercised without a live feed.

| File | What |
|---|---|
| `demo_momentum_day.jsonl` | a synthetic momentum day for demos and tests |
| `workstation_open_2026-09-01.jsonl` | a real recorded open |

Replay exists so scanners, charts and cards behave **identically** on
recorded and live data — the same normalized records either way. A test that
only passes on a fixture is not evidence about live behaviour.
