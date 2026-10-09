"""Running Up, strengthened (2026-10-09): four triggers, three qualifiers, one
alert per leg, and never a gate. Synthetic one-minute tapes, plus the desk's
replay fixture for the discovery-only check."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.dashboard import session_builder as SB  # noqa: E402
from momentum_platform.engine import ScannerEngine  # noqa: E402
from momentum_platform.models import Bar, DataStatus, FloatQuality  # noqa: E402
from momentum_platform.notify import NotificationRouter, RouterConfig  # noqa: E402
from momentum_platform.scanners import RunningUpFilters  # noqa: E402
from momentum_platform.scanners.running_up_filters import TRIGGERS  # noqa: E402
from momentum_platform.state import HotState, MarketUpdate, ReferenceData  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 3, 14, 0, tzinfo=UTC)          # 10:00 ET
FIXTURE = ROOT / "fixtures" / "market_replay" / "workstation_open_2026-09-01.jsonl"
BASE = (4.00, 4.01, 3.99, 4.00, 5_000)                 # a flat minute: o h l c v


class Sink:
    name = "test-sink"

    def deliver(self, event, group=None):
        pass


def run(bars, *, triggers=TRIGGERS, start=T0, halts=None, prev_close=3.0, float_shares=5_000_000,
        quality=FloatQuality.VERIFIED, **kw):
    """Feed (o, h, l, c, v) one-minute bars from `start`; `halts` maps a bar
    index to the official status set before that bar. Returns the events."""
    hot = HotState()
    hot.load_reference([ReferenceData("AAA", prev_close=prev_close, avg_daily_volume=2_000_000,
                                      float_shares=float_shares, float_quality=quality)])
    engine = ScannerEngine(hot=hot, scanners=[RunningUpFilters(triggers=triggers, **kw)],
                           router=NotificationRouter(RouterConfig(), [Sink()]))
    out = []
    for i, (o, h, l, c, v) in enumerate(bars):
        if halts and i in halts:
            hot.set_halt("AAA", halts[i])
        ts = start + timedelta(minutes=i)
        out += engine.process(MarketUpdate("AAA", ts, price=c, size=v, bar=Bar("AAA", "1m", ts, o, h, l, c, v),
                                           data_status=DataStatus.REPLAY))
    return out


def minute(e):
    return int((e.source_ts - T0).total_seconds() // 60)


def curl(base=10, low=3.80, close=4.00, high=None, volume=5_000, top=4.60):
    """An early high of day at `top`, a sag to `low`, then one green bar
    closing at `close`: a curl off a dip, below the high of day."""
    bars = [(4.00, top, 3.99, 4.00, 5_000)] + [BASE] * (base - 2)
    bars.append((3.95, 3.96, low, 3.90, 5_000))
    bars.append((3.92, high or close + 0.01, 3.91, close, volume))
    return bars


# -- each trigger fires on its pattern and stays quiet off it --------------------------

def test_pct_in_n_fires_on_a_curl_off_the_five_minute_low_below_the_high_of_day():
    events = run(curl(close=4.00))                        # 3.80 -> 4.00 = +5.3 %, HOD 4.60 untouched
    assert [e.branch for e in events] == ["running_up.pct_in_n"]
    e = events[0]
    assert minute(e) == 10
    assert e.values["window_low"] == pytest.approx(3.80)
    assert e.values["move_from_window_low_pct"] == pytest.approx(5.26, abs=0.01)
    assert e.values["filters_fired"] == ["running_up.pct_in_n"]


def test_pct_in_n_stays_quiet_under_five_percent_and_on_a_red_bar():
    assert run(curl(close=3.95)) == []                    # +3.9 %
    red = curl(close=4.00)
    red[-1] = (4.10, 4.12, 3.91, 4.00, 5_000)             # +5.3 % off the low, but red
    assert run(red) == []


def test_vol_surge_fires_on_three_percent_in_two_minutes_on_double_volume():
    bars = [BASE] * 30 + [(4.00, 4.07, 4.00, 4.06, 100_000), (4.06, 4.13, 4.06, 4.125, 100_000)]
    events = run(bars, triggers=("vol_surge",))
    assert [(e.branch, minute(e)) for e in events] == [("running_up.vol_surge", 31)]
    assert events[0].values["rvol_5m"] >= 2.0


def test_vol_surge_stays_quiet_on_the_same_move_without_the_volume():
    bars = [BASE] * 30 + [(4.00, 4.07, 4.00, 4.06, 5_000), (4.06, 4.13, 4.06, 4.125, 5_000)]
    assert run(bars, triggers=("vol_surge",)) == []


def test_new_hod_fires_on_a_high_and_close_over_the_high_of_day_on_volume():
    bars = [BASE] * 30 + [(4.00, 4.10, 4.00, 4.08, 100_000)]
    events = run(bars, triggers=("new_hod",))
    assert [(e.branch, minute(e)) for e in events] == [("running_up.new_hod", 30)]
    assert events[0].values["prior_hod"] == pytest.approx(4.01)


def test_new_hod_stays_quiet_without_volume_or_when_the_close_falls_back():
    assert run([BASE] * 30 + [(4.00, 4.10, 4.00, 4.08, 5_000)], triggers=("new_hod",)) == []
    assert run([BASE] * 30 + [(4.00, 4.10, 3.98, 4.00, 100_000)], triggers=("new_hod",)) == []


def run_into_halt(direction=+1, halted_minutes=4):
    """Ten minutes moving 1.5 % a minute, an official halt, then the reopening
    print — a red flush, as resumptions often are."""
    bars = []
    for i in range(10):
        c = round(4.00 * (1 + direction * 0.015 * i), 4)
        bars.append((c, c + 0.01, c - 0.01, c, 5_000))
    last = bars[-1][3]
    bars += [(last, last, last, last, 0)] * halted_minutes
    bars.append((last * 1.05, last * 1.06, last * 0.97, last * 0.98, 80_000))
    return bars, {10: "halted", 10 + halted_minutes: "trading"}


def test_halt_resume_fires_on_the_first_print_after_a_halt_it_ran_into():
    bars, halts = run_into_halt(+1)
    events = run(bars, triggers=("halt_resume",), halts=halts)
    assert [(e.branch, minute(e), e.severity) for e in events] == [("running_up.halt_resume", 14, "high")]
    assert events[0].values["halt_pre_close"] == pytest.approx(bars[9][3])


def test_halt_resume_stays_quiet_after_a_halt_it_fell_into_and_without_an_official_halt():
    bars, halts = run_into_halt(-1)
    assert run(bars, triggers=("halt_resume",), halts=halts) == []
    bars, _ = run_into_halt(+1)
    assert run(bars, triggers=("halt_resume",)) == [], "nothing is inferred from empty bars"


def test_a_halt_ends_the_leg_so_the_resumption_is_always_a_new_alert():
    bars, halts = run_into_halt(+1, halted_minutes=1)     # shorter than the re-arm
    events = run(bars, halts=halts)
    branches = [(e.branch, minute(e)) for e in events]
    assert branches[0][0] == "running_up.pct_in_n"        # the run into the halt, called once
    assert branches[-1] == ("running_up.halt_resume", 11)


# -- one alert per leg --------------------------------------------------------------------

def leg_pause_leg(quiet):
    """A leg climbing 1.2 % a minute, `quiet` flat minutes, then one bar that
    qualifies at once."""
    up = [(c, c + 0.01, c - 0.01, c, 5_000) for c in (4.00 * 1.012 ** i for i in range(12))]
    top = up[-1][3]
    flat = [(top, top + 0.005, top - 0.005, top, 5_000)] * quiet
    jump = round(top * 1.06, 4)
    return up + flat + [(top, jump + 0.01, top - 0.005, jump, 5_000)]


def test_one_alert_per_leg_and_a_new_leg_after_three_quiet_minutes():
    events = run(leg_pause_leg(3), triggers=("pct_in_n",))
    assert [minute(e) for e in events] == [4, 15]


def test_two_quiet_minutes_do_not_rearm():
    events = run(leg_pause_leg(2), triggers=("pct_in_n",))
    assert [minute(e) for e in events] == [4]


def test_rearm_counts_bar_minutes_not_snapshots():
    """Live snapshots arrive seconds apart: VEEE alerted at 09:55, 09:56 and
    09:57 on one move when the re-arm counted evaluations (running_up 3.2.0)."""
    s = RunningUpFilters()
    m = [T0 + timedelta(minutes=i) for i in range(5)]
    assert s._rising_edge("AAA", True, m[0]) is True
    for _ in range(10):                                    # ten quiet snapshots, one minute
        assert s._rising_edge("AAA", False, m[1]) is False
    assert s._rising_edge("AAA", True, m[1]) is False, "still the same leg"
    for t in m[2:5]:                                       # three quiet MINUTES
        s._rising_edge("AAA", False, t)
    assert s._rising_edge("AAA", True, m[4]) is True


# -- qualifiers -----------------------------------------------------------------------------

def test_the_price_band_silences_names_under_two_and_over_twenty_dollars():
    cheap = [tuple(x / 4 if k < 4 else x for k, x in enumerate(b)) for b in curl(close=4.00)]
    dear = [tuple(x * 6 if k < 4 else x for k, x in enumerate(b)) for b in curl(close=4.00)]
    assert run(cheap) == [] and run(dear) == []
    assert len(run(curl(close=4.00))) == 1


def test_only_a_verified_float_over_twenty_million_silences_it():
    assert run(curl(close=4.00), float_shares=30_000_000, quality=FloatQuality.VERIFIED) == []
    assert len(run(curl(close=4.00), float_shares=30_000_000,
                   quality=FloatQuality.SHARES_OUTSTANDING)) == 1, "an upper bound is 'verify'"
    assert len(run(curl(close=4.00), float_shares=None, quality=FloatQuality.UNKNOWN)) == 1, \
        "a blank float is 'verify', never 'dead'"


@pytest.mark.parametrize("et_start, fires", [((6, 40), False), ((7, 0), True), ((11, 25), False), ((11, 15), True)])
def test_the_session_window_is_seven_to_eleven_thirty_et(et_start, fires):
    # the curl's alert lands on bar 10: start 06:40 -> 06:50, 07:00 -> 07:10, 11:15 -> 11:25, 11:25 -> 11:35
    h, m = et_start
    start = datetime(2026, 9, 3, h + 4, m, tzinfo=UTC)
    assert bool(run(curl(close=4.00), start=start)) is fires


def test_every_alert_reports_every_trigger_and_qualifier_pass_or_fail():
    (e,) = run(curl(close=4.00))
    names = [r.filter for r in e.reasons]
    assert names == ["running_up." + t for t in TRIGGERS] + ["price_band", "float_verified_max",
                                                              "session_window_et"]
    by = {r.filter: r.passed for r in e.reasons}
    assert by["running_up.pct_in_n"] and not by["running_up.new_hod"]
    assert by["price_band"] and by["float_verified_max"] and by["session_window_et"]


def test_unknown_triggers_are_refused():
    with pytest.raises(ValueError):
        RunningUpFilters(triggers=("pct_in_n", "gap_up"))
    with pytest.raises(ValueError):
        RunningUpFilters(triggers=())


# -- discovery only: a scanner never gates the bot -----------------------------------------

class _Silenced(RunningUpFilters):
    def on_snapshot(self, *a, **k):
        return []


@pytest.fixture(scope="module")
def with_and_without():
    on = SB.build_session(FIXTURE)
    real = SB.RunningUpFilters
    SB.RunningUpFilters = _Silenced
    try:
        off = SB.build_session(FIXTURE)
    finally:
        SB.RunningUpFilters = real
    return on, off


def _alerts(s, keep):
    return sorted((a["symbol"], a["scannerId"], a.get("branch") or "", a["sourceTime"])
                  for f in s["frames"] for a in f["alerts"] if keep(a["scannerId"]))


def test_the_filters_alert_on_the_replayed_day(with_and_without):
    on, off = with_and_without
    assert _alerts(on, lambda k: k == "running_up_filters"), "the check below would be vacuous"
    assert not _alerts(off, lambda k: k == "running_up_filters")


def test_plans_cascade_and_cards_are_identical_without_the_filters(with_and_without):
    on, off = with_and_without
    same = lambda ps: [{k: v for k, v in p.items() if k != "planId"} for p in ps]  # noqa: E731  (a fresh id per build)
    assert on["plans"] and same(on["plans"]) == same(off["plans"])
    assert same(on["suppressedPlans"]) == same(off["suppressedPlans"])
    assert {k: v["verdict"] for k, v in on["cascade"].items()} == {k: v["verdict"] for k, v in off["cascade"].items()}
    assert {k: c["verdict"] for k, c in on["cards"].items()} == {k: c["verdict"] for k, c in off["cards"].items()}


def test_every_row_the_desks_own_scanners_showed_survives_the_filters(with_and_without):
    on, off = with_and_without
    mine = lambda k: k != "running_up_filters"  # noqa: E731
    assert _alerts(on, mine) == _alerts(off, mine)


def test_the_filters_run_last_and_join_the_running_up_tile():
    src = (ROOT / "src" / "momentum_platform" / "dashboard" / "session_builder.py").read_text()
    block = src[src.index("engine = ScannerEngine("):src.index("router=router,", src.index("engine = ScannerEngine("))]
    assert block.rstrip().rstrip("],").rstrip().endswith("RunningUpFilters(),")
    assert "running_up_filters" in SB.ALERT_META
    js = (ROOT / "src" / "momentum_platform" / "dashboard" / "web" / "app.js").read_text()
    tile = js[js.index("running_up: { id: \"running_up\""):js.index("hod_momentum: { id:")]
    assert '"running_up_filters"' in tile
    assert RouterConfig().cooldown_for("running_up_filters") == 120.0
