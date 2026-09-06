"""Offline tests for the momentum_platform package (stdlib-only: no pandas,
no network). Covers sessions, formulas, hot state, scanners, notification
routing, the event store, the first-pullback state machine and a golden
end-to-end replay."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from momentum_platform.models import (  # noqa: E402
    Bar,
    FloatQuality,
    Reason,
    ScannerEvent,
    Session,
    SymbolSnapshot,
    flame_color,
)
from momentum_platform.sessions import SessionCalendar  # noqa: E402
from momentum_platform import formulas  # noqa: E402
from momentum_platform.state import HotState, MarketUpdate, ReferenceData  # noqa: E402
from momentum_platform.scanners import (  # noqa: E402
    Breakout52wScanner,
    EdgeTracker,
    FivePillarsAlert,
    FivePillarsList,
    HodMomentumScanner,
    RunningMoveScanner,
    TopGappersScanner,
    score_pillars,
    top_gainers,
)
from momentum_platform.notify import (  # noqa: E402
    CallbackChannel,
    Channel,
    NotificationRouter,
    RouterConfig,
)
from momentum_platform.store import EventStore  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector, SetupState  # noqa: E402
from momentum_platform.engine import ScannerEngine  # noqa: E402
from momentum_platform.datasources.replay import ReplaySource  # noqa: E402

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "market_replay"


def utc(y, mo, d, h, mi, s=0):
    return datetime(y, mo, d, h, mi, s, tzinfo=UTC)


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------

class TestSessions:
    cal = SessionCalendar()

    def test_regular_session_edt(self):
        # 2026-09-01 is EDT (UTC-4): 13:30Z == 09:30 ET.
        assert self.cal.session_at(utc(2026, 9, 1, 13, 30)) == Session.REGULAR
        assert self.cal.session_at(utc(2026, 9, 1, 13, 29)) == Session.PREMARKET

    def test_regular_session_est(self):
        # 2026-01-15 is EST (UTC-5): 14:30Z == 09:30 ET.
        assert self.cal.session_at(utc(2026, 1, 15, 14, 30)) == Session.REGULAR
        assert self.cal.session_at(utc(2026, 1, 15, 14, 29)) == Session.PREMARKET

    def test_premarket_start_and_after_hours_end(self):
        assert self.cal.session_at(utc(2026, 9, 1, 8, 0)) == Session.PREMARKET
        assert self.cal.session_at(utc(2026, 9, 1, 7, 59)) == Session.CLOSED
        assert self.cal.session_at(utc(2026, 9, 1, 20, 0)) == Session.AFTER_HOURS
        assert self.cal.session_at(utc(2026, 9, 2, 0, 0)) == Session.CLOSED

    def test_weekend_closed(self):
        assert self.cal.session_at(utc(2026, 9, 5, 14, 0)) == Session.CLOSED  # Saturday

    def test_holiday_closed(self):
        cal = SessionCalendar(holidays=[datetime(2026, 9, 7).date()])  # Labor Day
        assert cal.session_at(utc(2026, 9, 7, 14, 0)) == Session.CLOSED

    def test_before_open(self):
        assert self.cal.is_before_open(utc(2026, 9, 1, 13, 29))
        assert not self.cal.is_before_open(utc(2026, 9, 1, 13, 30))


# --------------------------------------------------------------------------
# Formulas
# --------------------------------------------------------------------------

class TestFormulas:
    def test_pct_change(self):
        assert formulas.pct_change(11.0, 10.0) == pytest.approx(10.0)
        assert formulas.pct_change(11.0, None) is None
        assert formulas.pct_change(11.0, 0.0) is None

    def test_spread(self):
        abs_s, bps = formulas.spread(6.73, 6.76)
        assert abs_s == pytest.approx(0.03)
        assert bps == pytest.approx(10000 * 0.03 / 6.745)
        assert formulas.spread(6.76, 6.73) == (None, None)  # crossed

    def test_rvol_5m_fallback(self):
        assert formulas.rvol_5m_fallback(500, [100, 100, 100]) == pytest.approx(5.0)
        assert formulas.rvol_5m_fallback(500, []) is None

    def test_range_position_clamps(self):
        assert formulas.range_position(5.0, 4.0, 6.0) == pytest.approx(0.5)
        assert formulas.range_position(7.0, 4.0, 6.0) == 1.0
        assert formulas.range_position(5.0, 5.0, 5.0) is None

    def test_flame_boundaries(self):
        # Confirmed platform mapping: red 0-2h, orange 2-12h, yellow 12-24h.
        assert flame_color(0) == "red"
        assert flame_color(120) == "red"
        assert flame_color(120.1) == "orange"
        assert flame_color(720) == "orange"
        assert flame_color(720.1) == "yellow"
        assert flame_color(1440) == "yellow"
        assert flame_color(1440.1) is None
        assert flame_color(None) is None

    def test_risk_plan_2r(self):
        plan = formulas.risk_plan(entry=6.75, stop=6.65)
        assert plan["risk_share"] == pytest.approx(0.10)
        assert plan["target"] == pytest.approx(6.95)

    def test_position_size_course_example(self):
        # Playbook example: $25 risk, entry 6.75, stop 6.65, 0.02 slippage
        # reserve -> floor(25 / 0.12) = 208 shares.
        sizing = formulas.position_size(25, 6.75, 6.65, slippage_reserve=0.02)
        assert sizing["theoretical_shares"] == 208
        assert sizing["final_shares"] == 208

    def test_position_size_liquidity_cap(self):
        sizing = formulas.position_size(200, 5.0, 4.9, liquidity_limit_shares=1000)
        assert sizing["theoretical_shares"] == 2000
        assert sizing["final_shares"] == 1000


# --------------------------------------------------------------------------
# Hot state
# --------------------------------------------------------------------------

def make_bar(symbol, ts, o, h, l, c, v):
    return Bar(symbol=symbol, timeframe="1m", ts=ts, open=o, high=h, low=l, close=c, volume=v)


class TestHotState:
    def test_bar_ingestion_updates_snapshot(self):
        hot = HotState()
        hot.load_reference([ReferenceData("ABCD", prev_close=5.0, avg_daily_volume=100_000)])
        ts = utc(2026, 9, 1, 13, 31)
        snap = hot.apply(MarketUpdate("ABCD", ts, price=5.6, size=50_000,
                                      bar=make_bar("ABCD", ts, 5.5, 5.65, 5.45, 5.6, 50_000)))
        assert snap.last == 5.6
        assert snap.session_high == 5.65
        assert snap.session_low == 5.45
        assert snap.volume_today == 50_000
        assert snap.change_from_close_pct == pytest.approx(12.0)
        assert snap.rvol_daily == pytest.approx(0.5)
        assert snap.session == Session.REGULAR
        assert snap.regular_open == 5.5

    def test_tick_builds_minute_bars(self):
        hot = HotState()
        base = utc(2026, 9, 1, 13, 31, 5)
        hot.apply(MarketUpdate("ABCD", base, price=5.0, size=100))
        hot.apply(MarketUpdate("ABCD", base + timedelta(seconds=20), price=5.2, size=200))
        hot.apply(MarketUpdate("ABCD", base + timedelta(minutes=1), price=5.1, size=50))
        state = hot.get("ABCD")
        assert len(state.minute_bars) == 1          # first minute completed
        done = state.minute_bars[0]
        assert (done.open, done.high, done.close, done.volume) == (5.0, 5.2, 5.2, 300)

    def test_daily_reset(self):
        hot = HotState()
        d1 = utc(2026, 9, 1, 14, 0)
        d2 = utc(2026, 9, 2, 14, 0)
        hot.apply(MarketUpdate("ABCD", d1, price=5.0, size=1000))
        snap = hot.apply(MarketUpdate("ABCD", d2, price=6.0, size=10))
        assert snap.volume_today == 10
        assert snap.session_high == 6.0

    def test_closed_session_does_not_accumulate(self):
        hot = HotState()
        snap = hot.apply(MarketUpdate("ABCD", utc(2026, 9, 1, 2, 0), price=5.0, size=1000))
        assert snap.volume_today == 0


# --------------------------------------------------------------------------
# Five Pillars
# --------------------------------------------------------------------------

def snapshot(**kw):
    snap = SymbolSnapshot(symbol=kw.pop("symbol", "ABCD"))
    for k, v in kw.items():
        setattr(snap, k, v)
    return snap


class TestFivePillars:
    NOW = utc(2026, 9, 1, 14, 0)

    def qualifying(self):
        return snapshot(
            last=6.0, change_from_close_pct=15.0, rvol_daily=6.0,
            float_shares=12_000_000, float_quality=FloatQuality.VERIFIED,
            event_ts=self.NOW, session=Session.REGULAR,
        )

    def test_technical_score_four(self):
        reasons, technical, news_ok = score_pillars(self.qualifying(), self.NOW)
        assert technical == 4
        assert not news_ok

    def test_unknown_float_fails_with_reason(self):
        snap = self.qualifying()
        snap.float_shares = None
        reasons, technical, _ = score_pillars(snap, self.NOW)
        assert technical == 3
        float_reason = next(r for r in reasons if r.filter == "float_shares")
        assert float_reason.value == "unknown"
        assert not float_reason.passed

    def test_news_is_separate_from_technical(self):
        snap = self.qualifying()
        snap.latest_news_ts = self.NOW - timedelta(hours=1)
        reasons, technical, news_ok = score_pillars(snap, self.NOW)
        assert technical == 4 and news_ok

    def test_alert_rising_edge_only(self):
        alert = FivePillarsAlert(rearm_after_fails=2)
        hot = HotState()
        snap = self.qualifying()
        state = hot.get("ABCD")
        assert len(alert.on_snapshot(snap, None, state, hot)) == 1
        assert len(alert.on_snapshot(snap, None, state, hot)) == 0  # still qualifying
        snap.rvol_daily = 1.0
        assert len(alert.on_snapshot(snap, None, state, hot)) == 0  # fail 1
        assert len(alert.on_snapshot(snap, None, state, hot)) == 0  # fail 2 -> re-armed
        snap.rvol_daily = 6.0
        assert len(alert.on_snapshot(snap, None, state, hot)) == 1  # fires again

    def test_list_requires_all_four(self):
        hot = HotState()
        good, bad = self.qualifying(), self.qualifying()
        bad.symbol = "BADD"
        bad.rvol_daily = 2.0
        hot.get("ABCD").snapshot = good
        hot.get("BADD").snapshot = bad
        rows = FivePillarsList().rank(hot, self.NOW)
        assert [r.symbol for r in rows] == ["ABCD"]
        assert rows[0].values["technical_score"] == 4


# --------------------------------------------------------------------------
# Momentum event scanners
# --------------------------------------------------------------------------

class TestHodMomentum:
    NOW = utc(2026, 9, 1, 14, 0)

    def snap(self, high, rvol=6.0):
        return snapshot(
            last=high, session_high=high, change_from_close_pct=20.0,
            rvol_daily=rvol, volume_5m=50_000, float_shares=10_000_000,
            event_ts=self.NOW, session=Session.REGULAR,
        )

    def test_first_observation_seeds_no_alert(self):
        scanner = HodMomentumScanner()
        hot = HotState()
        assert scanner.on_snapshot(self.snap(6.0), None, hot.get("ABCD"), hot) == []

    def test_new_hod_fires_with_branch(self):
        scanner = HodMomentumScanner()
        hot = HotState()
        state = hot.get("ABCD")
        scanner.on_snapshot(self.snap(6.0), None, state, hot)
        events = scanner.on_snapshot(self.snap(6.1), None, state, hot)
        assert len(events) == 1
        assert events[0].branch == "low_float_high_rvol_price_under_20"
        assert any(r.filter == "new_hod" for r in events[0].reasons)

    def test_no_alert_without_new_hod(self):
        scanner = HodMomentumScanner()
        hot = HotState()
        state = hot.get("ABCD")
        scanner.on_snapshot(self.snap(6.0), None, state, hot)
        assert scanner.on_snapshot(self.snap(6.0), None, state, hot) == []

    def test_momentum_condition_required(self):
        scanner = HodMomentumScanner(min_recent_rvol=3.0)
        hot = HotState()
        state = hot.get("ABCD")
        scanner.on_snapshot(self.snap(6.0, rvol=1.0), None, state, hot)
        assert scanner.on_snapshot(self.snap(6.1, rvol=1.0), None, state, hot) == []


class TestRunningUp:
    def test_five_percent_in_five_minutes(self):
        hot = HotState()
        state = hot.get("ABCD")
        base = utc(2026, 9, 1, 13, 31)
        for i, close in enumerate([5.0, 5.05, 5.1, 5.15, 5.2, 5.6]):
            ts = base + timedelta(minutes=i)
            hot.apply(MarketUpdate("ABCD", ts, price=close, size=60_000,
                                   bar=make_bar("ABCD", ts, close, close, close, close, 60_000)))
        scanner = RunningMoveScanner(direction="up", window_minutes=5, threshold_pct=5.0)
        snap = state.snapshot
        events = scanner.on_snapshot(snap, None, state, hot)
        assert len(events) == 1
        move = next(r for r in events[0].reasons if r.filter.startswith("move_"))
        # 5.60 vs close 5 minutes earlier (5.05) = +10.9%
        assert move.value > 5.0


class TestBreakout52w:
    NOW = utc(2026, 9, 1, 14, 0)

    def test_breakout_fires_once(self):
        scanner = Breakout52wScanner()
        hot = HotState()
        state = hot.get("ABCD")
        snap = snapshot(last=8.0, session_high=8.0, high_52w=7.9, volume_5m=50_000,
                        event_ts=self.NOW, session=Session.REGULAR)
        assert len(scanner.on_snapshot(snap, None, state, hot)) == 1
        assert len(scanner.on_snapshot(snap, None, state, hot)) == 0

    def test_below_52w_high_no_event(self):
        scanner = Breakout52wScanner()
        hot = HotState()
        snap = snapshot(last=7.0, session_high=7.0, high_52w=7.9, volume_5m=50_000,
                        event_ts=self.NOW, session=Session.REGULAR)
        assert scanner.on_snapshot(snap, None, hot.get("ABCD"), hot) == []


class TestTopLists:
    def test_gainers_ranked_descending_and_capped(self):
        hot = HotState()
        now = utc(2026, 9, 1, 14, 0)
        for symbol, chg in [("AAA", 5.0), ("BBB", 25.0), ("CCC", 15.0)]:
            snap = hot.get(symbol).snapshot
            snap.last = 6.0
            snap.change_from_close_pct = chg
        rows = top_gainers(max_rows=2).rank(hot, now)
        assert [r.symbol for r in rows] == ["BBB", "CCC"]

    def test_gappers_freeze_at_open(self):
        cal = SessionCalendar()
        scanner = TopGappersScanner(calendar=cal)
        hot = HotState()
        snap = hot.get("ABCD").snapshot
        snap.last = 6.0
        snap.gap_pct = 20.0
        pre = utc(2026, 9, 1, 13, 0)
        rows_pre = scanner.rank(hot, pre)
        assert rows_pre[0].rank_metric == 20.0
        # gap keeps changing after the open, but the list is frozen
        snap.gap_pct = 50.0
        rows_post = scanner.rank(hot, utc(2026, 9, 1, 14, 0))
        assert rows_post[0].rank_metric == 20.0


# --------------------------------------------------------------------------
# Notification router
# --------------------------------------------------------------------------

def make_event(symbol="ABCD", scanner="hod_momentum", branch=None, ts=None,
               last=6.0, severity="high"):
    ts = ts or utc(2026, 9, 1, 14, 0)
    return ScannerEvent(
        symbol=symbol, scanner=scanner, branch=branch, event_type="qualified",
        severity=severity, session=Session.REGULAR, source_ts=ts, scan_ts=ts,
        definition_version=f"{scanner}@1.0.0", values={"last": last},
        reasons=[Reason("test", 1, True)],
    )


class FailingChannel(Channel):
    name = "failing"

    def deliver(self, event, consolidated=None):
        raise RuntimeError("boom")


class TestNotificationRouter:
    def collector(self):
        delivered = []
        router = NotificationRouter(
            RouterConfig(consolidation_window_seconds=0.0),
            [CallbackChannel(lambda e, c: delivered.append(e))],
        )
        return router, delivered

    def test_duplicate_idempotency_key_suppressed(self):
        router, delivered = self.collector()
        ts = utc(2026, 9, 1, 14, 0)
        assert router.handle(make_event(ts=ts))
        assert not router.handle(make_event(ts=ts))  # same second -> same key
        assert len(delivered) == 1

    def test_cooldown_suppresses_then_rearms(self):
        router, delivered = self.collector()
        t0 = utc(2026, 9, 1, 14, 0)
        cooldown = router.config.cooldown_for("hod_momentum")
        assert cooldown == 180.0          # Configuration, not a Warrior value
        assert router.handle(make_event(ts=t0))
        assert not router.handle(make_event(ts=t0 + timedelta(seconds=cooldown - 1)))
        assert router.handle(make_event(ts=t0 + timedelta(seconds=cooldown + 1)))
        assert len(delivered) == 2

    def test_consolidation_group_records_later_alerts(self):
        # The primary alert's group keeps filling so the UI can show "+N more"
        # while every raw event stays in history.
        groups = []
        router = NotificationRouter(
            RouterConfig(consolidation_window_seconds=3.0),
            [CallbackChannel(lambda e, c: groups.append(c))],
        )
        t0 = utc(2026, 9, 1, 14, 0)
        router.handle(make_event(ts=t0, scanner="five_pillars_alert"))
        router.handle(make_event(ts=t0 + timedelta(seconds=1), scanner="running_up"))
        router.handle(make_event(ts=t0 + timedelta(seconds=2), scanner="squeeze_5_in_5"))
        assert len(groups) == 1
        assert groups[0]["primary"] == "five_pillars_alert"
        assert groups[0]["also_triggered"] == ["running_up", "squeeze_5_in_5"]
        assert groups[0]["count"] == 3

    def test_hod_requires_meaningful_advance(self):
        from momentum_platform.scanners import HodMomentumScanner
        scanner = HodMomentumScanner(min_hod_advance_pct=0.5)
        hot = HotState()
        state = hot.get("ABCD")
        base = snapshot(last=10.0, session_high=10.0, change_from_close_pct=20.0,
                        rvol_daily=6.0, volume_5m=50_000, float_shares=10_000_000,
                        event_ts=utc(2026, 9, 1, 14, 0), session=Session.REGULAR)
        scanner.on_snapshot(base, None, state, hot)
        tick = snapshot(last=10.02, session_high=10.02, change_from_close_pct=20.0,
                        rvol_daily=6.0, volume_5m=50_000, float_shares=10_000_000,
                        event_ts=utc(2026, 9, 1, 14, 1), session=Session.REGULAR)
        assert scanner.on_snapshot(tick, None, state, hot) == []   # +0.2% is noise
        real = snapshot(last=10.30, session_high=10.30, change_from_close_pct=20.0,
                        rvol_daily=6.0, volume_5m=50_000, float_shares=10_000_000,
                        event_ts=utc(2026, 9, 1, 14, 2), session=Session.REGULAR)
        assert len(scanner.on_snapshot(real, None, state, hot)) == 1

    def test_price_tier_overrides_cooldown(self):
        router, delivered = self.collector()
        t0 = utc(2026, 9, 1, 14, 0)
        assert router.handle(make_event(ts=t0, last=6.00))
        # +3% within cooldown -> new tier -> delivered anyway
        assert router.handle(make_event(ts=t0 + timedelta(seconds=10), last=6.18))
        assert len(delivered) == 2

    def test_consolidation_groups_same_symbol(self):
        delivered = []
        router = NotificationRouter(
            RouterConfig(consolidation_window_seconds=3.0),
            [CallbackChannel(lambda e, c: delivered.append(e))],
        )
        t0 = utc(2026, 9, 1, 14, 0)
        assert router.handle(make_event(ts=t0, scanner="five_pillars_alert"))
        assert not router.handle(make_event(ts=t0 + timedelta(seconds=1), scanner="running_up"))
        assert len(delivered) == 1

    def test_min_severity_filter(self):
        router, delivered = self.collector()
        router.config.min_severity = "high"
        assert not router.handle(make_event(severity="medium", scanner="running_up"))
        assert router.handle(make_event(severity="high"))

    def test_channel_failure_does_not_raise(self):
        router = NotificationRouter(
            RouterConfig(consolidation_window_seconds=0.0), [FailingChannel()]
        )
        assert router.handle(make_event())  # handled, delivery recorded as failed
        assert router.deliveries[-1].status == "failed"


# --------------------------------------------------------------------------
# Event store
# --------------------------------------------------------------------------

class TestEventStore:
    def test_save_and_query(self, tmp_path):
        store = EventStore(str(tmp_path / "events.db"))
        assert store.save_event(make_event())
        assert not store.save_event(make_event())  # duplicate idempotency key
        rows = store.events(symbol="ABCD")
        assert len(rows) == 1
        assert rows[0]["scanner_id"] == "hod_momentum"
        store.close()

    def test_watchlist_roundtrip(self, tmp_path):
        store = EventStore(str(tmp_path / "events.db"))
        store.add_to_watchlist("abcd")
        store.add_to_watchlist("QUIE")
        assert store.watchlist() == ["ABCD", "QUIE"]
        store.remove_from_watchlist("ABCD")
        assert store.watchlist() == ["QUIE"]
        store.close()


# --------------------------------------------------------------------------
# First-pullback state machine
# --------------------------------------------------------------------------

class TestFirstPullback:
    def bars(self, specs):
        base = utc(2026, 9, 1, 13, 31)
        return [
            make_bar("ABCD", base + timedelta(minutes=i), o, h, l, c, v)
            for i, (o, h, l, c, v) in enumerate(specs)
        ]

    def test_arms_and_freezes_plan(self):
        det = FirstPullbackDetector()
        bars = self.bars([
            (5.00, 5.25, 4.98, 5.20, 900_000),   # impulse 1 (green)
            (5.20, 5.55, 5.18, 5.50, 1_000_000), # impulse 2 (green)
            (5.50, 5.52, 5.38, 5.40, 300_000),   # pullback 1 (red, light volume)
            (5.40, 5.42, 5.30, 5.35, 250_000),   # pullback 2
            (5.35, 5.50, 5.34, 5.48, 800_000),   # trigger: high > prior bar high
        ])
        plan = None
        for bar in bars:
            result = det.on_bar(bar)
            plan = result or plan
        assert plan is not None
        assert det.state == SetupState.ARMED
        # Entry above the trigger high; stop under the COMPLETE pullback low.
        assert plan.trigger_high == 5.42
        assert plan.entry == pytest.approx(5.43)
        assert plan.stop == pytest.approx(5.29)
        assert plan.risk_share == pytest.approx(0.14)
        assert plan.target == pytest.approx(5.43 + 0.28)
        assert plan.pullback_candles == 2
        assert plan.volume_ok  # pullback volume lighter than impulse volume

    def test_plan_does_not_repaint(self):
        det = FirstPullbackDetector()
        for bar in self.bars([
            (5.00, 5.25, 4.98, 5.20, 900_000),
            (5.20, 5.55, 5.18, 5.50, 1_000_000),
            (5.50, 5.51, 5.38, 5.40, 300_000),
            (5.42, 5.55, 5.40, 5.53, 800_000),   # trigger after one pullback bar
        ]):
            det.on_bar(bar)
        frozen = det.active_plan
        entry, stop, target = frozen.entry, frozen.stop, frozen.target
        # Later bars must not move the bands.
        det.on_bar(make_bar("ABCD", utc(2026, 9, 1, 13, 40), 5.48, 5.49, 5.40, 5.45, 100_000))
        assert (frozen.entry, frozen.stop, frozen.target) == (entry, stop, target)

    def test_triggered_then_target_hit(self):
        det = FirstPullbackDetector()
        for bar in self.bars([
            (5.00, 5.25, 4.98, 5.20, 900_000),
            (5.20, 5.55, 5.18, 5.50, 1_000_000),
            (5.50, 5.52, 5.38, 5.40, 300_000),
            (5.40, 5.42, 5.30, 5.35, 250_000),
            (5.35, 5.50, 5.34, 5.48, 800_000),   # arms (entry 5.43, target 5.71)
        ]):
            det.on_bar(bar)
        det.on_bar(make_bar("ABCD", utc(2026, 9, 1, 13, 36), 5.44, 5.50, 5.42, 5.49, 500_000))
        assert det.state == SetupState.TRIGGERED
        det.on_bar(make_bar("ABCD", utc(2026, 9, 1, 13, 37), 5.49, 5.75, 5.48, 5.72, 700_000))
        assert det.state == SetupState.TARGET_HIT

    def test_quiet_drift_is_not_counted_as_the_impulse(self):
        """Regression: an unbounded impulse leg swallowed a long low-volume
        premarket drift, dragging mean impulse volume below the pullback's and
        inverting the volume test on a textbook setup."""
        det = FirstPullbackDetector()
        specs = [(5.00 + i * 0.002, 5.005 + i * 0.002, 4.998 + i * 0.002,
                  5.004 + i * 0.002, 2_400) for i in range(60)]   # quiet drift
        specs += [(5.12, 5.30, 5.11, 5.28, 70_000),               # real impulse
                  (5.28, 5.55, 5.27, 5.52, 65_000),
                  (5.52, 5.54, 5.38, 5.40, 14_000),               # light pullback
                  (5.40, 5.42, 5.30, 5.35, 13_000),
                  (5.35, 5.50, 5.34, 5.48, 60_000)]               # trigger
        for bar in self.bars(specs):
            det.on_bar(bar)
        assert det.active_plan is not None
        assert det.active_plan.volume_ok, "pullback volume was lighter than the impulse"

    def test_long_pullback_expires(self):
        det = FirstPullbackDetector(max_pullback_bars=4)
        specs = [
            (5.00, 5.25, 4.98, 5.20, 900_000),
            (5.20, 5.55, 5.18, 5.50, 1_000_000),
        ]
        # five pullback candles with declining highs: lost interest
        specs += [(5.50 - i * 0.05, 5.51 - i * 0.05, 5.40 - i * 0.05,
                   5.45 - i * 0.05, 200_000) for i in range(5)]
        for bar in self.bars(specs):
            det.on_bar(bar)
        assert det.state == SetupState.SEEKING_IMPULSE
        assert det.plans == []


# --------------------------------------------------------------------------
# Golden end-to-end replay
# --------------------------------------------------------------------------

class TestGoldenReplay:
    def run_replay(self, tmp_path):
        source = ReplaySource.from_file(FIXTURES / "demo_momentum_day.jsonl")
        store = EventStore(str(tmp_path / "replay.db"))
        collected = []
        router = NotificationRouter(
            RouterConfig(), [CallbackChannel(lambda e, c: collected.append(e))]
        )
        engine = ScannerEngine(
            scanners=[
                FivePillarsAlert(),
                HodMomentumScanner(),
                RunningMoveScanner(direction="up"),
                Breakout52wScanner(),
                FivePillarsList(),
                top_gainers(),
            ],
            router=router,
            store=store,
        )
        source.apply_static(engine.hot)
        events = []
        last_ts = None
        for update in source.market_updates():
            events.extend(engine.process(update))
            last_ts = update.ts
        return engine, events, collected, store, last_ts

    def test_replay_is_deterministic(self, tmp_path):
        _, events_a, _, store_a, _ = self.run_replay(tmp_path / "a")
        _, events_b, _, store_b, _ = self.run_replay(tmp_path / "b")
        key = lambda evs: [(e.symbol, e.scanner, e.branch, e.source_ts) for e in evs]
        assert key(events_a) == key(events_b)
        store_a.close(); store_b.close()

    def test_expected_scanners_fire(self, tmp_path):
        engine, events, collected, store, last_ts = self.run_replay(tmp_path)
        fired = {e.scanner for e in events}
        assert "five_pillars_alert" in fired    # rvol crosses 5x on the 4th bar
        assert "hod_momentum" in fired          # repeated new HODs
        assert "running_up" in fired            # +5% inside 5 minutes
        assert "breakout_52w" in fired          # 7.95 > 7.90 prior 52w high
        # The quiet control symbol never alerts.
        assert all(e.symbol == "ABCD" for e in events)
        # Every event is explainable and versioned.
        for e in events:
            assert e.reasons and e.definition_version
        # News flame attached: headline is ~35 minutes old at the open -> red.
        flames = [e.news["flame"] for e in events if e.news]
        assert "red" in flames
        store.close()

    def test_five_pillars_fires_exactly_once(self, tmp_path):
        _, events, _, store, _ = self.run_replay(tmp_path)
        fp = [e for e in events if e.scanner == "five_pillars_alert"]
        assert len(fp) == 1
        assert fp[0].source_ts == utc(2026, 9, 1, 13, 34)  # the 4th ABCD bar
        store.close()

    def test_events_persisted_with_dedupe(self, tmp_path):
        engine, events, _, store, _ = self.run_replay(tmp_path)
        assert len(store.events(limit=500)) == len(events)
        store.close()

    def test_ranked_lists(self, tmp_path):
        engine, _, _, store, last_ts = self.run_replay(tmp_path)
        lists = engine.rank_all(last_ts)
        gainers = lists["top_gainers"]
        assert gainers[0].symbol == "ABCD"      # +53.9% leads
        pillars = lists["five_pillars_list"]
        assert [r.symbol for r in pillars] == ["ABCD"]
        store.close()


# -- absent data must not silence discovery -----------------------------------
# No free feed publishes float. Gating discovery on it made the Five Pillars
# list permanently empty and the HOD scanner permanently silent on exactly the
# data most people have, while the verdict card could never reach GO.

def test_unknown_float_does_not_empty_the_five_pillars_list():
    from momentum_platform.scanners.five_pillars import FivePillarsList, score_pillars
    from momentum_platform.models import SymbolSnapshot, DataStatus, FloatQuality
    from datetime import datetime, timezone

    now = datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc)
    snap = SymbolSnapshot(
        symbol="TEST", last=7.0, change_from_close_pct=45.0, rvol_daily=12.0,
        float_shares=None, float_quality=FloatQuality.UNKNOWN,
        data_status=DataStatus.REPLAY, event_ts=now,
    )
    reasons, technical, _ = score_pillars(snap, now)
    assert technical == 3, "an unknown float still fails its own pillar"
    by = {r.filter: r for r in reasons}
    assert by["float_shares"].passed is False
    assert by["price_in_band"].passed and by["gain_pct"].passed and by["rvol_daily"].passed


def test_a_known_float_above_the_cap_still_excludes():
    """Unknown is not evidence of smallness. A verified-too-large float is a
    real disqualification and must keep excluding the candidate."""
    from momentum_platform.scanners.five_pillars import score_pillars, FLOAT_MAX_SHARES
    from momentum_platform.models import SymbolSnapshot, DataStatus, FloatQuality
    from datetime import datetime, timezone

    now = datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc)
    snap = SymbolSnapshot(
        symbol="BIG", last=7.0, change_from_close_pct=45.0, rvol_daily=12.0,
        float_shares=FLOAT_MAX_SHARES * 10, float_quality=FloatQuality.VERIFIED,
        data_status=DataStatus.REPLAY, event_ts=now,
    )
    reasons, _, _ = score_pillars(snap, now)
    fr = {r.filter: r for r in reasons}["float_shares"]
    assert fr.value != "unknown" and fr.passed is False


def test_hod_momentum_admits_three_pillars_in_thin_tape():
    """Premarket: 3,000 shares all session, but price in band, gain and a
    small known float. The share floor is replaced by 3/5 pillars."""
    from momentum_platform.scanners.momentum_events import HodMomentumScanner
    sc = HodMomentumScanner()
    now = utc(2026, 9, 4, 8, 40)
    first = snapshot(last=12.0, session_high=12.0, change_from_close_pct=26.0, event_ts=now,
                     volume_5m=500, rvol_5m=None, rvol_daily=0.1, float_shares=12_000_000,
                     float_quality=FloatQuality.SHARES_OUTSTANDING)
    assert sc.on_snapshot(first, None, None, None) == []
    second = snapshot(last=12.6, session_high=12.6, change_from_close_pct=32.0, event_ts=now,
                      volume_5m=500, rvol_5m=None, rvol_daily=0.1, float_shares=12_000_000,
                      float_quality=FloatQuality.SHARES_OUTSTANDING)
    events = sc.on_snapshot(second, first, None, None)
    assert len(events) == 1, "price, gain and float pillars admit the name"
    by = {r.filter: r for r in events[0].reasons}
    assert by["pillars_passed"].value == 3 and by["volume_5m"].passed
    # one pillar short and no volume: silent, as before
    poor = snapshot(last=25.0, session_high=25.0, change_from_close_pct=32.0, event_ts=now,
                    volume_5m=500, rvol_5m=None, rvol_daily=0.1, float_shares=None)
    sc2 = HodMomentumScanner()
    sc2.on_snapshot(snapshot(last=24.0, session_high=24.0, event_ts=now), None, None, None)
    assert sc2.on_snapshot(poor, None, None, None) == []


def test_hod_momentum_labels_an_unknown_float_rather_than_going_silent():
    """The branch is a label, by the scanner's own docstring. Letting a missing
    label suppress the alert made the scanner mute on every free feed."""
    from momentum_platform.scanners.momentum_events import HodMomentumScanner
    from momentum_platform.models import SymbolSnapshot, DataStatus, FloatQuality
    from datetime import datetime, timezone

    s = HodMomentumScanner()
    snap = SymbolSnapshot(
        symbol="TEST", last=7.0, change_from_close_pct=45.0, rvol_5m=6.0,
        volume_5m=90_000, float_shares=None, float_quality=FloatQuality.UNKNOWN,
        data_status=DataStatus.REPLAY, event_ts=datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc),
    )
    branch = s._branch(snap)
    assert branch is not None, "an unknown float must not suppress the alert"
    assert branch.startswith("unknown_float"), branch


def test_desk_band_is_the_operators_and_the_pillar_band_never_moves(monkeypatch):
    """Two bands. The Confirmed pillar ($2-20) is what the Five Pillars analysis
    evaluates and it cannot be overridden. The desk's discovery band is the
    operator's ($1-30 by default), labelled as theirs, never as Ross's."""
    import importlib
    from momentum_platform.scanners import five_pillars as fp
    monkeypatch.setenv("DESK_PRICE_MIN", "1")
    monkeypatch.setenv("DESK_PRICE_MAX", "30")
    mod = importlib.reload(fp)
    try:
        assert (mod.PRICE_MIN, mod.PRICE_MAX) == (2.0, 20.0)
        assert mod.PRICE_BAND_EVIDENCE == "confirmed_course"
        assert (mod.DESK_PRICE_MIN, mod.DESK_PRICE_MAX) == (1.0, 30.0)
        assert mod.DESK_BAND_EVIDENCE == "operator_override"
        monkeypatch.setenv("DESK_PRICE_MIN", "2")
        monkeypatch.setenv("DESK_PRICE_MAX", "20")
        mod = importlib.reload(fp)
        assert mod.DESK_BAND_EVIDENCE == "confirmed_course"
    finally:
        monkeypatch.delenv("DESK_PRICE_MIN")
        monkeypatch.delenv("DESK_PRICE_MAX")
        importlib.reload(fp)
    assert (fp.PRICE_MIN, fp.PRICE_MAX) == (2.0, 20.0)


def test_shares_outstanding_under_the_cap_passes_the_float_pillar():
    from momentum_platform.scanners.five_pillars import score_pillars, FLOAT_MAX_SHARES
    from momentum_platform.models import SymbolSnapshot, DataStatus, FloatQuality
    from datetime import datetime, timezone
    now = datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc)
    snap = SymbolSnapshot(symbol="SO", last=7.0, change_from_close_pct=40.0, rvol_daily=12.0,
                          float_shares=FLOAT_MAX_SHARES - 1, float_quality=FloatQuality.SHARES_OUTSTANDING,
                          data_status=DataStatus.REPLAY, event_ts=now)
    _, technical, _ = score_pillars(snap, now)
    assert technical == 4


def test_shares_outstanding_over_the_cap_does_not_exclude_from_the_list():
    """Over the cap the bound proves nothing about float, so the candidate
    must still be discoverable — only a VERIFIED float over the cap excludes."""
    from momentum_platform.scanners.five_pillars import FivePillarsList, FLOAT_MAX_SHARES
    from momentum_platform.models import SymbolSnapshot, DataStatus, FloatQuality
    from momentum_platform.state import HotState
    from datetime import datetime, timezone
    now = datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc)
    hot = HotState()
    for sym, q in (("BIG", FloatQuality.SHARES_OUTSTANDING), ("VER", FloatQuality.VERIFIED)):
        st = hot.get(sym)
        st.snapshot = SymbolSnapshot(symbol=sym, last=7.0, change_from_close_pct=40.0, rvol_daily=12.0,
                                     float_shares=FLOAT_MAX_SHARES * 5, float_quality=q,
                                     data_status=DataStatus.REPLAY, event_ts=now)
    rows = {r.symbol for r in FivePillarsList().rank(hot, now)}
    assert "BIG" in rows, "an over-cap proxy is unknown, not a disqualification"
    assert "VER" not in rows, "a verified float over the cap is a real disqualification"


def test_premarket_rvol_is_measured_against_the_same_clock_time():
    """The case from the desk on 2026-09-04 at 08:53 ET.

    A runner with 92,930 premarket shares against a 2.2M average full day
    reads 0.04x on the simple daily measure, so the RVOL pillar fails and the
    Five Pillars list is empty however violent the tape is. Measured against
    what prior sessions had traded by 08:53 (about 12,000 shares) the same
    name reads roughly 7.7x, which is what an independent screener showed for
    it that morning."""
    from datetime import datetime, timezone

    from momentum_platform.formulas import enrich_snapshot

    at_0853 = datetime(2026, 9, 4, 12, 53, tzinfo=timezone.utc)
    profile = [0.0] * 192
    for i in range(58):                       # cumulative premarket volume by bucket
        profile[i] = 208.0 * (i + 1)
    for i in range(58, 192):
        profile[i] = profile[57]
    snap = SymbolSnapshot(symbol="AOUT", last=12.73, prev_close=10.01,
                          volume_today=92_930, avg_daily_volume=2_200_000,
                          event_ts=at_0853, volume_profile=profile)
    enrich_snapshot(snap)
    assert snap.rvol_daily == pytest.approx(0.042, abs=0.002)
    assert snap.rvol_measure == "time_of_day"
    assert snap.rvol == pytest.approx(7.7, abs=0.3)
    assert snap.rvol >= 5.0, "the pillar the daily measure could never pass"

    # With no profile the desk says so rather than inventing one.
    bare = SymbolSnapshot(symbol="AOUT", last=12.73, prev_close=10.01,
                          volume_today=92_930, avg_daily_volume=2_200_000, event_ts=at_0853)
    enrich_snapshot(bare)
    assert bare.rvol_measure == "daily" and bare.rvol == bare.rvol_daily
