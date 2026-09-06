"""The decision ledger — the record of what was seen, decided and done.

Neutral ground. `momentum_platform` writes decisions and board snapshots
into it; `execution` writes orders and fills into it; neither imports the
other, and the guard test that keeps the desk order-free stays true. The
ledger is the bus between them: the runner reads the desk's decisions out
of SQLite rather than out of a live object.

The exercise it serves is `docs/paper-exercise-brief.md`. The things this
package exists to make measurable, none of which a P&L number gives you:

  R1  the denominator     every candidate, not just the ones taken
  R2  point in time       what was knowable at the instant, never what is true now
  R3  both R denominators planned (trigger - stop) and realised (fill - stop)
  R4  NBBO at fill        without it a paper fill is a gift, not a result
  R11 replay              the stored inputs must reproduce the stored verdict
"""
