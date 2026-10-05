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


def test_a_name_whose_float_is_over_the_cap_is_kept_off_before_joining(tmp_path, monkeypatch):
    """2026-10-05: QTEX (59M, known) was kept out while ALEC (82M) joined because
    its float was only looked up after it joined. The lookup now comes first."""
    monkeypatch.setenv("FLOAT_OVERRIDES", str(tmp_path / "f.json"))

    class _Stub:
        _add_now = D.IbkrDesk._add_now
        session_day = lambda self: "2026-10-05"
        no_live_data, sec, symbols = set(), True, []
        hub = types.SimpleNamespace(publish=lambda *a: None)

        def __init__(self):
            self.logs, self.subscribed = [], []

        def _finviz_float(self, sym):
            D._remember_float_override(sym, "2026-10-05", {"ALEC": 82e6, "OK": 5e6}[sym], "finviz on join")

        def _subscribe(self, syms):
            self.subscribed += syms
            return syms

        def refresh_session(self):
            pass

        def log(self, m):
            self.logs.append(m)

    d = _Stub()
    assert d._add_now(["ALEC", "OK"]) == ["OK"]
    assert any("ALEC 82M" in m for m in d.logs)


def test_finviz_shares_outstanding_stands_in_when_float_is_missing(monkeypatch, tmp_path):
    """SAIQ 2026-10-05: finviz float blank, shares outstanding 4.49M -> the
    float pillar can pass on the upper bound instead of reading UNKNOWN."""
    monkeypatch.setenv("FLOAT_OVERRIDES", str(tmp_path / "f.json"))
    monkeypatch.setattr(D, "reference_record", lambda sym, bars, **kw: {"float_shares": None, "float_quality": "unknown"})

    class _Stub:
        _set_reference = D.IbkrDesk._set_reference
        session_day = lambda self: "2026-10-05"
        stream = types.SimpleNamespace(_tickers={})
        clock = None
        profile_days = 0

        def __init__(self):
            self._float_inputs, self._reference, self._reference_day, self._profiles = {}, {}, {}, {}
            self._facts = {"SAIQ": {"day": "2026-10-05", "finviz_shares_out": 4.49e6}}

    d = _Stub()
    d._set_reference("SAIQ", types.SimpleNamespace(), [])
    r = d._reference["SAIQ"]
    assert r["float_shares"] == 4.49e6 and r["float_quality"] == "shares_outstanding_proxy"
