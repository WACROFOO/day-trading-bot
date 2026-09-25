"""2026-09-25 full assessment: A11 (MACD flags in regular hours), the chart
autoscale reset on a symbol change, keep-awake on macOS, and the backtest
tool's simulator."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_recent as BT  # noqa: E402
import day  # noqa: E402
from execution import runner as RN  # noqa: E402
from execution.runner import Runner  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"
NOW = lambda: datetime(2026, 9, 1, 14, 5, tzinfo=timezone.utc)   # noqa: E731
FRESH = lambda s: dict(bid=6.02, ask=6.04, bid_size=100, ask_size=100, ts="2026-09-01T14:04:58Z")   # noqa: E731


def _gates(**st):
    base = {"price": "PASS", "vwap": "PASS", "ema9": "PASS", "macd": "PASS"}
    base.update(st)
    return json.dumps([{"id": k, "state": v, "value": "", "reason": "", "kills": False} for k, v in base.items()])


class _T:
    account = "DU1"; placed = []
    def place_bracket(self, *a, **k): raise AssertionError("not reached: the quote check refuses first")
    def adopt(self, rows): return 0
    def sync(self): pass


def _run(session: str, **st):
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    c.execute("UPDATE decisions SET verdict='WAIT', volume_ok=1, session=?, gates_json=? WHERE plan_allowed=1",
              (session, _gates(**st))); c.commit()
    # no quote: a plan that clears Layer 2 is refused by the quote clock instead, so no order path is needed
    return Runner(c, mode="TRADE", dollar_risk=20.0, trader=_T(), now=NOW, max_age_s=36000, quote=lambda s: None).step()


def _l2(acted):
    return [any(x.startswith("Layer 2 not green") for x in a.reasons) for a in acted]


def test_a11_macd_alone_does_not_refuse_in_regular_hours():
    assert RN.MACD_FLAG_ONLY_REGULAR is True
    acted = _run("regular", macd="FAIL")
    assert acted and not any(_l2(acted)), [a.reasons for a in acted]


def test_a11_vwap_and_ema9_still_refuse_in_regular_hours():
    assert all(_l2(_run("regular", vwap="FAIL")))
    assert all(_l2(_run("regular", ema9="FAIL", macd="FAIL")))
    assert all(_l2(_run("regular", vwap="UNKNOWN")))          # unknown is red, as before


def test_a11_does_not_touch_pre_market():
    assert all(_l2(_run("premarket", macd="FAIL")))


def test_a_symbol_change_restores_price_autoscale():
    js = (ROOT / "src/momentum_platform/dashboard/web/app.js").read_text()
    i = js.index('priceScale("right").applyOptions({ autoScale: true })')
    assert "opts.snapToLive" in js[i - 400:i]


def test_keep_awake_is_macos_only_and_never_raises(monkeypatch):
    assert day.keep_awake(True) is None
    monkeypatch.setattr(day.sys, "platform", "linux")
    assert day.keep_awake(False) is None


def test_backtest_simulator_fills_a_gap_through_the_stop_at_the_open():
    t0 = datetime(2026, 9, 25, 10, 28, tzinfo=ZoneInfo("America/New_York"))
    bars = [(t0, 16.39, 16.50, 16.30, 16.45, 1), (t0 + timedelta(minutes=1), 15.99, 16.0, 15.90, 15.95, 1)]
    r, why, _ = BT.simulate(bars, 16.39, 16.11, "trail")
    assert why == "trail" and r == round((15.99 - 16.39) / 0.28, 3)       # opened under the 16.22 trail
    r, why, _ = BT.simulate(bars, 16.39, 16.11, "fixed")
    assert why == "stop" and r == round((15.99 - 16.39) / 0.28, 3)       # and under the 16.11 stop
