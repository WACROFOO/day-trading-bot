"""The desk as a manual decision tool (owner, 2026-10-08).

docs/desk-assessment-2026-10-08.md lists what the card did not show; these
tests pin what it shows now: the bot's own order arithmetic, the catalyst
grade and its rules file, the verdict table, the bot's answer, and the
owner's manual calls — all fixture-driven, no market, no broker.
"""
from __future__ import annotations

import json
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import ledger as L  # noqa: E402
from momentum_platform import order_math as OM  # noqa: E402
from momentum_platform.catalyst import card_read, classify, news_cutoff  # noqa: E402
from momentum_platform.decision_card import bot_line, build_card, plan_outcome  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

FIXTURE = ROOT / "fixtures" / "market_replay" / "workstation_open_2026-09-01.jsonl"
ET_OFF = timedelta(hours=4)          # EDT: the fixtures below are September/October


# ------------------------------------------------------------ the order math
def test_the_desk_and_the_bot_share_one_copy_of_the_order_arithmetic():
    """The desk may not import `execution`; the bot's numbers moved to
    momentum_platform.order_math and `execution.intent` re-exports them. The
    same objects, not equal copies: one formula cannot drift from itself."""
    from execution import intent as I
    from execution import runner as R
    for name in ("entry_limit", "exit_offset", "sizing_reserve", "shares_for", "sized_for",
                 "ENTRY_LIMIT_OFFSET_PCT", "SPREAD_K", "TRAIL_R", "WORST_FILL_SIZING",
                 "HARD_STOP", "ENTRY_CUTOFF", "PREMARKET_START"):
        assert getattr(I, name) is getattr(OM, name), name
    assert R.SELECTIVE_MIN_STOP_PCT is OM.SELECTIVE_MIN_STOP_PCT
    assert R.SELECTIVE_MIN_PRICE is OM.SELECTIVE_MIN_PRICE


def test_the_ticket_is_the_runners_order_for_the_plan():
    """trigger 5.00 / stop 4.80 / $20 / spread 2c: the A10 limit 5.01, the A18
    reserve 0.04, 83 shares — the worked example of the order-math map."""
    t = OM.ticket("ABCD", 5.00, 4.80, 20.0, session="regular", bid=4.98, ask=5.00)
    assert (t.limit, t.reserve, t.shares, t.bound_by) == (5.01, 0.04, 83, "risk")
    assert t.target_2r == 5.40 and t.stop_pct == 4.0
    assert t.loss_at_stop == pytest.approx(83 * 0.20)
    assert t.order_line == "BUY 83 ABCD STP LMT · stop 5.00 · limit 5.01 · DAY · attach SELL STP 4.80"
    ids = {c.id: c.ok for c in t.checks}
    assert ids["stop_pct"] is True and ids["price"] is True and ids["spread"] is True


def test_the_ticket_carries_the_runners_refusals_as_checks():
    t = OM.ticket("TINY", 3.00, 2.97, 20.0, session="regular", bid=2.98, ask=3.00)
    checks = {c.id: c for c in t.checks}
    assert checks["stop_pct"].ok is False and "A13" in checks["stop_pct"].rule      # 1.0% < 2%
    assert checks["spread"].ok is False and "A6" in checks["spread"].rule           # 0.03 < 4 x 0.02
    unknown = OM.ticket("NOQ", 3.00, 2.70, 20.0, session="regular")
    assert {c.id: c.ok for c in unknown.checks}["spread"] is None, "no quote is unknown, never a pass"


def test_the_account_bounds_the_size_and_says_so():
    t = OM.ticket("ABCD", 10.00, 9.90, 100.0, session="regular", max_notional=2000.0)
    assert t.bound_by == "funds" and t.shares == 200
    assert {c.id: c.ok for c in t.checks}["funds"] is False


def test_a_premarket_ticket_says_ibkr_holds_no_stop():
    t = OM.ticket("PRE", 4.00, 3.80, 20.0, session="premarket", bid=3.98, ask=4.00)
    assert "outside RTH" in t.order_line and "no stop leg" in t.order_line
    assert "2109" in t.exit_text and "SELL LMT at bid" in t.exit_text


def test_the_honest_stop_and_the_halt_band():
    """tape.py: the median 1-minute range is the smallest stop the tape honours;
    FILTERS.md: the prior close sets the LULD band."""
    assert OM.halt_band_pct(2.00) == 20.0 and OM.halt_band_pct(5.00) == 10.0
    assert OM.halt_band_pct(0.50) == 30.0 and OM.halt_band_pct(None) is None
    t = OM.ticket("NOISE", 5.00, 4.90, 20.0, session="regular", ranges=[0.15] * 30, prev_close=4.0)
    checks = {c.id: c for c in t.checks}
    assert checks["noise"].ok is False and "0.15" in checks["noise"].value
    halting = OM.ticket("HALT", 5.00, 4.40, 20.0, session="regular", prev_close=4.0, halts_today=2)
    assert {c.id: c.ok for c in halting.checks}["halt"] is False


def test_a_manual_position_trails_like_the_bot():
    p = OM.position(5.00, 4.80, 100, high_since=5.50, last=5.35)
    assert p.trail == 5.30 and p.target_2r == 5.40 and p.r_now == 1.75 and p.breach is None
    assert OM.position(5.00, 4.80, 100, 5.50, 5.25).breach == "trail"
    assert OM.position(5.00, 4.80, 100, 5.10, 4.75).breach == "stop"
    assert OM.position(5.00, 4.80, 100, 5.45, 5.42).breach == "2R"


# ------------------------------------------------------------ the catalyst
NOW = datetime(2026, 10, 7, 12, 30, tzinfo=timezone.utc)          # 08:30 ET


def _item(h, pub, cat="", shared=False):
    return {"headline": h, "publishedAt": pub, "firstObservedAt": pub, "category": cat, "sharedTag": shared}


def test_whole_words_only():
    assert classify("Window maker posts record quarter").grade == "soft"
    assert classify("Company treats a rare disorder").grade == "soft"
    assert classify("ABCD (Nasdaq: ABCD) announces FDA approval").grade == "hard"
    assert classify("Dow Tumbles 600 Points").grade == "roundup"
    assert classify("XYZ receives orders worth $5M").grade == "hard"


def test_an_unread_filing_is_not_news():
    """A 6-K became the headline 'SEC 6-K · 6-K', graded WEAK and passed the
    news pillar. What the desk could not read is a filing to open."""
    assert classify("SEC 6-K · 6-K", "sec_filing").grade == "filing"
    assert classify("SEC 8-K · Item 8.01 other events", "sec_filing").grade == "filing"
    assert classify("SEC 8-K · Item 2.02 results of operations (earnings)", "sec_filing").grade == "hard"
    from momentum_platform.dashboard import session_builder as SB
    assert SB._catalyst_today([{"publishedAt": "2026-10-07T11:00:00Z", "headline": "SEC 6-K · 6-K",
                                "category": "sec_filing"}], "2026-10-07") is False


def test_the_cutoff_is_the_previous_trading_days_close():
    assert news_cutoff("2026-10-08").isoformat() == "2026-10-07T16:00:00-04:00"
    assert news_cutoff("2026-10-12").isoformat() == "2026-10-09T16:00:00-04:00"      # Monday -> Friday
    assert news_cutoff("2026-09-08").isoformat() == "2026-09-04T16:00:00-04:00"      # after Labor Day


@pytest.mark.parametrize("items,grade,typ,rule", [
    ([_item("ABCD receives FDA approval for X", "2026-10-07T11:02:00Z")], "STRONG", "FDA", "C3"),
    ([_item("ABCD announces partnership with Big Co", "2026-10-07T11:02:00Z")], "MODERATE", "partnership", "C4"),
    ([_item("ABCD to present at investor conference", "2026-10-07T11:02:00Z")], "WEAK", "PR", "C5"),
    ([_item("ABCD wins $40M contract", "2026-10-06T14:00:00Z")], "MODERATE", "contract", "C8"),
    ([_item("ABCD wins $40M contract", "2026-10-06T21:00:00Z")], "STRONG", "contract", "C3"),
    ([_item("ABCD wins $40M contract", "2026-10-02T14:00:00Z")], "WEAK", "none found", "C5"),
    ([_item("ABCD agrees to be acquired by DEF for $5.00", "2026-10-07T11:00:00Z")], "WEAK", "deal", "C7"),
    ([_item("ABCD prices $5M registered direct offering", "2026-10-07T12:00:00Z")], "WEAK", "offering/dilution", "C6"),
    ([_item("SEC 6-K · 6-K", "2026-10-07T11:00:00Z", "sec_filing")], "WEAK", "filing", "C9"),
    ([_item("Why Is ABCD Stock Soaring Today?", "2026-10-07T12:10:00Z")], "WEAK", "none found", "C5"),
    ([_item("ABCD receives FDA approval", "2026-10-07T11:00:00Z", shared=True)], "WEAK", "none found", "C5"),
    ([], "WEAK", "none found", "C5"),
])
def test_the_grade_rules(items, grade, typ, rule):
    r = card_read(items, now=NOW, trading_date="2026-10-07")
    assert (r["grade"], r["type"], r["rule"]) == (grade, typ, rule), r


def test_dilution_is_a_flag_beside_the_best_catalyst():
    """LPCN 2026-10-07 read DILUTIVE at 07:26 and STRONG at 07:54 because the
    word followed the newest headline. Both facts stand now: the grade comes
    from the best catalyst and the dilution is a red flag next to it."""
    items = [_item("ABCD prices $5M registered direct offering", "2026-10-07T12:00:00Z"),
             _item("ABCD receives FDA approval", "2026-10-07T11:00:00Z")]
    r = card_read(items, now=NOW, trading_date="2026-10-07", filings_checked=True,
                  filings=[{"form": "424B5", "age_days": 3, "filed": "2026-10-04"},
                           {"form": "S-3", "age_days": 200, "filed": "2026-03-21"}])
    assert r["grade"] == "STRONG"
    flags = {f["id"]: f for f in r["flags"]}
    assert flags["dilution_news"]["level"] == "bad"
    assert flags["takedown"]["level"] == "bad" and "3 d ago" in flags["takedown"]["text"]
    assert flags["shelf"]["level"] == "warn"


def test_an_old_takedown_is_history_not_a_sale_now():
    r = card_read([], now=NOW, trading_date="2026-10-07", filings_checked=True,
                  filings=[{"form": "424B4", "age_days": 80, "filed": "2026-07-19"}])
    ids = {f["id"] for f in r["flags"]}
    assert "takedown_old" in ids and "takedown" not in ids


def test_foreign_issuers_are_flagged_as_the_dilution_blind_spot():
    r = card_read([], now=NOW, trading_date="2026-10-07", filings_checked=True,
                  filings=[{"form": "6-K", "age_days": 1, "filed": "2026-10-06"}])
    f = next(f for f in r["flags"] if f["id"] == "foreign_filer")
    assert "rule 7" in f["text"]


def test_the_split_test_is_reported_as_run_or_not():
    assert any(f["text"].startswith("split test not run") for f in card_read([], now=NOW)["flags"])
    assert any("not arithmetic" in f["text"] for f in card_read([], now=NOW, split_checked=True)["flags"])
    assert any("8-for-1" in f["text"] for f in card_read([], now=NOW, split_ratio=8)["flags"])


@pytest.mark.parametrize("items,source_ok,label,tone,words", [
    ([_item("ABCD receives FDA approval for X", "2026-10-07T11:02:00Z")], True, "STRONG", "ok",
     "FDA news, today 07:02 · pre-market — real company news"),
    ([_item("ABCD announces partnership with Big Co", "2026-10-07T11:02:00Z")], True, "SOME", "warn",
     "a partnership, today 07:02 · pre-market — news, but no hard numbers in it"),
    ([_item("ABCD wins $40M contract", "2026-10-06T14:00:00Z")], True, "SOME", "warn",
     "a contract from yesterday 10:00 — not today's news"),
    ([_item("ABCD to present at investor conference", "2026-10-07T11:02:00Z")], True, "WEAK", "bad",
     "a press release, today 07:02 · pre-market — no real news in it"),
    ([_item("ABCD agrees to be acquired by DEF for $5.00", "2026-10-07T11:00:00Z")], True, "WEAK", "bad",
     "a buyout, today 07:00 · pre-market — the price stays stuck near the deal price"),
    ([_item("ABCD prices $5M registered direct offering", "2026-10-07T12:00:00Z")], True, "WEAK", "bad",
     "a share offering, today 08:00 · pre-market — more shares for sale, not good news"),
    ([_item("SEC 6-K · 6-K", "2026-10-07T11:00:00Z", "sec_filing")], True, "WEAK", "bad",
     "an SEC filing, today 07:00 · pre-market — the desk can't read it: open it yourself"),
    ([_item("ABCD wins $40M contract", "2026-10-02T14:00:00Z")], True, "NONE", "bad",
     "no company news since Tuesday's close (the latest is 5 days old)"),
    ([], True, "NONE", "bad", "no company news since Tuesday's close"),
    ([], False, "?", "unk", "no news feed on this desk — check the news yourself"),
])
def test_the_news_reads_in_plain_words(items, source_ok, label, tone, words):
    """Owner, 2026-10-09: "make sure news catalyst is clearly displayed in
    simple words". The card's face reads `plain`: a label, a tone and one
    sentence — no rule ids, no grading jargon. The grade and the reason the
    fold shows are unchanged."""
    r = card_read(items, now=NOW, trading_date="2026-10-07", source_ok=source_ok)
    assert r["plain"] == {"label": label, "tone": tone, "text": words}, r["plain"]
    for jargon in ("C0", "C3", "C5", "quantifiable", "catalyst", "pillar", "momentum"):
        assert jargon not in r["plain"]["text"], jargon


def test_no_headline_feed_reads_unknown_never_weak():
    r = card_read([], now=NOW, trading_date="2026-10-07", source_ok=False)
    assert r["grade"] == "UNKNOWN" and r["rule"] == "C0"


def test_every_rule_id_in_the_code_is_written_down_with_its_origin():
    """knowledge-base/strategies/CATALYST.md is the rules file: every id the
    code can return or flag must be there, each with an origin line."""
    src = (ROOT / "src" / "momentum_platform" / "catalyst.py").read_text()
    ids = sorted(set(re.findall(r'"(C\d+)"', src)), key=lambda x: int(x[1:]))
    doc = (ROOT / "knowledge-base" / "strategies" / "CATALYST.md").read_text()
    for rid in ids:
        row = next((ln for ln in doc.splitlines() if ln.startswith(f"| {rid} ")), None)
        assert row is not None, f"{rid} is not in CATALYST.md"
        assert ("Approximation" in row) or ("Confirmed" in row) or ("CLAUDE.md" in row) or ("FILTERS.md" in row), row


# ------------------------------------------------------------ the verdict
def _bars(rows, start="2026-10-07T13:30:00Z"):
    t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
    return [[int((t0 + timedelta(minutes=i)).timestamp()), o, h, l, c, v] for i, (o, h, l, c, v) in enumerate(rows)]


def _det(bars, sym="ABCD"):
    d = FirstPullbackDetector()
    for b in bars:
        d.on_bar(Bar(symbol=sym, timeframe="1m", ts=datetime.fromtimestamp(b[0], timezone.utc),
                     open=b[1], high=b[2], low=b[3], close=b[4], volume=b[5]))
    return d


#: a push (two green bars, +6%) then a two-bar red pullback on lighter volume
PULLBACK = [(5.00, 5.05, 4.98, 5.04, 1000)] * 3 + [
    (5.04, 5.20, 5.03, 5.18, 9000), (5.18, 5.40, 5.17, 5.38, 9000),
    (5.38, 5.39, 5.25, 5.28, 3000), (5.28, 5.30, 5.20, 5.22, 2000)]


def _cascade(verdict="REVIEW", killed=None, **gates):
    base = {g: "PASS" for g in ("price", "float", "catalyst", "pillars", "rising", "split", "instrument",
                                "tick", "buyout", "vwap", "ema9", "macd")}
    base.update(gates)
    return {"verdict": verdict, "killedBy": killed, "planAllowed": killed is None and verdict != "STALE",
            "gates": [{"id": k, "label": k, "state": v, "value": "v", "reason": f"{k} reason"}
                      for k, v in base.items()]}


def _card(cascade, rows=PULLBACK, minute=None, **kw):
    bars = _bars(rows)
    now = datetime.fromtimestamp(bars[-1][0], timezone.utc) + timedelta(seconds=30)
    if minute:
        h, m = minute
        now = now.replace(hour=h + 4, minute=m)
    meta = {"metrics": {"last": rows[-1][3], "changePct": 30.0, "rvol": 8.0, "sessionHigh": max(r[1] for r in rows),
                        "volumeToday": 2e6}, "prevClose": 4.0}
    return build_card("ABCD", meta=meta, cascade=cascade, bars=bars, detector=_det(bars), now=now, risk=25.0,
                      risk_source="yours", **kw)


def test_a_clean_first_pullback_reads_review_with_the_trigger_as_the_level():
    c = _card(_cascade())
    v = c["verdict"]
    assert v["word"] == "REVIEW" and "first pullback, 2 bars on lighter volume" in v["reason"]
    assert v["level"] == 5.31 and "break of the" in v["levelLabel"]        # 5.30 high + 1c
    assert c["ticket"]["trigger"] == 5.31 and c["ticket"]["stop"] == 5.19
    assert c["ticket"]["shares"] > 0


def test_heavier_pullback_volume_is_a_wait_because_the_bot_refuses_it():
    rows = PULLBACK[:-2] + [(5.38, 5.39, 5.25, 5.28, 9500), (5.28, 5.30, 5.20, 5.22, 9900)]
    c = _card(_cascade(), rows)
    assert c["verdict"]["word"] == "WAIT" and "heavier" in c["verdict"]["reason"]


def test_a_red_chart_gate_names_its_level():
    c = _card(_cascade(verdict="WAIT", vwap="FAIL"))
    assert c["verdict"]["word"] == "WAIT" and c["verdict"]["reason"].startswith("below the VWAP")
    assert c["verdict"]["levelLabel"] == "reclaim the VWAP" and c["verdict"]["level"] is not None


def test_a_warming_macd_is_watch():
    c = _card(_cascade(verdict="WATCH", macd="UNKNOWN"))
    assert c["verdict"]["word"] == "WATCH" and "warming up" in c["verdict"]["reason"]


def test_a_kill_is_no_and_the_fade_kill_names_the_line_that_reopens_it():
    """SXTC 2026-10-07 08:12: REJECT '25.4% off 2.72' with the trigger at 2.02.
    The window reopens at 0.75 x 2.72 = 2.04; the card never said so."""
    rows = [(2.0, 2.72, 1.99, 2.0, 5000)] + [(2.0, 2.05, 1.98, 2.03, 3000)] * 3
    c = _card(_cascade(verdict="REJECT", killed="rising", rising="FAIL"), rows)
    assert c["verdict"]["word"] == "NO"
    assert c["verdict"]["level"] == 2.04 and c["verdict"]["levelLabel"] == "back above"
    assert c["ticket"] is None, "a killed name gets no order"


def test_the_clock_speaks_after_the_cascade():
    assert _card(_cascade(), minute=(11, 35))["verdict"]["word"] == "NO"
    assert "A8" in _card(_cascade(), minute=(11, 25))["verdict"]["reason"]
    assert _card(_cascade(), minute=(6, 50))["verdict"]["word"] == "WATCH"


def test_stale_and_halted_are_waits_and_stale_draws_no_order():
    stale = _card(_cascade(verdict="STALE"))
    assert stale["verdict"]["word"] == "WAIT" and stale["ticket"] is None
    halted = _card(_cascade(), halted=True)
    assert halted["verdict"]["word"] == "WAIT" and "halted" in halted["verdict"]["reason"]


def test_lamps_show_the_bots_thresholds_and_a_reason_only_when_red():
    c = _card(_cascade(verdict="WAIT", vwap="FAIL"))
    lamps = {l["id"]: l for l in c["lamps"]}
    assert lamps["price"]["rule"] == "$2–20" and lamps["price"]["why"] is None    # no kill sentence on a PASS
    assert lamps["vwap"]["state"] == "FAIL" and lamps["vwap"]["why"]
    assert "25% off the high" in lamps["rising"]["rule"]
    assert lamps["tape"]["state"] == "MANUAL_CONFIRMATION_REQUIRED"
    assert lamps["room"]["kind"] == "info"


def test_without_a_stated_risk_nothing_is_sized():
    bars = _bars(PULLBACK)
    c = build_card("ABCD", meta={"metrics": {"last": 5.22}}, cascade=_cascade(), bars=bars, detector=_det(bars),
                   now=datetime.fromtimestamp(bars[-1][0], timezone.utc))
    assert c["ticket"]["shares"] is None and "state your risk" in c["ticket"]["order_line"]


def test_the_last_plan_and_what_became_of_it():
    rows = PULLBACK + [(5.22, 5.35, 5.21, 5.34, 8000), (5.34, 5.60, 5.33, 5.58, 9000)]
    bars = _bars(rows)
    d = _det(bars)
    assert d.plans, "the break armed a plan"
    assert plan_outcome(d.plans[-1], bars).startswith("reached 2R")


def test_the_bots_answer_in_plain_words():
    assert "no ledger" in bot_line(None, False)["text"]
    assert "no plan" in bot_line(None, True)["text"]
    refused = bot_line({"outcome": "REFUSED", "ts_et": "2026-10-07T09:24:00-04:00",
                        "reasons": ["selective (A13): stop 0.9% of price, under 2%", "one position at a time"]}, True)
    assert refused["text"].startswith("bot refused the 09:24 plan: stop 0.9% of price — the bot needs ≥ 2% (A13)")
    assert "(+1 more)" in refused["text"] and refused["reasons"][0]["raw"].startswith("selective")
    taken = bot_line({"outcome": "TAKEN", "ts_et": "2026-10-07T07:26:00-04:00",
                      "order": {"fill_price": 3.31, "exit_price": 3.55, "exit_reason": "trail"}}, True)
    assert "out at 3.55 (trail)" in taken["text"]


# ------------------------------------------------------------ manual calls
def test_manual_calls_are_recorded_and_a_position_closes():
    c = L.connect(":memory:")
    at = datetime(2026, 10, 7, 13, 45, tzinfo=timezone.utc)
    L.record_manual(c, "abcd", "took", price=5.31, shares=80, stop=5.19, verdict="REVIEW", at=at)
    L.record_manual(c, "EFGH", "passed", verdict="WAIT", at=at)
    assert list(L.open_manual(c, "2026-10-07")) == ["ABCD"]
    L.record_manual(c, "ABCD", "closed", price=5.50, at=at + timedelta(minutes=9))
    assert L.open_manual(c, "2026-10-07") == {}
    assert [r["action"] for r in L.manual_rows(c, "2026-10-07")] == ["took", "passed", "closed"]
    with pytest.raises(ValueError):
        L.record_manual(c, "ABCD", "took", price=5.0, shares=10, stop=5.2)          # stop above the price
    with pytest.raises(ValueError):
        L.record_manual(c, "ABCD", "bought")


def test_the_bot_view_reads_the_runners_latest_decision():
    c = L.connect(":memory:")
    c.execute("""INSERT INTO decisions (decision_id, ts_et, session, symbol, source, verdict, plan_allowed,
                 gates_json, warnings_json, inputs_json, outcome, refusal_reasons_json, recorded_at)
                 VALUES ('d1','2026-10-07T09:24:00-04:00','regular','ABCD','pullback','REVIEW',1,'[]','[]','{}',
                 'REFUSED','["selective (A13): stop 0.9% of price, under 2%"]','x')""")
    v = L.bot_view(c, "ABCD", "2026-10-07")
    assert v["outcome"] == "REFUSED" and v["reasons"][0].startswith("selective")
    assert L.bot_view(c, "ABCD", "2026-10-08") is None


# ------------------------------------------------------------ the server
@pytest.fixture()
def fixture_server(monkeypatch):
    monkeypatch.delenv("JOURNAL_DB", raising=False)
    monkeypatch.delenv("DESK_KEY", raising=False)
    monkeypatch.delenv("DESK_VIEWER_KEY", raising=False)
    from momentum_platform.dashboard import server as SRV
    srv = ThreadingHTTPServer(("127.0.0.1", 0), SRV.make_handler(str(FIXTURE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _post(url, body, ctype="application/json"):
    req = Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": ctype})
    try:
        with urlopen(req) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def test_the_session_ships_a_card_for_every_symbol(fixture_server):
    with urlopen(fixture_server + "/api/v1/replay/session") as r:
        s = json.loads(r.read())
    assert set(s["cards"]) == set(s["symbols"])
    for card in s["cards"].values():
        assert card["verdict"]["word"] in ("REVIEW", "WATCH", "WAIT", "NO")
        assert card["catalyst"]["grade"] in ("STRONG", "MODERATE", "WEAK", "UNKNOWN")
        assert "no ledger" in card["bot"]["text"]


def test_the_buttons_record_and_the_card_follows(fixture_server):
    st, j = _post(fixture_server + "/api/v1/settings", {"risk": 25})
    assert st == 200 and j["saved"] is False                      # a replay desk keeps nothing
    st, j = _post(fixture_server + "/api/v1/manual",
                  {"symbol": "ABCD", "action": "took", "price": 7.21, "shares": 100, "stop": 7.05})
    assert st == 200 and "nothing is saved" in j["note"]
    with urlopen(fixture_server + "/api/v1/replay/session") as r:
        card = json.loads(r.read())["cards"]["ABCD"]
    assert card["position"]["entry"] == 7.21 and card["position"]["trail"] >= 7.05
    assert card["manual"]["action"] == "took" and card["risk"] == {"dollars": 25.0, "source": "yours"}
    assert "no ledger" in card["bot"]["text"], "a replay's in-memory ledger never saw the bot"
    st, j = _post(fixture_server + "/api/v1/manual", {"symbol": "ABCD", "action": "took", "price": 7.0,
                                                       "shares": 10, "stop": 7.5})
    assert st == 400


def test_a_post_must_be_json_and_a_viewer_cannot_record(fixture_server, monkeypatch):
    st, _ = _post(fixture_server + "/api/v1/manual", {"symbol": "ABCD", "action": "passed"}, ctype="text/plain")
    assert st == 415, "a cross-site form cannot post into the ledger"
    monkeypatch.setenv("DESK_KEY", "own")
    monkeypatch.setenv("DESK_VIEWER_KEY", "see")
    st, j = _post(fixture_server + "/api/v1/manual?key=see", {"symbol": "ABCD", "action": "passed"})
    assert st == 403 and "views the desk" in j["error"]


def test_a_journalled_desk_writes_the_call_to_its_ledger(tmp_path, monkeypatch):
    db = tmp_path / "j.sqlite"
    monkeypatch.setenv("JOURNAL_DB", str(db))
    from momentum_platform.dashboard import server as SRV

    class Holder:
        symbols, hub = [], object()                # a live desk: rebuilds on its own
        def current(self):
            return {"cards": {}}
    body, status = SRV._manual_post(Holder(), {"symbol": "ZZZ", "action": "passed"})
    assert status == 200 and body["saved"] is True
    assert L.manual_rows(L.connect(db))[0]["symbol"] == "ZZZ"


def test_the_live_tick_carries_only_the_cards_that_changed():
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    desk = IbkrDesk.__new__(IbkrDesk)
    a = {"ABCD": {"verdict": {"word": "WAIT"}, "asOf": "t1"}}
    assert desk._changed_cards(a) == a
    assert desk._changed_cards({"ABCD": {"verdict": {"word": "WAIT"}, "asOf": "t2"}}) == {}
    b = {"ABCD": {"verdict": {"word": "REVIEW"}, "asOf": "t3"}}
    assert desk._changed_cards(b) == b


def test_a_hand_order_is_sized_on_the_owners_risk_or_not_at_all(tmp_path):
    """Owner, 2026-10-08: no fallback to the bot's paper risk. With only the
    exercise's dollar risk in the ledger, the card sizes nothing; once the
    owner states a figure, that figure sizes it."""
    from momentum_platform.dashboard import cards as C
    conn = L.connect(tmp_path / "j.sqlite")
    L.set_state(conn, dollar_risk=40.0, account_size=2000.0)
    assert C._risk(conn) == (None, None, 2000.0), "the bot's risk never sizes a hand order"
    L.set_setting(conn, C.RISK_KEY, 25)
    assert C._risk(conn) == (25.0, "yours", 2000.0)
