"""Amendment A2 (owner, 2026-09-17): the catalyst gate flags, it does not kill.

What the ledger showed after five sessions: 389 decisions, 389 REJECT, 254
of them at gate 3, and `catalyst_today` False on every one of them — the
desk had no headline source since the 2026-09-11 reset, so the gate was
deciding on missing data. These tests pin the three parts of the answer:
the desk tells the builder when it has no news feed, the cascade reads
that as UNKNOWN rather than "none", and the rules hash moves with the
amendment so no decision can be mistaken for one made under the old rule.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform import cascade as C  # noqa: E402
from momentum_platform import desk_profile as DP  # noqa: E402
from momentum_platform.dashboard import session_builder as SB  # noqa: E402


def test_a_news_source_record_reaches_the_cascade_as_source_unknown():
    meta = {"symbol": "AAA", "floatShares": 4e6, "floatQuality": "verified",
            "metrics": {"last": 6.0, "changePct": 50.0, "sessionHigh": 6.2, "volumeToday": 3e6},
            "news": [], "tradingDate": "2026-09-17"}
    assert SB.cascade_inputs(meta).catalyst_source_ok is True
    meta["newsSourceOk"] = False
    inp = SB.cascade_inputs(meta)
    assert inp.catalyst_source_ok is False and inp.catalyst_today is False
    res = C.evaluate(inp)
    assert res.killed_by is None
    assert next(g for g in res.gates if g.id == "catalyst").state is C.GateState.UNKNOWN


def test_the_builder_stamps_the_desk_level_answer_on_every_symbol():
    records = [
        {"type": "reference", "symbol": "AAA", "prev_close": 4.0, "float_shares": 4e6,
         "float_quality": "verified"},
        {"type": "reference", "symbol": "BBB", "prev_close": 4.0, "float_shares": 4e6,
         "float_quality": "verified"},
        {"type": "news_source", "ok": False, "note": "no headline source: no keys"},
    ]
    s = SB.build_session_from_records(records, "t", "test", trading_date="2026-09-17")
    for sym in ("AAA", "BBB"):
        g = next(x for x in s["cascade"][sym]["gates"] if x["id"] == "catalyst")
        assert g["state"] in ("UNKNOWN", "NOT_APPLICABLE"), g   # unknown, or an earlier gate stopped it
        assert s["cascade"][sym]["killedBy"] != "catalyst"


def test_the_rules_hash_moves_with_the_amendment(monkeypatch):
    before = DP.fingerprint()["hash"]
    monkeypatch.setattr(C, "CATALYST_GATE_KILLS", not C.CATALYST_GATE_KILLS)
    after = DP.fingerprint()["hash"]
    assert before != after
    assert DP.fingerprint()["cascade"] == {"catalystGateKills": C.CATALYST_GATE_KILLS}


def test_controls_split_by_catalyst_presence(tmp_path):
    from journal import ledger as L, controls
    conn = L.connect(tmp_path / "j.sqlite")
    # two allowed, triggered plans: one with a catalyst, one without
    for did, cat in (("d1", 1), ("d2", 0)):
        conn.execute("""INSERT INTO decisions (decision_id, ts_et, session, symbol, source, source_name,
                        data_status, catalyst, verdict, plan_allowed, trigger, stop, target, last,
                        reward_multiple, gates_json, warnings_json, inputs_json, outcome, recorded_at)
                        VALUES (?, '2026-09-17T10:00:00', 'regular', 'AAA', 'pullback', 'test', 'live',
                                ?, 'REVIEW', 1, 5.0, 4.9, 5.2, 5.0, 2.0, '[]', '[]', '{}', 'LOG_ONLY',
                                '2026-09-17T14:00:00+00:00')""", (did, cat))
        conn.execute("""INSERT INTO actuals (decision_id, ref_price, risk_share, first_hit, c_close, trigger_hit,
                        bars_available, computed_at)
                        VALUES (?, 5.0, 0.1, 'target', 5.1, 1, 30, '2026-09-17T16:00:00+00:00')""", (did,))
    conn.commit()
    s = controls.summary(conn)
    assert s["strat·news"]["n"] == 1 and s["strat·no-news"]["n"] == 1
    assert s["strat·news"]["n"] + s["strat·no-news"]["n"] == s["strat·allowed"]["n"]


def test_a_roundup_is_recognised_by_its_headline_not_by_a_category_that_never_arrives():
    """The 2026-09-08 audit added a roundup filter keyed on `category`. Every
    live record carries the PROVIDER there ("benzinga"), so the filter never
    fired once. Verified against the live endpoint 2026-09-17: VEEA read
    catalyst=True on four headlines, all roundups."""
    day = "2026-09-17"
    fresh = "2026-09-17T12:05:57Z"

    def item(h, cat="benzinga"):
        return {"publishedAt": fresh, "headline": h, "category": cat}

    roundups = [
        "12 Information Technology Stocks Moving In Thursday's Pre-Market Session",
        "Dow Tumbles Over 600 Points as Fed Raises Rates: Investor Sentiment Weakens",
        "Crude Oil Down Over 3%; US Business Inventories Surge In July",
        "Nasdaq Gains Over 100 Points; US Retail Sales Beat Estimates",
        "Veea Inc., DataMEDS AI, Trip.com, Datavault AI and Circle Internet Group: Movers",
    ]
    for h in roundups:
        assert SB.is_roundup(h, "benzinga") is True, h
        assert SB._catalyst_today([item(h)], day) is False, h

    real = [
        "Acme Pharma Announces FDA Approval Of Its Lead Candidate",
        "DataMEDS AI Stock Soars 65% Pre-market: Here's What You Need to Know",
    ]
    for h in real:
        assert SB.is_roundup(h, "benzinga") is False, h
        assert SB._catalyst_today([item(h)], day) is True, h
