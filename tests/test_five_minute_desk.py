"""The 5-minute display state on the desk (owner, 2026-10-06) and the B30 switch.

E1 — buy the first 5-minute candle to make a new high after a straight green
1-minute run — failed its preregistered test (research/edge-hunt/PREREGISTRATION.md
addendum 2026-10-06b; research/paper-exercise/reports/five_minute_output.txt).
The desk therefore SHOWS the state and never orders on it. B30 passed the
per-trade rule but adds trades that lose after costs, so it is built OFF."""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from execution import runner as RN  # noqa: E402
from execution.runner import Runner  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform import five_minute as FM  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402
from momentum_platform.sessions import ET  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"
T0 = int(datetime(2024, 3, 5, 9, 30, tzinfo=ET).timestamp())


def minutes(spec, t0=T0):
    return [(t0 + 60 * i, o, h, l, c, v) for i, (o, h, l, c, v) in enumerate(spec)]


def candle(o, c, lo=None, hi=None, v=1000, n=5):
    out, step = [], (c - o) / n
    for i in range(n):
        a, b = o + step * i, o + step * (i + 1)
        out.append([a, max(a, b), min(a, b), b, v])
    if hi is not None:
        out[n // 2][1] = hi
    if lo is not None:
        out[n // 2][2] = lo
    return [tuple(x) for x in out]


# ------------------------------------------------------------------ parity with the study
def test_the_desk_machine_is_the_studys_machine():
    """Same placements as scripts/five_minute.e1_placements on random tapes."""
    FS = pytest.importorskip("five_minute")
    rng = random.Random(7)
    for _ in range(60):
        px, spec = 5.0, []
        for _ in range(rng.randint(20, 90)):
            o = px
            c = max(0.5, o * (1 + rng.uniform(-0.02, 0.025)))
            spec.append((o, max(o, c) * (1 + rng.uniform(0, 0.01)), min(o, c) * (1 - rng.uniform(0, 0.01)), c,
                         rng.randint(100, 5000)))
            px = c
        rows = minutes(spec)
        mine, _, _, _ = FM.walk(rows)
        theirs = FS.e1_placements([(datetime.fromtimestamp(t, ET), o, h, l, c, v) for t, o, h, l, c, v in rows])
        assert [(p["entry"], p["stop"], p["order_t"], p["seq"], p["n_pull"]) for p in mine] == \
               [(p["entry"], p["stop"], p["order_t"], p["seq"], p["n_pull"]) for p in theirs]


# ------------------------------------------------------------------ the states
def test_a_straight_green_run_at_the_high_reads_extended():
    up = [(5.0 + 0.1 * i, 5.1 + 0.1 * i, 5.0 + 0.1 * i, 5.1 + 0.1 * i, 1000) for i in range(4)]
    rows = minutes(up)
    st = FM.state_at(rows, now=rows[-1][0] + 60)
    assert st.state == FM.EXTENDED and st.green_run == 4 and st.since == rows[0][0]
    assert "no order" in st.text() and "first 5-minute candle to make a new high" in st.text()
    assert FM.state_at(rows, now=rows[-1][0] + 30).state is None, "a forming minute is not a candle"


def test_three_green_minutes_or_a_red_one_is_not_extended():
    up = [(5.0 + 0.1 * i, 5.1 + 0.1 * i, 5.0 + 0.1 * i, 5.1 + 0.1 * i, 1000) for i in range(3)]
    assert FM.state_at(minutes(up), now=T0 + 180).state is None
    red = up + [(5.3, 5.35, 5.2, 5.25, 1000)]
    assert FM.state_at(minutes(red), now=T0 + 240).state is None


def test_a_5_minute_pause_names_the_trigger_and_the_stop():
    rows = minutes(candle(5.0, 5.3) + candle(5.3, 5.6) + candle(5.6, 5.5, lo=5.45, hi=5.62))
    st = FM.state_at(rows, now=T0 + 15 * 60)
    assert st.state == FM.PULLBACK_5M and st.trigger == 5.63 and st.stop == 5.44 and st.n_pull == 1
    assert st.stop_pct == pytest.approx(round((5.63 - 5.44) / 5.63 * 100, 2))
    assert "over 5.63" in st.text() and "no order" in st.text()
    assert FM.state_at(rows, now=T0 + 20 * 60 + 1).state != FM.PULLBACK_5M, \
        "the trigger lives for the next candle only"


# ------------------------------------------------------------------ desk, ledger, watch
def test_the_session_payload_and_the_ledger_carry_the_state_once():
    c = L.connect(":memory:")
    s1 = build_session(FIXTURE, journal=c)
    assert "fiveMinute" in s1 and isinstance(s1["fiveMinute"], dict)
    st = FM.FiveMinuteState(FM.EXTENDED, since=T0, green_run=5)
    assert L.record_five_minute_state(c, "TEST", st, data_status="live") == "new"
    assert L.record_five_minute_state(c, "TEST", st, data_status="live") == "seen"
    rows = L.five_minute_rows(c, "2024-03-05")
    assert len(rows) == 1 and rows[0]["state"] == "EXTENDED" and rows[0]["ts_et"].startswith("2024-03-05T09:30")
    assert L.record_five_minute_state(c, "TEST", FM.FiveMinuteState(None)) == "skipped"


def test_watch_prints_each_state_once(tmp_path):
    import watch as W
    db = tmp_path / "j.sqlite"
    c = L.connect(str(db))
    L.record_five_minute_state(c, "AMOD", FM.FiveMinuteState(FM.PULLBACK_5M, since=T0, trigger=5.63, stop=5.44,
                                                             n_pull=1), data_status="live")
    c.commit()
    w = W.Watcher(W.connect_ro(db), day="2024-03-05")
    got = [t for _, t in w.poll() if "5-MIN PB" in t]
    assert len(got) == 1 and "5.63/5.44" in got[0] and "no order" in got[0]
    assert [t for _, t in w.poll() if "5-MIN PB" in t] == []


def test_the_runner_never_reads_the_display_table():
    src = (ROOT / "src" / "execution" / "runner.py").read_text() + (ROOT / "src" / "execution" / "bridge.py").read_text()
    assert "five_minute_states" not in src and "five_minute" not in src.replace("five_minute_output", "")


# ------------------------------------------------------------------ B30, OFF
def _warmup_journal(bars: int):
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    gj = json.dumps([{"id": "vwap", "state": "PASS"}, {"id": "ema9", "state": "PASS"},
                     {"id": "macd", "state": "UNKNOWN"}])
    c.execute("UPDATE decisions SET verdict='WATCH', gates_json=?, chart_json=?, volume_ok=1 WHERE plan_allowed=1",
              (gj, json.dumps({"bars": bars})))
    c.commit()
    L.set_state(c, phase="B")
    return c


class _T:
    account = "DU1"; placed = []

    def __init__(self):
        self.sent = []

    def place_bracket(self, intent, now=None):
        from execution.intent import PlacedOrder
        self.sent.append(intent)
        rec = PlacedOrder(symbol=intent.symbol, parent_id=100 + len(self.sent), stop_id=200 + len(self.sent),
                          trigger=intent.trigger, stop=intent.stop, shares=intent.shares, protected=True)
        self.placed.append(rec)
        return rec

    def adopt(self, rows): return 0
    def sync(self): pass


NOW = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
FRESH = lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z")  # noqa: E731


def test_b30_is_off_and_the_refusal_names_the_warm_up():
    assert RN.B30_WARMUP_MACD is False
    c = _warmup_journal(bars=20)
    done = Runner(c, mode="TRADE", dollar_risk=20.0, trader=_T(), now=NOW, max_age_s=3600, quote=FRESH).step()
    l2 = [x for a in done for x in a.reasons if x.startswith("Layer 2")]
    assert l2 and all("desk held 20" in x and "B30 candidate, OFF" in x for x in l2)


def test_b30_on_lets_only_a_warm_up_macd_through(monkeypatch):
    monkeypatch.setattr(RN, "B30_WARMUP_MACD", True)
    c = _warmup_journal(bars=20)
    done = Runner(c, mode="TRADE", dollar_risk=20.0, trader=_T(), now=NOW, max_age_s=3600, quote=FRESH).step()
    assert done and not any(x.startswith("Layer 2") for a in done for x in a.reasons)
    c2 = _warmup_journal(bars=40)                     # MACD should exist at 40 bars: UNKNOWN there is not warm-up
    done2 = Runner(c2, mode="TRADE", dollar_risk=20.0, trader=_T(), now=NOW, max_age_s=3600, quote=FRESH).step()
    assert done2 and all(any(x.startswith("Layer 2") for x in a.reasons) for a in done2)
