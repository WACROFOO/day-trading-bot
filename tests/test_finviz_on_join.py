"""A name that joins the desk after the gap scan gets finviz's float (2026-10-01, NXL)."""
import json
import sys
import types

from momentum_platform.dashboard import ibkr_desk as D


def test_override_roundtrip_keeps_per_symbol_source(tmp_path, monkeypatch):
    f = tmp_path / "float_overrides.json"
    f.write_text(json.dumps({"date": "2026-10-01", "source": "finviz via premarket_stars.py",
                             "floats": {"AAA": 5e6}}))
    monkeypatch.setenv("FLOAT_OVERRIDES", str(f))
    D._remember_float_override("nxl", "2026-10-01", 650000.0, "finviz on join")
    assert D._float_override("NXL", "2026-10-01") == {"float": 650000.0, "source": "finviz on join"}
    assert D._float_override("AAA", "2026-10-01")["source"] == "finviz via premarket_stars.py"


def test_yesterdays_file_is_replaced(tmp_path, monkeypatch):
    f = tmp_path / "float_overrides.json"
    f.write_text(json.dumps({"date": "2026-09-30", "floats": {"AAA": 5e6}}))
    monkeypatch.setenv("FLOAT_OVERRIDES", str(f))
    D._remember_float_override("NXL", "2026-10-01", 650000.0, "finviz on join")
    doc = json.loads(f.read_text())
    assert doc["date"] == "2026-10-01" and doc["floats"] == {"NXL": 650000.0}


class _Desk:
    session_day = lambda self: "2026-10-01"
    _finviz_float = D.IbkrDesk._finviz_float

    def __init__(self):
        self.logs = []

    def log(self, msg):
        self.logs.append(msg)


def test_lookup_writes_verified_float(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOAT_OVERRIDES", str(tmp_path / "f.json"))
    calls = []
    fake = types.SimpleNamespace(finviz=lambda s: calls.append(s) or {"float": 650000.0})
    monkeypatch.setitem(sys.modules, "premarket_stars", fake)
    desk = _Desk()
    desk._finviz_float("NXL")
    desk._finviz_float("NXL")                    # already known: no second request
    assert calls == ["NXL"]
    assert D._float_override("NXL", "2026-10-01")["float"] == 650000.0


def test_lookup_miss_or_failure_leaves_no_override(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOAT_OVERRIDES", str(tmp_path / "f.json"))
    monkeypatch.setitem(sys.modules, "premarket_stars", types.SimpleNamespace(finviz=lambda s: {"fv_ok": False}))
    _Desk()._finviz_float("ZZZ")
    assert D._float_override("ZZZ", "2026-10-01") is None

    def boom(s):
        raise RuntimeError("offline")
    monkeypatch.setitem(sys.modules, "premarket_stars", types.SimpleNamespace(finviz=boom))
    desk = _Desk()
    desk._finviz_float("ZZZ")
    assert D._float_override("ZZZ", "2026-10-01") is None and "failed" in desk.logs[0]
