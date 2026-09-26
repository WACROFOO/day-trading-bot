"""The edge hunt's guards: engine semantics, costs, the holdout ledger, and
look-ahead (truncating the future changes nothing up to the decision)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

from edge_hunt import costs as C  # noqa: E402
from edge_hunt import engine as G  # noqa: E402
from edge_hunt import features as F  # noqa: E402
from edge_hunt import protocol as P  # noqa: E402
from edge_hunt.data import ET, minute, split_of  # noqa: E402


def arr(rows):
    a = np.array(rows, float)
    return a[:, 0].astype(np.int64), a[:, 1], a[:, 2], a[:, 3], a[:, 4]


# ------------------------------------------------------------------ engine
def test_stop_first_and_gap_through_fills_at_open():
    m, o, h, l, c = arr([[330, 10.0, 10.1, 9.95, 10.0], [331, 9.80, 9.85, 9.70, 9.75]])
    r, n, k, why, stopish = G.simulate(m, o, h, l, c, 0, 10.0, 10.0, 9.90, G.spec(trail=1.0))
    assert why == G.R_STOP and k == 1 and stopish == 1
    assert r == pytest.approx((9.80 - 10.0) / 0.10)          # the bar opened through the stop


def test_target_and_flatten():
    m, o, h, l, c = arr([[330, 10.0, 10.05, 9.95, 10.0], [331, 10.0, 10.25, 9.99, 10.2]])
    r, n, k, why, s = G.simulate(m, o, h, l, c, 0, 10.0, 10.0, 9.90, G.spec(target=2.0))
    assert why == G.R_TARGET and r == pytest.approx(2.0) and s == 0
    m, o, h, l, c = arr([[449, 10.0, 10.05, 9.95, 10.0], [450, 10.03, 10.04, 10.0, 10.02]])
    r, n, k, why, s = G.simulate(m, o, h, l, c, 0, 10.0, 10.0, 9.90, G.spec(trail=1.0, flat_min=450))
    assert why == G.R_FLAT and r == pytest.approx(0.3)


def test_trail_moves_only_for_the_next_bar():
    # bar 0 makes +2R; the trail (1R) is 10.10 from bar 1 on; bar 1 low 10.05 stops at 10.10
    m, o, h, l, c = arr([[330, 10.0, 10.20, 9.95, 10.15], [331, 10.15, 10.16, 10.05, 10.06]])
    r, n, k, why, s = G.simulate(m, o, h, l, c, 0, 10.0, 10.0, 9.90, G.spec(trail=1.0))
    assert k == 1 and r == pytest.approx(1.0)


def test_stop_limit_fill_rules():
    m, o, h, l, c = arr([[1, 9.9, 10.0, 9.8, 9.95], [2, 9.95, 10.02, 9.9, 10.0]])
    assert G.stop_limit_fill(m, o, h, l, 1, 10.0, 3, 0.003, 0.01) == (1, 10.0, 0)
    m, o, h, l, c = arr([[1, 9.9, 9.95, 9.8, 9.9], [2, 10.02, 10.05, 10.0, 10.04]])
    assert G.stop_limit_fill(m, o, h, l, 1, 10.0, 3, 0.003, 0.01) == (1, 10.02, 0)     # opened inside the cap
    m, o, h, l, c = arr([[1, 9.9, 9.95, 9.8, 9.9], [2, 10.20, 10.30, 10.15, 10.25], [3, 10.2, 10.2, 10.02, 10.1]])
    k, px, capf = G.stop_limit_fill(m, o, h, l, 1, 10.0, 3, 0.003, 0.01)
    assert k == 2 and px == pytest.approx(10.03) and capf == 1                          # back to the cap
    m, o, h, l, c = arr([[1, 9.9, 9.95, 9.8, 9.9], [2, 10.20, 10.30, 10.15, 10.25], [3, 10.01, 10.1, 10.0, 10.1]])
    k, px, capf = G.stop_limit_fill(m, o, h, l, 1, 10.0, 3, 0.003, 0.01)
    assert k == 2 and px == pytest.approx(10.01) and capf == 1                          # a later open under the cap fills there
    m, o, h, l, c = arr([[1, 9.9, 9.95, 9.8, 9.9], [2, 10.20, 10.30, 10.15, 10.25], [3, 10.3, 10.4, 10.2, 10.3]])
    assert G.stop_limit_fill(m, o, h, l, 1, 10.0, 3, 0.003, 0.01)[0] == -2              # never back: no fill


def test_stop_limit_ttl_is_minutes_not_bars():
    # sparse pre-market bars: armed at 08:01, the next bars print at 08:02 and 08:20; the TTL is 3 minutes
    m, o, h, l, c = arr([[241, 9.9, 9.95, 9.8, 9.9], [242, 9.9, 9.95, 9.85, 9.9], [260, 10.0, 10.1, 9.99, 10.05]])
    assert G.stop_limit_fill(m, o, h, l, 1, 10.0, 3, 0.003, 0.01)[0] == -1


def test_fill_bar_stop_fills_at_the_stop_not_the_earlier_open():
    # the fill bar opened at 9.85 (below the 9.90 stop), rose through 10.00 (fill), fell back to 9.80
    m, o, h, l, c = arr([[330, 9.85, 10.05, 9.80, 9.82]])
    r, n, k, why, s = G.simulate(m, o, h, l, c, 0, 10.0, 10.0, 9.90, G.spec(trail=1.0))
    assert why == G.R_STOP and r == pytest.approx(-1.0)


def test_cap_return_fill_earns_no_fill_bar_high():
    # filled on a return to the cap; the bar's 10.30 high printed before the fill: no 2R target on that bar
    m, o, h, l, c = arr([[330, 10.20, 10.30, 10.03, 10.10], [331, 10.10, 10.12, 10.05, 10.08]])
    r, n, k, why, s = G.simulate(m, o, h, l, c, 0, 10.03, 10.0, 9.90, G.spec(target=2.0), False)
    assert why != G.R_TARGET
    r2, *_ = G.simulate(m, o, h, l, c, 0, 10.03, 10.0, 9.90, G.spec(target=2.0), True)
    assert r2 == pytest.approx((10.20 - 10.03) / 0.10)


def test_random_baseline_is_deterministic_and_window_bound():
    rng = np.random.default_rng(1)
    n = 200
    mins = np.arange(300, 300 + n)
    px = 10 + np.cumsum(rng.normal(0, 0.02, n))
    o, c = px, px + rng.normal(0, 0.01, n)
    h, l = np.maximum(o, c) + 0.02, np.minimum(o, c) - 0.02
    a = G.random_entries(mins, o, h, l, c, 350, 360, 0.02, G.spec(trail=1.0), 30, 7)
    b = G.random_entries(mins, o, h, l, c, 350, 360, 0.02, G.spec(trail=1.0), 30, 7)
    assert np.allclose(a[0], b[0], equal_nan=True)
    fills = a[3][~np.isnan(a[3])]
    allowed = set(np.round(o[(mins >= 350) & (mins < 360)], 8))
    assert fills.size and set(np.round(fills, 8)) <= allowed


# ------------------------------------------------------------------ costs
def test_commissions():
    assert C.commission(100, 10.0, "fixed") == pytest.approx(1.0)                   # the $1 minimum
    assert C.commission(400, 10.0, "fixed") == pytest.approx(2.0)
    assert C.commission(100, 10.0, "tiered") == pytest.approx(0.35 + 0.32)
    assert C.commission(100, 10.0, "tiered", sell=True) == pytest.approx(0.35 + 0.32 + 0.0166)


def test_cost_models_prereg_light_old():
    args = ([10.0], [9.9], [10.0], [9.9], [1], [1], [0.02], [0.02])
    assert C.cost_r_vec(*args)[0] == pytest.approx((2.0 + 200 * 0.03 * 2) / 20.0)                    # hs + 1c
    assert C.cost_r_vec(*args, model="light")[0] == pytest.approx((2.0 + 200 * 0.02 * 2) / 20.0)     # max(hs, 1c)
    assert C.cost_r_vec(*args, model="old")[0] == pytest.approx((2.0 + 200 * 0.01 * 2) / 20.0)       # 1c
    tight = ([10.0], [9.9], [10.0], [9.9], [1], [1], [0.004], [0.004])
    assert C.cost_r_vec(*tight, model="light")[0] == pytest.approx((2.0 + 200 * 0.01 * 2) / 20.0)


def test_holdout_rows_need_the_ledger(monkeypatch):
    from edge_hunt import families as FM
    df = pd.DataFrame({"split": ["train", "holdout"], "x": [1, 2]})
    monkeypatch.setattr(FM.P, "opened", lambda fam, path=None: None)
    assert len(FM.Ctx.frame(None, df, "train", "F1-selection")) == 1
    with pytest.raises(FM.HoldoutClosed):
        FM.Ctx.frame(None, df, "holdout", "F1-selection")
    monkeypatch.setattr(FM.P, "opened", lambda fam, path=None: {"family": fam})
    assert len(FM.Ctx.frame(None, df, "holdout", "F1-selection")) == 1


def test_cost_r_hand_computed():
    # 10c stop at $20 risk = 200 shares; fixed: $1 in + $1 out; half-spread 2c + 1c slip, two marketable sides
    r = C.cost_r(10.0, 9.9, 10.0, 9.9, 1, True, half_spread=0.02)
    assert r == pytest.approx((1.0 + 1.0 + 200 * 0.03 * 2) / 20.0)
    # a resting target pays the spread on entry only
    r = C.cost_r(10.0, 9.9, 10.0, 10.2, 1, False, half_spread=0.02)
    assert r == pytest.approx((1.0 + 1.0 + 200 * 0.03) / 20.0)


# ------------------------------------------------------------------ protocol
def test_holdout_opens_once(tmp_path):
    led = tmp_path / "ledger.jsonl"
    e = P.open_holdout("F1-selection", {"a": 1}, 69, {"mean": 0.1}, {"mean": 0.05}, path=led)
    assert e["family"] == "F1-selection" and led.exists()
    with pytest.raises(P.HoldoutAlreadyOpened):
        P.open_holdout("F1-selection", {"a": 2}, 69, {}, {}, path=led)
    with pytest.raises(ValueError):
        P.open_holdout("F9-invented", {}, 1, {}, {}, path=led)
    P.open_holdout("F2-premarket", {"b": 1}, 216, {}, {}, path=led)                # another family is fine


def test_split_boundaries():
    assert split_of("2022-12-30") == "train" and split_of("2023-01-03") == "valid"
    assert split_of("2023-12-29") == "valid" and split_of("2024-01-02") == "holdout"


def test_adoption_rule_needs_all_five():
    days = np.repeat([f"2024-0{m}-1{d}" for m in range(1, 10) for d in range(0, 9)], 3)
    days = np.array([d.replace("2024-0", "2025-0") if i % 3 == 1 else d for i, d in enumerate(days)])
    good = np.full(len(days), 0.5)
    res = P.adoption(good, days, random_diff=np.full(len(days), 0.3))
    assert res["checks"]["1 positive net mean"] and res["checks"]["3 at least 200 trades"]
    assert res["adopted"]
    res = P.adoption(good[:150], days[:150], random_diff=np.full(150, 0.3))
    assert not res["adopted"] and not res["checks"]["3 at least 200 trades"]
    res = P.adoption(good, days, random_diff=np.full(len(days), -0.1))
    assert not res["adopted"]
    assert P.corrected_alpha() == pytest.approx(0.05 / 2 / 6)


def test_one_position_skips_overlaps():
    t = [{"day": "d", "fill_min": 10, "exit_min": 20, "sym": "A"},
         {"day": "d", "fill_min": 15, "exit_min": 25, "sym": "B"},
         {"day": "d", "fill_min": 21, "exit_min": 30, "sym": "C"},
         {"day": "e", "fill_min": 5, "exit_min": 9, "sym": "D"}]
    assert [x["sym"] for x in P.one_position(t)] == ["A", "C", "D"]


# ------------------------------------------------------------------ look-ahead
class FakeStore:
    def __init__(self, days_bars: list[tuple[str, str, float, np.ndarray, np.ndarray]]):
        rows, mins, ohlcv, pos = [], [], [], 0
        for day, sym, pc, m, a in days_bars:
            rows.append({"day": day, "sym": sym, "prev_close": pc, "open_px": a[0, 0], "gap_pct": 0.0,
                         "dv20": 1e6, "start": pos, "end": pos + len(m)})
            mins.append(m); ohlcv.append(a); pos += len(m)
        self.sd = pd.DataFrame(rows)
        self.minute = np.concatenate(mins); self.ohlcv = np.concatenate(ohlcv)

    def bars(self, i):
        r = self.sd.iloc[i]
        return self.minute[r["start"]:r["end"]], self.ohlcv[r["start"]:r["end"]]


def synth(n=300, seed=3, start=150, base=5.0):
    rng = np.random.default_rng(seed)
    m = np.arange(start, start + n, dtype=np.int16)
    px = base * np.exp(np.cumsum(rng.normal(0.001, 0.01, n)))
    o = px; c = px * (1 + rng.normal(0, 0.004, n))
    h = np.maximum(o, c) * 1.003; l = np.minimum(o, c) * 0.997
    v = rng.integers(1_000, 50_000, n).astype(float)
    return m, np.column_stack([o, h, l, c, v])


def test_features_do_not_see_past_the_decision_minute(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "NEWS", tmp_path / "news"); monkeypatch.setattr(F, "SEC", tmp_path / "sec")
    m, a = synth()
    m2, a2 = synth(seed=4)
    t = int(m[120])
    full = FakeStore([("2024-03-05", "AAA", 4.5, m, a), ("2024-03-05", "BBB", 4.0, m2, a2)])
    cut = FakeStore([("2024-03-05", "AAA", 4.5, m[:121], a[:121]), ("2024-03-05", "BBB", 4.0, m2[m2 <= t], a2[m2 <= t])])
    plans = pd.DataFrame([{"sid": 0, "day": "2024-03-05", "sym": "AAA", "plan_min": t}])
    f_full = F.plan_features(full, F.Grid(full), plans)
    f_cut = F.plan_features(cut, F.Grid(cut), plans)
    pd.testing.assert_frame_equal(f_full, f_cut)


def test_desk_plans_do_not_change_when_the_future_is_cut():
    import backtest_recent as E
    m, a = synth(n=360, seed=11, start=180)
    base = datetime.fromisoformat("2024-03-05T04:00:00").replace(tzinfo=ET)
    rows = [(base + timedelta(minutes=int(mm)), *map(float, a[k])) for k, mm in enumerate(m)]
    full = E.plans_for_day("AAA", rows, 4.0, desk_vwap=True, gap_miss=True)
    k = 250
    cut = E.plans_for_day("AAA", rows[:k], 4.0, desk_vwap=True, gap_miss=True)
    key = lambda p: (p["t"], p["entry"], p["stop"], tuple(p["red"]), p["pb_index"])  # noqa: E731
    early_full = [key(p) for p in full if p["ts"] < rows[k - 1][0]]
    early_cut = [key(p) for p in cut if p["ts"] < rows[k - 1][0]]
    assert early_full == early_cut


def test_news_counts_only_headlines_before_the_decision(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "NEWS", tmp_path)
    (tmp_path / "2024-03-05.json").write_text(json.dumps([
        {"t": "2024-03-05T12:00:00Z", "s": ["AAA"]},                 # 07:00 ET
        {"t": "2024-03-05T14:45:00Z", "s": ["AAA"]}]))                # 09:45 ET
    n = F.News()
    since = F._utc("2024-03-04", minute(16, 0))
    assert n.count("2024-03-05", "AAA", since, F._utc("2024-03-05", minute(9, 30))) == 1
    assert n.count("2024-03-05", "AAA", since, F._utc("2024-03-05", minute(9, 46))) == 2


def test_shares_outstanding_must_be_filed_before_the_day(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "SEC", tmp_path)
    (tmp_path / "AAA.json").write_text(json.dumps({"rows": [
        {"c": "dei", "end": "2023-12-31", "val": 8_000_000, "filed": "2024-02-01"},
        {"c": "dei", "end": "2024-02-29", "val": 30_000_000, "filed": "2024-03-05"}]}))
    s = F.Shares()
    assert s.at("AAA", "2024-03-05") == 8_000_000                     # filed ON the day: not yet known
    assert s.at("AAA", "2024-03-06") == 30_000_000
    assert s.at("AAA", "2023-01-01") is None


def test_former_runner_reads_earlier_sessions_only():
    m, a = synth(n=100)
    a_run = a.copy(); a_run[:, 1] *= 1.0; a_run[50, 1] = 4.0 * 1.8     # +80 % intraday
    st = FakeStore([("2024-03-04", "AAA", 4.0, m, a_run), ("2024-03-05", "AAA", 4.0, m, a),
                    ("2024-03-04", "BBB", 4.0, m, a)])
    fr = F.former_runner(st, F.Grid(st))
    assert list(fr) == [False, True, False]


def test_reverse_split_days_are_not_gappers():
    """The universe's split flag never fires; a reverse split shows as a clean integer
    ratio and a pre-split previous close (FRO 2016-02-03, 1-for-5): a fake 415 % gap."""
    from edge_hunt.data import universe_rows
    import backtest_history as H
    assert "FRO" not in universe_rows().get("2016-02-03", {})
    assert "FRO" not in H.load_universe("2016-02-03", "2016-02-03").get("2016-02-03", {})
