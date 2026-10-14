# scanners/

Candidate discovery. A scanner match is a **research candidate**, never an
entry signal and never an order.

| Module | What |
|---|---|
| `five_pillars.py` | the Confirmed course pillars: price $2-20, gain >=10%, daily RVOL >=5x, float <20M, catalyst. Keeps `technical_score` (0-4) and `full_score` (0-5) separate on purpose — the Warrior scanner does not automatically require news |
| `momentum_events.py` | HOD Momentum (which also records the new highs it turns down, with the condition that failed), Running Up, squeeze, 52-week breakout, and **Former Momo** since 2026-10-14 (this row claimed one before it existed) — a new high on a former runner, a +100 % day in the past year, on a looser trigger. Every one an **Approximation** of a server-side rule that is not public |
| `running_up_filters.py` | Running Up, strengthened (2026-10-09): four named triggers, one alert per leg — Approximations |
| `top_lists.py` | the ranked lists |
| `base.py` | shared scanner scaffolding and edge tracking |

Two price bands exist and must not be confused: the Confirmed course pillar
band ($2-20), which the pillars and verdict evaluate, and the operator's wider
DISCOVERY band, which decides what the desk admits at all. The second is
labelled as the operator's wherever it appears.
