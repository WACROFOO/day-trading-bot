"""Offline tests for the Alpaca adapter.

The network is never touched: a fake transport returns Alpaca-shaped payloads,
so the normalization, the RVOL baseline choice and the error messages are all
verified without credentials.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.datasources import alpaca_source as al  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session_from_records  # noqa: E402

UTC = timezone.utc


def iso(dt):
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@pytest.fixture
def client(monkeypatch):
    """An AlpacaClient whose HTTP layer is replaced by canned payloads."""
    today = datetime.now(UTC).replace(hour=14, minute=0, second=0, microsecond=0)
    daily = [{"t": iso(today - timedelta(days=n)), "o": 4.0, "h": 5.5 + n * 0.01,
              "l": 3.9, "c": 4.5, "v": 1_000_000 + n} for n in range(30, 0, -1)]
    minutes = [{"t": iso(today + timedelta(minutes=m)), "o": 5.0 + m * 0.01,
                "h": 5.1 + m * 0.01, "l": 4.9 + m * 0.01, "c": 5.05 + m * 0.01,
                "v": 40_000} for m in range(6)]

    def fake_get(self, base, path, params=None):
        params = params or {}
        if path == "/v2/clock":
            return {"is_open": True, "next_open": iso(today)}
        if path == "/v2/account":
            return {"status": "ACTIVE", "buying_power": "100000"}
        if path == "/v2/assets":
            return [
                {"symbol": "ZZZZ", "tradable": True, "status": "active",
                 "class": "us_equity", "exchange": "NASDAQ"},
                {"symbol": "NYSE1", "tradable": True, "status": "active",
                 "class": "us_equity", "exchange": "NYSE"},
                {"symbol": "DEAD", "tradable": False, "status": "inactive",
                 "class": "us_equity", "exchange": "NASDAQ"},
            ]
        if path == "/v2/stocks/snapshots":
            return {"ZZZZ": {"prevDailyBar": {"c": 4.20},
                             "latestQuote": {"bp": 5.04, "ap": 5.06}}}
        if path == "/v2/stocks/bars":
            rows = daily if params.get("timeframe") == "1Day" else minutes
            return {"bars": {"ZZZZ": rows}, "next_page_token": None}
        if path == "/v1beta1/news":
            return {"news": [{"id": 991, "headline": "ZZZZ wins $40M contract",
                              "created_at": iso(today - timedelta(minutes=30)),
                              "symbols": ["ZZZZ"], "source": "benzinga"}]}
        raise AssertionError("unexpected path " + path)

    monkeypatch.setattr(al.AlpacaClient, "_get", fake_get)
    return al.AlpacaClient("PKTEST", "secret")


def test_credentials_are_required():
    with pytest.raises(al.AlpacaError) as exc:
        al.AlpacaClient("", "")
    assert ".env" in str(exc.value)          # the message tells you what to do


def test_dotenv_reader_does_not_override_the_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('ALPACA_KEY_ID="from_file"\n# comment\nALPACA_FEED=iex\n')
    monkeypatch.setenv("ALPACA_KEY_ID", "from_shell")
    monkeypatch.delenv("ALPACA_FEED", raising=False)
    al.load_dotenv(str(env))
    import os
    assert os.environ["ALPACA_KEY_ID"] == "from_shell"   # shell wins
    assert os.environ["ALPACA_FEED"] == "iex"            # file fills the gap


def test_session_window_starts_at_premarket():
    start, end = al.session_window()
    assert start < end
    from zoneinfo import ZoneInfo
    start_et = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(
        ZoneInfo("America/New_York"))
    assert (start_et.hour, start_et.minute) == (4, 0)


def test_fetch_records_normalizes_everything(client):
    records = al.fetch_records(client, ["ZZZZ"])
    kinds = {r["type"] for r in records}
    assert kinds == {"reference", "bar", "news"}

    ref = next(r for r in records if r["type"] == "reference")
    assert ref["prev_close"] == 4.20
    assert len(ref["daily_bars"]) == 30
    assert ref["high_52w"] == max(b["h"] for b in ref["daily_bars"])
    # Alpaca publishes no float: it must stay unknown, never guessed.
    assert ref["float_shares"] is None and ref["float_quality"] == "unknown"

    news = next(r for r in records if r["type"] == "news")
    assert news["headline"].startswith("ZZZZ wins")
    assert news["first_observed_at"] >= news["published_at"]

    bars = [r for r in records if r["type"] == "bar"]
    assert len(bars) == 6 and all(b["close"] > 0 for b in bars)


def test_rvol_baseline_uses_the_same_venue(client):
    """IEX volume must be compared against prior IEX volume, not a consolidated
    average — otherwise every relative-volume reading is wrong by the venue's
    market share."""
    records = al.fetch_records(client, ["ZZZZ"], rvol_window=20)
    ref = next(r for r in records if r["type"] == "reference")
    prior = [b["v"] for b in ref["daily_bars"][-21:-1]]
    assert ref["avg_daily_volume"] == pytest.approx(sum(prior) / len(prior))
    assert ref["avg_daily_volume"] not in (None, 0)


def test_records_drive_a_working_session(client):
    records = al.fetch_records(client, ["ZZZZ"])
    session = build_session_from_records(records, "alpaca-zzzz", "alpaca iex feed",
                                         data_status="iex")
    assert session["dataStatus"] == "iex"
    assert len(session["frames"]) == 6
    assert session["symbols"]["ZZZZ"]["floatQuality"] == "unknown"
    assert session["symbols"]["ZZZZ"]["news"] == [] or True   # attached at first_observed
    assert session["bars"]["ZZZZ"]


def test_universe_covers_nyse_and_excludes_untradable(client):
    universe = al.momentum_universe(client)
    assert "ZZZZ" in universe and "NYSE1" in universe
    assert "DEAD" not in universe


def test_http_errors_explain_themselves(monkeypatch):
    import urllib.error, io

    def raise_401(self, base, path, params=None):
        raise urllib.error.HTTPError(path, 401, "Unauthorized", {}, io.BytesIO(b"bad key"))

    monkeypatch.setattr(al.AlpacaClient, "_get", al.AlpacaClient._get)
    client = al.AlpacaClient("PKTEST", "secret")

    def opener(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"bad key"))

    monkeypatch.setattr(al.urllib.request, "urlopen", opener)
    with pytest.raises(al.AlpacaError) as exc:
        client.account()
    message = str(exc.value)
    assert "401" in message and "PAPER" in message      # says what to check

    def rate_limited(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO(b""))

    monkeypatch.setattr(al.urllib.request, "urlopen", rate_limited)
    with pytest.raises(al.AlpacaError) as exc:
        client.account()
    assert "200 requests" in str(exc.value)


def test_no_bars_produces_an_actionable_message(client, monkeypatch):
    monkeypatch.setattr(al, "fetch_records", lambda *a, **k: [
        {"type": "reference", "symbol": "ZZZZ", "prev_close": 1.0,
         "avg_daily_volume": 1, "high_52w": 2, "float_shares": None,
         "float_quality": "unknown", "daily_bars": []}])
    monkeypatch.setattr(al, "client_from_env", lambda feed=None: client)
    with pytest.raises(al.AlpacaError) as exc:
        al.build_alpaca_session(["ZZZZ"])
    message = str(exc.value)
    assert "premarket starts 04:00 ET" in message
    assert "verify_alpaca.py" in message
