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
    assert names == {"move_10m_pct", "fresh_high_3m", "above_vwap_10m", "volume_5m", "pillars_passed", "price_min"}
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
