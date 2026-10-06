"""The 5-minute state of a name whose 1-minute chart gives no pullback. Display only.

The owner, 2026-10-06: "adapt handling the green uptrending 1 min bars without a
proper pullback in the one minute chart." The desk's detector needs a red
1-minute candle, so a straight green run arms nothing and the card said nothing
about why. The method's answer is the 5-minute chart — *"the one minute is fine
what's the first five minute candle to make a new high it'll be over 65 so your
entry is 65 your stop is the low at 60"* (`Xdw5azEqs6o` [00:12:38]).

This module names that state on the desk and in `scripts/watch.py`:

    EXTENDED     >= 4 green 1-minute candles in a row, the last at a new high of
                 day, and no 5-minute pullback yet — the method waits
    5M PULLBACK  a 5-minute candle closed without a new high after a 5-minute
                 impulse; its high + 1c is the first-new-high trigger, the
                 pullback low - 1c the stop

It never places, arms or sizes anything: there is no path from here to an order.
Whether the 5-minute entry is traded was preregistered as E1 (research/edge-hunt/
PREREGISTRATION.md, addendum 2026-10-06b; `scripts/five_minute.py`), and this
module's machine is the same as that script's, pinned by tests/test_five_minute_desk.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

BarT = Tuple[int, float, float, float, float, float]      # (start_epoch, o, h, l, c, v), completed

CANDLE_S = 300
MIN_IMPULSE, MAX_IMPULSE, MIN_RANGE_PCT, MAX_PULLBACK = 2, 6, 2.0, 4   # FirstPullbackDetector defaults
EXT_GREEN = 4

EXTENDED = "EXTENDED"
PULLBACK_5M = "5M PULLBACK"


@dataclass(frozen=True)
class FiveMinuteState:
    state: Optional[str]                # EXTENDED · 5M PULLBACK · None
    since: Optional[int] = None         # epoch of the bar that started the state
    trigger: Optional[float] = None     # 5M PULLBACK: the pullback candle's high + 1c
    stop: Optional[float] = None        # 5M PULLBACK: the pullback low - 1c
    green_run: int = 0                  # consecutive green 1-minute candles at the last bar
    n_pull: int = 0

    @property
    def stop_pct(self) -> Optional[float]:
        if self.trigger and self.stop is not None and self.trigger > self.stop:
            return round((self.trigger - self.stop) / self.trigger * 100.0, 2)
        return None

    def text(self) -> str:
        if self.state == EXTENDED:
            return (f"{self.green_run} green 1-min candles to a new high, no 1-min pullback — "
                    f"the method waits for the first 5-minute candle to make a new high · display only, no order")
        if self.state == PULLBACK_5M:
            return (f"5-min pullback ({self.n_pull} candle{'s' if self.n_pull > 1 else ''}): the first 5-min candle "
                    f"over {self.trigger:.2f} is the method's entry, stop {self.stop:.2f} ({self.stop_pct:.1f}%) · "
                    f"E1 is untested on live orders · display only, no order")
        return ""


def candles5(rows: Sequence[BarT]) -> List[dict]:
    """Clock-aligned 5-minute candles from completed 1-minute bars."""
    out: List[dict] = []
    for i, (t, o, h, l, c, v) in enumerate(rows):
        slot = int(t) // CANDLE_S * CANDLE_S
        if out and out[-1]["t"] == slot:
            k = out[-1]
            k["h"], k["l"], k["c"], k["v"] = max(k["h"], h), min(k["l"], l), c, k["v"] + v
            k["last"] = i
        else:
            out.append({"t": slot, "o": o, "h": h, "l": l, "c": c, "v": v, "first": i, "last": i})
    return out


def _green(k: dict) -> bool:
    return k["c"] > k["o"]


def _impulse_ok(imp: List[dict]) -> bool:
    if len(imp) < MIN_IMPULSE or imp[0]["o"] <= 0:
        return False
    return 100.0 * (max(k["h"] for k in imp) - imp[0]["o"]) / imp[0]["o"] >= MIN_RANGE_PCT


def walk(rows: Sequence[BarT], until: Optional[int] = None):
    """Run the 5-minute machine over the candles COMPLETED by `until` (default:
    every candle whose slot has a later minute after it, or that is full).
    Returns (placements, state, impulse, pullback) — placements as
    scripts/five_minute.e1_placements makes them (entry, stop, order_t, seq, n_pull)."""
    ks = candles5(rows)
    if until is not None:
        ks = [k for k in ks if k["t"] + CANDLE_S <= until]
    out: list = []
    imp: List[dict] = []
    pull: List[dict] = []
    seq = 0
    state = "seek"
    for k in ks:
        if state == "pull":
            if k["h"] > pull[-1]["h"]:
                state, imp, pull = "seek", [], []
                if _green(k):
                    imp = [k]
                continue
            pull.append(k)
            if len(pull) > MAX_PULLBACK:
                state, imp, pull = "seek", ([k] if _green(k) else []), []
                continue
            if min(p["l"] for p in pull) < min(p["l"] for p in pull[:-1]) and k["l"] < min(b["l"] for b in imp):
                state, imp, pull = "seek", [], []
                continue
            out.append(_placement(pull, seq))
            continue
        if _green(k):
            imp.append(k)
            del imp[:-MAX_IMPULSE]
        elif _impulse_ok(imp):
            seq += 1
            state, pull = "pull", [k]
            out.append(_placement(pull, seq))
        else:
            imp = []
    return out, state, imp, pull


def _placement(pull: List[dict], seq: int) -> dict:
    last = pull[-1]
    return {"entry": round(last["h"] + 0.01, 4), "stop": round(min(p["l"] for p in pull) - 0.01, 4),
            "order_t": last["t"] + CANDLE_S, "seq": seq, "n_pull": len(pull)}


def green_run(rows: Sequence[BarT]) -> int:
    """Consecutive green 1-minute candles ending at the last bar, counted only
    when the last of them made a new high of day."""
    if not rows:
        return 0
    n = 0
    for t, o, h, l, c, v in reversed(rows):
        if c > o:
            n += 1
        else:
            break
    if not n:
        return 0
    last_h = rows[-1][2]
    if any(r[2] >= last_h for r in rows[:-1]):
        return 0
    return n


def state_at(rows: Sequence[BarT], now: int) -> FiveMinuteState:
    """The display state from the completed 1-minute bars of the session (04:00
    on) at epoch `now`. A 5-minute pullback outranks the 1-minute extension: once
    a 5-minute candle has closed without a new high, the trigger is the news."""
    rows = [r for r in rows if r[0] + 60 <= now]
    if not rows:
        return FiveMinuteState(None)
    placements, st, imp, pull = walk(rows, until=now)
    if st == "pull" and placements and placements[-1]["order_t"] + CANDLE_S > now:
        p = placements[-1]
        return FiveMinuteState(PULLBACK_5M, since=p["order_t"] - CANDLE_S, trigger=round(p["entry"], 2),
                               stop=round(p["stop"], 2), n_pull=p["n_pull"])
    run = green_run(rows)
    if run >= EXT_GREEN:
        return FiveMinuteState(EXTENDED, since=rows[-run][0], green_run=run)
    return FiveMinuteState(None)
