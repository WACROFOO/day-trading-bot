"""Offline tests for the performance / accuracy report."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import portfolio, report  # noqa: E402

TZ = "America/New_York"


def decision(verdict="SKIP", reason="gate: no_trigger", r=float("nan"),
             resolved=False, **kw):
    row = {"session": "2026-08-20", "symbol": "AAA",
           "timestamp": pd.Timestamp("2026-08-20 09:40", tz=TZ),
           "verdict": verdict, "reason": reason, "price": 5.0,
           "confluence_count": 2, "support_reasons": "ema9|vwap",
           "outcome_resolved": resolved, "outcome_r_multiple": r,
           "outcome_net_pnl": 0.0}
    row.update(kw)
    return row


def trade(net=100.0, r=1.0, mfe=1.5, mae=-0.2, exit_reason="stop", **kw):
    row = {"session": "2026-08-20", "symbol": "AAA",
           "entry_time": pd.Timestamp("2026-08-20 09:40", tz=TZ),
           "exit_time": pd.Timestamp("2026-08-20 09:50", tz=TZ),
           "entry": 5.0, "stop": 4.9, "target": 5.2, "shares": 1000,
           "risk_per_share": 0.1, "reward_risk": 2.0, "r_multiple": r,
           "net_pnl": net, "exit_reason": exit_reason, "mae_r": mae,
           "mfe_r": mfe, "bars_held": 10, "equity_before": 100_000.0,
           "equity_after": 100_000.0 + net, "size_capped_by_cash": False,
           "confluence_count": 2, "support_reasons": "ema9|vwap"}
    row.update(kw)
    return row


def sim_from(trades, blocked=None, days=None):
    return {"trades": pd.DataFrame(trades),
            "blocked": pd.DataFrame(blocked or []),
            "days": pd.DataFrame(days or []),
            "config": {"starting_equity": 100_000.0},
            "final_equity": 100_000.0 + sum(t["net_pnl"] for t in trades),
            "return_pct": sum(t["net_pnl"] for t in trades) / 1000.0}


def build(logs, sim):
    return report.build(pd.DataFrame(logs), sim, symbols=["AAA"],
                        sessions=["2026-08-20"], data_note="test data")


# ------------------------------------------------------------------ missed

def test_missed_winners_finds_skipped_winners():
    logs = pd.DataFrame([
        decision("SKIP", "gate: no_confluence", r=2.0, resolved=True),
        decision("SKIP", "gate: no_trigger", r=-1.0, resolved=True),
        decision("TAKE", "ok", r=1.0, resolved=True),
    ])
    missed = report.missed_winners(logs)
    assert len(missed) == 1
    assert missed.iloc[0]["blocked_by"] == "no_confluence"


def test_opportunity_cost_identifies_the_sole_blocker():
    """The gate that alone stood between you and a winner is the finding."""
    logs = pd.DataFrame([
        decision("SKIP", "gate: no_confluence", r=2.0, resolved=True),
        decision("SKIP", "gate: no_confluence", r=1.5, resolved=True),
        decision("SKIP", "gate: no_confluence,macd_hist<=0", r=3.0, resolved=True),
    ])
    oc = report.opportunity_cost_by_gate(logs)
    row = oc[oc["token"] == "no_confluence"].iloc[0]
    assert row["winners_blocked"] == 3
    assert row["sole_blocker"] == 2          # the third had a second blocker
    assert row["total_R_forgone"] == pytest.approx(6.5)


def test_opportunity_cost_empty_when_nothing_was_missed():
    logs = pd.DataFrame([decision("TAKE", "ok", r=1.0, resolved=True)])
    assert report.opportunity_cost_by_gate(logs).empty


# ------------------------------------------------------------------ losers

def test_loser_that_gave_back_a_gain_is_diagnosed_as_an_exit_problem():
    t = pd.DataFrame([trade(net=-100.0, r=-1.0, mfe=2.2, exit_reason="stop")])
    d = report.losing_trade_diagnosis(t)
    assert "gave it back" in d.iloc[0]["diagnosis"]


def test_loser_that_never_worked_is_diagnosed_separately():
    t = pd.DataFrame([trade(net=-100.0, r=-1.0, mfe=0.1, exit_reason="stop")])
    d = report.losing_trade_diagnosis(t)
    assert "never worked" in d.iloc[0]["diagnosis"]


def test_vwap_break_loser_cites_the_rule():
    t = pd.DataFrame([trade(net=-50.0, r=-0.5, mfe=0.4, exit_reason="vwap_break")])
    assert "VWAP" in report.losing_trade_diagnosis(t).iloc[0]["diagnosis"]


def test_winners_are_not_diagnosed_as_losers():
    t = pd.DataFrame([trade(net=250.0, r=2.5)])
    assert report.losing_trade_diagnosis(t).empty


# ------------------------------------------------------------------ render

def test_report_renders_with_no_trades_at_all():
    md = build([decision()], sim_from([]))
    assert "No trades were executed" in md
    assert "# Performance & accuracy report" in md


def test_report_flags_an_undersized_sample():
    md = build([decision("TAKE", "ok", r=1.0, resolved=True)],
               sim_from([trade(net=200.0, r=2.0)]))
    assert "Not significant" in md


def test_report_states_the_untestable_inputs():
    """The report must never let Level 2 / float / catalyst pass silently."""
    md = build([decision()], sim_from([]))
    assert "Level 2" in md and "float_max" in md
    assert "upper bound" in md


def test_report_includes_blocked_signal_opportunity_cost():
    blocked = [{"session": "2026-08-20", "symbol": "BBB",
                "timestamp": pd.Timestamp("2026-08-20 10:00", tz=TZ),
                "reason": portfolio.BLOCK_MAX_TRADES, "detail": "2 taken",
                "would_be_r": 2.0, "would_be_pnl": 400.0}]
    md = build([decision()], sim_from([trade()], blocked=blocked))
    assert "never got to trade" in md
    assert portfolio.BLOCK_MAX_TRADES in md
    assert "capacity, not signal quality" in md


def test_report_surfaces_the_gate_that_blocks_winners():
    logs = [decision("SKIP", "gate: no_confluence", r=2.0, resolved=True)]
    md = build(logs, sim_from([]))
    assert "sole_blocker" in md
    assert "support reasons" in md.lower()


def test_report_reports_the_risk_lock():
    days = [{"date": "2026-08-20", "start_equity": 100_000.0,
             "peak_equity": 100_000.0, "end_equity": 94_000.0, "trades": 3,
             "consecutive_losses": 3, "locked": True,
             "lock_reason": "3 consecutive losses", "lock_time": None}]
    md = build([decision()], sim_from([trade(net=-2000.0, r=-1.0)], days=days))
    assert "risk gate locked the account on 1 day" in md


def test_report_is_plain_markdown_and_non_empty():
    md = build([decision()], sim_from([trade()]))
    assert md.startswith("# ")
    assert len(md) > 1000


def test_distinct_missed_collapses_overlapping_opportunities():
    """One move produces many profitable SKIP candles; counting them all
    would overstate the opportunity cost by an order of magnitude."""
    rows = []
    for i in range(6):
        rows.append(decision("SKIP", "gate: no_confluence", r=2.0, resolved=True,
                             cursor=i, timestamp=pd.Timestamp(f"2026-08-20 09:4{i}", tz=TZ),
                             outcome_bars_held=3))
    logs = pd.DataFrame(rows)
    assert len(report.missed_winners(logs)) == 6
    assert len(report.distinct_missed(logs)) == 2      # cursors 0 and 4


def test_distinct_missed_keeps_genuinely_separate_setups():
    rows = [decision("SKIP", "gate: no_confluence", r=2.0, resolved=True, cursor=0,
                     timestamp=pd.Timestamp("2026-08-20 09:40", tz=TZ),
                     outcome_bars_held=1),
            decision("SKIP", "gate: no_confluence", r=2.0, resolved=True, cursor=50,
                     timestamp=pd.Timestamp("2026-08-20 10:30", tz=TZ),
                     outcome_bars_held=1)]
    assert len(report.distinct_missed(pd.DataFrame(rows))) == 2


def test_report_states_the_collapse_ratio():
    rows = [decision("SKIP", "gate: no_confluence", r=2.0, resolved=True, cursor=i,
                     timestamp=pd.Timestamp(f"2026-08-20 09:4{i}", tz=TZ),
                     outcome_bars_held=5) for i in range(4)]
    md = build(rows, sim_from([]))
    assert "distinct opportunities" in md
