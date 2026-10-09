"""The shadow strategies (2026-10-09, research/month-study/REPORT.md): S6 the
best found, S3 its robust core — judged on a plan's own numbers, scored like
the bot's fill with a break-even exit, logged, never traded."""
from __future__ import annotations

import csv
import json
import sys
from datetime import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from momentum_platform.shadow import judge, levers  # noqa: E402


def _v(**kw):
    base = {"trigger": 5.00, "stop": 4.80, "armed": time(9, 45), "last": 5.00, "vwap": 4.90, "hod": 5.20,
            "volume_ok": True}
    base.update(kw)
    return base


def test_s6_takes_a_plan_only_when_all_six_levers_pass_and_s3_needs_three():
    j = {x["id"]: x for x in judge(_v())}
    assert j["S6"]["takes"] and j["S3"]["takes"]
    tight = {x["id"]: x for x in judge(_v(stop=4.90))}                    # a 2 % stop
    assert not tight["S6"]["takes"] and not tight["S3"]["takes"] and "stop ≥ 3 %" in tight["S3"]["failed"]
    below = {x["id"]: x for x in judge(_v(vwap=5.10))}
    assert not below["S6"]["takes"] and below["S3"]["takes"] and below["S6"]["failed"] == ["above VWAP"]
    early = {x["id"]: x for x in judge(_v(armed=time(8, 15)))}
    assert not early["S3"]["takes"], "S3 arms in regular hours only"
    late = {x["id"]: x for x in judge(_v(armed=time(11, 20)))}
    assert not late["S3"]["takes"], "11:20 is the bot's entry cutoff"
    assert levers(**_v(last=3.80))["rising"] is False                        # 27 % off the 5.20 high
    assert levers(**_v(volume_ok=None))["pullback"] is None


def test_the_card_carries_the_shadow_judgement():
    from datetime import datetime, timedelta, timezone
    from momentum_platform.decision_card import build_card
    from momentum_platform.pullback import FirstPullbackDetector
    card = build_card("ABCD", meta={"metrics": {"last": 5.0}}, cascade={}, bars=[], detector=FirstPullbackDetector(),
                      now=datetime(2026, 10, 9, 14, 0, tzinfo=timezone.utc))
    assert card["shadow"] == [], "no plan, nothing to judge"


def test_the_record_scores_the_desk_decisions_like_the_bots_fill(tmp_path):
    import shadow_record as SR
    d = tmp_path / "2026-10-09"; d.mkdir()
    dec = {"decision_id": "x1", "ts_et": "2026-10-09T09:45:00-04:00", "session": "regular", "symbol": "ABCD",
           "last": "5.00", "session_high": "5.20", "trigger": "5.00", "stop": "4.80", "volume_ok": "1",
           "chart_json": json.dumps({"vwap": 4.9}), "outcome": "REFUSED", "data_status": "LIVE"}
    with (d / "decisions.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dec)); w.writeheader(); w.writerow(dec)
    bars = [("2026-10-09T13:45:00Z", 4.98, 5.00, 4.95, 4.99, 9000),       # the arming minute
            ("2026-10-09T13:46:00Z", 4.99, 5.05, 4.98, 5.04, 12000),      # touches 5.00: filled
            ("2026-10-09T13:47:00Z", 5.04, 5.25, 5.03, 5.22, 15000),      # +1 R reached: stop to break-even
            ("2026-10-09T13:48:00Z", 5.22, 5.45, 5.20, 5.40, 15000)]      # 2 R = 5.40: target
    with (d / "bars.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["symbol", "ts", "open", "high", "low", "close", "volume"])
        for b in bars:
            w.writerow(["ABCD", *b])
    rows = SR.record(tmp_path, "2026-10-09")
    assert {r["strategy"] for r in rows} == {"S6", "S3"}
    r = rows[0]
    assert r["filled"] and r["exit"] == "target" and r["r_gross"] == 2.0 and r["r_net"] < 2.0
    lines = SR.summary(rows)
    assert lines[0].startswith("S6 (best found): 1 plans taken, 1 filled")
