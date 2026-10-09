"""The month study's mechanics (research/month-study/PREREGISTRATION.md): the
universe is the ledger export's names, a lever is a filter, the greedy build
stops under +0.02 R a trade and never goes under 30 trades."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import month_study as M  # noqa: E402


def _plan(net, gross=None, red=(), gain=0.3, rv=2.0, fl=5e6, news=True, stop_pct=2.5, window="regular",
          first=True, day="2026-09-10"):
    return {"touched": True, "red": list(red), "gain": gain, "rv": rv, "float": fl, "news": news,
            "stop_pct": stop_pct, "window": window, "first": first, "day": day,
            "trail": gross if gross is not None else net, "trail_net": net,
            "fixed": gross if gross is not None else net, "fixed_net": net,
            "be": gross if gross is not None else net, "be_net": net}


def test_the_universe_is_the_union_of_the_exported_names(tmp_path):
    d = tmp_path / "2026-09-10"; d.mkdir()
    (d / "screener.csv").write_text("symbol,float_shares\nAAA,4000000\nBBB,\n")
    (d / "board.csv").write_text("symbol,first_ts\nAAA,2026-09-10T07:01:00\nCCC,2026-09-10T08:00:00\n")
    (d / "decisions.csv").write_text("symbol,float_shares\nCCC,30000000\n")
    (tmp_path / "2026-10-20").mkdir()                       # outside the window
    (tmp_path / "2026-10-20" / "screener.csv").write_text("symbol\nZZZ\n")
    uni = M.load_universe(tmp_path, "2026-09-08", "2026-10-08")
    assert set(uni) == {"2026-09-10"}
    assert set(uni["2026-09-10"]) == {"AAA", "BBB", "CCC"}
    assert uni["2026-09-10"]["AAA"]["float"] == 4e6 and uni["2026-09-10"]["AAA"]["from"] == {"screener", "board"}
    assert uni["2026-09-10"]["BBB"]["float"] is None and uni["2026-09-10"]["CCC"]["float"] == 30e6


def test_a_lever_is_a_filter_and_unknown_fails_closed():
    p = _plan(0.5, red=["vwap"], fl=None)
    assert M.passes(p, {}) and not M.passes(p, {"VW": True}) and M.passes(p, {"E9": True})
    assert not M.passes(p, {"FL": 20e6}), "an unknown float fails closed, as on the desk"
    assert M.passes(_plan(0.5, gain=0.25), {"GN": 0.20}) and not M.passes(_plan(0.5, gain=0.25), {"GN": 0.30})
    assert not M.passes(_plan(0.5, rv=None), {"RV": 0.5})
    assert M.passes(_plan(0.5, stop_pct=2.0), {"SW": 2.0}) and not M.passes(_plan(0.5, stop_pct=1.9), {"SW": 2.0})
    assert not M.passes(_plan(0.5, window="pre-market"), {"WN": "regular"})
    assert not M.passes(_plan(0.5, first=False), {"FP": True})
    assert M.stricter("GN", 0.3, 0.2) and M.stricter("FL", 10e6, 20e6) and not M.stricter("WN", "regular", "pre-market")


def test_the_greedy_build_keeps_thirty_trades_and_stops_under_two_hundredths():
    # 40 plans: 32 with news (+0.10 net each), 8 without (−1.0 each). NW is the
    # one lever that helps; after it nothing else can add 0.02 R a trade.
    plans = [_plan(0.10) for _ in range(32)] + [_plan(-1.0, news=False) for _ in range(8)]
    steps = M.greedy(plans, "trail", [0])
    assert steps[0]["label"] == "L0 (no lever)" and steps[0]["n"] == 40
    assert steps[-1]["config"] == {"NW": True} and steps[-1]["n"] == 32 and steps[-1]["mean"] == 0.1
    # never below 30 trades: a filter leaving 20 winners is not taken
    plans = [_plan(1.0, news=True) for _ in range(20)] + [_plan(-0.2, news=False) for _ in range(25)]
    steps = M.greedy(plans, "trail", [0])
    assert all(s["n"] >= 30 for s in steps[1:]), steps
