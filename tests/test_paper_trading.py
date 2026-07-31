"""Tests for the paper_trading package. yfinance is mocked — runs offline."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import broker, indicators, ledger, risk  # noqa: E402
from paper_trading.broker import Quote  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.db"
    ledger.reset_account(10_000.0, db_path=path)
    return path


FAKE_QUOTE = Quote(symbol="ABC", price=5.00, open=4.80, high=5.20,
                   low=4.70, volume=2_000_000, prev_close=4.50)


# ------------------------------------------------------------- ledger
class TestLedger:
    def test_account_created_with_default(self, db):
        acc = ledger.get_account(db)
        assert acc.starting_cash == 10_000.0
        assert acc.cash == 10_000.0

    def test_buy_reduces_cash(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        assert ledger.get_account(db).cash == pytest.approx(9_500.0)

    def test_sell_increases_cash_and_realizes_pnl(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.5, db_path=db)
        assert ledger.get_account(db).cash == pytest.approx(10_050.0)
        pnl = ledger.get_daily_pnl("9999-12-31", db)  # no trades that day
        assert pnl["realized_pnl"] == 0.0

    def test_positions_avg_cost(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.record_fill("ABC", "BUY", 100, 6.0, db_path=db)
        pos = ledger.get_open_positions(db)
        assert pos == [{"symbol": "ABC", "qty": 200, "avg_cost": pytest.approx(5.5)}]

    def test_partial_close_keeps_avg_cost(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.record_fill("ABC", "BUY", 100, 6.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 7.0, db_path=db)
        pos = ledger.get_open_positions(db)
        assert pos[0]["qty"] == pytest.approx(100)
        assert pos[0]["avg_cost"] == pytest.approx(5.5)

    def test_oversell_rejected(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        with pytest.raises(ValueError, match="cannot sell"):
            ledger.record_fill("ABC", "SELL", 101, 5.0, db_path=db)

    def test_insufficient_cash_rejected(self, db):
        with pytest.raises(ValueError, match="insufficient cash"):
            ledger.record_fill("ABC", "BUY", 10_000, 5.0, db_path=db)

    def test_equity_snapshot_per_fill(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.5, db_path=db)
        curve = ledger.get_equity_curve(db)
        assert len(curve) == 2
        assert curve[0]["equity"] == pytest.approx(10_000.0)
        assert curve[1]["equity"] == pytest.approx(10_050.0)

    def test_daily_pnl_fifo(self, db):
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.record_fill("ABC", "BUY", 100, 6.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 150, 7.0, db_path=db)
        pnl = ledger.get_daily_pnl(today, db)
        # 100 * (7-5) + 50 * (7-6) = 250
        assert pnl["realized_pnl"] == pytest.approx(250.0)
        assert pnl["n_trades"] == 3

    def test_reset_wipes_everything(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.reset_account(20_000.0, db_path=db)
        acc = ledger.get_account(db)
        assert acc.cash == 20_000.0
        assert ledger.get_trade_history(db) == []
        assert ledger.get_open_positions(db) == []
        assert ledger.get_equity_curve(db) == []


# ------------------------------------------------------------- broker
class TestBroker:
    def test_sizing_formula(self):
        # risk_budget / (entry - stop), floored to int
        assert broker.position_size(200.0, 5.00, 4.90) == 2000
        assert broker.position_size(200.0, 5.00, 4.93) == 2857

    def test_sizing_rejects_bad_stop(self):
        with pytest.raises(ValueError):
            broker.position_size(200.0, 5.00, 5.10)

    def test_reward_risk(self):
        assert broker.reward_risk(5.0, 4.9, 5.2) == pytest.approx(2.0)

    def test_buy_applies_slippage(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            res = broker.buy("ABC", 100, db_path=db)
        assert res["price"] == pytest.approx(5.02)

    def test_sell_applies_slippage(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            broker.buy("ABC", 100, db_path=db)
            res = broker.sell("ABC", 100, db_path=db)
        assert res["price"] == pytest.approx(4.98)

    def test_no_shorting(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            with pytest.raises(ValueError, match="cannot sell"):
                broker.sell("ABC", 100, db_path=db)


# ------------------------------------------------------------- indicators
def _df(closes, volumes=None, start="2024-01-02 09:30"):
    idx = pd.date_range(start, periods=len(closes), freq="min")
    volumes = volumes or [1000.0] * len(closes)
    return pd.DataFrame({
        "Open": closes, "High": [c + 0.1 for c in closes],
        "Low": [c - 0.1 for c in closes], "Close": closes,
        "Volume": volumes,
    }, index=idx)


class TestIndicators:
    def test_ema_known_series(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        out = indicators.ema(s, 3)  # alpha = 0.5
        # 1, 1.5, 2.25, 3.125, 4.0625
        assert out.iloc[-1] == pytest.approx(4.0625)
        assert out.iloc[0] == pytest.approx(1.0)

    def test_ema9_flat_series(self):
        s = pd.Series([10.0] * 30)
        assert indicators.ema9(s).iloc[-1] == pytest.approx(10.0)

    def test_vwap_single_day(self):
        df = _df([10.0, 20.0], volumes=[100.0, 300.0])
        v = indicators.vwap(df)
        # bar1: typical 10 * 100; bar2: (10*100 + 20*300)/400 = 17.5
        assert v.iloc[0] == pytest.approx(10.0)
        assert v.iloc[-1] == pytest.approx(17.5)

    def test_vwap_resets_daily(self):
        day1 = _df([10.0, 20.0], volumes=[100.0, 300.0])
        day2 = _df([50.0], volumes=[100.0], start="2024-01-03 09:30")
        df = pd.concat([day1, day2])
        v = indicators.vwap(df)
        # first bar of day 2 starts fresh
        assert v.iloc[-1] == pytest.approx(50.0)

    def test_macd_flat_series_zero(self):
        s = pd.Series([10.0] * 60)
        m = indicators.macd(s)
        assert m["macd"].iloc[-1] == pytest.approx(0.0, abs=1e-9)
        assert m["hist"].iloc[-1] == pytest.approx(0.0, abs=1e-9)

    def test_macd_rising_series_positive(self):
        s = pd.Series([float(i) for i in range(1, 61)])
        m = indicators.macd(s)
        assert m["macd"].iloc[-1] > 0
        assert m["hist"].iloc[-1] > 0


# ------------------------------------------------------------- risk
class TestRisk:
    def test_max_daily_loss(self):
        assert risk.check_max_daily_loss(-500, 10_000).ok
        assert not risk.check_max_daily_loss(-601, 10_000).ok

    def test_giveback(self):
        assert risk.check_giveback(60, 100).ok        # floor = 50
        assert not risk.check_giveback(40, 100).ok
        assert risk.check_giveback(-10, 0).ok         # no peak gain yet

    def test_green_to_red(self):
        assert risk.check_green_to_red(-5, was_green=False).ok
        assert not risk.check_green_to_red(-5, was_green=True).ok

    def test_consecutive_losses(self):
        assert risk.check_consecutive_losses([-10, -20, 5, -1, -2]).ok
        assert not risk.check_consecutive_losses([5, -1, -2, -3]).ok

    def test_reward_risk_flag(self):
        assert risk.check_reward_risk(5.0, 4.9, 5.2).ok        # 2.0
        assert not risk.check_reward_risk(5.0, 4.9, 5.15).ok   # 1.5

    def test_daily_report_stops_on_violation(self):
        report = risk.daily_report(-700, 100, 10_000, [-100, -200, -400])
        assert report.should_stop
        names = {r.name for r in report.violations}
        assert f"Max daily loss {risk.MAX_DAILY_LOSS_PCT:.0f}%" in names
        assert "3 consecutive losses" in names
