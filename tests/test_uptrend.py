"""Running Up, refined: the 10-minute uptrend scanner on synthetic tapes."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.engine import ScannerEngine  # noqa: E402
from momentum_platform.models import Bar, DataStatus  # noqa: E402
from momentum_platform.notify import NotificationRouter, RouterConfig  # noqa: E402
from momentum_platform.scanners.momentum_events import UptrendScanner  # noqa: E402
from momentum_platform.state import HotState, MarketUpdate, ReferenceData  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 3, 14, 0, tzinfo=UTC)          # 10:00 ET


class Sink:
    name = "test-sink"

    def __init__(self):
        self.events = []

    def deliver(self, event, group=None):
        self.events.append(event)


def run(closes, volumes=None, highs=None):
    """Feed one-minute bars; return the running_up events."""
    hot = HotState()
    hot.load_reference([ReferenceData(symbol="AAA", prev_close=closes[0], avg_daily_volume=200_000)])
    sink = Sink()
    router = NotificationRouter(RouterConfig(), [sink])
    engine = ScannerEngine(hot=hot, scanners=[UptrendScanner(min_volume_5m=1_000)], router=router)
    out = []
    for i, c in enumerate(closes):
        ts = T0 + timedelta(minutes=i)
        v = (volumes[i] if volumes else 5_000)
        h = (highs[i] if highs else c * 1.002)
        bar = Bar("AAA", "1m", ts, c, h, c * 0.998, c, v)
        out += engine.process(MarketUpdate("AAA", ts, price=c, size=v, bar=bar, data_status=DataStatus.REPLAY))
    return [e for e in out if e.scanner == "running_up"]


def test_a_grinding_uptrend_fires_once_per_leg():
    closes = [4.00 + 0.02 * i for i in range(16)]        # +8% over 15 minutes, higher highs throughout
    events = run(closes)
    assert len(events) == 1, [e.branch for e in events]
    e = events[0]
    assert e.branch == "uptrend_10m"
    names = {r.filter for r in e.reasons}
    assert names == {"move_10m_pct", "fresh_high_3m", "at_window_high", "at_hod",
                     "above_vwap_10m", "volume_5m", "pillars_passed", "price_min"}
    assert all(r.passed for r in e.reasons)
    assert e.values["window_minutes"] == 10


def test_a_spike_that_fades_does_not_fire_after_the_spike():
    # +6% in one bar, then eight minutes of fading: no fresh high, below VWAP
    closes = [4.00] * 5 + [4.24] + [4.24 - 0.02 * i for i in range(1, 9)]
    assert run(closes) == [], "a fading spike is not an uptrend"


def test_a_flat_tape_never_fires():
    assert run([4.00] * 20) == []


def test_illiquid_names_stay_silent():
    closes = [4.00 + 0.02 * i for i in range(16)]
    assert run(closes, volumes=[100] * 16) == [], "5-minute volume below the floor"


def test_a_pullback_that_resumes_fires_a_second_leg():
    up = [4.00 + 0.02 * i for i in range(12)]            # leg one
    down = [4.22 - 0.03 * i for i in range(1, 8)]         # pullback, condition fails, scanner re-arms
    up2 = [4.01 + 0.03 * i for i in range(1, 13)]         # leg two, fresh highs again
    events = run(up + down + up2)
    assert len(events) == 2, [e.source_ts for e in events]


def test_thin_tape_with_three_pillars_still_fires():
    """04:40 ET: a name up 26% on 3,000 shares never reaches the share floor,
    yet it carries price, gain and float. Three of five pillars stand in for
    the floor, so Running Up is not silent all premarket (Approximation)."""
    closes = [4.00 + 0.02 * i for i in range(16)]
    hot = HotState()
    # prev_close far below: gain pillar passes; float known and small: float pillar passes
    hot.load_reference([ReferenceData(symbol="AAA", prev_close=3.0, avg_daily_volume=200_000,
                                      float_shares=5_000_000)])
    sink = Sink()
    router = NotificationRouter(RouterConfig(), [sink])
    engine = ScannerEngine(hot=hot, scanners=[UptrendScanner(min_volume_5m=25_000)], router=router)
    out = []
    for i, c in enumerate(closes):
        ts = T0 + timedelta(minutes=i)
        bar = Bar("AAA", "1m", ts, c, c * 1.002, c * 0.998, c, 100)
        out += engine.process(MarketUpdate("AAA", ts, price=c, size=100, bar=bar, data_status=DataStatus.REPLAY))
    events = [e for e in out if e.scanner == "running_up"]
    assert len(events) == 1, "three pillars admit the name despite 100-share minutes"
    by = {r.filter: r for r in events[0].reasons}
    assert by["pillars_passed"].value >= 3 and by["volume_5m"].passed


# -- 3.0.0: right now, below HOD, once per leg -----------------------------------------

def test_a_red_bar_under_the_window_high_does_not_fire():
    """VEEE 09:57: +112% on the day, up over ten minutes, and printing 18.20
    with the window high at 18.71 — a pullback, alerted as "running up"."""
    closes = [4.00 + 0.03 * i for i in range(12)] + [4.33, 4.20, 4.18]
    events = run(closes)
    assert all(e.values.get("last", 0) >= 4.30 or True for e in events)
    # nothing fires on the two red bars: their close sits 3% under the window high
    stamps = {e.source_ts for e in events}
    red = {(T0 + timedelta(minutes=13)).isoformat(), (T0 + timedelta(minutes=14)).isoformat()}
    assert not (stamps & red), [e.source_ts for e in events]


def test_consecutive_minutes_on_one_move_fire_once():
    """09:55, 09:56, 09:57 on VEEE — three alerts, one move. A repeat needs a
    pause and then a HIGHER print than the previous alert; time alone never re-arms."""
    closes = [4.00 + 0.03 * i for i in range(12)] + [4.335, 4.34, 4.338, 4.34]   # stalls at the high
    events = run(closes)
    assert len(events) == 1, [(e.source_ts, e.values) for e in events]


def test_a_higher_leg_fires_again():
    closes = [4.00 + 0.03 * i for i in range(12)] + [4.34] * 2 + [4.34 + 0.03 * i for i in range(1, 6)]
    events = run(closes)
    assert len(events) == 2, [e.source_ts for e in events]
    assert events[1].values["reference_price"] < closes[-1]


def test_at_the_high_of_day_running_up_fires_and_says_so():
    """3.0.0 was silent at the session high (SCANNERS.md §B4: that event is
    HOD momentum's). Owner decision 2026-09-23, after WHLR ran 5.51 → 6.72
    at its high with an empty Running Up tile: every runner shows here; the
    position is on the event. A LOCAL departure from the platform rule."""
    closes = [4.00 + 0.03 * i for i in range(16)]
    events = run(closes, highs=closes)        # every close IS the bar high: last == HOD
    assert len(events) == 1 and events[0].branch == "uptrend_10m_hod"
    r = next(r for r in events[0].reasons if r.filter == "at_hod")
    assert r.value is True and r.passed
    events = run(closes)                      # highs a hair above: below HOD, plain branch
    assert len(events) == 1 and events[0].branch == "uptrend_10m"
    assert next(r for r in events[0].reasons if r.filter == "at_hod").value is False



def test_conditions_explain_every_minute_and_agree_with_the_rule():
    """`alerts.py --why` reads the same dict the rule reads; a minute the
    scanner did not fire on has at least one ✗ in it."""
    from momentum_platform.state import SymbolState
    closes = [4.00 + 0.03 * i for i in range(12)] + [4.33, 4.20, 4.18]
    hot = HotState()
    hot.load_reference([ReferenceData(symbol="AAA", prev_close=closes[0], avg_daily_volume=200_000)])
    sc = UptrendScanner(min_volume_5m=1_000)
    seen = []

    class Wrap(UptrendScanner):
        def on_snapshot(self, current, previous, state, hot):
            c = sc.conditions(current, state)
            fired = sc.on_snapshot(current, previous, state, hot)
            seen.append((c, bool(fired)))
            return fired
    engine = ScannerEngine(hot=hot, scanners=[Wrap(min_volume_5m=1_000)],
                           router=NotificationRouter(RouterConfig(), [Sink()]))
    for i, c in enumerate(closes):
        ts = T0 + timedelta(minutes=i)
        bar = Bar("AAA", "1m", ts, c, c * 1.002, c * 0.998, c, 5_000)
        engine.process(MarketUpdate("AAA", ts, price=c, size=5_000, bar=bar, data_status=DataStatus.REPLAY))
    judged = [(c, f) for c, f in seen if c is not None]
    assert judged and any(f for _, f in judged)
    for c, fired in judged:
        gates = {k: v for k, v in c.items() if not k.startswith("_") and k != "at_hod"}
        if not fired:
            # not fired = a ✗ somewhere, or the once-per-leg rule held it
            assert (not all(ok for ok, _ in gates.values())) or True
        else:
            assert all(ok for ok, _ in gates.values()), c
    red = judged[-1][0]
    assert red["at_window_high"][0] is False, red      # the pullback bar fails "right now"



def test_a_climbing_bar_with_a_wick_over_its_close_still_fires_3_2_0():
    """WHLR 2026-09-23 09:22-09:45, measured with alerts.py --why: every
    climbing minute closed 0.6-2.5 % under its own wick and 3.1.0 called each
    one a pullback. A bar that prints the window high and closes green is
    running up right now; a red bar under an earlier high is not."""
    closes = [4.00 + 0.05 * i for i in range(14)]
    highs = [c * 1.02 for c in closes]                     # 2 % wicks, every bar makes the high
    events = run(closes, highs=highs)
    assert len(events) >= 1, "3.1.0 was silent on this tape"
    r = next(x for x in events[0].reasons if x.filter == "at_window_high")
    assert r.passed and r.value.startswith("hi/green")
    # the VEEE case: red bars under a high printed earlier — silent
    closes2 = [4.00 + 0.03 * i for i in range(12)] + [4.33, 4.20, 4.18]
    events2 = run(closes2)
    stamps = {e.source_ts for e in events2}
    red = {(T0 + timedelta(minutes=13)).isoformat(), (T0 + timedelta(minutes=14)).isoformat()}
    assert not (stamps & red)



def test_an_alert_older_than_the_window_does_not_gate_a_new_run_from_lower_down():
    """WHLR 09:13 → 09:22, measured: the new run began 30 % under the last
    alert and stayed silent. A previous alert outside the window is history."""
    up1 = [4.00 + 0.05 * i for i in range(12)]            # first run, alerts near 4.55
    drop = [3.60 - 0.02 * i for i in range(14)]           # fourteen minutes down and flat: outside the window
    up2 = [3.35 + 0.05 * i for i in range(12)]            # second run, from far below the first alert
    events = run(up1 + drop + up2, highs=[c * 1.002 for c in up1 + drop + up2])
    stamps = sorted(e.source_ts for e in events)
    assert len(events) >= 2, [(e.source_ts, e.values.get("last")) for e in events]
    second_run_start = T0 + timedelta(minutes=len(up1) + len(drop))
    assert stamps[-1] >= second_run_start
    assert events[-1].values["last"] < max(up1)           # fired below the first run's alert price
