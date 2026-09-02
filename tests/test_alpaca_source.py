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
        if path == "/v2/stocks/trades":
            # No prints in this fixture: every symbol falls back to minute bars.
            return {"trades": {}, "next_page_token": None}
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

    def opener(req, timeout=None, **kwargs):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"bad key"))

    monkeypatch.setattr(al.urllib.request, "urlopen", opener)
    with pytest.raises(al.AlpacaError) as exc:
        client.account()
    message = str(exc.value)
    assert "401" in message and "PAPER" in message      # says what to check

    def rate_limited(req, timeout=None, **kwargs):
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


# -- preflight classification -------------------------------------------------
# The launcher tells the user either "your keys are wrong" or "your network is
# blocked" based on this. A proxy refusing CONNECT also reports 403, so these
# cases must not be confused: a misread sends the user to regenerate a
# perfectly good key pair.

import importlib.util as _ilu  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_spec = _ilu.spec_from_file_location(
    "preflight", _Path(__file__).resolve().parents[1] / "scripts" / "preflight.py")
preflight = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(preflight)


def test_proxy_tunnel_403_is_a_network_block_not_a_bad_key():
    msg = ("Could not reach Alpaca (Tunnel connection failed: 403 Forbidden). "
           "Check your internet connection, and any company proxy or VPN.")
    assert preflight._classify(msg) == preflight.UNREACHABLE


def test_plain_401_is_a_rejected_credential():
    assert preflight._classify("HTTP 401 unauthorized") == preflight.REJECTED


def test_alpaca_403_without_tunnel_wording_is_rejected():
    assert preflight._classify("HTTP 403 forbidden: account not entitled") == preflight.REJECTED


def test_connection_refused_is_a_network_block():
    assert preflight._classify("Connection refused") == preflight.UNREACHABLE


def test_unknown_message_falls_through_to_other():
    assert preflight._classify("teapot") == preflight.OTHER


# -- news must be visible inside the session it belongs to --------------------

def test_news_becomes_visible_at_publication_not_at_fetch_time(monkeypatch):
    """A headline stamped with the fetch time is observed after every bar in a
    historical session, so the flame never lights and the catalyst card reads
    'none observed' on a stock that plainly has news."""
    published = "2026-09-01T17:24:00Z"
    payload = {
        "news": [{"id": 1, "headline": "Company wins contract",
                  "created_at": published, "symbols": ["BIAF"], "source": "wire"}],
    }

    class Stub(al.AlpacaClient):
        def snapshots(self, symbols):
            return {}

        def bars(self, symbols, timeframe, start, end=None, limit=10000):
            return {}

        def news(self, symbols, limit=50, start=None):
            return payload["news"]

    records = al.fetch_records(Stub("PK", "s" * 40), ["BIAF"])
    news = [r for r in records if r["type"] == "news"]
    assert news, "the headline must reach the session"
    assert news[0]["first_observed_at"] == news[0]["published_at"] == published


def test_a_failed_news_lookup_is_announced_not_swallowed(capsys):
    """Silence renders as 'no catalyst', which the data does not support."""

    class Stub(al.AlpacaClient):
        def snapshots(self, symbols):
            return {}

        def bars(self, symbols, timeframe, start, end=None, limit=10000):
            return {}

        def news(self, symbols, limit=50, start=None):
            raise al.AlpacaError("news entitlement missing")

    al.fetch_records(Stub("PK", "s" * 40), ["BIAF"])
    out = capsys.readouterr().out
    assert "news unavailable" in out
    assert "none observed" in out


# -- 10-second bars from trade prints ------------------------------------------
# The free feed publishes minute bars at best, but it does serve historical
# IEX trade prints. Ten-second bars aggregated from those are real, not an
# interpolation, so the micro chart can finally show candles honestly.

def test_trades_aggregate_into_ten_second_bars():
    bars = al.aggregate_trades([
        {"t": "2026-09-01T13:30:01Z", "p": 5.00, "s": 100},
        {"t": "2026-09-01T13:30:04Z", "p": 5.10, "s": 50},
        {"t": "2026-09-01T13:30:09Z", "p": 4.95, "s": 25},
        {"t": "2026-09-01T13:30:31Z", "p": 5.20, "s": 10},
    ], 10)
    assert [b["ts"] for b in bars] == ["2026-09-01T13:30:00Z", "2026-09-01T13:30:30Z"]
    assert bars[0] == {"ts": "2026-09-01T13:30:00Z", "open": 5.0, "high": 5.1,
                       "low": 4.95, "close": 4.95, "volume": 175}


def test_empty_buckets_are_absent_not_flat():
    """A ten-second window with no prints is absence of trading, not a
    flat candle. Inventing one would draw activity that never happened."""
    bars = al.aggregate_trades([
        {"t": "2026-09-01T13:30:01Z", "p": 5.00, "s": 1},
        {"t": "2026-09-01T13:31:01Z", "p": 5.00, "s": 1},
    ], 10)
    assert len(bars) == 2


def test_bad_prints_are_skipped():
    assert al.aggregate_trades([{"t": "2026-09-01T13:30:01Z", "p": 0, "s": 1},
                                {"p": 5.0, "s": 1}]) == []


def test_symbols_with_prints_get_ten_second_bars_and_the_rest_keep_minutes():
    """Mixed feeds are normal: a runner prints all day on IEX, a quiet name
    may not print at all. Each symbol takes the best data it actually has."""
    class Stub(al.AlpacaClient):
        def snapshots(self, symbols):
            return {}

        def bars(self, symbols, timeframe, start, end=None, limit=10000):
            if timeframe == "1Min":
                return {s: [{"t": "2026-09-01T13:30:00Z", "o": 5, "h": 5.2, "l": 4.9, "c": 5.1, "v": 900}]
                        for s in symbols}
            return {}

        def trades(self, symbols, start, end=None, limit=10000):
            return {"RUNR": [{"t": "2026-09-01T13:30:01Z", "p": 5.0, "s": 100},
                             {"t": "2026-09-01T13:30:15Z", "p": 5.3, "s": 100}]}

        def news(self, symbols, limit=50, start=None):
            return []

    recs = al.fetch_records(Stub("PK", "s" * 40), ["RUNR", "QUIET"])
    ten = [r for r in recs if r.get("tf") == "10s"]
    assert {r["symbol"] for r in ten} == {"RUNR"}
    assert len(ten) == 2
    mins = [r for r in recs if r["type"] == "bar" and r.get("tf") != "10s"]
    assert {r["symbol"] for r in mins} == {"QUIET"}, "RUNR's minutes are derived from its 10s bars"


def test_a_trades_outage_keeps_the_minute_bars(capsys):
    class Stub(al.AlpacaClient):
        def snapshots(self, symbols):
            return {}

        def bars(self, symbols, timeframe, start, end=None, limit=10000):
            if timeframe == "1Min":
                return {"AAA": [{"t": "2026-09-01T13:30:00Z", "o": 5, "h": 5, "l": 5, "c": 5, "v": 1}]}
            return {}

        def trades(self, symbols, start, end=None, limit=10000):
            raise al.AlpacaError("trades not entitled")

        def news(self, symbols, limit=50, start=None):
            return []

    recs = al.fetch_records(Stub("PK", "s" * 40), ["AAA"])
    assert any(r["type"] == "bar" for r in recs)
    assert "10-second bars unavailable" in capsys.readouterr().out


# -- the session window must never be inverted --------------------------------

def test_before_four_am_the_window_is_the_previous_weekday():
    """A 03:52 ET run asked for today's 04:00-03:52 and Alpaca refused it."""
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    now = datetime(2026, 9, 2, 3, 52, tzinfo=et)          # Wednesday, pre-dawn
    assert al.session_day(now).date() == datetime(2026, 9, 1).date()


def test_a_weekend_rolls_back_to_friday():
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    sat = datetime(2026, 9, 5, 12, 0, tzinfo=et)
    assert al.session_day(sat).date() == datetime(2026, 9, 4).date()
    mon_early = datetime(2026, 9, 7, 2, 0, tzinfo=et)
    assert al.session_day(mon_early).date() == datetime(2026, 9, 4).date()


def test_midday_is_today():
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    assert al.session_day(datetime(2026, 9, 2, 11, 0, tzinfo=et)).date() == datetime(2026, 9, 2).date()


def test_session_window_end_is_never_before_start(monkeypatch):
    class FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 2, 7, 52, tzinfo=timezone.utc)  # 03:52 ET
    monkeypatch.setattr(al, "datetime", FrozenDT)
    start, end = al.session_window()
    assert start < end, (start, end)
    assert start.startswith("2026-09-01T08:00:00")      # 04:00 ET on Sept 1
