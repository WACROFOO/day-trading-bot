"""The strategy candidates' guards (research/strategy-candidates/PREREGISTRATION.md):
the exit engine against the edge hunt's, the short side as the mirror of the long, costs
against the month study's live model, look-ahead in every entry rule, the holdout
ledger, the registry count, the portfolio, the choice-on-train-only, the adoption rule."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

from candidates import data as D  # noqa: E402
from candidates import diagnose as G  # noqa: E402
from candidates import protocol as P  # noqa: E402
from candidates import rules as R  # noqa: E402
from candidates import sim as S  # noqa: E402
from candidates.data import SymbolDay, minute  # noqa: E402


def sday(rows, pc=10.0, open_px=None, day="2022-03-01", split="train", dv20=None):
    sd = SymbolDay(day, "TEST", pc, open_px, dv20, split)
    for mm, o, h, l, c, v in rows:
        sd.m.append(mm); sd.o.append(o); sd.h.append(h); sd.l.append(l); sd.c.append(c); sd.v.append(v)
    return sd


def walk(seed, n=200, start=10.0, m0=330, vol=0.004):
    rnd = random.Random(seed)
    rows, px = [], start
    for i in range(n):
        o = px * (1 + rnd.gauss(0, vol / 3))
        c = o * (1 + rnd.gauss(0, vol))
        h = max(o, c) * (1 + abs(rnd.gauss(0, vol / 2)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, vol / 2)))
        rows.append((m0 + i, o, h, l, c, rnd.randint(1_000, 50_000)))
        px = c
    return rows


def gapper(seed, pc=10.0, gap=0.30, spike=0.18, fade=0.22, pm_vol=12_000):
    """A synthetic gapper: pre-market climb to the gap, a spike after the open, a fade."""
    rnd = random.Random(seed)
    rows, px = [], pc * 1.08
    for mm in range(0, 720):
        if mm < 330:
            target, vol, sh = pc * (1 + gap * (0.4 + 0.6 * mm / 330)), 0.003, pm_vol
        elif mm < 350:
            target, vol, sh = pc * (1 + gap + spike * (mm - 330) / 20), 0.006, 60_000
        elif mm < 480:
            target, vol, sh = pc * (1 + gap + spike - (spike + fade) * (mm - 350) / 130), 0.006, 40_000
        else:
            target, vol, sh = px, 0.004, 15_000
        o = px * (1 + rnd.gauss(0, vol / 3))
        c = o + (target - o) * 0.3 + o * rnd.gauss(0, vol)
        h = max(o, c) * (1 + abs(rnd.gauss(0, vol / 2)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, vol / 2)))
        rows.append((mm, o, h, l, c, sh * rnd.uniform(0.5, 1.5)))
        px = c
    first = next(r for r in rows if r[0] >= 330)
    return sday(rows, pc=pc, open_px=first[1])


# ------------------------------------------------------------------ the exit engine
def test_the_long_manager_matches_the_edge_hunt_engine_bar_for_bar():
    from edge_hunt import engine as EG
    specs = {"trail1": EG.spec(trail=1.0, flat_min=450), "fixed2": EG.spec(target=2.0, flat_min=450),
             "newlow": EG.spec(newlow=True, flat_min=450)}
    checked = 0
    for seed in range(150):
        rows = walk(seed, n=140, m0=330)
        m = np.array([r[0] for r in rows], np.int64)
        o, h, l, c = (np.array([r[j] for r in rows]) for j in (1, 2, 3, 4))
        k0 = 3
        for high_ok in (True, False):
            entry = o[k0] * (1.0 if high_ok else 0.997)
            fill = o[k0] if high_ok else entry + max(0.01, 0.003 * entry)
            stop = entry * (1 - 0.02 - 0.01 * (seed % 4))
            for name, sp in specs.items():
                r1, _, k1, _, _ = EG.simulate(m, o, h, l, c, k0, fill, entry, stop, sp, high_ok)
                r2, k2, *_ = S.manage(list(m), list(o), list(h), list(l), list(c), k0, fill, entry, stop,
                                      S.EXITS[name], 450, high_ok)
                assert k2 == k1 and r2 == pytest.approx(r1, abs=1e-9), (seed, name, high_ok)
                checked += 1
    assert checked == 900


def test_a_short_is_exactly_the_mirror_of_a_long():
    K = 40.0
    for seed in range(60):
        rows = walk(seed, n=150, start=12.0, m0=360)
        sd = sday(rows)
        mirror = sday([(mm, K - o, K - l, K - h, K - c, v) for mm, o, h, l, c, v in rows])
        k0 = 2
        entry = sd.o[k0]
        stop = entry * 1.05
        for ex in S.EXITS:
            a = S.run(sd, -1, k0, entry, entry, stop, ex, minute(15, 55))
            b = S.run(mirror, 1, k0, K - entry, K - entry, K - stop, ex, minute(15, 55))
            assert a[1] == b[1] and a[2] == b[2], (seed, ex)
            assert a[0] == pytest.approx(b[0], abs=1e-9) and a[4] == pytest.approx(b[4], abs=1e-9)
            assert a[3] == pytest.approx(K - b[3], abs=1e-9)


def test_short_target_gap_through_the_stop_and_the_vwap_exits():
    # short 10.00, stop 10.50: a bar trading down to 9.00 makes +2R on fixed2
    sd = sday([(400, 10.0, 10.1, 9.9, 10.0, 1e4), (401, 10.0, 10.2, 8.9, 9.0, 1e4), (402, 9.0, 9.1, 8.9, 9.0, 1e4)])
    r, k, why, px, *_ = S.run(sd, -1, 0, 10.0, 10.0, 10.5, "fixed2", minute(15, 55))
    assert why == "target" and r == pytest.approx(2.0) and k == 1
    # a bar opening at 10.80, through the stop: filled at that open, -1.6 R
    sd = sday([(400, 10.0, 10.1, 9.9, 10.0, 1e4), (401, 10.8, 10.9, 10.7, 10.8, 1e4)])
    r, k, why, px, *_ = S.run(sd, -1, 0, 10.0, 10.0, 10.5, "close", minute(15, 55))
    assert why == "stop" and px == pytest.approx(10.8) and r == pytest.approx(-1.6)
    # vwap_reclaim: a close back above VWAP covers at the NEXT open
    sd = sday([(400, 10.0, 10.0, 9.0, 9.2, 1e5), (401, 9.2, 9.3, 9.1, 9.2, 1e3), (402, 9.2, 10.3, 9.2, 10.2, 1e3),
               (403, 10.1, 10.2, 10.0, 10.1, 1e3)])
    assert sd.c[2] > sd.vwap[2]
    r, k, why, px, *_ = S.run(sd, -1, 1, 9.2, 9.2, 10.5, "vwap_reclaim", minute(15, 55))
    assert why == "cross" and k == 3 and px == pytest.approx(10.1)
    assert r == pytest.approx((9.2 - 10.1) / (10.5 - 9.2))
    # the same bar through a tighter stop: the stop is tested before any close-based exit
    assert S.run(sd, -1, 1, 9.2, 9.2, 9.7, "vwap_reclaim", minute(15, 55))[2] == "stop"
    # vwap: the buy-to-cover limit at the previous bar's VWAP; a bar opening under it fills at its open
    sd = sday([(400, 11.0, 11.0, 9.0, 9.4, 1e5), (401, 11.0, 11.1, 10.9, 11.0, 1e3), (402, 9.0, 9.1, 8.9, 9.0, 1e3)])
    lv = sd.vwap[1]
    assert 9.0 < lv < 11.0
    r, k, why, px, *_ = S.run(sd, -1, 1, 11.0, 11.0, 11.5, "vwap", minute(15, 55))
    assert why == "level" and k == 2 and px == pytest.approx(9.0)        # opened under the limit
    assert S.MARKETABLE[why] is False


def test_flatten_and_end_of_data_are_marketable_exits():
    sd = sday([(714, 10.0, 10.1, 9.9, 10.0, 1e4), (715, 9.8, 9.9, 9.7, 9.8, 1e4)])
    r, k, why, *_ = S.run(sd, -1, 0, 10.0, 10.0, 10.5, "close", minute(15, 55))
    assert why == "flat" and k == 1 and r == pytest.approx(0.4) and S.MARKETABLE[why]


# ------------------------------------------------------------------ costs
def test_long_costs_equal_the_month_studys_live_model():
    import backtest_recent as E
    old = E.COST_MODEL
    E.COST_MODEL = "live"
    try:
        c = S.Costs()
        for entry, stop, pm, dv5 in ((5.0, 4.85, False, 80_000), (12.3, 11.1, True, 20_000), (3.1, 3.05, False, 900_000)):
            for marketable in (True, False):
                cm, sp, bw = c.parts(entry, entry - stop, marketable, pm, dv5)
                assert bw == 0.0
                assert cm + sp == pytest.approx(E.cost_r(entry, stop, marketable, pm=pm, dv5=dv5), abs=6e-4)
    finally:
        E.COST_MODEL = old


def test_borrow_is_charged_on_the_entry_value_in_r():
    c = S.Costs()
    cm0, sp0, b0 = c.parts(10.0, 0.5, True, False, 100_000)
    cm1, sp1, b1 = c.parts(10.0, 0.5, True, False, 100_000, borrow_pct=1.0)
    assert (cm0, sp0, b0) == (cm1, sp1, 0.0)
    assert b1 == pytest.approx(0.01 * 10.0 / 0.5)                         # 1 % of price on a 5 % stop = 0.2 R
    t = [{"net": 0.2, "entry": 10.0, "risk": 0.5}, {"net": 0.0, "entry": 10.0, "risk": 0.5}]
    assert P.break_even_borrow(t) == pytest.approx(0.5)                   # mean 0.1 R x 5 % = 0.5 % of price
    assert G.mean(P.with_borrow(t, 0.5)) == pytest.approx(0.0)


# ------------------------------------------------------------------ look-ahead
def _entries(sd):
    out = []
    for fam in ("S1", "S2", "L1"):
        for cfg in R.FAMILIES[fam].configs:
            key = R.signal_key(fam, cfg)
            for e, _w in R.entries(fam, sd, key):
                out.append((fam, key, e))
    return out


def _cut(sd, k_last):
    return sday([(sd.m[k], sd.o[k], sd.h[k], sd.l[k], sd.c[k], sd.v[k]) for k in range(k_last + 1)],
                pc=sd.pc, open_px=sd.open_px)


def _scramble(sd, k_last, seed):
    """Bars after k_last replaced by an unrelated path (a crash, then a squeeze)."""
    rnd = random.Random(seed)
    rows = [(sd.m[k], sd.o[k], sd.h[k], sd.l[k], sd.c[k], sd.v[k]) for k in range(k_last + 1)]
    px = sd.c[k_last] * rnd.choice((0.7, 1.4))
    for mm in range(sd.m[k_last] + 1, 720):
        o = px; c = px * (1 + rnd.gauss(0, 0.02)); rows.append((mm, o, max(o, c) * 1.01, min(o, c) * 0.99, c, 5e4)); px = c
    return sday(rows, pc=sd.pc, open_px=sd.open_px)


def test_every_entry_rule_decides_from_bars_up_to_its_fill_bar_only():
    fired = {"S1": 0, "S2": 0, "L1": 0}
    for seed in range(80):
        sd = gapper(seed, pm_vol=12_000 if seed % 2 else 40_000)
        for fam, key, e in _entries(sd):
            fired[fam] += 1
            assert e.sig_k < e.k0 and e.entry > 0 and e.stop > 0
            for alt in (_cut(sd, e.k0), _scramble(sd, e.k0, seed)):
                got = R.entries(fam, alt, key)
                assert got and got[0][0] == e, (seed, fam, key)
    assert all(v >= 5 for v in fired.values()), fired


def test_s2_reads_the_gap_and_premarket_volume_known_at_the_open():
    sd = gapper(3, pm_vol=40_000)
    assert sum(sd.v[:sd.first_at(D.RTH)]) >= R.S2_PM_VOL
    thin = gapper(3, pm_vol=1_000)
    assert sum(thin.v[:thin.first_at(D.RTH)]) < R.S2_PM_VOL
    assert R.s2(thin, 0.20, "hod") is None and R.s2(thin, 0.20, "bar5") is None
    low_gap = sday(list(zip(sd.m, sd.o, sd.h, sd.l, sd.c, sd.v)), pc=sd.pc, open_px=sd.pc * 1.1)
    assert R.s2(low_gap, 0.20, "hod") is None


def test_shorts_stand_aside_once_the_short_sale_restriction_has_fired():
    sd = gapper(5, pm_vol=40_000)
    assert R.s1(sd, 30) is not None or R.s2(sd, 0.20, "hod") is not None
    k = 10                                                    # one pre-market print 11 % under the close before
    sd.l[k] = sd.pc * 0.89
    sd._vwap = None
    assert R.s1(sd, 30) is None and R.s1(sd, 60) is None
    assert R.s2(sd, 0.20, "hod") is None and R.s2(sd, 0.20, "bar5") is None


def test_the_l3_reference_runs_the_desks_own_detector():
    sd = gapper(7, pm_vol=40_000)
    out = R.l3(sd)
    for e, window in out:
        assert window in ("pre-market", "regular")
        assert (e.entry - e.stop) / e.entry * 100 >= R.L3_MIN_STOP_PCT - 1e-6
        assert e.k0 > e.sig_k


# ------------------------------------------------------------------ the random baseline
def test_the_random_baseline_is_deterministic_and_stays_in_its_window():
    sd = gapper(11)
    c = S.Costs()
    a = S.random_baseline(sd, -1, minute(10, 1), minute(15, 1), 0.05, "close", minute(15, 55), c, 20, 123)
    b = S.random_baseline(sd, -1, minute(10, 1), minute(15, 1), 0.05, "close", minute(15, 55), c, 20, 123)
    assert a == b and a is not None
    assert S.random_baseline(sd, -1, minute(17, 0), minute(18, 0), 0.05, "close", minute(15, 55), c, 20, 1) is None
    seen = []
    orig = S.run

    def spy(sd_, side, k0, *rest, **kw):
        seen.append(sd_.m[k0])
        return orig(sd_, side, k0, *rest, **kw)
    S.run = spy
    try:
        S.random_baseline(sd, 1, minute(9, 31), minute(11, 21), 0.03, "trail1", minute(11, 30), c, 50, 7)
    finally:
        S.run = orig
    assert seen and all(minute(9, 31) <= mm < minute(11, 21) for mm in seen)


# ------------------------------------------------------------------ the protocol
def test_the_holdout_opens_once_per_family_in_either_ledger(tmp_path):
    local, committed = tmp_path / "local.jsonl", tmp_path / "committed.jsonl"
    both = (committed, local)
    a, b = {"A": 30, "exit": "close"}, {"A": 60, "exit": "close"}
    e = P.open_holdout("S1", a, 6, {"n": 120}, {"n": 40}, ledger=local, ledgers=both)
    assert e["hash"] == P.config_hash("S1", a) and local.exists()
    assert P.open_holdout("S1", a, 6, {}, {}, ledger=local, ledgers=both)["reread"] is True
    with pytest.raises(P.HoldoutAlreadyOpened):
        P.open_holdout("S1", b, 6, {}, {}, ledger=local, ledgers=both)
    committed.write_text(json.dumps({"family": "S2", "hash": "abc", "utc": "2026-10-13T00:00:00+00:00"}) + "\n")
    with pytest.raises(P.HoldoutAlreadyOpened):                         # opened on the other machine
        P.open_holdout("S2", {"G": 0.2, "stop": "hod", "exit": "vwap"}, 8, {}, {}, ledger=local, ledgers=both)
    with pytest.raises(ValueError):
        P.open_holdout("L3", {"ref": "x"}, 1, {}, {}, ledger=local, ledgers=both)


def test_the_registry_counts_every_configuration_once_plus_prior_reads(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    P.register([{"family": "S1", "hash": "h1"}, {"family": "S1", "hash": "h2"}], a)
    P.register([{"family": "S1", "hash": "h2"}, {"family": "S1", "hash": "h3"}, {"family": "L1", "hash": "x"}], b)
    P.register([{"family": "prior:F7-leader", "relates_to": "L2", "n_configs": 18}], b)
    assert P.n_configs("S1", (a, b)) == 3 and P.n_configs("L1", (a, b)) == 1 and P.n_configs("L2", (a, b)) == 18


def test_the_committed_registry_records_the_prior_reads():
    rows = [json.loads(x) for x in (ROOT / "research" / "strategy-candidates" / "registry.jsonl").read_text().splitlines()
            if x.strip()]
    prior = {r["family"]: r for r in rows if r.get("prior")}
    assert prior["prior:F7-leader"]["n_configs"] == 18 and prior["prior:F8-leader-spread"]["n_configs"] == 54
    assert prior["prior:20-day shorts"]["n_configs"] == 31
    for r in prior.values():
        assert (ROOT / r["source"].split(" ")[0]).exists(), r["source"]


def test_one_position_at_a_time_and_done_after_a_loss():
    t = [{"day": "d", "sym": "A", "fill_min": 10, "exit_min": 20, "net": -1.0},
         {"day": "d", "sym": "B", "fill_min": 15, "exit_min": 25, "net": 2.0},     # overlaps A: not taken
         {"day": "d", "sym": "C", "fill_min": 21, "exit_min": 30, "net": 1.0},
         {"day": "e", "sym": "D", "fill_min": 5, "exit_min": 6, "net": 0.5}]
    assert [x["sym"] for x in P.portfolio(t)] == ["A", "C", "D"]
    assert [x["sym"] for x in P.portfolio(t, done_after_loss=True)] == ["A", "D"]


def _fake(split, net, n, day0="2021-02-01"):
    return [{"split": split, "day": f"{day0[:8]}{1 + i % 27:02d}", "sym": f"S{i}", "fill_min": 400 + i,
             "exit_min": 400 + i, "net": net + (0.01 if i % 2 else -0.01), "gross": net + 0.2, "comm": 0.05,
             "spread": 0.15, "mfe": 1.0, "mae": -0.5, "why": "stop", "rnd": None, "entry": 10.0, "risk": 0.5,
             "risk_pct": 5.0, "gap": 0.3, "dv20": 2e6, "window": "regular"} for i in range(n)]


def test_train_chooses_and_validation_only_gates():
    from candidates import run as RUN
    fam = "S1"
    a, b = R.FAMILIES[fam].configs[0], R.FAMILIES[fam].configs[1]
    got = {(fam, P.config_hash(fam, a)): _fake("train", 0.30, 120) + _fake("valid", -0.20, 40, "2023-03-01"),
           (fam, P.config_hash(fam, b)): _fake("train", 0.10, 120) + _fake("valid", +0.50, 40, "2023-03-01")}
    rows, chosen, gate = RUN.evaluate(fam, got)
    assert chosen["hash"] == P.config_hash(fam, a)                          # best on TRAIN, though worse on validation
    assert gate["passed"] is False
    got = {(fam, P.config_hash(fam, a)): _fake("train", 0.30, 60)}
    rows, chosen, gate = RUN.evaluate(fam, got)
    assert chosen is None and "too few train trades" in gate["why"]


def test_the_adoption_rule_needs_all_seven():
    port = []
    for y in ("2024", "2025", "2026"):
        for i in range(90):
            port.append({"day": f"{y}-03-{1 + i % 28:02d}", "net": 0.3 + (0.1 if i % 2 else -0.1), "rnd": -0.1,
                         "entry": 10.0, "risk": 1.0})
    older = [{"net": 0.2, "day": "2018-01-02"}]
    a = P.adoption(port, 1, older)
    assert a["adopted"], a["checks"]
    assert not P.adoption(port, 1, [{"net": -0.1, "day": "2018-01-02"}])["adopted"]          # criterion 7
    tight = [dict(t, risk=0.05) for t in port]                       # 0.5 % stops: +0.3 R is 0.15 % of price
    assert P.break_even_borrow(tight) == pytest.approx(0.15)
    key6 = f"6 break-even borrow >= {P.BORROW_MIN_PCT} % (shorts)"
    assert not P.adoption(tight, -1, older)["checks"][key6] and P.adoption(tight, 1, older)["checks"][key6]


# ------------------------------------------------------------------ the data
def test_bars_convert_to_eastern_minutes_in_winter_and_summer():
    raw_w = [[f"2024-01-10T{14 + i // 60:02d}:{i % 60:02d}:00Z", 10, 10.1, 9.9, 10, 100] for i in range(45)]
    raw_s = [[f"2024-07-10T{13 + i // 60:02d}:{i % 60:02d}:00Z", 10, 10.1, 9.9, 10, 100] for i in range(45)]
    w = D.symbol_day("2024-01-10", "X", 9.0, raw_w)
    s = D.symbol_day("2024-07-10", "X", 9.0, raw_s)
    assert w.m[30] == minute(9, 30) and s.m[30] == minute(9, 30)
    assert D.symbol_day("2024-07-10", "X", 9.0, raw_s[:10]) is None         # under 40 bars


def test_the_universe_drops_reverse_splits_and_keeps_the_window(tmp_path):
    f = tmp_path / "u.csv"
    f.write_text("sym,day,prev_close,open_px,gap_pct,prior_dollar_volume_20d,split_on_day,reverse_split_ratio\n"
                 "AAA,2021-03-01,2.0,2.5,25,1e6,False,\n"
                 "BBB,2021-03-01,2.0,2.5,25,1e6,False,10\n"
                 "CCC,2020-12-31,2.0,2.5,25,1e6,False,\n")
    u = D.universe(path=f)
    assert list(u) == ["2021-03-01"] and list(u["2021-03-01"]) == ["AAA"]
    assert [D.split_of(d) for d in ("2020-12-31", "2021-01-04", "2023-06-01", "2024-01-02")] == \
        ["older", "train", "valid", "holdout"]


def test_a_smoke_run_writes_nothing_to_the_registry_or_the_ledger(tmp_path, monkeypatch, capsys):
    from candidates import run as RUN
    monkeypatch.setattr(P, "LOCAL_REGISTRY", tmp_path / "registry.jsonl")
    monkeypatch.setattr(P, "LOCAL_LEDGER", tmp_path / "ledger.jsonl")
    assert RUN.main(["--source", "daily", "--families", "S1", "--draws", "2", "--out", str(tmp_path / "out")]) == 0
    assert not (tmp_path / "registry.jsonl").exists() and not (tmp_path / "ledger.jsonl").exists()
    assert (tmp_path / "out" / "report.txt").read_text().count("REG S1 ") == 6
    assert "SMOKE" in capsys.readouterr().out


def test_the_history_source_reads_the_cache_format_the_mac_has(tmp_path, monkeypatch, capsys):
    """data/cache/history/{day}.json as backtest_history.fetch_day writes it: {sym: [[t_utc, o, h, l, c, v]]}."""
    from candidates import run as RUN
    sd = gapper(4, pm_vol=40_000)
    day = "2022-03-01"                                                    # EST: 04:00 ET = 09:00 UTC
    raw = [[f"{day}T{(9 * 60 + mm) // 60:02d}:{(9 * 60 + mm) % 60:02d}:00Z", o, h, l, c, v]
           for mm, o, h, l, c, v in zip(sd.m, sd.o, sd.h, sd.l, sd.c, sd.v)]
    cache = tmp_path / "history"
    cache.mkdir()
    (cache / f"{day}.json").write_text(json.dumps({"AAA": raw}))
    row = {"prev_close": "10.0", "open_px": str(sd.open_px), "prior_dollar_volume_20d": "2000000"}
    monkeypatch.setattr(D, "universe", lambda since=D.WINDOW[0], until=D.WINDOW[1], path=None:
                        {day: {"AAA": row}} if since <= day <= until else {})
    monkeypatch.setattr(P, "LOCAL_REGISTRY", tmp_path / "registry.jsonl")
    monkeypatch.setattr(P, "LOCAL_LEDGER", tmp_path / "ledger.jsonl")
    rc = RUN.main(["--cache", str(cache), "--no-fetch", "--sample", "5", "--families", "S1,S2,L1", "--draws", "2",
                   "--out", str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert rc == 0 and "train 1 / 1 symbol-days with bars" in out
    got = D.symbol_day(day, "AAA", 10.0, raw)
    assert got.m == sd.m and got.c == sd.c                                 # UTC stamps back to the same ET minutes
    assert not (tmp_path / "registry.jsonl").exists()                      # --sample is plumbing: nothing registered
    assert "REG S1 " in out and "REG L1 " in out
