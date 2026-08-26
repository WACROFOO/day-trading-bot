"""Session-aware slicing of the cached Alpaca minute bars.

The cache written by `first-pullback-edge` is one gzipped JSON per
ticker-month: {"YYYY-MM-DD": [[ts, o, h, l, c, v], ...]}. Bars are as the
feed served them — missing minutes are absent, not filled.

The one rule that matters here: a context window never crosses a session
boundary. 150 bars back from 09:45 would otherwise reach into yesterday's
tape, and the overnight gap is exactly the event this project cares about.
Anchors without enough same-session history are DROPPED and counted, never
padded from the previous day.
"""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

FPE = Path(__file__).resolve().parents[2] / "first-pullback-edge"
CACHE = FPE / "data" / "cache" / "alpaca" / "minute_month"


@lru_cache(maxsize=256)
def _month(sym: str, ym: str) -> dict:
    p = CACHE / f"{sym}_{ym}_sip.json.gz"
    if not p.exists():
        return {}
    with gzip.open(p, "rt") as fh:
        return json.load(fh)


def session_bars(sym: str, day: str) -> list[list]:
    """Every cached bar for one ticker-day, ascending. [] if not cached."""
    rows = _month(sym, day[:7]).get(day) or []
    return sorted(rows, key=lambda r: r[0])


def context_window(sym: str, day: str, anchor_ts: int, n: int) -> list[list] | None:
    """The last `n` bars at or before `anchor_ts`, same session only.

    Returns None when the session does not hold `n` bars up to the anchor —
    the caller counts those rather than filling them.
    """
    rows = session_bars(sym, day)
    if not rows:
        return None
    upto = [r for r in rows if r[0] <= anchor_ts]
    if len(upto) < n:
        return None
    return upto[-n:]


def forward_bars(sym: str, day: str, anchor_ts: int, n: int) -> list[list]:
    """The bars actually traded after the anchor — the ground truth path.

    Same session only, so a 30-bar horizon near the close returns short.
    """
    rows = session_bars(sym, day)
    return [r for r in rows if r[0] > anchor_ts][:n]
