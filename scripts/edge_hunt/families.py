#!/usr/bin/env python3
"""The six families of `research/edge-hunt/PREREGISTRATION.md`.

    python3 scripts/edge_hunt/families.py F4 --stage search      # train + validation only
    python3 scripts/edge_hunt/families.py F4 --stage holdout     # the ONE opening (ledger first)

`--stage search` never reads a holdout row: `Ctx.frame` refuses the holdout
split unless the family's opening is already in the ledger.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

from edge_hunt import costs as C  # noqa: E402
from edge_hunt import engine as G  # noqa: E402
from edge_hunt import features as F  # noqa: E402
from edge_hunt import protocol as P  # noqa: E402
from edge_hunt.data import STORE, Store, minute, split_of  # noqa: E402

RESULTS = ROOT / "research" / "edge-hunt" / "results"
FEAT_CACHE = STORE / "plan_features.parquet"
W_PM = (minute(7, 0), minute(9, 30))
W_RTH = (minute(9, 30), minute(11, 20))
FLAT_1130, FLAT_1600 = minute(11, 30), 720
MIN_TRAIN_PLANS, TOP_K, MIN_VALID_TRADES, RANDOM_DRAWS = 300, 5, 30, 20
COST_MODEL = "prereg"          # sensitivities "light" and "old" are reported at every opening, never chosen on


class HoldoutClosed(RuntimeError):
    pass


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, features: bool = True):
        self.S = Store()
        self.sd = self.S.sd
        self.grid = F.Grid(self.S)
        self.m = self.S.minute.astype(np.int64)
        self.o, self.h, self.l, self.c, self.v = (np.ascontiguousarray(self.S.ohlcv[:, j]) for j in range(5))
        self.starts = self.sd["start"].to_numpy(np.int64); self.ends = self.sd["end"].to_numpy(np.int64)
        self.pc = self.sd["prev_close"].to_numpy(float)
        self.proxy = C.SpreadProxy()
        p = pd.read_parquet(STORE / "desk_plans.parquet")
        # the desk detector's plans, re-filled with the edge engine's A10 (TTL in MINUTES, cap-return
        # fills priced at a later bar's open when it opens under the cap) — see engine.stop_limit_fill
        sids = p["sid"].to_numpy(np.int64)
        fk, fp, cf = G.fills_many(self.m, self.o, self.h, self.l, self.starts[sids], self.ends[sids],
                                  p["plan_min"].to_numpy(np.int64), p["entry"].to_numpy(float), 3)
        p = p.assign(k0=fk, fill=fp, high_ok=1 - cf, gap_missed=fk == -2)
        p = p[p["k0"] >= 0].reset_index(drop=True)
        p["fill_min"] = self.m[self.starts[p["sid"].to_numpy(np.int64)] + p["k0"].to_numpy(np.int64)]
        p["split"] = p["day"].map(split_of)
        if features:
            p = p.join(self.features_for(p, FEAT_CACHE))
        self.plans = p

    # point-in-time features, cached for the desk plans
    def features_for(self, rows: pd.DataFrame, cache: Path | None = None) -> pd.DataFrame:
        keys = rows[["sid", "plan_min"]].reset_index(drop=True)
        if cache is not None and cache.exists():
            f = pd.read_parquet(cache)
            if len(f) == len(rows) and "_sid" in f and (f["_sid"].to_numpy() == keys["sid"].to_numpy()).all() \
                    and (f["_plan_min"].to_numpy() == keys["plan_min"].to_numpy()).all():
                return f.drop(columns=["_sid", "_plan_min"]).set_index(rows.index)
        f = F.plan_features(self.S, self.grid, rows[["sid", "day", "sym", "plan_min"]].reset_index(drop=True))
        if cache is not None:
            f.assign(_sid=keys["sid"].to_numpy(), _plan_min=keys["plan_min"].to_numpy()).to_parquet(cache, index=False)
        return f.set_index(rows.index)

    def frame(self, df: pd.DataFrame, split: str, family: str) -> pd.DataFrame:
        if split == "holdout" and P.opened(family) is None:
            raise HoldoutClosed(f"{family}: the holdout is read only after open_holdout records it")
        return df[df["split"] == split]

    def dv5(self, sids, mins):
        sids = np.asarray(sids, np.int64); mins = np.clip(np.asarray(mins, np.int64), 0, 719)
        lo = mins - 5
        prev = np.where(lo >= 0, self.grid.cumdv[sids, np.clip(lo, 0, 719)], 0.0)
        return self.grid.cumdv[sids, mins] - prev

    # ---------------------------------------------------------------- trades
    def trades(self, df: pd.DataFrame, stop_rule: tuple, sp: np.ndarray, plan: str = "fixed",
               model: str | None = None) -> pd.DataFrame:
        """Simulate every row (needs sid, entry, stop, fill, k0, plan_min,
        window) under a stop rule and an exit spec; net of costs."""
        if df.empty:
            return df.assign(gross=[], net=[], cost=[], exit_min=[], fill_min=[])
        entry = df["entry"].to_numpy(float); stop = df["stop"].to_numpy(float).copy()
        keep = np.ones(len(df), bool)
        kind = stop_rule[0]
        hs_in = self.proxy.spread_vec(df["fill"].to_numpy(float), df["window"].to_numpy() == "pre-market",
                                      self.dv5(df["sid"], df["plan_min"])) / 2
        if kind == "skip_pct":
            keep = (entry - stop) / entry * 100 >= stop_rule[1]
        elif kind == "widen_pct":
            stop = np.minimum(stop, entry * (1 - stop_rule[1] / 100))
        elif kind == "skip_spread":
            keep = (entry - stop) >= stop_rule[1] * hs_in
        elif kind == "skip_abs":
            keep = (entry - stop) >= stop_rule[1] - 1e-9
        d = df[keep]
        entry, stop, hs_in = entry[keep], stop[keep], hs_in[keep]
        sids = d["sid"].to_numpy(np.int64)
        high_ok = d["high_ok"].to_numpy(np.int64) if "high_ok" in d else np.ones(len(d), np.int64)
        R, orders, kex, why, st = G.simulate_many(self.m, self.o, self.h, self.l, self.c, self.starts[sids],
                                                  self.ends[sids], d["k0"].to_numpy(np.int64),
                                                  d["fill"].to_numpy(float), entry, stop, sp, high_ok)
        exit_min = self.m[kex]
        fill = d["fill"].to_numpy(float)
        exit_px = fill + R * (entry - stop)
        hs_out = self.proxy.spread_vec(exit_px, exit_min < minute(9, 30), self.dv5(sids, exit_min - 1)) / 2
        cost = C.cost_r_vec(entry, stop, fill, exit_px, orders, st, hs_in, hs_out, plan, model=model or COST_MODEL)
        out = d.assign(entry_used=entry, stop_used=stop, gross=R, cost=cost, net=R - cost, exit_min=exit_min,
                       orders=orders, why=why, stop_side=st)
        return out[~np.isnan(out["gross"].to_numpy())]

    def random_diff(self, port: pd.DataFrame, sp: np.ndarray, windows: pd.Series | None = None,
                    plan: str = "fixed") -> np.ndarray:
        """Per trade: its net R minus the mean net R of RANDOM_DRAWS market
        entries at random bars of the same symbol-day and window, same stop
        %, same exit, same costs."""
        out = np.full(len(port), np.nan)
        for j, r in enumerate(port.itertuples(index=False)):
            s, e = self.starts[r.sid], self.ends[r.sid]
            w0, w1 = (windows.iloc[j] if windows is not None else (W_PM if r.window == "pre-market" else W_RTH))
            spct = (r.entry_used - r.stop_used) / r.entry_used
            rr, oo, ss, ff, stp, kk, ke = G.random_entries(self.m[s:e], self.o[s:e], self.h[s:e], self.l[s:e],
                                                           self.c[s:e], w0, w1, spct, sp, RANDOM_DRAWS,
                                                           int(r.sid) * 1000 + int(r.fill_min))
            ok = ~np.isnan(rr)
            if not ok.any():
                continue
            ent_min = self.m[s:e][kk[ok]]; ex_min = self.m[s:e][ke[ok]]
            ex_px = ff[ok] + rr[ok] * (ff[ok] - stp[ok])
            hin = self.proxy.spread_vec(ff[ok], ent_min < minute(9, 30), self.dv5(np.full(ok.sum(), r.sid), ent_min - 1)) / 2
            hout = self.proxy.spread_vec(ex_px, ex_min < minute(9, 30), self.dv5(np.full(ok.sum(), r.sid), ex_min - 1)) / 2
            cost = C.cost_r_vec(ff[ok], stp[ok], ff[ok], ex_px, oo[ok], ss[ok], hin, hout, plan, model=COST_MODEL)
            out[j] = r.net - float(np.mean(rr[ok] - cost))
        return out


# ------------------------------------------------------------------ evaluation
def portfolio(tr: pd.DataFrame) -> pd.DataFrame:
    if tr.empty:
        return tr
    rows = tr.assign(_i=np.arange(len(tr)))
    kept = P.one_position(rows[["day", "fill_min", "exit_min", "sym", "_i"]].to_dict("records"))
    return tr.iloc[[k["_i"] for k in kept]]


def stats(tr: pd.DataFrame, col: str = "net") -> dict:
    if tr.empty:
        return {"n": 0}
    out = P.summary(tr[col].to_numpy(float), tr["day"].to_numpy())
    out["gross"] = round(float(tr["gross"].mean()), 4)
    out["cost"] = round(float(tr["cost"].mean()), 4)
    return out


def discipline(port: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "none" or port.empty:
        return port
    keep = []
    for _, g in port.groupby("day", sort=True):
        losses, cum, stop = 0, 0.0, False
        for i, r in g.iterrows():
            if stop:
                continue
            keep.append(i)
            losses += r.net < 0; cum += r.net
            if (rule == "first_loss" and r.net < 0) or (rule == "two_losses" and losses >= 2) or \
               (rule == "minus2R" and cum <= -2) or (rule == "first_win1R" and r.net >= 1):
                stop = True
    return port.loc[keep]


def sizing(port: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "flat" or port.empty:
        return port.assign(w=1.0)
    small = port["shares_out"].fillna(np.inf) <= 20e6
    news = port["news_n"] > 0
    both, neither = small & news, ~small & ~news
    w = np.where(both, 1.5, np.where(neither, 0.5, 1.0))
    if rule == "inverse":
        w = np.where(both, 0.5, np.where(neither, 1.5, 1.0))
    p = port.assign(w=w)
    return p.assign(net=p["net"] * p["w"], gross=p["gross"] * p["w"], cost=p["cost"] * p["w"])


def spec_of(exit_name: str, flat: int = FLAT_1130) -> np.ndarray:
    table = {
        "trail0.5": dict(trail=0.5), "trail1": dict(trail=1.0), "trail1.5": dict(trail=1.5), "trail2": dict(trail=2.0),
        "fixed2": dict(target=2.0), "fixed3": dict(target=3.0), "be1_trail2": dict(be_at=1.0, trail=2.0),
        "ladder1_2": dict(ladder=(1.0, 2.0)), "ladder2_3": dict(ladder=(2.0, 3.0)),
        "time5_trail1": dict(trail=1.0, time_stop=5), "newlow": dict(newlow=True),
    }
    return G.spec(flat_min=flat, **table[exit_name])


def choose(family: str, configs: list[dict], evaluate) -> dict:
    """Rank on train (plan level, >= MIN_TRAIN_PLANS), take the top K, pick
    the best validation portfolio (>= MIN_VALID_TRADES). Registers all."""
    rows = []
    for cfg in configs:
        tr = evaluate(cfg, "train")
        rows.append({"hash": P.config_hash(cfg), "config": cfg, "train_plan": stats(tr), "train_port": stats(portfolio(tr))})
    ranked = sorted([r for r in rows if r["train_plan"].get("n", 0) >= MIN_TRAIN_PLANS],
                    key=lambda r: r["train_plan"]["mean"], reverse=True)
    for r in ranked[:TOP_K]:
        va = evaluate(r["config"], "valid")
        r["valid_plan"] = stats(va); r["valid_port"] = stats(portfolio(va))
    P.register(family, rows)
    cands = [r for r in ranked[:TOP_K] if r["valid_port"].get("n", 0) >= MIN_VALID_TRADES]
    best = max(cands, key=lambda r: r["valid_port"]["mean"]) if cands else None
    return {"n_configs": len(configs), "n_eligible": len(ranked), "top": ranked[:TOP_K], "all": rows, "best": best}


def print_search(family: str, res: dict) -> None:
    print(f"\n{family} · {res['n_configs']} configurations · {res['n_eligible']} with >= {MIN_TRAIN_PLANS} train plans")
    print(f"  {'config':<70}{'train plan':>18}{'train port':>18}{'valid port':>18}")
    for r in res["top"]:
        tp, tq, vq = r["train_plan"], r["train_port"], r.get("valid_port", {})
        f = lambda s: f"{s.get('mean', float('nan')):+.3f} ({s.get('n', 0)})"  # noqa: E731
        print(f"  {json.dumps(r['config'])[:70]:<70}{f(tp):>18}{f(tq):>18}{f(vq):>18}")
    b = res["best"]
    if b is None:
        print("  no configuration reached validation with enough trades — family FAILS, holdout stays closed")
    elif b["valid_port"]["mean"] <= 0:
        print(f"  chosen {b['hash']} is not positive on validation ({b['valid_port']['mean']:+.3f}) — "
              "family FAILS at the validation gate, holdout stays closed")
    else:
        print(f"  chosen {b['hash']} — positive on validation, eligible for its one holdout opening")


def open_and_read(ctx: Ctx, family: str, res: dict, evaluate, windows_fn=None, spec_fn=None) -> dict:
    b = res["best"]
    if b is None or b["valid_port"]["mean"] <= 0:
        raise SystemExit(f"{family}: validation gate not met; the holdout stays closed")
    P.open_holdout(family, b["config"], res["n_configs"], b["train_port"], b["valid_port"])
    ho = evaluate(b["config"], "holdout")
    port = portfolio(ho)
    sp = spec_fn(b["config"]) if spec_fn else spec_of(b["config"]["exit"], b["config"].get("flat", FLAT_1130))
    wins = windows_fn(port) if windows_fn else None
    rd = ctx.random_diff(port, sp, wins)
    res_h = P.adoption(port["net"].to_numpy(float), port["day"].to_numpy(), rd)
    res_h["plan_level"] = stats(ho); res_h["portfolio"] = stats(port)
    res_h["tiered"] = stats(portfolio(evaluate(b["config"], "holdout", plan="tiered")))
    global COST_MODEL
    for mdl in ("light", "old"):
        COST_MODEL = mdl
        try:
            res_h["cost_" + mdl] = stats(portfolio(evaluate(b["config"], "holdout")))
        finally:
            COST_MODEL = "prereg"
    P.record_result(family, res_h)
    return res_h


# ------------------------------------------------------------------ F4 exits and sizing
STOP_RULES = [("none",), ("skip_pct", 1.0), ("skip_pct", 2.0), ("skip_pct", 3.0), ("widen_pct", 2.0),
              ("widen_pct", 3.0), ("skip_spread", 4.0), ("skip_abs", 0.05), ("skip_abs", 0.10)]
EXITS = ["trail0.5", "trail1", "trail1.5", "trail2", "fixed2", "fixed3", "be1_trail2", "ladder1_2", "ladder2_3",
         "time5_trail1", "newlow"]


def base_rows(ctx: Ctx) -> pd.DataFrame:
    return ctx.plans[ctx.plans["red"] == 0]


def f4(ctx: Ctx, stage: str):
    fam = "F4-exits-sizing"
    base = base_rows(ctx)

    def ev(cfg, split, plan="fixed"):
        tr = ctx.trades(ctx.frame(base, split, fam), tuple(cfg["stop"]), spec_of(cfg["exit"]), plan)
        if "discipline" in cfg:
            tr = sizing(discipline(portfolio(tr), cfg["discipline"]), cfg["sizing"])
        return tr

    configs = [{"stop": list(s), "exit": e} for s in STOP_RULES for e in EXITS]
    res = choose(fam, configs, ev)
    # second stage on the train-best five: discipline x sizing, chosen on train portfolio
    second = []
    for r in res["top"]:
        for dsc in ("none", "first_loss", "two_losses", "minus2R", "first_win1R"):
            for sz in ("flat", "pillars", "inverse"):
                second.append({**r["config"], "discipline": dsc, "sizing": sz})
    rows = []
    for cfg in second:
        tr = ev(cfg, "train")
        rows.append({"hash": P.config_hash(cfg), "config": cfg, "train_plan": stats(tr), "train_port": stats(tr)})
    rows.sort(key=lambda r: r["train_port"].get("mean", -9), reverse=True)
    for r in rows[:TOP_K]:
        va = ev(r["config"], "valid")
        r["valid_plan"] = stats(va); r["valid_port"] = stats(va)
    P.register(fam, rows)
    cands = [r for r in rows[:TOP_K] if r["valid_port"].get("n", 0) >= MIN_VALID_TRADES]
    res2 = {"n_configs": len(configs) + len(second), "n_eligible": len(rows), "top": rows[:TOP_K],
            "best": max(cands, key=lambda r: r["valid_port"]["mean"]) if cands else None}
    print_search(fam + " (stop x exit)", res)
    print_search(fam + " (+ discipline x sizing)", res2)
    if stage == "holdout":
        out = open_and_read(ctx, fam, res2, ev)
        print(json.dumps(out, indent=1, default=str))
    return res, res2


# ------------------------------------------------------------------ F5 new hypotheses
def gen_orb(ctx: Ctx) -> pd.DataFrame:
    t = minute(9, 34)
    gain = ctx.grid.close[:, t] / ctx.pc - 1
    dv = ctx.grid.cumdv[:, t]
    rank = pd.Series(dv).groupby(ctx.sd["day"].to_numpy()).rank(ascending=False, method="first").to_numpy()
    rows = []
    for i in range(len(ctx.sd)):
        if not (gain[i] >= 0.10):
            continue
        s, e = ctx.starts[i], ctx.ends[i]
        arm, trig, stop, fk, fpx, green, capf = G.orb(ctx.m[s:e], ctx.o[s:e], ctx.h[s:e], ctx.l[s:e], ctx.c[s:e],
                                                     minute(9, 30), minute(9, 35), minute(10, 30))
        if arm < 0 or fk < 0 or not green:
            continue
        rows.append({"sid": i, "day": ctx.sd["day"].iat[i], "sym": ctx.sd["sym"].iat[i], "plan_min": minute(9, 34),
                     "fill_min": int(ctx.m[s + fk]), "k0": int(fk), "entry": trig, "stop": stop, "fill": fpx,
                     "window": "regular", "rank": int(rank[i]), "high_ok": 1 - int(capf)})
    d = pd.DataFrame(rows)
    d["split"] = d["day"].map(split_of)
    return d


def gen_vwap(ctx: Ctx, gain: float) -> pd.DataFrame:
    rows = []
    for i in range(len(ctx.sd)):
        s, e = ctx.starts[i], ctx.ends[i]
        arm, trig, stop, fk, fpx, capf = G.vwap_test(ctx.m[s:e], ctx.o[s:e], ctx.h[s:e], ctx.l[s:e], ctx.c[s:e],
                                                     ctx.v[s:e], ctx.pc[i], minute(9, 35), minute(10, 30), gain, 10, 0.002)
        if arm < 0:
            continue
        rows.append({"sid": i, "day": ctx.sd["day"].iat[i], "sym": ctx.sd["sym"].iat[i], "plan_min": int(ctx.m[s + arm]),
                     "fill_min": int(ctx.m[s + fk]), "k0": int(fk), "entry": trig, "stop": stop, "fill": fpx,
                     "window": "regular", "high_ok": 1 - int(capf)})
    d = pd.DataFrame(rows)
    d["split"] = d["day"].map(split_of)
    return d


def f5(ctx: Ctx, stage: str):
    fam = "F5-new"
    base = base_rows(ctx)
    orb_rows = gen_orb(ctx)
    vw = {g: gen_vwap(ctx, g / 100) for g in (20, 40)}

    def ev(cfg, split, plan="fixed"):
        h = cfg["h"]
        if h == "orb":
            d = orb_rows[orb_rows["rank"] <= cfg["k"]]
            rule = ("widen_pct", 2.0) if cfg["stop"] == "widen2" else ("none",)
            return ctx.trades(ctx.frame(d, split, fam), rule, spec_of(cfg["exit"], cfg["flat"]), plan)
        if h == "vwap":
            rule = ("widen_pct", 2.0) if cfg["stop"] == "widen2" else ("none",)
            return ctx.trades(ctx.frame(vw[cfg["gain"]], split, fam), rule, spec_of(cfg["exit"]), plan)
        if h == "hot":
            d = base[base["hot30"] >= cfg["k"]]
            return ctx.trades(ctx.frame(d, split, fam), ("none",), spec_of("trail1"), plan)
        return ctx.trades(ctx.frame(base, split, fam), ("none",), spec_of(cfg["exit"], FLAT_1600), plan)

    configs = ([{"h": "orb", "k": k, "stop": s, "exit": e, "flat": f} for k in (1, 3) for s in ("orlow", "widen2")
                for e in ("trail1", "trail2", "fixed2", "fixed3") for f in (FLAT_1130, FLAT_1600)]
               + [{"h": "vwap", "gain": g, "exit": e, "stop": s} for g in (20, 40) for e in ("trail1", "fixed2")
                  for s in ("asis", "widen2")]
               + [{"h": "hot", "k": k} for k in (2, 4, 6)]
               + [{"h": "late", "exit": e} for e in ("trail1", "trail2")])
    assert len(configs) == 45
    res = choose(fam, configs, ev)
    print_search(fam, res)

    def spec_fn(cfg):
        if cfg["h"] == "orb":
            return spec_of(cfg["exit"], cfg["flat"])
        if cfg["h"] == "late":
            return spec_of(cfg["exit"], FLAT_1600)
        return spec_of(cfg.get("exit", "trail1"))

    def windows_fn(port):
        cfg = res["best"]["config"]
        if cfg["h"] in ("orb", "vwap"):
            return pd.Series([(minute(9, 35), minute(10, 30))] * len(port))
        return None
    if stage == "holdout":
        out = open_and_read(ctx, fam, res, ev, windows_fn=windows_fn, spec_fn=spec_fn)
        print(json.dumps(out, indent=1, default=str))
    return res


# ------------------------------------------------------------------ F1 selection
F1_CONDS = {
    "gain>=20%": lambda d: d["gain"] >= 0.20, "gain>=30%": lambda d: d["gain"] >= 0.30,
    "gain>=50%": lambda d: d["gain"] >= 0.50, "gain>=100%": lambda d: d["gain"] >= 1.00,
    "pm_vol<=2M": lambda d: d["pm_vol"] <= 2e6, "pm_vol>=250k": lambda d: d["pm_vol"] >= 2.5e5,
    "rvol>=1.5": lambda d: d["rvol"] >= 1.5, "rvol>=3": lambda d: d["rvol"] >= 3, "rvol>=5": lambda d: d["rvol"] >= 5,
    "vol>=1M": lambda d: d["cum_vol"] >= 1e6,
    "shares<=5M": lambda d: d["shares_out"] <= 5e6, "shares<=10M": lambda d: d["shares_out"] <= 10e6,
    "shares<=20M": lambda d: d["shares_out"] <= 20e6,
    "headline": lambda d: d["news_n"] >= 1, "no_headline": lambda d: d["news_n"] == 0,
    "former_runner": lambda d: d["former_runner"], "not_former_runner": lambda d: ~d["former_runner"],
    "first_move<07:00": lambda d: (d["first_move_min"] >= 0) & (d["first_move_min"] < minute(7, 0)),
    "first_move_07-09": lambda d: (d["first_move_min"] >= minute(7, 0)) & (d["first_move_min"] < minute(9, 0)),
    "first_move>=09:00": lambda d: d["first_move_min"] >= minute(9, 0),
    "price_2-5": lambda d: d["entry"] < 5, "price_5-10": lambda d: (d["entry"] >= 5) & (d["entry"] < 10),
    "price_10-20": lambda d: d["entry"] >= 10,
    "rank1": lambda d: d["rank_dv"] == 1, "rank<=3": lambda d: d["rank_dv"] <= 3,
}
F1_FLOORS = {"none": ("none",), "skip<2%": ("skip_pct", 2.0)}


def f1(ctx: Ctx, stage: str):
    fam = "F1-selection"
    base = base_rows(ctx)
    assert len(F1_CONDS) == 25

    def ev(cfg, split, plan="fixed"):
        d = ctx.frame(base, split, fam)
        mask = np.ones(len(d), bool)
        for c in cfg["conds"]:
            mask &= F1_CONDS[c](d).fillna(False).to_numpy(bool)
        return ctx.trades(d[mask], F1_FLOORS[cfg["stop"]], spec_of("trail1"), plan)

    singles = [{"conds": [c], "stop": f, "exit": "trail1"} for c in F1_CONDS for f in F1_FLOORS]
    scored = []
    for cfg in singles:
        st = stats(ev(cfg, "train"))
        if st.get("n", 0) >= MIN_TRAIN_PLANS:
            scored.append((st["mean"], cfg))
    scored.sort(key=lambda x: x[0], reverse=True)
    best6 = []
    for _, cfg in scored:
        if cfg["conds"][0] not in [b["conds"][0] for b in best6]:
            best6.append(cfg)
        if len(best6) == 6:
            break
    pairs = [{"conds": [a["conds"][0], b["conds"][0]], "stop": a["stop"], "exit": "trail1"}
             for a, b in itertools.combinations(best6, 2)]
    triples = [{"conds": [a["conds"][0], b["conds"][0], c["conds"][0]], "stop": a["stop"], "exit": "trail1"}
               for a, b, c in itertools.combinations(best6[:4], 3)]
    configs = singles + pairs + triples
    assert len(configs) == 69
    res = choose(fam, configs, ev)
    print("  best six singles on train:", [(b["conds"][0], b["stop"]) for b in best6])
    print_search(fam, res)
    # descriptive, train only: each single condition's plan-level train mean
    print("\n  every single condition, train plan level (net R, n):")
    for m, cfg in scored:
        print(f"    {cfg['conds'][0]:<20}{cfg['stop']:<10}{m:+.3f}")
    if stage == "holdout":
        out = open_and_read(ctx, fam, res, ev)
        print(json.dumps(out, indent=1, default=str))
    return res


# ------------------------------------------------------------------ F2 pre-market
F2_WINDOWS = {"07-08": (minute(7, 0), minute(8, 0)), "08-09:30": (minute(8, 0), minute(9, 30)),
              "07-09:30": (minute(7, 0), minute(9, 30))}
F2_STOPS = {"none": ("none",), "skip<2%": ("skip_pct", 2.0), "widen2%": ("widen_pct", 2.0)}
F2_SEL = {"none": lambda d: np.ones(len(d), bool), "gain>=30%": lambda d: (d["gain"] >= 0.30).to_numpy(bool),
          "headline": lambda d: (d["news_n"] >= 1).to_numpy(bool), "rvol>=3": lambda d: (d["rvol"] >= 3).to_numpy(bool)}


def gen_pmh(ctx: Ctx, w0: int, w1: int) -> pd.DataFrame:
    rows = []
    for i in range(len(ctx.sd)):
        s, e = ctx.starts[i], ctx.ends[i]
        arm, trig, stop, fk, fpx, capf = G.pmh_break(ctx.m[s:e], ctx.o[s:e], ctx.h[s:e], ctx.l[s:e], ctx.c[s:e],
                                                     w0, w1, 3, 0.03, 5)
        if arm < 0:
            continue
        rows.append({"sid": i, "day": ctx.sd["day"].iat[i], "sym": ctx.sd["sym"].iat[i], "plan_min": int(ctx.m[s + arm]),
                     "fill_min": int(ctx.m[s + fk]), "k0": int(fk), "entry": trig, "stop": stop, "fill": fpx,
                     "window": "pre-market", "gain": float(ctx.c[s + arm] / ctx.pc[i] - 1), "high_ok": 1 - int(capf)})
    d = pd.DataFrame(rows)
    d["split"] = d["day"].map(split_of)
    return d


def f2(ctx: Ctx, stage: str):
    fam = "F2-premarket"
    base = base_rows(ctx)
    pb = base[base["window"] == "pre-market"]
    pmh = {}
    for name, (w0, w1) in F2_WINDOWS.items():
        d = gen_pmh(ctx, w0, w1)
        pmh[name] = d.join(ctx.features_for(d, STORE / f"pmh_features_{name}.parquet"))

    def rows_for(cfg, split):
        w0, w1 = F2_WINDOWS[cfg["window"]]
        if cfg["entry"] == "pb":
            d = pb[(pb["plan_min"] >= w0) & (pb["plan_min"] < w1)]
        else:
            d = pmh[cfg["window"]]
        d = ctx.frame(d, split, fam)
        return d[F2_SEL[cfg["sel"]](d)]

    def ev(cfg, split, plan="fixed"):
        return ctx.trades(rows_for(cfg, split), F2_STOPS[cfg["stop"]], spec_of(cfg["exit"]), plan)

    configs = [{"entry": e, "window": w, "stop": s, "exit": x, "sel": z} for e in ("pb", "pmh") for w in F2_WINDOWS
               for s in F2_STOPS for x in ("trail1", "trail2", "fixed2") for z in F2_SEL]
    assert len(configs) == 216
    res = choose(fam, configs, ev)
    print_search(fam, res)
    # descriptive, TRAIN only: pre-market first? same symbol-days, base rules, trail 1R
    tr = ctx.trades(ctx.frame(base, "train", fam), ("none",), spec_of("trail1"))
    by = tr.groupby(["sid", "window"])["net"].mean().unstack()
    both = by.dropna()
    print(f"\n  pre-market first? train, symbol-days with a trade in both windows: {len(both)}")
    print(f"    pre-market mean {both['pre-market'].mean():+.3f} · regular mean {both['regular'].mean():+.3f} · "
          f"pre-market better on {np.mean(both['pre-market'] > both['regular']):.0%} of them")
    for w in ("pre-market", "regular"):
        x = tr[tr["window"] == w]
        print(f"    all train {w:<11} n {len(x):>5} gross {x.gross.mean():+.3f} net {x.net.mean():+.3f}")

    def windows_fn(port):
        return pd.Series([F2_WINDOWS[res["best"]["config"]["window"]]] * len(port))
    if stage == "holdout":
        out = open_and_read(ctx, fam, res, ev, windows_fn=windows_fn)
        # PREREGISTRATION.md §6 F2: the universe audit on holdout sessions weighs in on criterion 1
        from edge_hunt import audit
        audit.main(["--split", "holdout"])
        au = json.loads((RESULTS / "f2_audit_holdout.json").read_text())
        share, miss = au["missing_share"], au["miss_net"]
        adj = out["portfolio"]["mean"] * (1 - share) + (miss if miss is not None else 0.0) * share
        out["audit"] = {**au, "adjusted_mean": round(adj, 4)}
        if adj <= 0:
            out["checks"]["1 positive net mean"] = False
            out["checks"]["1b audit-adjusted mean > 0"] = False
            out["adopted"] = False
        else:
            out["checks"]["1b audit-adjusted mean > 0"] = True
            out["adopted"] = all(out["checks"].values())
        P.record_result(fam + " audit", out["audit"] | {"adopted": out["adopted"]})
        print(json.dumps(out, indent=1, default=str))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("family", choices=("F1", "F2", "F3", "F4", "F5"))
    ap.add_argument("--stage", choices=("search", "holdout"), default="search")
    args = ap.parse_args(argv)
    ctx = Ctx(features=True)
    {"F1": f1, "F2": f2, "F4": f4, "F5": f5}[args.family](ctx, args.stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
