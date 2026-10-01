"""scripts/indicator_audit.py: the independent recompute agrees with the
desk's chart_gates, the seeding variants are what they claim to be, and the
ledger and Alpaca-compare modes run on a ledger built from the fixture."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import indicator_audit as A  # noqa: E402
from journal import bars as B  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform import indicators as I  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"
UTC = timezone.utc


def fixture_rows() -> dict:
    return {s: [(datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(A.ET), o, h, l, c, v)
                for t, o, h, l, c, v in rows] for s, rows in B.from_fixture(FIXTURE).items()}


def test_first_seed_is_the_desk_ema_and_sma_seed_is_tradingview():
    x = list(np.random.default_rng(1).normal(10, 0.3, 60))
    assert np.allclose(A.ema_first(x, 9), I.ema(x, 9), rtol=0, atol=1e-12)
    s = A.ema_sma([1, 2, 3, 4, 5], 3)            # seed = mean(1,2,3) = 2 at index 2
    assert np.isnan(s[:2]).all() and s[2] == 2.0
    assert s[3] == 0.5 * 4 + 0.5 * 2.0 and s[4] == 0.5 * 5 + 0.5 * s[3]


def test_macd_warm_up_and_semantics():
    closes = [10 + 0.01 * k for k in range(40)]
    f = A.frame([(None, c, c, c, c, 100.0) for c in closes])
    assert A.gates_at(f, 33, "first")["macd"] is None and A.gates_at(f, 34, "first")["macd"] is not None
    assert A.gates_at(f, 32, "sma")["macd"] is None and A.gates_at(f, 33, "sma")["macd"] is not None
    line, sig, hist = I.macd(closes)
    assert abs(f["line_first"][-1] - line[-1]) < 1e-12 and abs(f["sig_first"][-1] - sig[-1]) < 1e-12


def test_every_fixture_plan_agrees_with_chart_gates():
    plans = []
    for sym, rows in fixture_rows().items():
        if len(rows) >= 40:
            plans += A.audit_symbol_day(sym, rows, rows[0][1])
    assert plans, "the fixture arms plans between 08:00 and 10:30"
    for p in plans:
        assert p["desk"] == p["first"], p
        assert p["rec"]["t"] == p["t"]
    text = "\n".join(A.report(plans, {"sessions": 1, "seed": 0, "missing": 0, "symdays": 1}))
    assert "(a1)" in text and "(b)" in text and "(e)" in text


def _fixture_ledger():
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    return c


def test_ledger_mode_agrees_on_the_fixture_and_names_a_tampered_gate():
    c = _fixture_ledger()
    res = A.audit_ledger(c)
    rows = [r for r in res["rows"] if r["recorded"]["vwap"] != "NA"]
    assert rows and all(r["recorded"][g] == r["final"][g] for r in rows for g in A.GATES)
    assert all(int(bool(r["volume_ok"])) == r["volume_ok_replay"] for r in res["rows"])
    # Flip one recorded state: the audit must list it as a disagreement.
    d = c.execute("SELECT decision_id, gates_json FROM decisions WHERE gates_json LIKE '%\"vwap\"%'").fetchone()
    gates = json.loads(d["gates_json"])
    for g in gates:
        if g["id"] == "vwap":
            g["state"] = "FAIL" if g["state"] == "PASS" else "PASS"
    c.execute("UPDATE decisions SET gates_json=? WHERE decision_id=?", (json.dumps(gates), d["decision_id"]))
    text = "\n".join(A.print_ledger(A.audit_ledger(c)))
    assert "disagreements (1;" in text and " vwap " in text


def test_ledger_mode_from_the_command_line(tmp_path, capsys):
    path = tmp_path / "journal.sqlite"
    c = L.connect(path)
    build_session(FIXTURE, journal=c)
    c.close()
    assert A.main(["--ledger", str(path)]) == 0
    out = capsys.readouterr().out
    assert "LEDGER AUDIT" in out and "volume_ok agree 5/5" in out


def test_point_in_time_minute_uses_only_closed_ten_second_candles():
    m = datetime(2026, 9, 1, 13, 40, tzinfo=UTC)
    tens = [(m + timedelta(seconds=10 * k), 5.0 + k, 5.1 + k, 4.9 + k, 5.05 + k, 100.0) for k in range(6)]
    fm = A.forming_minute(tens, m, m + timedelta(seconds=31))       # candles ending :10 :20 :30
    assert fm[1] == 5.0 and fm[2] == 7.1 and fm[4] == 7.05 and fm[5] == 300.0
    assert A.forming_minute(tens, m, m + timedelta(seconds=9)) is None


class FakeAlpaca:
    feed = "sip"; data_base = "https://data.example"; key_id = "x"
    def __init__(self, scale=1.0):
        self.scale = scale
        self.bars = B.from_fixture(FIXTURE)
    def _get(self, base, path, params):
        assert path == "/v2/stocks/bars" and params["feed"] == "sip"
        return {"bars": {s: [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4], "v": r[5] * self.scale}
                             for r in self.bars.get(s, [])] for s in params["symbols"].split(",")},
                "next_page_token": None}


def test_alpaca_compare_reads_one_on_the_same_tape_and_100_on_lots(tmp_path):
    c = _fixture_ledger()
    cells = A.alpaca_compare(c, FakeAlpaca(), tmp_path / "a")
    for win in ("pre-market", "regular"):
        assert np.median(cells[(win, "minute-history")]["ratio"]) == 1.0
    lots = A.alpaca_compare(c, FakeAlpaca(scale=0.01), tmp_path / "b")     # a feed in lots of 100
    assert abs(np.median(lots[("regular", "minute-history")]["ratio"]) - 100.0) < 1e-9
    assert "ALPACA COMPARE" in "\n".join(A.print_compare(cells))


def test_cache_mode_end_to_end(tmp_path, monkeypatch, capsys):
    day = "2026-09-01"
    raw = {s: [list(r) for r in rows] for s, rows in B.from_fixture(FIXTURE).items()}
    (tmp_path / f"{day}.json").write_text(json.dumps(raw))
    monkeypatch.setattr(A.H, "load_universe", lambda since, until: {day: {s: None for s in raw}})
    assert A.main(["--cache", str(tmp_path), "--sample", "0"]) == 0
    out = capsys.readouterr().out
    assert "1 sessions sampled" in out and "agree" in out
