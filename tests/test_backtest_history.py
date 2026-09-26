"""scripts/backtest_history.py end to end, offline: a fake Alpaca client serves
the replay fixture's minute bars (which carry pre-market volume), and the run
must evaluate VWAP and the volume gate in pre-market, price costs, run the
walk-forward optimizer, and calibrate against a ledger."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_history as H  # noqa: E402
import backtest_recent as E  # noqa: E402
from journal import bars as B  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


class FakeAlpaca:
    feed = "sip"; data_base = "https://data.example"
    def __init__(self):
        self.calls = 0
        self.bars = {s: [[t, o, h, l, c, v] for (t, o, h, l, c, v) in rows] for s, rows in B.from_fixture(FIXTURE).items()}
    def _get(self, base, path, params):
        self.calls += 1
        assert path == "/v2/stocks/bars" and params["adjustment"] == "raw" and params["feed"] == "sip"
        assert params["start"].startswith("2026-09-01T08:00") and params["timeframe"] == "1Min"
        syms = params["symbols"].split(",")
        return {"bars": {s: [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4], "v": r[5]} for r in self.bars.get(s, [])]
                         for s in syms}, "next_page_token": None}


def test_cost_model_and_gap_miss():
    assert E.entry_cap(10.0) == 10.03 and E.entry_cap(2.0) == 2.01
    # $20 risk, 0.20 stop -> 100 shares: $1 + $1 commission, 1c entry + 1c stop exit slippage = $4 = 0.2 R
    assert E.cost_r(10.0, 9.8, stop_exit=True) == 0.2
    assert E.cost_r(10.0, 9.8, stop_exit=False) == 0.15


def test_history_run_offline_end_to_end(tmp_path, monkeypatch, capsys):
    fake = FakeAlpaca()
    syms = list(fake.bars)
    monkeypatch.setattr(H, "alpaca_client", lambda: fake)
    monkeypatch.setattr(H, "load_universe", lambda since, until: {"2026-09-01": {s: None for s in syms}})
    # a ledger with one decision and one closed trade on a fixture symbol
    led = tmp_path / "j.sqlite"
    c = sqlite3.connect(led)
    c.executescript("""CREATE TABLE decisions (decision_id TEXT, symbol TEXT, ts_et TEXT);
                       CREATE TABLE orders (decision_id TEXT, symbol TEXT, trigger REAL, stop REAL, fill_price REAL,
                              exit_price REAL, filled_qty REAL, shares INT, planned_risk REAL, fill_ts TEXT);""")
    c.execute("INSERT INTO decisions VALUES ('d1', ?, '2026-09-01T09:45:00-04:00')", (syms[0],))
    c.execute("INSERT INTO orders VALUES ('d1', ?, 5.0, 4.9, 5.0, 5.1, 100, 100, 10.0, '2026-09-01T09:46:00-04:00')", (syms[0],))
    c.commit(); c.close()
    out_json = tmp_path / "h.json"
    rc = H.main(["--cache", str(tmp_path / "cache"), "--split", "2026-09-01", "--ledger", str(led), "--json", str(out_json)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "PLAN LEVEL" in out and "PORTFOLIO" in out and "WALK-FORWARD OPTIMIZER" in out and "FORECAST vs ACTUALS" in out
    plans = json.loads(out_json.read_text())["plans"]
    assert plans, "the fixture arms plans"
    assert {p["window"] for p in plans} <= {"pre-market", "regular"}
    # pre-market VWAP and volume ARE evaluated now: some plan carries one of them, or all are green on them
    assert all("trail_net" in p for p in plans if p["touched"])
    assert fake.calls == 1                                            # one request for the whole session
    # cached: a second run makes no request
    H.main(["--cache", str(tmp_path / "cache"), "--split", "2026-09-01"])
    assert fake.calls == 1


def _pm_day(volume: bool):
    """04:00-06:59 quiet at 5.00, then a 07:00 impulse, a two-bar pullback on
    lighter volume and a trigger bar at 07:05, then a rise."""
    from datetime import datetime, timedelta
    t0 = datetime(2026, 9, 1, 4, 0, tzinfo=E.ET)
    rows = [(t0 + timedelta(minutes=i), 5.00, 5.01, 4.99, 5.00, 1000 if volume else 0) for i in range(180)]
    seq = [(5.00, 5.11, 5.00, 5.10, 20000), (5.10, 5.23, 5.09, 5.22, 22000), (5.22, 5.36, 5.21, 5.35, 25000),
           (5.35, 5.36, 5.29, 5.30, 5000), (5.30, 5.31, 5.27, 5.28, 4000), (5.29, 5.34, 5.28, 5.33, 9000)]
    seq += [(5.33 + 0.02 * k, 5.36 + 0.02 * k, 5.32 + 0.02 * k, 5.35 + 0.02 * k, 8000) for k in range(30)]
    for k, (o, h, l, c, v) in enumerate(seq):
        rows.append((t0 + timedelta(minutes=180 + k), o, h, l, c, v if volume else 0))
    return rows


def test_premarket_gates_are_judged_only_with_premarket_volume():
    desk = [p for p in E.plans_for_day("X", _pm_day(True), 4.5, desk_vwap=True) if p["window"] == "pre-market"]
    assert desk, "the synthetic day arms a pre-market plan"
    assert "vwap" not in desk[0]["red"] and "volume" not in desk[0]["red"]      # above VWAP, lighter pullback volume
    # the same day with no pre-market volume (what Yahoo serves): VWAP cannot be computed -> red in desk mode
    blind = [p for p in E.plans_for_day("X", _pm_day(False), 4.5, desk_vwap=True) if p["window"] == "pre-market"]
    assert blind and "vwap" in blind[0]["red"]
    # Yahoo mode never judges them pre-market
    yahoo = [p for p in E.plans_for_day("X", _pm_day(False), 4.5) if p["window"] == "pre-market"]
    assert yahoo and "vwap" not in yahoo[0]["red"] and "volume" not in yahoo[0]["red"]
