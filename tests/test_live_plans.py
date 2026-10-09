"""Only a plan live NOW is drawn or priced (owner, 2026-10-09 07:41).

The owner's screen recording, VEEA then SAIQ: VEEA drew ENTRY 5.44 / STOP 4.61
at 07:41 from a 04:03 plan the bot had refused as outside its window — a 15.3 %
stop — and its WAIT card priced it in a full ORDER block; SAIQ drew TARGET 6.72
/ ENTRY 6.50 / STOP 6.39 from a plan that had stopped at 07:37. Beside it the
card read "WAIT · hands off until the level" over "no level yet".

A plan is live while it is armed inside the bot's 07:00–11:20 entry window,
inside its A10 fill window, not stopped, not at 2R, not killed. These tests pin
the life (`pullback.PlanLife`), the card that reads it (`decision_card`), the
session that stamps it for a scrubbed page (`session_builder`), and that none
of it changes a single plan the bot sees.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from momentum_platform import order_math as OM  # noqa: E402
from momentum_platform.decision_card import build_card  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector, SetupState  # noqa: E402

UTC = timezone.utc
ET = ZoneInfo("America/New_York")

#: a two-bar push (+6 %), a two-bar pullback on lighter volume, then the break
PUSH_PULL = [(5.00, 5.05, 4.98, 5.04, 1000)] * 3 + [
    (5.04, 5.20, 5.03, 5.18, 9000), (5.18, 5.40, 5.17, 5.38, 9000),
    (5.38, 5.39, 5.25, 5.28, 3000), (5.28, 5.30, 5.20, 5.22, 2000)]
BREAK = (5.22, 5.31, 5.21, 5.30, 4000)            # trades over 5.30: arms entry 5.31, stop 5.19
QUIET = (5.27, 5.29, 5.25, 5.28, 1500)            # neither the entry nor the stop


def _rows(rows, start):
    t0 = datetime.fromisoformat(start)
    return [[int((t0 + timedelta(minutes=i)).timestamp()), o, h, l, c, v] for i, (o, h, l, c, v) in enumerate(rows)]


def _feed(rows, sym="ABCD"):
    d = FirstPullbackDetector()
    for b in rows:
        d.on_bar(Bar(symbol=sym, timeframe="1m", ts=datetime.fromtimestamp(b[0], UTC),
                     open=b[1], high=b[2], low=b[3], close=b[4], volume=b[5]))
    return d


def _at(rows, i):
    return datetime.fromtimestamp(rows[i][0], UTC)


# ------------------------------------------------------------------ the life
def test_a_plan_is_live_for_its_fill_window_and_no_longer():
    """Armed on the 09:37 bar (closes 09:38): the bot's entry rests until
    09:41 (A10, ENTRY_TTL_MINUTES = 3). Live on the 09:37–09:40 minutes, not
    on 09:41."""
    rows = _rows(PUSH_PULL + [BREAK] + [QUIET] * 6, "2026-10-07T09:30:00-04:00")
    d = _feed(rows)
    plan = d.plans[0]
    armed = 7
    assert plan.armed_at_bar == _at(rows, armed) and (plan.entry, plan.stop) == (5.31, 5.19)
    for i in range(armed, armed + 1 + OM.ENTRY_TTL_MINUTES):
        assert d.life_of(plan, _at(rows, i))["live"], i
    dead = d.life_of(plan, _at(rows, armed + 1 + OM.ENTRY_TTL_MINUTES))
    assert not dead["live"] and "fill window closed 09:41 (A10: 3 min)" in dead["why"]
    assert d.lives[plan.plan_id].live_until() == _at(rows, armed + 1 + OM.ENTRY_TTL_MINUTES)


def test_a_plan_armed_outside_the_bots_window_is_never_live():
    """VEEA's 04:03 plan: the bot refuses it ("bar is outside the 07:00-16:00 ET
    session window"), so the desk never draws or prices it."""
    rows = _rows(PUSH_PULL + [BREAK] + [QUIET] * 3, "2026-10-07T03:56:00-04:00")
    d = _feed(rows)
    plan = d.plans[0]
    assert plan.armed_at_bar.astimezone(ET).strftime("%H:%M") == "04:03"
    life = d.life_of(plan, _at(rows, 8))
    assert not life["live"] and "outside the bot's 07:00–11:20 entry window" in life["why"]
    assert d.lives[plan.plan_id].live_until() is None
    # the same at 11:20 and after: A8's cut-off is the end of the window
    late = _feed(_rows(PUSH_PULL + [BREAK] + [QUIET], "2026-10-07T11:13:00-04:00"))
    assert not late.lives[late.plans[0].plan_id].in_window


def test_a_stopped_plan_dies_on_the_bar_that_stopped_it():
    """SAIQ: the plan stopped at 07:37 and was still drawn at 07:41."""
    stop_bar = (5.25, 5.26, 5.10, 5.12, 6000)           # low 5.10 under the 5.19 stop
    rows = _rows(PUSH_PULL + [BREAK, stop_bar, QUIET, QUIET], "2026-10-07T07:29:00-04:00")
    d = _feed(rows)
    plan = d.plans[0]
    assert d.life_of(plan, _at(rows, 7))["live"]
    life = d.life_of(plan, _at(rows, 8))
    assert not life["live"] and life["why"] == "the 07:36 plan stop broke before the entry 07:37"
    assert d.lives[plan.plan_id].live_until() == _at(rows, 8)


def test_a_triggered_plan_that_reaches_2r_is_done():
    up = (5.30, 5.60, 5.29, 5.58, 9000)                 # through the entry and the 5.55 target
    rows = _rows(PUSH_PULL + [BREAK, (5.29, 5.33, 5.27, 5.32, 5000), up], "2026-10-07T09:30:00-04:00")
    d = _feed(rows)
    life = d.lives[d.plans[0].plan_id]
    assert life.triggered_bar == _at(rows, 8) and life.end == "reached 2R" and life.ended_bar == _at(rows, 9)
    assert not d.life_of(d.plans[0], _at(rows, 9))["live"]


def test_the_bookkeeping_never_changes_the_machine():
    """The life is read beside the machine: every state and every plan the bot
    sees is what the machine produced before it existed. (The full check —
    2026-10-06 and 2026-10-07, every name, against the code before this change
    — is in docs/desk-recording-2026-10-09/plan_life_output.txt.)"""
    rows = _rows(PUSH_PULL + [BREAK] + [QUIET] * 4 + PUSH_PULL + [BREAK], "2026-10-07T09:30:00-04:00")
    a, b = FirstPullbackDetector(), FirstPullbackDetector()
    states = []
    for r in rows:
        bar = Bar(symbol="ABCD", timeframe="1m", ts=datetime.fromtimestamp(r[0], UTC),
                  open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5])
        a.on_bar(bar)
        b.on_bar(bar)
        b.lives.clear()                                   # bookkeeping thrown away on one side
        states.append((a.state, b.state))
    assert all(x == y for x, y in states)
    assert [(p.entry, p.stop, p.armed_at_bar) for p in a.plans] == [(p.entry, p.stop, p.armed_at_bar) for p in b.plans]


# ------------------------------------------------------------------ the card
def _cascade(verdict="REVIEW", killed=None, **gates):
    base = {g: "PASS" for g in ("price", "float", "catalyst", "pillars", "rising", "split", "instrument",
                                "tick", "buyout", "vwap", "ema9", "macd")}
    base.update(gates)
    out = {"verdict": verdict, "killedBy": killed, "planAllowed": killed is None and verdict != "STALE",
           "gates": [{"id": k, "label": k, "state": v, "value": "v", "reason": f"{k} reason"}
                     for k, v in base.items()]}
    for g in out["gates"]:
        if g["id"] == "pillars":
            g["value"] = "5/5"
    return out


def _card(rows, i, cascade=None, last=None, **kw):
    """The card at minute `i` (the frame of rows[i]), from rows[:i+1]."""
    bars = rows[:i + 1]
    meta = {"metrics": {"last": last if last is not None else bars[-1][4], "changePct": 30.0, "rvol": 8.0,
                        "sessionHigh": max(b[2] for b in bars), "volumeToday": 2e6}, "prevClose": 4.0}
    return build_card("ABCD", meta=meta, cascade=cascade or _cascade(), bars=bars, detector=_feed(bars),
                      now=_at(rows, i), risk=25.0, risk_source="yours", **kw)


def test_a_live_plan_is_drawn_and_priced_on_review():
    rows = _rows(PUSH_PULL + [BREAK] + [QUIET] * 6, "2026-10-07T09:30:00-04:00")
    c = _card(rows, 8)
    assert c["verdict"]["word"] == "REVIEW" and c["verdict"]["action"] == "read the chart, then the tape at the trigger"
    assert c["plan"]["kind"] == "armed" and (c["plan"]["entry"], c["plan"]["stop"]) == (5.31, 5.19)
    assert c["plan"]["liveUntilEt"] == "09:41" and c["setup"]["live"] is True
    assert c["ticket"] and c["ticket"]["trigger"] == 5.31


def test_after_the_fill_window_there_are_no_lines_and_no_order():
    """The fill window closed at 09:41: no plan, no order, and the card says
    the plan still holds the detector (the blackout, kept on purpose —
    addendum 2026-10-06d) rather than promising a pullback that cannot arm."""
    rows = _rows(PUSH_PULL + [BREAK, (5.29, 5.33, 5.27, 5.32, 5000)] + [QUIET] * 6, "2026-10-07T09:30:00-04:00")
    c = _card(rows, 12)
    assert c["plan"] is None and c["ticket"] is None and c["setup"]["live"] is False
    assert c["verdict"]["word"] == "WATCH"
    assert c["verdict"]["reason"] == "no live plan — the 09:37 plan holds the detector until its stop 5.19 or 2R 5.55"
    assert "triggered, then its fill window closed 09:41" in c["setup"]["text"]


def test_saiq_a_stopped_plan_leaves_no_lines_and_says_waiting():
    stop_bar = (5.25, 5.26, 5.10, 5.12, 6000)
    rows = _rows(PUSH_PULL + [BREAK, stop_bar, QUIET, QUIET, QUIET], "2026-10-07T07:29:00-04:00")
    c = _card(rows, 11)
    assert c["plan"] is None and c["ticket"] is None
    assert c["verdict"]["reason"] == "no live plan — waiting for the next pullback"
    assert "last plan 07:36 5.31/5.19 → stop broke before the entry (07:37)" in c["setup"]["text"]


def test_veea_a_plan_from_before_the_window_is_never_priced():
    """04:03 plan, triggered, held all morning: at 07:41 the WAIT card has no
    order and no lines; its setup line says why."""
    rows = _rows(PUSH_PULL + [BREAK, (5.29, 5.33, 5.27, 5.32, 5000)] + [QUIET] * 220,
                 "2026-10-07T03:56:00-04:00")
    i = next(k for k, r in enumerate(rows) if datetime.fromtimestamp(r[0], ET).strftime("%H:%M") == "07:41")
    c = _card(rows, i, cascade=_cascade(verdict="WAIT", vwap="FAIL"))
    assert c["verdict"]["word"] == "WAIT" and c["ticket"] is None and c["plan"] is None
    assert "armed outside the bot's 07:00–11:20 entry window" in c["setup"]["text"]


def test_the_order_exists_on_review_only():
    """A forming pullback with a red chart gate: WAIT, and no ticket (owner,
    2026-10-09: "the order only on REVIEW")."""
    rows = _rows(PUSH_PULL, "2026-10-07T09:30:00-04:00")
    wait = _card(rows, len(rows) - 1, cascade=_cascade(verdict="WAIT", vwap="FAIL"))
    assert wait["verdict"]["word"] == "WAIT" and wait["ticket"] is None and wait["plan"] is None
    review = _card(rows, len(rows) - 1)
    assert review["verdict"]["word"] == "REVIEW" and review["ticket"]["trigger"] == 5.31
    assert review["plan"]["kind"] == "forming" and review["plan"]["target"] == 5.55


@pytest.mark.parametrize("cascade,kw,level", [
    (_cascade(verdict="WAIT", vwap="FAIL"), {}, True),                 # reclaim the VWAP: a level
    (_cascade(verdict="WAIT", macd="FAIL"), {}, False),                # MACD under its signal: none
    (_cascade(verdict="STALE"), {}, False),
    (_cascade(), {"halted": True}, False),
])
def test_the_action_names_a_level_only_when_there_is_one(cascade, kw, level):
    """SAIQ read "WAIT · hands off until the level" beside "no level yet"."""
    rows = _rows(PUSH_PULL, "2026-10-07T09:30:00-04:00")
    v = _card(rows, len(rows) - 1, cascade=cascade, **kw)["verdict"]
    assert v["word"] == "WAIT"
    assert (v["level"] is not None) == level, v
    assert "until the level" not in v["action"]
    if level:
        assert v["action"] == "hands off until it reclaims the VWAP"
    else:
        assert v["levelLabel"] is None


def test_a_heavier_pullback_has_no_level_because_its_break_changes_nothing():
    rows = _rows(PUSH_PULL[:-2] + [(5.38, 5.39, 5.25, 5.28, 9500), (5.28, 5.30, 5.20, 5.22, 9900)],
                 "2026-10-07T09:30:00-04:00")
    v = _card(rows, len(rows) - 1)["verdict"]
    assert v["word"] == "WAIT" and v["level"] is None and "lighter volume" in v["action"]


def test_the_card_carries_the_cascades_pillar_count():
    rows = _rows(PUSH_PULL, "2026-10-07T09:30:00-04:00")
    c = _card(rows, len(rows) - 1)
    assert c["pillars"] == {"passed": 5, "of": 5, "needs": 4, "counted": True, "note": None}
    killed = _cascade(verdict="REJECT", killed="price", price="FAIL", pillars="NOT_APPLICABLE")
    for g in killed["gates"]:
        if g["id"] == "pillars":
            g["value"] = "—"
    k = _card(rows, len(rows) - 1, cascade=killed)
    assert k["pillars"]["counted"] is False and "stopped at price" in k["pillars"]["note"]
    assert k["plan"] is None and k["ticket"] is None


# ------------------------------------------------------------------ the session
def test_the_session_stamps_each_plan_with_its_life():
    """A page scrubbed back reads `liveUntil` on each published plan; the
    live edge reads the card. 2026-10-07 up to 09:40, from the day's export."""
    import fixture_from_export as F
    from momentum_platform.dashboard.session_builder import build_session_from_records
    s = build_session_from_records(F.build("2026-10-07", "09:40"), "t", "t")
    assert s["plans"], "the day armed plans"
    for p in s["plans"]:
        assert "liveUntil" in p and "inWindow" in p
        if p["liveUntil"] is not None:
            assert p["armedAt"] < p["liveUntil"] <= p["armedAt"] + 60 + OM.ENTRY_TTL_MINUTES * 60
        else:
            assert p["inWindow"] is False
    t = s["frames"][-1]["t"]
    for sym, card in s["cards"].items():
        if card["plan"] and card["plan"]["kind"] == "armed":
            assert card["plan"]["liveUntil"] > t
    json.dumps(s, default=str)                                    # still serialisable


def test_the_page_judges_nothing_about_a_plans_life():
    """app.js reads the server's `card.plan` and `liveUntil`; it computes no
    window, no TTL and no stop of its own."""
    app = (ROOT / "src" / "momentum_platform" / "dashboard" / "web" / "app.js").read_text()
    body = app.split("function livePlan")[1].split("\nfunction ")[0]
    for judged in ("ENTRY_TTL", "11:20", "07:00", ".low", "plan.stop"):
        assert judged not in body, judged
