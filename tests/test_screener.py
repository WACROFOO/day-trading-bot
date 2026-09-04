"""Screener: delayed consolidated quotes first, IEX fallback, never silent."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.datasources import alpaca_source as al  # noqa: E402
from momentum_platform.datasources import screener as sc  # noqa: E402
from momentum_platform.datasources.yahoo_quotes import YahooError, parse_quotes  # noqa: E402


def _yahoo_payload(**overrides):
    q = {"symbol": "SSM", "marketState": "PRE", "preMarketPrice": 4.76,
         "preMarketChangePercent": 77.4, "preMarketTime": 1756800000,
         "regularMarketPrice": 2.68, "regularMarketChangePercent": 1.1,
         "regularMarketPreviousClose": 2.68, "fullExchangeName": "NasdaqCM",
         "shortName": "Sono Group", "floatShares": 1_400_000}
    q.update(overrides)
    return {"quoteResponse": {"result": [q]}}


def test_premarket_state_uses_the_premarket_numbers():
    p = parse_quotes(_yahoo_payload())["SSM"]
    assert p["session"] == "premarket" and p["price"] == 4.76 and p["change_pct"] == 77.4


def test_regular_state_uses_the_regular_numbers():
    p = parse_quotes(_yahoo_payload(marketState="REGULAR"))["SSM"]
    assert p["session"] == "regular" and p["price"] == 2.68 and p["change_pct"] == 1.1


def test_premarket_state_without_a_premarket_print_falls_to_regular():
    p = parse_quotes(_yahoo_payload(preMarketPrice=None))["SSM"]
    assert p["session"] == "regular"


# A print only counts as a move in THIS session, so the stub's timestamps are
# derived from the session clock rather than hard-coded to a past day.
SESSION_START = al.session_window(al.session_day())[0]


class StubAlpaca(al.AlpacaClient):
    def __init__(self):
        super().__init__("PK", "s" * 40)

    def assets(self, status="active"):
        return [{"symbol": s, "tradable": True, "status": "active", "class": "us_equity", "exchange": "NASDAQ"}
                for s in ("SSM", "BIG", "FLAT")]

    def snapshots(self, symbols):
        return {
            "SSM": {"prevDailyBar": {"c": 2.68}, "dailyBar": {"v": 0, "t": "2026-09-01T04:00:00Z"},
                    "latestTrade": {"p": 2.68, "t": "2026-09-01T19:59:57Z"}},       # IEX: nothing today
            "BIG": {"prevDailyBar": {"c": 150.0}, "dailyBar": {"v": 10}, "latestTrade": {"p": 151}},  # out of band
            "FLAT": {"prevDailyBar": {"c": 5.0}, "dailyBar": {"v": 100}, "latestTrade": {"p": 5.05, "t": SESSION_START}},
        }


class StubYahoo:
    def __init__(self, payload=None, fail=False):
        self.payload, self.fail, self.asked = payload, fail, None

    def quotes(self, symbols):
        self.asked = list(symbols)
        if self.fail:
            raise YahooError("crumb expired")
        return parse_quotes(self.payload)


def test_yahoo_premarket_move_surfaces_a_name_iex_has_not_printed():
    al._EXCHANGE_CACHE.update(at=0.0, map={})
    y = StubYahoo(_yahoo_payload())
    out = sc.build_screener(StubAlpaca(), yahoo=y, min_price=2, max_price=20, min_gain=10, top=10)
    assert out["source"] == "yahoo-delayed"
    assert [r["symbol"] for r in out["rows"]] == ["SSM"]
    row = out["rows"][0]
    assert row["source"] == "yahoo" and row["change_pct"] == 77.4 and row["session"] == "premarket"
    assert "BIG" not in y.asked, "names far outside the band are not even quoted"


def test_yahoo_outage_falls_back_to_iex_and_says_so():
    al._EXCHANGE_CACHE.update(at=0.0, map={})
    out = sc.build_screener(StubAlpaca(), yahoo=StubYahoo(fail=True), min_price=2, max_price=20, min_gain=10, top=10)
    assert out["source"] == "iex"
    assert any("Yahoo" in n for n in out["notes"])
    assert out["rows"] == [], "on IEX alone nothing in this stub has moved 10%"


def test_iex_only_path_computes_change_from_prev_close():
    al._EXCHANGE_CACHE.update(at=0.0, map={})
    out = sc.build_screener(StubAlpaca(), yahoo=None, min_price=2, max_price=20, min_gain=0.5, top=10)
    assert out["source"] == "iex"
    assert [r["symbol"] for r in out["rows"]] == ["FLAT"]
    assert abs(out["rows"][0]["change_pct"] - 1.0) < 0.01


def test_server_exposes_the_screener_and_desk_add():
    server = (ROOT / "src" / "momentum_platform" / "dashboard" / "server.py").read_text()
    assert "class ScreenerLoop" in server
    assert '"/api/v1/screener"' in server and '"/api/v1/desk/add"' in server
    assert "def add_symbols" in server


def test_page_carries_the_screener_card_and_parks_it_in_the_tray():
    """The right column is the Five Pillars check, Level 2 and the verdict;
    the screener is one click away in the Cards tray and still polls."""
    web = ROOT / "src" / "momentum_platform" / "dashboard" / "web"
    html = (web / "index.html").read_text(); app = (web / "app.js").read_text()
    assert 'data-card="screener"' in html
    assert 'R1: "pillars-board"' in app and "function pollScreener" in app
    assert '"screener"' not in app.split("const DEFAULT_LAYOUT")[1].split("};")[0]
    assert '"screener"' in app.split("const ALL_CARDS")[1].split(";")[0]
    assert "/api/v1/desk/add?symbol=" in app
    assert 'LIVE — following the newest bar' in app
