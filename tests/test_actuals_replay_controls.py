"""Actuals are filled for every decision, replay reproduces every verdict,
and the controls run on the same rows in the same units.

The fixture is SYNTHETIC. These tests prove plumbing, never a market claim.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import actuals, bars, controls, ledger as L, replay  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


@pytest.fixture(scope="module")
def journal():
    conn = L.connect(":memory:")
    build_session(FIXTURE, journal=conn)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def tape():
    return bars.from_fixture(FIXTURE)


# ---------------------------------------------------------------- actuals
def test_actuals_are_computed_for_every_decision_including_suppressed(journal, tape):
    res = actuals.fill_all(journal, tape)
    assert res["no_tape"] == []
    n_dec = journal.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    n_act = journal.execute("SELECT COUNT(*) FROM actuals").fetchone()[0]
    assert n_act == n_dec == res["computed"]
    # suppressed ones too — "the one I passed on" becomes a measurement
    sup = journal.execute("""SELECT COUNT(*) FROM decisions d JOIN actuals a USING(decision_id)
                             WHERE d.outcome='SUPPRESSED'""").fetchone()[0]
    assert sup == 3


def test_actuals_start_strictly_after_the_decision_bar(journal, tape):
    row = L.decisions(journal)[0]
    fwd = actuals.forward(tape[row["symbol"]], actuals._utc(row["ts_et"]))
    first = actuals._bar_dt(fwd[0][0])
    assert first > actuals._utc(row["ts_et"])


def test_r_columns_are_named_planned_and_mfe_mae_have_the_right_signs(journal):
    a = journal.execute("SELECT * FROM actuals WHERE risk_share IS NOT NULL LIMIT 1").fetchone()
    assert a["mfe_r_planned"] >= a["mae_r_planned"]
    assert a["risk_share"] > 0
    cols = {d[0] for d in journal.execute("SELECT * FROM actuals LIMIT 1").description}
    assert "mfe_r_planned" in cols and "mfe_r" not in cols     # the name says which R


def test_same_bar_touching_both_levels_counts_the_stop_first():
    """The conservative rule, stated in the module docstring: on a 1-minute
    bar the order of events inside it is unknown, and the stop is assumed."""
    row = dict(ts_et="2026-09-01T09:40:00-04:00", trigger=10.0, stop=9.5, target=11.0,
               last=10.0)
    tape = [("2026-09-01T13:40:00Z", 10, 10.1, 9.9, 10, 1),        # the decision bar
            ("2026-09-01T13:41:00Z", 10, 11.5, 9.0, 10, 1)]        # touches both
    a = actuals.compute(row, tape)
    assert a["stop_hit"] == 1 and a["target_hit"] == 1
    assert a["first_hit"] == "stop"
    assert a["mfe_r_planned"] == 3.0 and a["mae_r_planned"] == -2.0


def test_no_forward_tape_yields_none_not_zeros():
    row = dict(ts_et="2026-09-01T09:40:00-04:00", trigger=10.0, stop=9.5, target=None, last=10.0)
    assert actuals.compute(row, [("2026-09-01T13:40:00Z", 10, 10, 10, 10, 1)]) is None


def test_fill_all_is_idempotent(journal, tape):
    assert actuals.fill_all(journal, tape)["computed"] == 0


# ----------------------------------------------------------------- replay
def test_every_recorded_verdict_is_reproduced_from_its_stored_inputs(journal):
    res = replay.check(journal)
    assert res["checked"] == 5
    assert res["diverged"] == [], res
    assert res["reproduced"] == res["checked"]


def test_replay_detects_a_log_that_lost_an_input(journal):
    """Simulate the class of defect R11 exists for: a stored input that no
    longer matches the recorded verdict."""
    conn = L.connect(":memory:")
    build_session(FIXTURE, journal=conn)
    row = conn.execute("SELECT decision_id, inputs_json FROM decisions "
                       "WHERE plan_allowed=1 LIMIT 1").fetchone()
    inputs = json.loads(row["inputs_json"])
    inputs["last"] = 1.00                       # would now die on price
    conn.execute("UPDATE decisions SET inputs_json=? WHERE decision_id=?",
                 (json.dumps(inputs), row["decision_id"]))
    res = replay.check(conn)
    assert len(res["diverged"]) == 1
    assert res["diverged"][0]["replayed"] == ("REJECT", "price")


# --------------------------------------------------------------- controls
def test_controls_run_on_the_same_rows_in_planned_r(journal):
    s = controls.series(journal)
    assert len(s["strategy"]) == len(s["hold_close"]) == 5
    summ = controls.summary(journal)
    for k in ("strategy", "hold_close", "random_bar"):
        assert summ[k]["n"] >= 1
        assert summ[k]["mean_R"] is not None


def test_a_stopped_out_plan_scores_exactly_minus_one_planned_r(journal):
    rows = journal.execute("""SELECT d.trigger, d.stop, a.first_hit, a.c_close, a.risk_share
                              FROM decisions d JOIN actuals a USING(decision_id)""").fetchall()
    s = controls.series(journal)["strategy"]
    for r, val in zip(rows, s):
        if r["first_hit"] == "stop":
            assert val == -1.0


def test_actuals_run_from_the_ledgers_own_tape_with_no_fixture():
    """A live session has no fixture file. The desk wrote the bars; actuals
    must run from those alone and agree with the fixture path."""
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    from_ledger = bars.from_ledger(c)
    from_file = bars.from_fixture(FIXTURE)
    assert set(from_ledger) == set(from_file)
    for sym in from_file:
        assert [b[:6] for b in from_ledger[sym]] == [b[:6] for b in from_file[sym]]
    res = actuals.fill_all(c, from_ledger)
    assert res["computed"] == 5 and res["no_tape"] == []
