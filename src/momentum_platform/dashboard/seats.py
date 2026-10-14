"""Seat rotation: a dead name's seat goes to a new runner (owner, 2026-10-14: "go ahead
with the seat rotation too"; recorded in docs/preregistration.md §5).

The desk holds `maxSymbols` names. Until 2026-10-14 it never dropped one: once the seats
were full a later runner could not get in (2026-10-12 04:17: of sixteen gappers the
scanner found, one got a seat). Now:

  dead       the cascade answered REJECT — a Layer 1 kill: outside the price band, under
             three of the Five Pillars, 25 % off the high, a fund, a split, a buyout — on
             every rebuild for at least `seatDeadMinutes` (15). Any other answer, STALE
             included, restarts the clock. Fifteen minutes is this desk's Approximation:
             long enough that one bad print or a dip under +10 % does not cost a seat.
  never      a name the bot may hold an order in (the ledger's alive orders), a manual
             position, a live plan or a forming pullback, the name selected for the tape
             and the book
  order      the longest dead first, one seat for one new name, the new names in the
             scanner's order
  no return  a name that gave up its seat does not take one back by rotation the same day

Nothing here is a gate: it decides which names the desk watches, not what it trades. A
name off the desk is no longer a candidate, which is why it is an amendment.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple


class SeatClock:
    """How long each name has been dead, from the cascade's answer at every rebuild."""

    def __init__(self, dead_minutes: float) -> None:
        self.dead_after = timedelta(minutes=max(0.0, float(dead_minutes or 0)))
        self.dead_since: Dict[str, datetime] = {}
        self.why: Dict[str, str] = {}
        self._gave_up: Dict[str, str] = {}            # symbol -> session day it gave up its seat

    @property
    def on(self) -> bool:
        return self.dead_after > timedelta(0)

    def observe(self, now: datetime, answers: Dict[str, Tuple[Optional[str], Optional[str]]]) -> None:
        """`answers`: {symbol: (cascade verdict, killedBy)} for every name on the desk."""
        for sym, (verdict, killed_by) in answers.items():
            if verdict == "REJECT":
                self.dead_since.setdefault(sym, now)
                self.why[sym] = killed_by or "?"
            else:
                self.dead_since.pop(sym, None)
                self.why.pop(sym, None)
        for sym in [s for s in self.dead_since if s not in answers]:
            self.dead_since.pop(sym, None)
            self.why.pop(sym, None)

    def dead(self, now: datetime, keep: Iterable[str] = ()) -> List[Tuple[str, datetime]]:
        """Names dead long enough to give up their seat, the longest dead first."""
        if not self.on:
            return []
        keep = set(keep)
        out = [(s, t) for s, t in self.dead_since.items() if s not in keep and now - t >= self.dead_after]
        return sorted(out, key=lambda x: (x[1], x[0]))

    def gave_up(self, sym: str, day: str) -> None:
        self._gave_up[sym] = day
        self.dead_since.pop(sym, None)
        self.why.pop(sym, None)

    def gave_up_today(self, sym: str, day: str) -> bool:
        return self._gave_up.get(sym) == day


def pairs(dead: List[Tuple[str, datetime]], fresh: List[str]) -> List[Tuple[str, datetime, str]]:
    """(dead name, dead since, the new name taking its seat) — the longest dead first."""
    return [(s, t, new) for (s, t), new in zip(dead, fresh)]
