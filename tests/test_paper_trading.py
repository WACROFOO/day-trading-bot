"""Tests for the paper_trading package. yfinance is mocked — runs offline."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import broker, indicators, ledger, risk, risk_gate  # noqa: E402
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

    def test_reset_clears_orders_and_risk_state(self, db):
        ledger.create_order("ABC", "SELL", 100, "STOP", stop_price=4.9, db_path=db)
        ledger.get_risk_day("2024-01-02", 10_000.0, db_path=db)
        ledger.set_equity_hwm(12_000.0, db_path=db)
        ledger.set_walkaway_locked(True, db_path=db)
        ledger.reset_account(20_000.0, db_path=db)
        assert ledger.get_open_orders(db) == []
        assert ledger.get_equity_hwm(db) == 20_000.0  # falls back to starting_cash
        assert not ledger.is_walkaway_locked(db)
        with ledger._connect(db) as conn:
            assert conn.execute("SELECT COUNT(*) FROM risk_day").fetchone()[0] == 0


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
        # cash drops by qty*price plus $0.50 commission (100 * $0.005)
        assert res["commission"] == pytest.approx(0.50)
        assert ledger.get_account(db).cash == pytest.approx(10_000.0 - 502.0 - 0.50)

    def test_sell_applies_slippage(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            broker.buy("ABC", 100, db_path=db)
            res = broker.sell("ABC", 100, db_path=db)
        assert res["price"] == pytest.approx(4.98)
        # round trip: -$4.00 gross, -$1.00 commissions
        assert ledger.get_account(db).cash == pytest.approx(10_000.0 - 4.0 - 1.0)

    def test_no_shorting(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            with pytest.raises(ValueError, match="cannot sell"):
                broker.sell("ABC", 100, db_path=db)

    def test_affordable_shares(self):
        # floor(cash / (price + slippage + per_share)) = floor(10000 / 5.025)
        assert broker.affordable_shares(10_000, 5.0) == 1990
        assert broker.affordable_shares(0, 5.0) == 0

    def test_marketable_limit_price(self):
        assert broker.marketable_limit_price("BUY", 5.0) == pytest.approx(5.15)
        assert broker.marketable_limit_price("SELL", 5.0) == pytest.approx(4.85)

    def test_marketable_limit_buy_fills_at_better_price(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            res = broker.buy("ABC", 100, order_type="LIMIT",
                             limit_price=5.10, db_path=db)
        assert res["price"] == pytest.approx(5.02)  # min(5.10, 5.00 + 0.02)

    def test_non_marketable_limit_rejected(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            with pytest.raises(ValueError, match="limit not marketable"):
                broker.buy("ABC", 100, order_type="LIMIT",
                           limit_price=4.90, db_path=db)

    def test_cancel_all(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            broker.buy("ABC", 100, stop_price=4.9, db_path=db)
            broker.buy("XYZ", 100, stop_price=4.9, db_path=db)
        assert broker.cancel_all("ABC", db_path=db) == 1
        assert len(ledger.get_open_orders(db)) == 1
        assert broker.cancel_all(db_path=db) == 1
        assert ledger.get_open_orders(db) == []


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

    def test_ema20_flat_series(self):
        s = pd.Series([10.0] * 30)
        assert indicators.ema20(s).iloc[-1] == pytest.approx(10.0)

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

    def test_drawdown(self):
        assert risk.check_drawdown(8_500, 10_000).ok
        assert not risk.check_drawdown(7_900, 10_000).ok

    def test_daily_report_appends_drawdown_with_hwm(self):
        report = risk.daily_report(0, 0, 7_500, [], high_watermark=10_000)
        assert report.should_stop
        names = {r.name for r in report.violations}
        assert f"Drawdown walkaway {risk.DRAWDOWN_WALKAWAY_PCT:.0f}%" in names
        # without the kwarg: 4 rules only, no drawdown
        assert len(risk.daily_report(0, 0, 7_500, []).rules) == 4


# ------------------------------------------------------------- helpers
def _today_et() -> str:
    return ledger._et_date(datetime.now(timezone.utc).isoformat())


def _set_trade_ts(db, trade_id: int, ts: str) -> None:
    """Move a recorded fill to a fixed (past) timestamp."""
    with sqlite3.connect(str(db)) as conn:
        conn.execute("UPDATE trades SET timestamp = ? WHERE id = ?", (ts, trade_id))


def _three_small_losses(db) -> None:
    """Three losing round trips, -$100 each (isolated consecutive-loss trip)."""
    for _ in range(3):
        ledger.record_fill("ABC", "BUY", 200, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 200, 4.5, db_path=db)


def _backdated_25pct_drawdown(db) -> None:
    """Past (not today) losses: equity $7.5k vs $10k HWM = 25% drawdown."""
    t1 = ledger.record_fill("ABC", "BUY", 2000, 5.0, db_path=db)
    t2 = ledger.record_fill("ABC", "SELL", 2000, 3.75, db_path=db)
    _set_trade_ts(db, t1, "2020-01-02T15:00:00+00:00")
    _set_trade_ts(db, t2, "2020-01-02T16:00:00+00:00")


# ------------------------------------------------------------- migration
V1_SCHEMA = """
CREATE TABLE account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    starting_cash REAL NOT NULL,
    cash REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty REAL NOT NULL,
    price REAL NOT NULL
);
CREATE TABLE equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    trade_id INTEGER,
    equity REAL NOT NULL,
    cash REAL NOT NULL
);
"""


def _make_v1_db(path):
    """Build a schema-v1 database by hand (old DDL + account + one trade)."""
    conn = sqlite3.connect(str(path))
    conn.executescript(V1_SCHEMA)
    conn.execute(
        "INSERT INTO account (id, starting_cash, cash, created_at) VALUES (1, ?, ?, ?)",
        (10_000.0, 9_500.0, "2024-01-01T00:00:00+00:00"),
    )
    conn.execute(
        "INSERT INTO trades (timestamp, symbol, side, qty, price) VALUES (?, ?, ?, ?, ?)",
        ("2024-01-02T15:00:00+00:00", "ABC", "BUY", 100, 5.0),
    )
    conn.commit()
    conn.close()
    return path


class TestMigration:
    def test_v1_db_migrates_in_place(self, tmp_path):
        db = _make_v1_db(tmp_path / "v1.db")
        with ledger._connect(db) as conn:  # opening triggers _migrate
            trades_cols = {r["name"] for r in conn.execute("PRAGMA table_info(trades)")}
            account_cols = {r["name"] for r in conn.execute("PRAGMA table_info(account)")}
            tables = {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            row = conn.execute("SELECT * FROM trades").fetchone()
            n_trades = conn.execute("SELECT COUNT(*) c FROM trades").fetchone()["c"]
            cash = conn.execute("SELECT cash FROM account WHERE id = 1").fetchone()["cash"]
        assert {"commission", "order_id", "reason"} <= trades_cols
        assert {"equity_hwm", "walkaway_locked"} <= account_cols
        assert {"orders", "risk_day"} <= tables
        # existing data intact; new columns defaulted
        assert n_trades == 1
        assert row["qty"] == 100 and row["price"] == 5.0
        assert row["commission"] == 0.0
        assert row["order_id"] is None and row["reason"] is None
        assert cash == 9_500.0

    def test_migrate_is_idempotent(self, tmp_path):
        db = _make_v1_db(tmp_path / "v1.db")
        with ledger._connect(db) as conn:
            ledger._migrate(conn)  # no-op on second/third run, no error
            ledger._migrate(conn)
            assert conn.execute("SELECT COUNT(*) c FROM trades").fetchone()["c"] == 1


# ------------------------------------------------------------- commissions
class TestCommissions:
    def test_buy_cash_includes_commission(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, commission=0.5, db_path=db)
        assert ledger.get_account(db).cash == pytest.approx(10_000 - 500 - 0.5)

    def test_sell_cash_nets_commission(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.5, commission=0.5, db_path=db)
        assert ledger.get_account(db).cash == pytest.approx(10_000 - 500 + 550 - 0.5)

    def test_cash_guard_includes_commission(self, db):
        ledger.reset_account(500.0, db_path=db)
        with pytest.raises(ValueError, match="insufficient cash"):
            ledger.record_fill("ABC", "BUY", 100, 5.0, commission=0.01, db_path=db)

    def test_daily_pnl_reports_commissions(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, commission=0.5, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.5, commission=0.5, db_path=db)
        pnl = ledger.get_daily_pnl(_today_et(), db)
        assert pnl["commissions"] == pytest.approx(1.0)
        # realized = gross 50 minus the day's commissions
        assert pnl["realized_pnl"] == pytest.approx(49.0)

    def test_broker_round_trip_net_of_commissions(self, db):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            broker.buy("ABC", 100, db_path=db)   # 5.02, comm $0.50
            broker.sell("ABC", 100, db_path=db)  # 4.98, comm $0.50
        trips = ledger.get_round_trips(db)
        assert len(trips) == 1
        assert trips[0].pnl == pytest.approx(-4.0 - 1.0)


# ------------------------------------------------------------- risk gate
class TestRiskGate:
    def test_allows_buy_when_all_rules_ok(self, db):
        # fully offline: no quote mock, no market data anywhere
        risk_gate.RiskGate(db).assert_can_buy()

    def test_max_daily_loss_trips(self, db):
        ledger.record_fill("ABC", "BUY", 2000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 2000, 4.68, db_path=db)  # -$640 (-6.4%)
        with pytest.raises(risk_gate.RiskVeto, match="Max daily loss"):
            risk_gate.RiskGate(db).assert_can_buy()

    def test_giveback_trips(self, db):
        gate = risk_gate.RiskGate(db)
        ledger.record_fill("ABC", "BUY", 1000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 1000, 6.0, db_path=db)  # +$1000
        gate.state()  # persist the $1000 peak
        ledger.record_fill("ABC", "BUY", 1000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 1000, 4.4, db_path=db)  # day now +$400
        with pytest.raises(risk_gate.RiskVeto, match="Giveback"):
            gate.assert_can_buy()

    def test_green_to_red_trips(self, db):
        gate = risk_gate.RiskGate(db)
        ledger.record_fill("ABC", "BUY", 1000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 1000, 6.0, db_path=db)  # +$1000
        gate.state()  # was_green latched
        ledger.record_fill("ABC", "BUY", 1000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 1000, 3.8, db_path=db)  # day now -$200
        with pytest.raises(risk_gate.RiskVeto, match="Green-to-red"):
            gate.assert_can_buy()

    def test_consecutive_losses_trip(self, db):
        _three_small_losses(db)
        with pytest.raises(risk_gate.RiskVeto, match="consecutive losses"):
            risk_gate.RiskGate(db).assert_can_buy()

    def test_drawdown_walkaway_trips(self, db):
        _backdated_25pct_drawdown(db)
        with pytest.raises(risk_gate.RiskVeto, match="Drawdown walkaway"):
            risk_gate.RiskGate(db).assert_can_buy()
        assert ledger.is_walkaway_locked(db)

    def test_broker_buy_vetoed_and_records_nothing(self, db):
        _three_small_losses(db)
        n_before = len(ledger.get_trade_history(db))
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            with pytest.raises(risk_gate.RiskVeto):
                broker.buy("ABC", 100, db_path=db)
        assert len(ledger.get_trade_history(db)) == n_before  # no fill recorded

    def test_latch_persists_across_instances(self, db):
        _three_small_losses(db)
        risk_gate.RiskGate(db).state()  # trips and latches
        gate2 = risk_gate.RiskGate(db)  # fresh instance = process restart
        assert gate2.state().locked
        with pytest.raises(risk_gate.RiskVeto):
            gate2.assert_can_buy()

    def test_latch_survives_pnl_recovery(self, db):
        gate = risk_gate.RiskGate(db)
        ledger.record_fill("ABC", "BUY", 1000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 1000, 6.0, db_path=db)  # +$1000
        gate.state()
        ledger.record_fill("ABC", "BUY", 1000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 1000, 4.4, db_path=db)  # giveback trips
        with pytest.raises(risk_gate.RiskVeto):
            gate.assert_can_buy()
        ledger.record_fill("ABC", "BUY", 1000, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 1000, 6.0, db_path=db)  # P&L recovers
        with pytest.raises(risk_gate.RiskVeto):  # still locked
            gate.assert_can_buy()

    def test_sell_allowed_while_locked(self, db):
        _three_small_losses(db)
        with pytest.raises(risk_gate.RiskVeto):
            risk_gate.RiskGate(db).assert_can_buy()
        ledger.record_fill("ABC", "BUY", 500, 5.0, db_path=db)  # raw ledger, unguarded
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            res = broker.sell("ABC", 500, db_path=db)  # exits never gated
        assert res["qty"] == 500
        assert ledger.get_open_positions(db) == []

    def test_new_day_rollover_unlocks(self, db):
        _three_small_losses(db)
        with pytest.raises(risk_gate.RiskVeto):
            risk_gate.RiskGate(db).assert_can_buy()
        tomorrow = lambda: datetime.now(timezone.utc) + timedelta(days=1)  # noqa: E731
        risk_gate.RiskGate(db, clock=tomorrow).assert_can_buy()  # no raise

    def test_reset_for_new_day_clears_latch(self, db):
        _three_small_losses(db)
        gate = risk_gate.RiskGate(db)
        with pytest.raises(risk_gate.RiskVeto):
            gate.assert_can_buy()
        gate.reset_for_new_day()
        row = ledger.get_risk_day(gate._today(), 0.0, db_path=db)
        assert row["locked"] == 0
        assert row["lock_reason"] is None

    def test_reset_walkaway_clears(self, db):
        _backdated_25pct_drawdown(db)
        gate = risk_gate.RiskGate(db)
        with pytest.raises(risk_gate.RiskVeto):
            gate.assert_can_buy()
        assert ledger.is_walkaway_locked(db)
        gate.reset_walkaway()
        assert not ledger.is_walkaway_locked(db)
        gate.assert_can_buy()  # no raise: HWM rebased to current equity


# ------------------------------------------------------------- brackets
class TestBracket:
    def _buy_with_stop(self, db, qty=100, stop=4.90):
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            return broker.buy("ABC", qty, stop_price=stop, db_path=db)

    def test_buy_creates_bracket_stop(self, db):
        res = self._buy_with_stop(db)
        assert res["price"] == pytest.approx(5.02)
        stops = ledger.get_open_orders(db, symbol="ABC")
        assert len(stops) == 1
        assert stops[0]["order_type"] == "STOP"
        assert stops[0]["side"] == "SELL"
        assert stops[0]["qty"] == 100
        assert stops[0]["stop_price"] == pytest.approx(4.90)
        assert stops[0]["reason"] == "BRACKET"
        # the entry order itself is FILLED, not open
        assert [o for o in ledger.get_open_orders(db) if o["side"] == "BUY"] == []

    def test_stop_triggers_at_stop_minus_slippage(self, db):
        self._buy_with_stop(db)
        assert broker.check_stops({"ABC": (5.00, 4.94)}, db_path=db) == []
        fills = broker.check_stops({"ABC": (5.00, 4.88)}, db_path=db)
        assert len(fills) == 1
        assert fills[0]["price"] == pytest.approx(4.90 - 0.02)
        assert fills[0]["reason"] == "STOP"
        assert fills[0]["commission"] == pytest.approx(0.50)
        assert ledger.get_open_positions(db) == []
        assert ledger.get_open_orders(db) == []
        trade = ledger.get_trade_history(db)[0]  # newest first
        assert trade["reason"] == "STOP"
        assert trade["commission"] == pytest.approx(0.50)

    def test_gap_through_fills_at_open_minus_slippage(self, db):
        self._buy_with_stop(db)
        fills = broker.check_stops({"ABC": (4.80, 4.70)}, db_path=db)
        assert len(fills) == 1
        assert fills[0]["price"] == pytest.approx(4.80 - 0.02)
        assert ledger.get_open_positions(db) == []

    def test_manual_exit_cancels_stop(self, db):
        self._buy_with_stop(db)
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            broker.sell_all("ABC", db_path=db)
        assert ledger.get_open_orders(db) == []  # bracket canceled
        assert broker.check_stops({"ABC": (4.80, 4.70)}, db_path=db) == []

    def test_sell_half_shrinks_stop_qty(self, db):
        self._buy_with_stop(db)
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            broker.sell_half("ABC", db_path=db)
        stops = ledger.get_open_orders(db, symbol="ABC")
        assert len(stops) == 1
        assert stops[0]["qty"] == pytest.approx(50)
        assert ledger.get_open_positions(db)[0]["qty"] == pytest.approx(50)

    def test_round_trip_recovers_risk_per_share(self, db):
        self._buy_with_stop(db)
        broker.check_stops({"ABC": (5.00, 4.88)}, db_path=db)
        trips = ledger.get_round_trips(db)
        assert len(trips) == 1
        assert trips[0].risk_per_share == pytest.approx(5.02 - 4.90)


# ------------------------------------------------------------- sell half
class TestSellHalf:
    def test_sell_half_of_100(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            res = broker.sell_half("ABC", db_path=db)
        assert res["qty"] == 50
        assert ledger.get_open_positions(db)[0]["qty"] == pytest.approx(50)

    def test_sell_half_floors_odd_qty(self, db):
        ledger.record_fill("ABC", "BUY", 2857, 3.0, db_path=db)
        with patch.object(broker, "quote", return_value=FAKE_QUOTE):
            res = broker.sell_half("ABC", db_path=db)
        assert res["qty"] == 1428
        assert ledger.get_open_positions(db)[0]["qty"] == pytest.approx(1429)

    def test_sell_half_rejects_one_share(self, db):
        ledger.record_fill("ABC", "BUY", 1, 5.0, db_path=db)
        with pytest.raises(ValueError, match="half"):
            broker.sell_half("ABC", db_path=db)


# ------------------------------------------------------------- round trips
class TestRoundTrips:
    def test_flat_to_flat_cycles(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.5, db_path=db)
        ledger.record_fill("ABC", "BUY", 100, 6.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.8, db_path=db)
        trips = ledger.get_round_trips(db)
        assert len(trips) == 2
        assert trips[0].pnl == pytest.approx(50.0)
        assert trips[0].entry_avg == pytest.approx(5.0)
        assert trips[0].exit_avg == pytest.approx(5.5)
        assert trips[0].closed_at is not None
        assert trips[1].pnl == pytest.approx(-20.0)

    def test_overnight_exit_attributes_to_exit_date(self, db):
        t1 = ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        t2 = ledger.record_fill("ABC", "SELL", 100, 5.5, db_path=db)
        _set_trade_ts(db, t1, "2024-01-02T15:00:00+00:00")  # Tue 10:00 ET
        _set_trade_ts(db, t2, "2024-01-03T15:00:00+00:00")  # Wed 10:00 ET
        entry_day = ledger.get_daily_pnl("2024-01-02", db)
        exit_day = ledger.get_daily_pnl("2024-01-03", db)
        assert entry_day["realized_pnl"] == pytest.approx(0.0)
        assert exit_day["realized_pnl"] == pytest.approx(50.0)
        assert exit_day["round_trips"] == [pytest.approx(50.0)]

    def test_scale_out_is_one_round_trip(self, db):
        ledger.record_fill("ABC", "BUY", 200, 5.0, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.5, db_path=db)
        ledger.record_fill("ABC", "SELL", 100, 5.5, db_path=db)
        trips = ledger.get_round_trips(db)
        assert len(trips) == 1
        assert trips[0].qty == pytest.approx(200)
        assert trips[0].pnl == pytest.approx(100.0)

    def test_open_cycle_reported_unclosed(self, db):
        ledger.record_fill("ABC", "BUY", 100, 5.0, db_path=db)
        trips = ledger.get_round_trips(db)
        assert len(trips) == 1
        assert trips[0].closed_at is None
        assert trips[0].exit_avg is None
