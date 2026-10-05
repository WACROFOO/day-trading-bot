"""Setup S (the green-run continuation) on the desk: parity with the frozen
research code, the reasoned record, the shadow log, its desk wiring, the
after-the-close score, and the proof that nothing of it reaches the runner.

Every market here is SYNTHETIC (a seeded random walk). It proves the code
agrees with itself and with `scripts/green_run.py`, never anything about a
market. data/cache is not needed: the frozen code's minute history is written
to a temporary directory and its order engine is stubbed out, so only the
detection and the filters — what the desk log reproduces — are compared.
"""
from __future__ import annotations

import inspect
import json
import math
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import green_run as FROZEN  # noqa: E402  scripts/green_run.py, setup frozen at 20aa85f
import runup_micro as RM  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform import green_run as G  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
SEEDS = range(8)


# ------------------------------------------------------------ synthetic tape
def _epoch(day: str, hm: str) -> int:
    return int(datetime.fromisoformat(f"{day}T{hm}:00").replace(tzinfo=ET).timestamp())


def synth(seed: int, day: str = "2026-09-15", end: str = "10:00"):
    """Prints from 04:00 ET: a slow walk until 07:00, then regimes of climb,
    pause, fade and spike, one print every 1-4 s. Starting prices straddle the
    $2-20 band so every refusal gets exercised somewhere."""
    rng = random.Random(seed)
    p0 = [4.0, 1.9, 15.0, 8.0][seed % 4]
    t, t7, t_end = _epoch(day, "04:00"), _epoch(day, "07:00"), _epoch(day, end)
    lp, drift, left = math.log(p0), 0.0, 0
    T, P, V = [], [], []
    while t < t_end:
        if left <= 0:
            drift = rng.choice([0.0004, 0.0, 0.0, -0.0004, 0.001, -0.0002]) if t >= t7 else 0.0
            left = rng.randint(20, 120)
        dt = rng.randint(1, 4) if t >= t7 else rng.randint(5, 40)
        t += dt
        left -= dt
        lp += drift * dt + rng.gauss(0, 0.0008) * math.sqrt(dt)
        lp = min(max(lp, math.log(1.5)), math.log(25))
        T.append(t * 1000 + rng.randint(0, 999))
        P.append(round(math.exp(lp), 2))
        V.append(rng.randint(1, 50) * 100)
    return np.array(T, dtype=np.int64), np.array(P), np.array(V)


def minutes_of(T, P, V):
    """1-minute bars (start, o, h, l, c, v) from prints — the history file's content."""
    out: dict = {}
    for t, p, v in zip(T, P, V):
        k = int(t // 60000) * 60
        b = out.setdefault(k, [float(p), float(p), float(p), float(p), 0.0])
        b[1], b[2], b[3], b[4] = max(b[1], p), min(b[2], p), float(p), b[4] + float(v)
    return [(k, *out[k]) for k in sorted(out)]


def tens_of(T, P, V):
    """10-second bars WITH volume: RM._bars10 plus the summed size (for the desk feed)."""
    out: dict = {}
    for t, p, v in zip(T, P, V):
        k = int(t // 10000) * 10
        b = out.setdefault(k, [float(p), float(p), float(p), float(p), 0.0])
        b[1], b[2], b[3], b[4] = max(b[1], p), min(b[2], p), float(p), b[4] + float(v)
    return [(k, *out[k]) for k in sorted(out)]


def frozen_day(seed, tmp_path, monkeypatch, day="2026-09-15"):
    """The frozen code's view of one synthetic symbol-day: its minute context,
    its 10-second bars, its chart-approved pauses, and run_day's signals with
    the order engine stubbed (every signal passed to it is recorded, none is
    'busy'), so what is compared is detection + filters, nothing else."""
    T, P, V = synth(seed, day)
    m = minutes_of(T, P, V)
    rows = [[datetime.fromtimestamp(k, UTC).isoformat().replace("+00:00", "Z"), o, h, l, c, v]
            for k, o, h, l, c, v in m]
    hist = tmp_path / "history"
    hist.mkdir(exist_ok=True)
    (hist / f"{day}.json").write_text(json.dumps({"SYN": rows}))
    monkeypatch.setattr(RM, "HISTORY", hist)
    sel = T >= _epoch(day, "07:00") * 1000                       # the research fetched ticks from 07:00
    t, p = T[sel], P[sel]
    bars = RM._bars10(t, p)
    ctx = FROZEN.minute_context(day, "SYN")
    armed = lambda ts: bool((FROZEN._ctx_at(ctx, ts) or {}).get("ok"))      # noqa: E731
    chart = list(RM._signals(bars, armed, None, False))
    monkeypatch.setattr(RM, "_trade", lambda *a, **k: {"t_out": 0})
    sig = FROZEN.run_day({"day": day, "sym": "SYN"}, t, p, bars, ctx, "1m")
    return m, bars, ctx, chart, sig


# ------------------------------------------------------------ 1. parity
@pytest.mark.parametrize("seed", SEEDS)
def test_parity_with_the_frozen_research_code(seed, tmp_path, monkeypatch):
    """Same bars in, same answer out: the 1-minute context bar by bar, the
    chart-approved pauses (entry), and the signals that survive the price,
    stop-floor and spread filters (entry, stop, pre-market flag)."""
    m, bars, ctx, chart, sig = frozen_day(seed, tmp_path, monkeypatch)
    ms = G.minute_series(m)
    assert len(ctx) == len(ms.t)
    for i, b in enumerate(ctx):
        assert ms.close_t[i] == b["close_t"]
        assert ms.ok(i) is b["ok"], f"bar {i}"
        assert ms.l[i] == b["low"]
        assert ms.dv5[i] == pytest.approx(b["dv5"], rel=1e-12)
        assert all(c.ok for c in ms.checks(i)) == ms.ok(i), "the reasons agree with the verdict"
    mine = G.signals_over_day("SYN", m, bars, window=None)
    assert [(e.t_arm, e.entry) for e in mine] == [(t_arm, entry) for t_arm, entry, _ in chart]
    got = [(e.t_arm, e.entry, e.stop, e.premarket) for e in mine if e.signal]
    want = [(x["t_arm"], x["entry"], x["stop"], x["pm"]) for x in sig]
    assert got == want
    # the desk's window changes nothing here: every synthetic close is 07:00-10:00 ET
    assert [(e.t_arm, e.entry, e.stop) for e in G.signals_over_day("SYN", m, bars) if e.signal] == \
        [(x["t_arm"], x["entry"], x["stop"]) for x in sig]


def test_parity_is_not_vacuous(tmp_path, monkeypatch):
    """The seeds produce signals, refusals of every kind, and pauses the
    1-minute context turns down — so the parity above compared real cases."""
    n_sig, kinds, no_ctx = 0, set(), 0
    for seed in SEEDS:
        m, bars, ctx, chart, sig = frozen_day(seed, tmp_path, monkeypatch)
        n_sig += len(sig)
        evs = G.signals_over_day("SYN", m, bars, window=None)
        kinds |= {c.name for e in evs for c in e.failed()}
        ms = G.minute_series(m)
        no_ctx += sum(1 for n in range(G.LEG_BARS + 1, len(bars) + 1)
                      if G.find_pause(bars[:n])[0] is not None
                      and not ms.ok(G.context_index(ms, int(bars[n - 1][0]) + 10)))
    assert n_sig >= 50
    assert {"price band", "stop >= 2% (A13)", "stop >= 4x spread (A6)"} <= kinds
    assert no_ctx > 0


def test_the_spread_proxy_is_the_repos_proxy():
    import rules_audit as RA
    mine = G.SpreadProxy()
    assert mine.table is not None, "research/edge-hunt/results/spread_proxy.json is tracked"
    for price in (2.0, 3.3, 4.99, 5.0, 7.5, 9.99, 10.0, 15.0, 20.0):
        for pm in (True, False):
            for dv in (0, 49_999, 50_000, 120_000, 499_999, 500_000, 2e6):
                assert mine.spread(price, pm, dv) == RA.PROXY.spread(price, pm, dv)


def test_parameters_are_the_frozen_ones():
    assert (G.STOP_FLOOR_PCT, G.SPREAD_K, G.FADE_MAX) == (FROZEN.STOP_FLOOR_PCT, FROZEN.SPREAD_K, FROZEN.FADE_MAX)
    assert (G.LEG_BARS, G.LEG_MIN_PCT, G.MIN_GREEN, G.TTL_ENTRY_S) == \
        (RM.LEG_BARS, RM.LEG_MIN_PCT, RM.MIN_GREEN, RM.TTL_ENTRY_S)
    import tick_replay as TR
    assert (G.CAP_PCT, G.TRAIL_R, G.TRAIL_EVERY_S) == (TR.CAP_PCT, TR.TRAIL_R, TR.TRAIL_EVERY_S)
    assert G.cap_of(4.0) == TR.RA.cap_of(4.0, TR.CAP_PCT) and G.cap_of(12.34) == TR.RA.cap_of(12.34, TR.CAP_PCT)


# ------------------------------------------------------------ 2. the record
def _first(seed, status, window=None, day="2026-09-15"):
    T, P, V = synth(seed, day)
    m = minutes_of(T, P, V)
    bars = RM._bars10(T[T >= _epoch(day, "07:00") * 1000], P[T >= _epoch(day, "07:00") * 1000])
    for e in G.signals_over_day("SYN", m, bars, window=window):
        if e.status == status:
            return e, m, bars
    return None, m, bars


def test_a_signal_carries_a_reason_for_every_condition():
    ev = next(e for s in SEEDS for e in [_first(s, "SIGNAL")[0]] if e is not None)
    names = [c.name for c in ev.checks]
    for need in ("10-s leg", "10-s pause", "warm-up", "bar green", "bar before green", "new high of day",
                 "above VWAP", "above EMA9", "MACD > signal", "off the high", "entry", "stop", "price band",
                 "stop >= 2% (A13)", "stop >= 4x spread (A6)"):
        assert need in names, need
    assert all(c.ok is True and c.why for c in ev.checks)
    assert ev.refusals() == [] and ev.entry > ev.stop and ev.stop_pct >= 2.0
    assert ev.spread_source == "proxy" and ev.spread == ev.proxy_spread
    assert all(r.startswith("[ok] ") for r in ev.reasons())
    json.dumps(ev.as_dict(), default=str)                      # it can be logged as it is


def test_a_refusal_names_the_rule_and_the_number():
    ev = next(e for s in SEEDS for e in [_first(s, "REFUSED")[0]] if e is not None)
    assert ev.refusals(), "a refusal says why"
    assert all(any(k in r for k in ("price band", "A13", "A6", "stop:")) for r in ev.refusals())
    assert not ev.signal


def test_a_live_spread_replaces_the_proxy_and_can_refuse():
    ev, m, bars = next(x for s in SEEDS for x in [_first(s, "SIGNAL")] if x[0] is not None)
    n = next(k for k in range(1, len(bars) + 1) if int(bars[k - 1][0]) + 10 == ev.t_arm)
    wide = (ev.entry - ev.stop) / 3                              # 3x: under A6's 4x
    out = G.evaluate("SYN", m, bars[:n], live_spread=wide, window=None)
    assert out.status == "REFUSED" and out.spread_source == "live" and out.proxy_spread == ev.proxy_spread
    assert [c.name for c in out.failed()] == ["stop >= 4x spread (A6)"]
    ok = G.evaluate("SYN", m, bars[:n], live_spread=0.01, window=None)
    assert ok.signal and ok.spread == 0.01


def test_outside_the_tested_window_is_its_own_status():
    ev, m, bars = next(x for s in SEEDS for x in [_first(s, "SIGNAL")] if x[0] is not None)
    n = next(k for k in range(1, len(bars) + 1) if int(bars[k - 1][0]) + 10 == ev.t_arm)
    out = G.evaluate("SYN", m, bars[:n], window=("11:30", "16:00"))
    assert out.status == "OUT_OF_WINDOW" and [c.name for c in out.failed()] == ["tested window"]
    # a refusal outside the window is not logged as a refusal either
    ref, m, bars = next(x for s in SEEDS for x in [_first(s, "REFUSED")] if x[0] is not None)
    n = next(k for k in range(1, len(bars) + 1) if int(bars[k - 1][0]) + 10 == ref.t_arm)
    assert G.evaluate("SYN", m, bars[:n], window=("11:30", "16:00")).status == "OUT_OF_WINDOW"


def test_a_forming_minute_is_never_the_context():
    """The context is the last COMPLETED minute: a bar whose end is after the
    10-second close is ignored even when it is handed in."""
    ev, m, bars = next(x for s in SEEDS for x in [_first(s, "SIGNAL")] if x[0] is not None)
    n = next(k for k in range(1, len(bars) + 1) if int(bars[k - 1][0]) + 10 == ev.t_arm)
    done = [b for b in m if b[0] + 60 <= ev.t_arm]
    assert G.evaluate("SYN", m, bars[:n], window=None).as_dict() == \
        G.evaluate("SYN", done, bars[:n], window=None).as_dict()


def test_empty_candles_are_not_bars():
    t0 = _epoch("2026-09-15", "08:00")
    got = G.bars10_from_candles([(t0, 4, 4.1, 3.9, 4.05, 100), (t0 + 10, 4.05, 4.05, 4.05, 4.05, 0),
                                 (t0 + 20, -1, -1, -1, -1, 0), (t0 + 30, 4.05, 4.2, 4.0, 4.1, 300)])
    assert [b[0] for b in got] == [t0, t0 + 30]


# ------------------------------------------------------------ 3. the ledger
def _ev(sym="GRN", t_arm=None, status="SIGNAL", pause_id=None, entry=5.01, stop=4.80):
    t_arm = t_arm or _epoch("2026-09-15", "09:41")
    return G.Evaluation(sym, t_arm, status, [G.Check("x", status == "SIGNAL", 1, "because")],
                        entry=entry, stop=stop, stop_pct=(entry - stop) / entry * 100, spread=0.02,
                        spread_source="live", proxy_spread=0.03, premarket=False,
                        pause_id=pause_id or t_arm - 30, minute_t=t_arm - 70)


def test_one_row_per_pause_rearms_append_and_a_refusal_upgrades():
    c = L.connect(":memory:")
    t = _epoch("2026-09-15", "09:41")
    assert L.record_green_run(c, _ev(t_arm=t, status="REFUSED")) == "new"
    assert L.record_green_run(c, _ev(t_arm=t, status="REFUSED")) == "seen", "same close: a no-op"
    assert L.record_green_run(c, _ev(t_arm=t + 10, status="REFUSED", pause_id=t - 30)) == "rearm"
    assert L.record_green_run(c, _ev(t_arm=t + 20, status="SIGNAL", pause_id=t - 30, entry=5.0)) == "upgraded"
    assert L.record_green_run(c, _ev(t_arm=t + 30, status="SIGNAL", pause_id=t - 30)) == "rearm"
    rows = L.green_run_rows(c, "2026-09-15")
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "SIGNAL" and r["entry"] == 5.0 and r["n_arms"] == 4
    assert r["ts_et"] == L._et(t + 20) and r["session"] == "regular"
    assert [a["status"] for a in r["arms"]] == ["REFUSED", "REFUSED", "SIGNAL", "SIGNAL"]
    assert r["refusals"] == [] and r["reasons"][0]["why"] == "because"
    assert L.record_green_run(c, _ev(t_arm=t + 40, status="NO_CONTEXT")) == "skipped"
    assert L.record_green_run(c, _ev(t_arm=t + 40, pause_id=t + 5)) == "new", "another pause, another row"
    assert len(L.green_run_rows(c)) == 2


# ------------------------------------------------------------ 4. nothing reaches the runner
def _tables_read(conn):
    seen = set()

    def auth(action, a1, a2, db, src):
        if action == sqlite3.SQLITE_READ and a1:
            seen.add(a1)
        return sqlite3.SQLITE_OK
    conn.set_authorizer(auth)
    return seen


def test_the_runner_never_reads_the_green_run_table():
    """Behavioural: a ledger holding green-run SIGNAL rows next to real
    decisions; the runner's loop in LOG_ONLY and TRADE is traced at the SQLite
    authorizer, which sees every table any statement reads. Not one of them
    is green_run_signals, and no order names a green-run symbol."""
    from datetime import datetime as _dt
    from execution.runner import Runner
    from momentum_platform.dashboard.session_builder import build_session
    sys.path.insert(0, str(ROOT / "tests"))
    from test_runner import FakeTrader

    conn = L.connect(":memory:")
    build_session(ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl", journal=conn)
    conn.execute("UPDATE decisions SET verdict='REVIEW' WHERE plan_allowed=1")
    L.set_state(conn, phase="B")
    t = int(_dt(2026, 9, 1, 13, 45, tzinfo=UTC).timestamp())
    for k in range(5):
        L.record_green_run(conn, _ev(sym="GRNRUN", t_arm=t + 60 * k, pause_id=t + 60 * k - 30))
    conn.commit()
    seen = _tables_read(conn)
    Runner(conn, mode="LOG_ONLY", dollar_risk=25.0).step()
    conn.execute("UPDATE decisions SET outcome='PENDING' WHERE plan_allowed=1"); conn.commit()
    trader = FakeTrader()
    now = lambda: _dt(2026, 9, 1, 13, 52, tzinfo=UTC)   # noqa: E731
    r = Runner(conn, mode="TRADE", dollar_risk=25.0, trader=trader, now=now, max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    r.step()
    r.fire_armed()
    conn.set_authorizer(None)
    assert "decisions" in seen, "the trace works: the runner's own table is in it"
    assert "green_run_signals" not in seen, sorted(seen)
    assert trader.intents and all(i.symbol != "GRNRUN" for i in trader.intents)
    assert conn.execute("SELECT COUNT(*) FROM decisions WHERE symbol='GRNRUN'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM orders WHERE symbol='GRNRUN'").fetchone()[0] == 0


def test_no_order_path_module_names_the_green_run():
    """Static: nothing in src/execution/ mentions the table or the module, and
    the desk-side module cannot reach the order path."""
    for f in (ROOT / "src" / "execution").rglob("*.py"):
        src = f.read_text()
        assert "green_run" not in src, f"{f.name} names the green run"
    mod = inspect.getsource(G)
    for word in ("import execution", "from execution", "placeOrder", "bracketOrder", "LimitOrder",
                 "StopOrder", "MarketOrder", "record_decision", "INSERT INTO decisions"):
        assert word not in mod, word


# ------------------------------------------------------------ 5. the desk
def _signal_for_desk(day="2026-09-03", spread=0.02):
    """A synthetic day on the desk's date with a close where setup S says
    SIGNAL with the fake ticker's live spread (bid 4.34 / ask 4.36)."""
    for seed in range(40):
        T, P, V = synth(seed, day)
        m = minutes_of(T, P, V)
        tens = tens_of(T[T >= _epoch(day, "07:00") * 1000], P[T >= _epoch(day, "07:00") * 1000],
                       V[T >= _epoch(day, "07:00") * 1000])
        ms = G.minute_series(m)
        for n in range(G.LEG_BARS + 1, len(tens) + 1):
            if G.find_pause(tens[:n])[0] is None:
                continue
            ev = G.evaluate("AAA", m, tens[:n], live_spread=spread, series=ms)
            if ev.signal:
                return m, tens[:n], ev
    raise AssertionError("no synthetic signal found")


def test_the_desk_logs_a_closed_candle_once_and_writes_no_decision(monkeypatch, tmp_path):
    from fake_ibkr import FakeTicker  # noqa: F401
    from momentum_platform.dashboard import ibkr_desk as D
    from momentum_platform.datasources.ibkr_stream import Bar5s, BarStore
    from test_ibkr_desk import make_desk

    m, tens, want = _signal_for_desk()
    desk, ib, clock = make_desk()
    conn = L.connect(tmp_path / "j.sqlite")
    monkeypatch.setattr(D, "_journal", lambda: conn)
    desk._bootstrap()
    decisions_before = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    t_close = want.t_arm
    # what the desk holds at that close: IBKR minutes completed by then, and
    # the stream's 5-second halves (the second half empty) up to the candle
    desk._minutes["AAA"] = [{"type": "bar", "tf": "1m", "symbol": "AAA",
                             "ts": datetime.fromtimestamp(k, UTC).isoformat().replace("+00:00", "Z"),
                             "open": o, "high": h, "low": l, "close": c, "volume": int(v)}
                            for k, o, h, l, c, v in m if k + 60 <= t_close]
    store = BarStore()
    for k, o, h, l, c, v in tens[:-1]:
        store.append(Bar5s("AAA", datetime.fromtimestamp(k, UTC), o, h, l, c, int(v)))
        store.append(Bar5s("AAA", datetime.fromtimestamp(k + 5, UTC), c, c, c, c, 0))
    desk.stream.store = store
    clock.now = datetime.fromtimestamp(t_close - 8, UTC)
    desk.tick()                                    # drains the history: too old to be a live signal
    assert conn.execute("SELECT COUNT(*) FROM green_run_signals").fetchone()[0] == 0
    k, o, h, l, c, v = tens[-1]
    clock.now = datetime.fromtimestamp(t_close + 2, UTC)
    ib.push_bar("AAA", datetime.fromtimestamp(k, UTC), o, h, l, c, int(v))
    ib.push_bar("AAA", datetime.fromtimestamp(k + 5, UTC), c, c, c, c, 0)
    desk.tick()
    rows = L.green_run_rows(conn)
    assert len(rows) == 1, rows
    r = rows[0]
    assert (r["symbol"], r["status"], r["entry"], r["stop"]) == ("AAA", "SIGNAL", want.entry, want.stop)
    assert r["ts_et"] == L._et(t_close) and r["spread_source"] == "live" and r["spread"] == 0.02
    assert r["lag_s"] == 2.0 and r["data_status"] == "live"
    assert [x["name"] for x in r["reasons"]] == [c.name for c in want.checks]
    # the same candle again (a re-drain, a restart): no second row, no change
    desk._green_pending = [b for b in store.candles_10s("AAA") if int(b.ts.timestamp()) == k]
    assert desk._green_run() == 0
    assert len(L.green_run_rows(conn)) == 1
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == decisions_before, \
        "a green run is never a decision"


def test_a_green_run_failure_never_reaches_the_desk(monkeypatch, tmp_path):
    from momentum_platform.dashboard import ibkr_desk as D
    from momentum_platform.datasources.ibkr_stream import Bar5s, BarStore  # noqa: F401
    from test_ibkr_desk import make_desk
    desk, ib, clock = make_desk()
    conn = L.connect(tmp_path / "j.sqlite")
    monkeypatch.setattr(D, "_journal", lambda: conn)
    desk._bootstrap()
    monkeypatch.setattr(L, "record_green_run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk")))
    monkeypatch.setattr(D.IbkrDesk, "_green_eval", lambda *a, **k: (_ev(sym="AAA"), 1.0))
    said = []
    desk.log = said.append
    for i in range(4):
        clock.now = desk.clock() + timedelta(seconds=5)
        ib.push_bar("AAA", clock.now - timedelta(seconds=5), 4.4, 4.45, 4.39, 4.41, 500)
        desk.tick()                                   # must not raise
    assert sum("green-run log failed" in s for s in said) == 1


# ------------------------------------------------------------ 6. the score
T9 = _epoch("2026-09-15", "09:40")


def _b(t, o, h, l, c):
    return (t, o, h, l, c, 100)


def test_score_fills_at_the_entry_then_trails_out():
    entry, stop = 5.00, 4.80                                     # 1 R = 0.20
    path = [_b(T9, 4.95, 5.02, 4.94, 5.01),                      # crosses from below: filled at 5.00
            _b(T9 + 10, 5.01, 5.30, 5.00, 5.28),                 # high 5.30 -> level 5.10
            _b(T9 + 20, 5.28, 5.40, 5.20, 5.35),                 # 5.20 > 5.10; level -> 5.20
            _b(T9 + 30, 5.30, 5.31, 5.15, 5.16)]                 # low 5.15 <= 5.20: out at 5.20
    s = G.score(entry, stop, T9, path)
    assert s["filled"] and s["fill"] == 5.00 and s["fill_kind"] == "entry"
    assert s["how"] == "trail" and s["exit"] == 5.20 and s["r"] == pytest.approx(1.0)


def test_score_open_over_the_cap_waits_for_the_return_and_misses_after_20s():
    entry, stop = 5.00, 4.80
    cap = G.cap_of(entry)                                        # 5.015
    gone = [_b(T9, 5.10, 5.20, 5.05, 5.15), _b(T9 + 10, 5.15, 5.25, 5.10, 5.20),
            _b(T9 + 20, 5.20, 5.20, 4.90, 4.95)]                 # back under the cap only after 20 s
    assert G.score(entry, stop, T9, gone)["how"] == "not filled"
    back = [_b(T9, 5.10, 5.20, 5.01, 5.15), _b(T9 + 10, 5.15, 5.16, 4.70, 4.75)]
    s = G.score(entry, stop, T9, back)
    assert s["fill"] == cap and s["fill_kind"] == "cap_return"
    # the close 5.15 is known to follow a cap-return fill: the trail rises to 5.15 - 1 R = 4.95
    assert s["how"] == "trail" and s["exit"] == 4.95 and s["r"] == pytest.approx((4.95 - cap) / 0.20)


def test_score_gap_through_the_stop_exits_at_the_open_and_flat_at_1130():
    entry, stop = 5.00, 4.80
    gap = [_b(T9, 4.99, 5.00, 4.99, 5.00), _b(T9 + 10, 4.70, 4.75, 4.60, 4.65)]   # high = entry: level stays
    s = G.score(entry, stop, T9, gap)
    assert s["exit"] == 4.70 and s["how"] == "stop"
    flat = _epoch("2026-09-15", "11:30")
    late = [_b(flat - 20, 4.99, 5.01, 4.99, 5.01), _b(flat - 10, 5.01, 5.05, 5.0, 5.04),
            _b(flat, 5.04, 5.06, 5.03, 5.05)]
    s = G.score(entry, stop, flat - 20, late, flat_t=flat)
    assert s["how"] == "flat" and s["exit"] == 5.04


def test_score_walks_a_minute_without_ten_second_candles_on_its_minute_bar():
    entry, stop = 5.00, 4.80
    t = _epoch("2026-09-15", "09:40")
    tens = [_b(t, 4.99, 5.00, 4.98, 5.00)]
    minute = [(t + 60, 5.0, 5.05, 4.70, 4.75, 1000)]             # no 10-s candle in 09:41
    s = G.score(entry, stop, t, tens, minute)
    assert s["minutes_from_1m"] == 1 and s["how"] == "stop" and s["exit"] == 4.80
    assert G.score(entry, stop, t, [], minute)["how"] == "no 10-s tape in the entry window"


# ------------------------------------------------------------ 7. watch and the close-out score
def _iso(t):
    return datetime.fromtimestamp(t, UTC).isoformat().replace("+00:00", "Z")


def test_watch_prints_green_run_rows_once_and_survives_an_old_ledger(tmp_path):
    import watch as W
    db = tmp_path / "j.sqlite"
    c = L.connect(db)
    t = _epoch("2026-09-15", "09:41")
    L.record_green_run(c, _ev(sym="GRN", t_arm=t, entry=5.01, stop=4.80))
    ref = _ev(sym="RFS", t_arm=t + 30, status="REFUSED", pause_id=t, entry=6.01, stop=5.95)
    ref.checks = [G.Check("stop >= 2% (A13)", False, 1.0, "stop 1.00% of the entry (floor 2%)")]
    L.record_green_run(c, ref)
    c.commit()
    w = W.Watcher(W.connect_ro(db), "2026-09-15")
    lines = [line for _, line in w.poll()]
    text = "\n".join(lines)
    assert "GREEN-RUN" in text and "5.01/4.80" in text and "SHADOW: no order" in text
    assert "GR REFUSED" in text and "stop >= 2% (A13): stop 1.00%" in text
    assert w.poll() == [], "printed once"
    up = _ev(sym="RFS", t_arm=t + 40, pause_id=t, entry=6.01, stop=5.70)
    L.record_green_run(c, up); c.commit()
    again = [line for _, line in w.poll()]
    assert len(again) == 1 and "GREEN-RUN" in again[0] and "[2 closes]" in again[0]
    assert "2 green-run signal(s) logged, never traded" in w.summary()
    c.execute("DROP TABLE green_run_signals"); c.commit()
    assert W.Watcher(W.connect_ro(db), "2026-09-15").poll() == [], "a ledger from before the log"


def test_exercise_green_runs_scores_each_pause_on_the_ledger_tape(tmp_path):
    import subprocess
    db = tmp_path / "j.sqlite"
    c = L.connect(db)
    t = _epoch("2026-09-15", "09:41")
    L.record_green_run(c, _ev(sym="GRN", t_arm=t, pause_id=t - 30, entry=5.01, stop=4.80))
    L.record_green_run(c, _ev(sym="GRN", t_arm=t + 10, pause_id=t - 20, entry=5.30, stop=5.00))   # while in the trade
    L.record_green_run(c, _ev(sym="NOF", t_arm=t, pause_id=t - 30, entry=8.01, stop=7.70))        # never reached
    ref = _ev(sym="RFS", t_arm=t, status="REFUSED", pause_id=t - 30)
    ref.checks = [G.Check("stop >= 4x spread (A6)", False, 2.0, "too tight")]
    L.record_green_run(c, ref)
    L.record_bars_10s(c, [("GRN", _iso(t), 4.99, 5.02, 4.98, 5.01, 900),         # fills at 5.01; level 4.81
                          ("GRN", _iso(t + 10), 5.01, 5.40, 5.00, 5.38, 900),    # level 5.19
                          ("GRN", _iso(t + 20), 5.38, 5.39, 5.10, 5.12, 900),    # out at 5.19
                          ("NOF", _iso(t), 7.90, 7.95, 7.88, 7.90, 100),
                          ("NOF", _iso(t + 10), 7.90, 7.99, 7.85, 7.95, 100)])
    c.commit()
    out = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "green-runs", "--date", "2026-09-15"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    s = out.stdout
    assert "GREEN-RUN SHADOW · 2026-09-15" in s and "3 SIGNAL · 1 REFUSED" in s and "NEVER traded" in s
    assert "5.010   5.190  trail" in s and "+0.86" in s
    assert "position open" in s and "not filled" in s
    assert "TOTAL" in s and "1 filled · gross +0.86 R" in s
    assert "REFUSED by rule: stop >= 4x spread (A6) 1" in s
    assert "APPROXIMATE" in s and "green_run_output.txt" in s
    none = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "green-runs", "--date", "2031-01-01"],
                          cwd=ROOT, capture_output=True, text=True)
    assert none.returncode == 1 and "no green-run signals on 2031-01-01" in none.stdout
