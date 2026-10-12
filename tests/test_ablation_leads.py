"""Section 5 of the ten-year ablation (preregistered 2026-10-12,
research/reddit-bot-rules-2026-10-12/README.md §7): the two leads read on the
live rules — "done after a loss" and a fixed 2R target — and the line a lead
must clear in BOTH periods before it is called a direction."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import ablation_history as A  # noqa: E402


def _p(day, sym, t, trail, fixed, stop_pct=3.0, red=()):
    x = {name: (0.0, 0.0) for name in A.EXITS}
    x["trail 1R (now)"] = (trail, trail)
    x["fixed 2R"] = (fixed, fixed)
    x["BE at 1R, target 2R"] = (fixed, fixed)
    return {"day": day, "sym": sym, "t": t, "stop_pct": stop_pct, "red": list(red), "x": x}


def test_done_after_a_loss_drops_the_later_plans_on_that_name_that_day_only():
    ps = [_p("2024-03-01", "AAA", "09:40", -1.0, -1.0),     # loses: AAA is done for the day
          _p("2024-03-01", "AAA", "09:52", +2.0, +2.0),     # dropped
          _p("2024-03-01", "BBB", "09:55", +1.0, +2.0),     # another name: kept
          _p("2024-03-02", "AAA", "09:41", +1.0, +2.0),     # the next day: kept
          _p("2024-03-01", "CCC", "10:05", +0.5, +2.0, stop_pct=1.5)]   # not on the live rules
    kept = A.after_loss(ps, A.live_ok, "trail 1R (now)")
    assert [(p["day"], p["sym"], p["t"]) for p in kept] == [
        ("2024-03-01", "AAA", "09:40"), ("2024-03-01", "BBB", "09:55"), ("2024-03-02", "AAA", "09:41")]
    # the loss is read under the exit being scored: here AAA's first plan also loses at 2R
    assert len(A.after_loss(ps, A.live_ok, "fixed 2R")) == 3


def test_a_lead_holds_only_when_it_gains_in_both_periods_with_enough_test_trades():
    def period(year, n, retry_r):
        out = []
        for i in range(n):
            day = "%s-01-0%d" % (year, i % 9 + 1)
            out.append(_p(day, "N%d" % i, "09:40", -1.0, -1.0))          # the first plan loses
            out.append(_p(day, "N%d" % i, "09:50", retry_r, retry_r))     # the re-try
        return out
    # re-tries after a loss lose 2 R in both periods: dropping them gains 0.5 R a trade
    rows, verdicts = A.leads(period(2020, 400, -2.0), period(2025, 400, -2.0))
    assert rows[0][0] == "live rules · trail 1R (now)" and rows[0][3] == 800
    assert verdicts["live + done after a loss · trail 1R"] == "HOLDS"
    # ... in the train years only: not a direction
    rows, verdicts = A.leads(period(2020, 400, -2.0), period(2025, 400, +2.0))
    assert verdicts["live + done after a loss · trail 1R"] == "DOES NOT HOLD"
    # ... in both, but on too few test trades
    rows, verdicts = A.leads(period(2020, 400, -2.0), period(2025, 100, -2.0))
    assert verdicts["live + done after a loss · trail 1R"] == "DOES NOT HOLD", "100 test trades is not 300"
