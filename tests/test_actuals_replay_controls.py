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
    # Three before amendment A2 (2026-09-17); two of them were catalyst kills,
    # which the gate now flags instead. One price/float kill remains.
    assert sup == 1


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


def test_no_forward_tape_is_recorded_as_no_tape_not_left_for_tomorrow():
    """A decision with no same-day forward bars used to return None and be
    re-scored on the NEXT day's tape when the symbol recurred."""
    row = dict(ts_et="2026-09-01T09:40:00-04:00", trigger=10.0, stop=9.5, target=None, last=10.0)
    a = actuals.compute(row, [("2026-09-01T13:40:00Z", 10, 10, 10, 10, 1),
                              ("2026-09-02T13:41:00Z", 10, 12, 9, 11, 1)])     # tomorrow's bar
    assert a["bars_available"] == 0 and a["first_hit"] == "no_tape"


def test_fill_all_is_idempotent(journal, tape):
    assert actuals.fill_all(journal, tape)["computed"] == 0


# ----------------------------------------------------------------- replay
def test_every_recorded_verdict_is_reproduced_from_its_stored_inputs(journal):
    res = replay.check(journal)
    assert res["checked"] == 5
    assert res["diverged"] == [], res
    assert res["reproduced"] == res["checked"]


def test_an_amendment_is_classified_superseded_not_reported_as_a_broken_log():
    """2026-09-18: `advance` said "282 decision(s) do not reproduce". Nothing
    was broken — Amendment A2 had correctly changed the answer for the rows the
    blind catalyst gate killed. A check that cannot tell a rule change from a
    defect reports both as the same alarm.

    A row recorded under pre-A2 rules must land in `superseded`, named, and
    must NOT land in `diverged`, which is what gates and reports act on.
    """
    conn = L.connect(":memory:")
    build_session(FIXTURE, journal=conn)
    row = conn.execute("SELECT decision_id, inputs_json FROM decisions LIMIT 1").fetchone()
    inputs = json.loads(row["inputs_json"])
    inputs["catalyst_today"], inputs["live_theme"] = False, None
    inputs["catalyst_source_ok"] = True
    # what the OLD rules recorded for these inputs: killed at the catalyst gate
    conn.execute("UPDATE decisions SET inputs_json=?, verdict='REJECT', killed_by='catalyst' "
                 "WHERE decision_id=?", (json.dumps(inputs), row["decision_id"]))
    res = replay.check(conn)
    assert res["diverged"] == [], "an amendment is not a broken log"
    assert len(res["superseded"]) == 1
    assert res["superseded"][0]["rules"] == "pre-A2"
    assert res["by_rules"]["pre-A2"] == 1 and res["current_rules"] == "A5"   # A5 since 2026-09-21
    # and it is not quietly counted as reproducing under the current rules
    assert res["reproduced"] == res["checked"] - 1


def test_a_pre_a5_float_kill_is_superseded_under_a2_not_diverged():
    """A5 changed the float gate. A row the OLD rules killed on float must
    reproduce under A2 (float still killed there) and be named as such."""
    conn = L.connect(":memory:")
    build_session(FIXTURE, journal=conn)
    row = conn.execute("SELECT decision_id, inputs_json FROM decisions LIMIT 1").fetchone()
    inputs = json.loads(row["inputs_json"])
    inputs.update({"float_shares": 45_000_000.0, "float_verified": True,
                   "catalyst_today": True, "catalyst_source_ok": True,
                   "change_pct": 50.0, "rvol": 8.0, "last": 6.0})
    conn.execute("UPDATE decisions SET inputs_json=?, verdict='REJECT', killed_by='float' "
                 "WHERE decision_id=?", (json.dumps(inputs), row["decision_id"]))
    res = replay.check(conn)
    assert res["diverged"] == []
    assert any(x["rules"] == "A2" for x in res["superseded"])
    assert res["current_rules"] == "A5"


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
def test_controls_run_on_the_same_rows_in_planned_r_and_skip_untriggered(journal):
    """Only plans whose trigger was touched are trades; the rest are counted
    under 'untriggered' instead of being charged −1 R."""
    triggered = journal.execute("SELECT COUNT(*) FROM actuals WHERE trigger_hit=1 AND risk_share>0").fetchone()[0]
    s = controls.series(journal)
    assert len(s["strategy"]) == len(s["hold_close"]) == triggered
    summ = controls.summary(journal)
    assert "untriggered" in summ
    assert summ["untriggered"]["n"] + triggered == 5


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


# ---------------------------------------------------------------- exit variants (review item 3)
def _bars(*rows):
    """(high, low, close) per bar, minute-stamped from 14:31Z."""
    return [(f"2026-09-01T14:{31 + i:02d}:00Z", c, h, l, c, 1000) for i, (h, l, c) in enumerate(rows)]


def test_the_simulated_trail_tests_the_low_before_the_high_raises_the_stop():
    """The within-bar look-ahead the review named: a bar that spikes to +2R
    and touches the initial stop in the same minute. Raising the stop on the
    high first would exit at +1R on a bar that actually stopped the trade."""
    trigger, stop = 10.0, 9.0                        # 1R = $1
    bars = _bars((12.0, 9.0, 11.0), (13.0, 11.5, 12.5))
    res = controls.simulate_exit(bars, trigger, stop, "trail_1r")
    assert res == {"r": -1.0, "exit": "stop", "bars_held": 1}, res
    # what a look-ahead implementation returns on the same bar, written out so the
    # difference is a number and not a sentence
    lookahead_stop = max(stop, 12.0 - 1.0)            # raised first ...
    assert bars[0][3] <= lookahead_stop               # ... then the low "hits" it at +1R
    assert (lookahead_stop - trigger) / 1.0 == 1.0 != res["r"]


def test_the_trail_ratchets_up_never_down_and_names_its_exit():
    trigger, stop = 10.0, 9.0
    bars = _bars((12.0, 10.5, 11.8), (12.5, 11.2, 12.0), (12.2, 10.9, 11.0), (14.0, 12.0, 13.0))
    res = controls.simulate_exit(bars, trigger, stop, "trail_1r")
    # bar1 raises to 11.0, bar2 to 11.5, bar3's low 10.9 <= 11.5: out at 11.5 = +1.5R
    assert res == {"r": 1.5, "exit": "trail", "bars_held": 3}


def test_the_three_variants_share_the_entry_and_differ_only_in_the_exit():
    trigger, stop = 10.0, 9.0
    runner = _bars((11.0, 9.8, 10.9), (12.5, 10.7, 12.4), (13.5, 12.0, 13.4), (15.0, 13.2, 14.9))
    base = controls.simulate_exit(runner, trigger, stop, "baseline", target=12.0)
    hold = controls.simulate_exit(runner, trigger, stop, "no_target")
    trail = controls.simulate_exit(runner, trigger, stop, "trail_1r")
    assert base == {"r": 2.0, "exit": "target", "bars_held": 2}
    assert hold == {"r": 4.9, "exit": "close", "bars_held": 4}
    assert trail == {"r": 4.9, "exit": "close", "bars_held": 4}     # never gave back 1R from its high
    loser = _bars((10.4, 8.9, 9.0),)
    for v in controls.VARIANTS:
        assert controls.simulate_exit(loser, trigger, stop, v, target=12.0)["r"] == -1.0


def test_exit_variants_run_on_the_ledger_rows_from_the_same_entry_bar(journal, tape):
    actuals.fill_all(journal, tape)
    ev = controls.exit_variants(journal, tape)
    n = {v: len(rows) for v, rows in ev.items()}
    assert n["baseline"] == n["no_target"] == n["trail_1r"] > 0
    summ = controls.exit_summary(journal, tape)
    for v in controls.VARIANTS:
        assert summ[v]["n"] == n[v] and summ[v]["stopped"] is not None
    # a variant can only differ from no_target by exiting earlier at a level: the
    # rows the tape never stopped agree exactly
    by_id = {v: {r["decision_id"]: r for r in ev[v]} for v in ev}
    for did, r in by_id["no_target"].items():
        if r["exit"] == "close" and by_id["trail_1r"][did]["exit"] == "close":
            assert by_id["trail_1r"][did]["r"] == r["r"]


def test_the_statistical_unit_is_reported_beside_the_mean(journal, tape):
    """Review item 9: rows, unique symbol-days, sessions, per-session series
    and the share the three largest winning symbol-days carry."""
    actuals.fill_all(journal, tape)
    u = controls.units(journal)
    n = len(controls.series(journal)["strategy"])
    assert u["rows"] == u["unique_setups"] == n > 0
    assert 1 <= u["unique_symbol_days"] <= n and u["sessions"] >= 1
    assert sum(v["n"] for v in u["per_session"].values()) == n
    assert len(u["top3_symbol_days"]) <= 3
    if u["top3_share_of_total"] is not None:
        assert 0 <= u["top3_share_of_total"]
    if u["mean_R_without_top3"] is not None:
        assert u["mean_R_without_top3"] <= (u["mean_R"] or 0) + 1e-9 or u["top3_share_of_total"] is None


def test_13b_no_simulated_fill_inside_the_decision_candle(journal, tape):
    """A decision on a completed candle can be filled no earlier than the next
    candle: actuals start strictly after the decision bar, and the exit
    simulation enters at the bar the trigger was first touched, never before."""
    actuals.fill_all(journal, tape)
    rows = journal.execute("SELECT d.ts_et, a.trigger_hit_ts FROM decisions d JOIN actuals a USING(decision_id) "
                           "WHERE a.trigger_hit_ts IS NOT NULL").fetchall()
    assert rows
    for r in rows:
        assert actuals._bar_dt(r["trigger_hit_ts"]) > actuals._utc(r["ts_et"])
    ev = controls.exit_variants(journal, tape)
    for v, items in ev.items():
        for it in items:
            d = journal.execute("SELECT ts_et FROM decisions WHERE decision_id=?", (it["decision_id"],)).fetchone()
            hit = journal.execute("SELECT trigger_hit_ts FROM actuals WHERE decision_id=?", (it["decision_id"],)).fetchone()
            assert actuals._bar_dt(hit[0]) > actuals._utc(d[0]) and it["bars_held"] >= 1
