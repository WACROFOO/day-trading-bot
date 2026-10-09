"""Running Up, strengthened (owner, 2026-10-09): four named triggers, one alert per leg.

A Running Up alert says "look at this name now". It is a research candidate,
never an entry signal and never an order: the session builder hands scanner
events only to the notification router and the frames' alert list. The
cascade, the first-pullback detector, the decision card and the runner work
from bars, reference data, halt status and the ledger — a scanner never gates
the bot (`tests/test_running_up_filters.py` checks it on a replayed day).

Each alert names the trigger that fired in its branch (`running_up.<name>`);
its reasons carry every trigger and qualifier, pass or fail.

Triggers — any one fires (every threshold an Approximation: the platform's
Running Up "move size and window: UNKNOWN", `knowledge-base/strategies/SCANNERS.md` §B4):

  pct_in_n     the price `pct_threshold` % over the LOWEST LOW of the last
               `pct_window_minutes` one-minute bars, on a bar that traded and is
               not red. 5 % in 5 minutes is the platform's "Squeeze Up 5% in
               5min" branch, which he calls "kind of like a pre-alert for
               something possibly that will go up 10 in 10 minutes"
               (yg5E_mqGFGg @00:17:16). Measured from the window's low, not from
               the close N minutes ago: Running Up is a stock "squeezing up right
               now even if it's below its high of day" (w97KlUrVDk0 @01:00:52) —
               a curl off a dip — and a close-to-close window anchored above the
               dip does not see it.
  vol_surge    up `surge_move_pct` % over `surge_window_minutes` (close against
               the close that long ago) with the 5-minute volume at least
               `surge_rvol_5m` x the recent 5-minute windows (the desk's rvol5m),
               on a bar that traded and is not red. "3% in 2 minutes with
               five-minute RVOL of at least 2x" is the clean-room Running Up
               starting point of the mastery bundle
               (CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/source-analysis.md,
               "Running Up"), labelled there as a starting point, not a recovered
               setting.
  new_hod      the bar's high AND its close above the prior high of day, with
               rvol5m at least `hod_rvol_5m` — the same file's "Five Pillars HOD
               alert" (starting point 2x). His Running Up EXCLUDES the high of day
               (SCANNERS.md §B4, w97KlUrVDk0 @01:00:52); this desk's tile includes
               it by owner decision (running_up 3.1.0, 2026-09-23: "every runner
               in this tile whether or not it is at its high"). A local display
               choice, labelled as one.
  halt_resume  the first print after a halt the name ran INTO (its last close
               before the halt above the close `halt_lookback_minutes` earlier):
               "halted_up -> usually resumes higher", and the named setup is the
               dip and rip on resumption (knowledge-base/strategies/PARAMETERS.md
               §8b). The halt is the official status the desk feeds
               (`HotState.set_halt`); nothing is inferred from bars here. The
               resumption bar is often the red flush, so no colour test.

Qualifiers — they gate the alert and are reported as reasons:

  price_band      $2–20, FILTERS.md Layer 0's scanner dial ("set these once,
                  leave them wide"), also the Confirmed pillar band.
  float           only a VERIFIED float over 20M (FILTERS.md Layer 0) silences
                  it. Unknown, or a shares-outstanding upper bound, never does:
                  "A blank float is 'verify', never 'dead'" (PLAYBOOK.md).
  session_window  07:00–11:30 ET: "he uses them 07:00–10:00 ET (w97 [00:47:48])
                  and stops at 11:30 (eCSzHYl8apo [00:09:52])" (SCANNERS.md,
                  Layer A); the bot's entry window starts at 07:00 too.

No share-count floor. The method sets none on the pre-market ("Pre-market
volume has a CEILING and no floor", FILTERS.md: he traded NCTY on 8,000
pre-market shares) and a discovery alert does not invent one. A trigger needs
the bar to have traded at all, which also keeps a halt's empty minutes silent.
The cost, measured on the recorded days: 43 of its 151 false alarms (1,007
alerts) were moves of under 10,000 shares (research/running-up-2026-10-09/).

One alert per leg: the triggers share one rising edge per symbol. A repeat
needs every trigger quiet (or a qualifier failing) for `rearm_minutes`
completed bar MINUTES — counted on the bars, never on snapshots, which arrive
seconds apart on a live feed (running_up 3.2.0's lesson: VEEE alerted at
09:55, 09:56 and 09:57 on one move) — and then a trigger firing again. A halt
ends the leg it interrupted, so the resumption is always a new alert.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from ..models import Bar, FloatQuality, Reason, ScannerEvent, SymbolSnapshot
from ..state import HotState, SymbolState
from .base import Scanner, _round

ET = ZoneInfo("America/New_York")

#: Trigger names, in the order the branch is chosen when several fire on one
#: bar: the rarest and most specific first.
TRIGGERS: Tuple[str, ...] = ("halt_resume", "new_hod", "pct_in_n", "vol_surge")
BRANCH_PREFIX = "running_up."
MIN_TICK_BUFFER = 0.0001

PRICE_BAND: Tuple[float, float] = (2.0, 20.0)          # FILTERS.md Layer 0
MAX_VERIFIED_FLOAT = 20_000_000                         # FILTERS.md Layer 0
SESSION_WINDOW: Tuple[time, time] = (time(7, 0), time(11, 30))


class RunningUpFilters(Scanner):
    """The Running Up tile's discovery filters. See the module docstring for
    every rule and where its threshold comes from."""

    scanner_id = "running_up_filters"
    definition_version = "running_up_filters@1.0.0"

    def __init__(self, triggers: Sequence[str] = TRIGGERS, pct_threshold: float = 5.0,
                 pct_window_minutes: int = 5, surge_move_pct: float = 3.0, surge_window_minutes: int = 2,
                 surge_rvol_5m: float = 2.0, hod_rvol_5m: float = 2.0, halt_lookback_minutes: int = 5,
                 price_band: Optional[Tuple[float, float]] = PRICE_BAND,
                 max_verified_float: Optional[float] = MAX_VERIFIED_FLOAT,
                 session_window: Optional[Tuple[time, time]] = SESSION_WINDOW,
                 rearm_minutes: int = 3) -> None:
        unknown = [t for t in triggers if t not in TRIGGERS]
        if unknown or not triggers:
            raise ValueError(f"unknown or empty triggers {list(triggers)}; choose from {TRIGGERS}")
        self.triggers = tuple(t for t in TRIGGERS if t in triggers)        # priority order
        self.pct_threshold = pct_threshold
        self.pct_window_minutes = max(1, int(pct_window_minutes))
        self.surge_move_pct = surge_move_pct
        self.surge_window_minutes = max(1, int(surge_window_minutes))
        self.surge_rvol_5m = surge_rvol_5m
        self.hod_rvol_5m = hod_rvol_5m
        self.halt_lookback_minutes = max(1, int(halt_lookback_minutes))
        self.price_band = price_band
        self.max_verified_float = max_verified_float
        self.session_window = session_window
        self.rearm_minutes = max(1, int(rearm_minutes))
        self._in_leg: Dict[str, bool] = {}
        self._quiet: Dict[str, Tuple[Optional[datetime], int]] = {}   # (last quiet minute, quiet minutes)
        # per symbol: ("halted", seen at) until the first print; then gone
        self._halt: Dict[str, Tuple[str, datetime]] = {}

    # -- the rule ---------------------------------------------------------------

    def on_snapshot(self, current: SymbolSnapshot, previous: Optional[SymbolSnapshot], state: SymbolState,
                    hot: HotState) -> List[ScannerEvent]:
        now = current.event_ts
        if now is None or current.last is None:
            return []
        self._observe_halts(hot, now)
        bar = _current_bar(state)
        if bar is None:
            return []
        sym = current.symbol
        traded = (bar.volume or 0) > 0
        not_red = bar.close >= bar.open

        checks: Dict[str, Tuple[bool, object, object]] = {}
        extra: dict = {}
        if "halt_resume" in self.triggers:
            checks["halt_resume"] = self._halt_resume(sym, current, state, bar, traded, extra)
        if "new_hod" in self.triggers:
            checks["new_hod"] = self._new_hod(current, previous, bar, traded, extra)
        if "pct_in_n" in self.triggers:
            checks["pct_in_n"] = self._pct_in_n(current, state, bar, traded, not_red, extra)
        if "vol_surge" in self.triggers:
            checks["vol_surge"] = self._vol_surge(current, state, bar, traded, not_red, extra)

        qualifiers = self._qualifiers(current, bar)
        fired = [t for t in self.triggers if checks[t][0]]
        qualifies = bool(fired) and all(q[1] for q in qualifiers)
        if not self._rising_edge(sym, qualifies, bar.ts, new_leg="halt_resume" in fired):
            return []
        branch = BRANCH_PREFIX + fired[0]
        reasons = [Reason(BRANCH_PREFIX + t, _json(checks[t][1]), checks[t][0], checks[t][2]) for t in self.triggers]
        reasons += [Reason(name, _json(value), ok, threshold) for name, ok, value, threshold in qualifiers]
        extra["filters_fired"] = [BRANCH_PREFIX + t for t in fired]
        severity = "high" if fired[0] == "halt_resume" else "medium"
        return [self._event(current, now, "qualified", severity, reasons, branch=branch, extra_values=extra)]

    # -- triggers ---------------------------------------------------------------

    def _pct_in_n(self, current, state, bar, traded, not_red, extra):
        cutoff = bar.ts - timedelta(minutes=self.pct_window_minutes - 1)
        lows = [b.low for b in _bars_since(state, cutoff) if b.low and b.low > 0]
        if not lows:
            return False, None, self.pct_threshold
        low = min(lows)
        move = 100.0 * (current.last / low - 1.0)
        extra.update(window_minutes=self.pct_window_minutes, window_low=_round(low, 4),
                     move_from_window_low_pct=_round(move))
        return (traded and not_red and move >= self.pct_threshold), _round(move), self.pct_threshold

    def _vol_surge(self, current, state, bar, traded, not_red, extra):
        ref = state.price_minutes_ago(bar.ts, self.surge_window_minutes)
        rvol5 = current.rvol_5m
        move = None if not ref or ref <= 0 else 100.0 * (current.last / ref - 1.0)
        extra.update(surge_move_pct=_round(move), surge_window_minutes=self.surge_window_minutes)
        ok = (traded and not_red and move is not None and move >= self.surge_move_pct
              and rvol5 is not None and rvol5 >= self.surge_rvol_5m)
        value = f"{_round(move)}% in {self.surge_window_minutes}m, rvol5m {_round(rvol5)}"
        return ok, value, f">={self.surge_move_pct}% and rvol5m>={self.surge_rvol_5m}"

    def _new_hod(self, current, previous, bar, traded, extra):
        prior = _prior_hod(current, previous)
        rvol5 = current.rvol_5m
        rule = f"high and close above the prior HOD, rvol5m>={self.hod_rvol_5m}"
        if prior is None:
            return False, None, rule
        extra["prior_hod"] = _round(prior, 4)
        ok = (traded and bar.high > prior + MIN_TICK_BUFFER and current.last > prior
              and rvol5 is not None and rvol5 >= self.hod_rvol_5m)
        return ok, f"high {_round(bar.high, 4)} close {_round(current.last, 4)} vs {_round(prior, 4)}, rvol5m {_round(rvol5)}", rule

    def _halt_resume(self, sym, current, state, bar, traded, extra):
        rule = "first print after a halt it ran into"
        mark = self._halt.get(sym)
        if mark is None or not traded or bar.ts <= mark[1]:
            return False, None, rule
        halted_at = mark[1]
        del self._halt[sym]                                 # the first print is the resumption
        pre = next((b for b in reversed(state.minute_bars) if b.ts < halted_at and (b.volume or 0) > 0), None)
        ref = state.price_minutes_ago(pre.ts, self.halt_lookback_minutes) if pre is not None else None
        extra.update(halt_seen_at=halted_at.isoformat(), halt_pre_close=None if pre is None else _round(pre.close, 4),
                     halt_ref_close=_round(ref, 4))
        if pre is None or ref is None or ref <= 0:
            return False, "the run into the halt is unknown", rule
        run_in = 100.0 * (pre.close / ref - 1.0)
        return run_in > 0, f"ran {_round(run_in)}% into the halt, resumed at {_round(current.last, 4)}", rule

    # -- halts ------------------------------------------------------------------

    def _observe_halts(self, hot: HotState, now: datetime) -> None:
        """Every desk name whose official status reads halted, on every
        snapshot of every name: a halted name prints nothing, so its own bars
        cannot say when the pause began."""
        for sym, st in hot.symbols.items():
            if st.snapshot.halt_status == "halted" and sym not in self._halt:
                self._halt[sym] = ("halted", now)

    # -- qualifiers and the leg ---------------------------------------------------

    def _qualifiers(self, current: SymbolSnapshot, bar: Bar) -> list:
        out = []
        if self.price_band is not None:
            lo, hi = self.price_band
            out.append(("price_band", lo <= current.last <= hi, _round(current.last, 4), f"{lo:g}-{hi:g}"))
        if self.max_verified_float is not None:
            f, q = current.float_shares, current.float_quality
            killed = q == FloatQuality.VERIFIED and f is not None and f > self.max_verified_float
            shown = "unknown" if f is None else f"{round(f / 1e6, 2)}M {getattr(q, 'value', q)}"
            out.append(("float_verified_max", not killed, shown, self.max_verified_float))
        if self.session_window is not None:
            start, end = self.session_window
            t = bar.ts.astimezone(ET).time()
            out.append(("session_window_et", start <= t < end, t.strftime("%H:%M"),
                        f"{start:%H:%M}-{end:%H:%M}"))
        return out

    def _rising_edge(self, sym: str, qualifies: bool, minute: datetime, new_leg: bool = False) -> bool:
        """True on the first qualifying snapshot of a leg. The leg ends after
        `rearm_minutes` distinct bar minutes with nothing qualifying."""
        if new_leg:
            self._in_leg[sym] = False                        # a halt ends the leg it interrupted
        if qualifies:
            self._quiet[sym] = (None, 0)
            was = self._in_leg.get(sym, False)
            self._in_leg[sym] = True
            return not was
        last, n = self._quiet.get(sym, (None, 0))
        if minute != last:
            n += 1
            self._quiet[sym] = (minute, n)
        if n >= self.rearm_minutes:
            self._in_leg[sym] = False
        return False


# -- helpers ----------------------------------------------------------------------

def _current_bar(state: SymbolState) -> Optional[Bar]:
    """The bar being printed now: the forming minute on a tick feed, else the
    newest bar (the session builder appends each minute before the scanners)."""
    building = getattr(state, "_building", None)
    if building is not None and (not state.minute_bars or building.ts >= state.minute_bars[-1].ts):
        return building
    return state.minute_bars[-1] if state.minute_bars else None


def _bars_since(state: SymbolState, cutoff: datetime) -> List[Bar]:
    """Bars with ts >= cutoff, newest last, the forming minute included."""
    out: List[Bar] = []
    for b in reversed(state.minute_bars):
        if b.ts < cutoff:
            break
        out.append(b)
    out.reverse()
    building = getattr(state, "_building", None)
    if building is not None and building.ts >= cutoff and (not out or building.ts > out[-1].ts):
        out.append(building)
    return out


def _prior_hod(current: SymbolSnapshot, previous: Optional[SymbolSnapshot]) -> Optional[float]:
    """The high of day before this update — the previous snapshot's, the same
    ET trading date only (the first bar of a day has no prior high to break)."""
    if previous is None or previous.session_high is None or previous.event_ts is None or current.event_ts is None:
        return None
    if previous.event_ts.astimezone(ET).date() != current.event_ts.astimezone(ET).date():
        return None
    return previous.session_high


def _json(value):
    """Reason values travel to the browser as JSON."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)
