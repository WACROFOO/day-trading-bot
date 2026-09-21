"""microflow: config provenance, bar folding, the sync assertion, the spread
gate and the Phase-0 verdict.

Each test names the property it protects. See
`src/momentum_platform/microflow/README.md` for the contracts.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import ledger as L  # noqa: E402
from momentum_platform.microflow import DEFAULT, MicroflowConfig, bars as B, spread as S  # noqa: E402
from momentum_platform.microflow import measure as M  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 18, 14, 0, 0, tzinfo=UTC)          # 10:00 ET


def c(i, o, h, l, cl, v=100, sym="AAA", t0=T0):
    return B.Candle(sym, t0 + timedelta(seconds=10 * i), o, h, l, cl, v)


# -- config -------------------------------------------------------------------

def test_every_parameter_declares_where_it_came_from():
    """An undeclared number is a defect, not a default. The repo has been
    bitten by unsourced local filters before."""
    assert DEFAULT.undeclared() == []


def test_the_unmeasured_values_are_named_not_hidden():
    unm = set(DEFAULT.unmeasured())
    assert "max_dip_retrace_pct" in unm and "bailout_bars_10s" in unm
    for k in unm:
        assert DEFAULT.provenance(k)["note"], f"{k} is unmeasured AND unexplained"


def test_the_spread_gate_is_eight_and_says_why():
    assert DEFAULT.spread_k == 8.0
    note = DEFAULT.provenance("spread_k")["note"]
    assert "0.25" in note and "k=4" in note, "the arithmetic that set it must be recorded"


def test_the_config_is_frozen_and_fingerprinted():
    with pytest.raises(Exception):
        DEFAULT.spread_k = 2.0                       # type: ignore[misc]
    assert DEFAULT.fingerprint() != MicroflowConfig(spread_k=4.0).fingerprint()


# -- bars ---------------------------------------------------------------------

def test_ten_second_candles_fold_into_their_minute():
    cs = [c(i, 5.0 + i * .01, 5.1 + i * .01, 4.9 + i * .01, 5.05 + i * .01, 10) for i in range(6)]
    m = B.to_minutes(cs)
    assert len(m) == 1
    assert m[0].open == cs[0].open and m[0].close == cs[-1].close
    assert m[0].high == max(x.high for x in cs) and m[0].low == min(x.low for x in cs)
    assert m[0].volume == 60


def test_a_partial_minute_folds_to_what_is_present_and_coverage_names_the_gap():
    cs = [c(0, 5.0, 5.1, 4.9, 5.05), c(3, 5.2, 5.3, 5.1, 5.25)]   # slots 0 and 3 only
    assert B.to_minutes(cs)[0].volume == 200
    cov = B.coverage(cs)
    assert cov["candles"] == 2 and cov["minutes"] == 1
    assert cov["gaps"][0]["missing_slots"] == [1, 2, 4, 5]
    assert cov["present_pct"] == pytest.approx(33.33, abs=0.01)


def test_the_forming_minute_never_includes_a_candle_that_has_not_closed():
    """Layer B may see the minute as it stood, not as it ended."""
    cs = [c(i, 5.0, 5.1 + i, 4.9, 5.0) for i in range(6)]
    at = T0 + timedelta(seconds=30)            # slots 0,1,2 have closed
    f = B.forming_minute(cs, at)
    assert f is not None and f.high == 5.1 + 2, "a later candle leaked in"
    assert B.forming_minute(cs, T0) is None, "nothing has closed yet"


def test_sync_passes_when_they_agree_and_raises_when_they_do_not():
    cs = [c(i, 5.0, 5.1, 4.9, 5.05, 10) for i in range(6)]
    good = [(T0, 5.0, 5.1, 4.9, 5.05, 60)]
    B.assert_sync(cs, good)                                   # no raise
    with pytest.raises(B.SyncError) as e:
        B.assert_sync(cs, [(T0, 5.0, 9.99, 4.9, 5.05, 60)])
    assert "high disagrees" in str(e.value)


def test_sync_skips_a_minute_only_one_side_saw():
    cs = [c(i, 5.0, 5.1, 4.9, 5.05, 10) for i in range(6)]
    other = T0 + timedelta(minutes=5)
    B.assert_sync(cs, [(other, 1.0, 2.0, 0.5, 1.5, 10)])      # silence is not disagreement


def test_load_reads_back_what_the_desk_wrote(tmp_path):
    conn = L.connect(tmp_path / "j.sqlite")
    L.record_bars_10s(conn, [("AAA", T0 + timedelta(seconds=10 * i), 5.0, 5.1, 4.9, 5.05, 10)
                             for i in range(6)])
    fine = B.load(conn, day="2026-09-18")
    assert len(fine["AAA"]) == 6
    assert B.load(conn, day="2026-09-19") == {}


# -- spread gate --------------------------------------------------------------

def test_the_gate_passes_a_stop_far_enough_from_the_spread():
    v = S.gate(trigger=5.10, stop=5.00, bid=5.09, ask=5.10, cfg=DEFAULT)   # risk .10, spread .01
    assert v.ok and v.state is S.State.PASS and v.kills is False
    assert v.ratio == pytest.approx(0.10)
    assert "10.0x" in v.reason


def test_the_gate_fails_a_stop_the_spread_would_eat():
    v = S.gate(trigger=3.51, stop=3.48, bid=3.50, ask=3.51, cfg=DEFAULT)   # risk .03, spread .01
    assert not v.ok and v.state is S.State.FAIL
    assert v.ratio == pytest.approx(1 / 3, abs=1e-6)
    assert "0.25" in v.reason, "the reason must name what the edge is worth"


def test_a_missing_or_crossed_quote_is_unknown_not_zero():
    """Fails closed. A spread that cannot be established is not a spread of nil."""
    assert S.gate(5.1, 5.0, None, None, DEFAULT).state is S.State.UNKNOWN
    assert S.gate(5.1, 5.0, 5.20, 5.05, DEFAULT).state is S.State.UNKNOWN
    assert S.gate(None, 5.0, 5.0, 5.01, DEFAULT).state is S.State.UNKNOWN


def test_a_stop_above_the_trigger_is_rejected():
    assert S.gate(5.0, 5.2, 4.99, 5.0, DEFAULT).state is S.State.FAIL


def test_k_changes_the_answer_and_nothing_else_does():
    loose = MicroflowConfig(spread_k=2.0)
    args = dict(trigger=5.10, stop=5.04, bid=5.09, ask=5.10)   # risk .06, spread .01 -> 6x
    assert S.gate(**args, cfg=loose).ok
    assert not S.gate(**args, cfg=DEFAULT).ok                  # needs 8x


def test_cost_in_r_and_the_minimum_stop_are_consistent():
    assert S.cost_in_r(0.01, 0.10) == pytest.approx(0.10)
    assert S.cost_in_r(0.01, 0) is None
    assert S.min_risk_per_share(0.01, DEFAULT) == pytest.approx(0.08)


# -- dip detection and the verdict --------------------------------------------

def test_a_dip_is_found_between_two_pushes_and_the_stop_is_its_low():
    cs = [c(0, 5.00, 5.10, 4.98, 5.08),        # push, high 5.10
          c(1, 5.08, 5.09, 5.02, 5.03),        # dip 1
          c(2, 5.03, 5.06, 5.01, 5.05),        # dip 2
          c(3, 5.05, 5.20, 5.04, 5.18)]        # new high -> the dip closes
    dips = M.find_dips(cs, DEFAULT)
    assert len(dips) == 1
    d = dips[0]
    assert d.trigger == 5.10 and d.dip_low == 5.01 and d.bars_in_dip == 2
    assert d.risk_per_share == pytest.approx(0.09)


def test_a_pause_longer_than_the_pattern_is_not_a_micro_pullback():
    cs = [c(0, 5.0, 5.10, 4.98, 5.08)] + [c(i, 5.0, 5.05, 4.99, 5.0) for i in range(1, 7)] \
         + [c(7, 5.0, 5.30, 4.99, 5.28)]
    assert M.find_dips(cs, DEFAULT) == []


def test_the_verdict_refuses_to_judge_a_session_that_did_not_happen():
    v, why = M.verdict({"candles": 12, "dips": 0, "dips_with_quote": 0,
                        "survival_by_k": {}, "spread_over_risk": {"median": None}}, DEFAULT)
    assert v == "INCONCLUSIVE" and "not a session" in why[0]


def test_the_verdict_says_no_go_when_the_spread_eats_the_stop():
    m = {"candles": 5000, "dips": 200, "dips_with_quote": 180,
         "survival_by_k": {8: {"n": 5, "pct": 2.8}}, "spread_over_risk": {"median": 1.4}}
    v, why = M.verdict(m, DEFAULT)
    assert v == "NO-GO" and any("spread eats" in w for w in why)


def test_the_verdict_says_go_only_with_real_survival():
    m = {"candles": 5000, "dips": 200, "dips_with_quote": 180,
         "survival_by_k": {8: {"n": 90, "pct": 50.0}}, "spread_over_risk": {"median": 0.08}}
    assert M.verdict(m, DEFAULT)[0] == "GO"
    m["survival_by_k"][8] = {"n": 27, "pct": 15.0}
    assert M.verdict(m, DEFAULT)[0] == "MARGINAL"


def test_the_limitations_are_always_available_and_name_the_gates_not_applied():
    lim = " ".join(M.limitations())
    assert "upper bound" in lim and "slippage" in lim and "halt" in lim


# -- the guard ----------------------------------------------------------------

def test_no_module_in_the_package_can_place_an_order():
    import momentum_platform.microflow as pkg
    root = Path(pkg.__file__).parent
    banned = ("placeOrder", "reqIds", "bracketOrder", "LimitOrder", "StopOrder", "MarketOrder")
    for f in root.glob("*.py"):
        src = f.read_text()
        for b in banned:
            assert b not in src, f"{f.name} names {b} — the order path lives in src/execution/"


def test_the_verdict_names_which_condition_decided_it():
    """Review item 7: median(spread/risk) = 0.41 is not "the median dip is
    inside the spread". A NO-GO on k-survival must say the plan's own stop
    condition did not fire; one on the median must say it did."""
    m = {"candles": 5000, "dips": 200, "dips_with_quote": 180,
         "survival_by_k": {8: {"n": 5, "pct": 2.8}}, "spread_over_risk": {"median": 0.41}}
    v, why = M.verdict(m, DEFAULT)
    assert v == "NO-GO" and any("did NOT fire" in w for w in why)
    m["spread_over_risk"]["median"] = 1.4
    v, why = M.verdict(m, DEFAULT)
    assert v == "NO-GO" and any("stop condition fired" in w for w in why)


def test_dips_inside_the_spread_are_counted_directly(tmp_path):
    """The statistic the stop condition needs: how many quoted dips have a
    spread at least as wide as their whole stop."""
    rows = [{"ratio": r} for r in (0.2, 0.5, 1.0, 2.5)]
    quoted = [r for r in rows if r["ratio"] is not None]
    inside = [r for r in quoted if r["ratio"] >= 1.0]
    assert len(inside) == 2
    # and the same arithmetic inside measure(): built from the module's own rule
    src = (ROOT / "src/momentum_platform/microflow/measure.py").read_text()
    assert 'inside = [r for r in quoted if r["ratio"] >= 1.0]' in src
