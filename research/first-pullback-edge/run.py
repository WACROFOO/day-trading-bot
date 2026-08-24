#!/usr/bin/env python3
"""First-pullback edge study - the executable pipeline.

    python3 run.py universe   --start 2022-09-01 --end 2026-08-21
    python3 run.py fetch       --days 25
    python3 run.py ablation    --days 25
    python3 run.py report

Every stage writes a manifest (results/run_manifest.json) carrying the git
commit, the config hash, the study period, the cost assumptions and the seed,
so the same version run twice reproduces the same numbers (brief section 31).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.backtest import run_day, trade_records                    # noqa: E402
from src.data import ET, YahooProvider, get_provider               # noqa: E402
from src.execution import COST_MODELS                              # noqa: E402
from src.indicators import same_time_cum_volume_profile            # noqa: E402
from src.metrics import (account_simulation, clustered_bootstrap,   # noqa: E402
                         by_bucket, core_metrics, verdict)
from src.setups import GATE_IDS, Params, Variant                   # noqa: E402
from src.universe import (ScanRules, candidate_days,                 # noqa: E402
                          candidate_days_grouped, nasdaq_listed,
                          qualify_intraday, to_records)
from src import validation as V                                    # noqa: E402

DATA = ROOT / "data"
RESULTS = ROOT / "results"
REPORTS = ROOT / "reports"
for d in (DATA, RESULTS, REPORTS):
    d.mkdir(parents=True, exist_ok=True)

CFG_PATH = ROOT / "config" / "strategy.yaml"


# ------------------------------------------------------------------ config --
def load_config() -> dict:
    return yaml.safe_load(CFG_PATH.read_text())


def _v(node):
    return node["value"] if isinstance(node, dict) and "value" in node else node


def params_from_config(cfg: dict) -> Params:
    i, pb, c, h, r, e = (cfg["impulse"], cfg["pullback"], cfg["confluence"],
                         cfg["hod_room"], cfg["risk"], cfg["execution"])
    sess = cfg["session"]["arm_window_et"]
    return Params(
        min_push_pct=_v(i["min_push_pct"]), min_impulse_bars=_v(i["min_impulse_bars"]),
        max_impulse_bars=_v(i["max_impulse_bars"]), min_push_atr=_v(i["min_push_atr"]),
        min_efficiency=_v(i["min_efficiency"]),
        vol_baseline_bars=_v(i["volume_baseline_bars"]),
        min_push_rvol=_v(i["min_push_rvol"]),
        min_dollar_volume=_v(i["min_dollar_volume"]),
        min_pullback_bars=_v(pb["min_pullback_bars"]),
        max_pullback_bars=_v(pb["max_pullback_bars"]),
        max_retracement_pct=_v(pb["max_retracement_pct"]),
        max_pb_volume_ratio=_v(pb["max_pb_volume_ratio"]),
        support_tolerance_pct=_v(c["support_tolerance_pct"]),
        support_tolerance_atr=_v(c["support_tolerance_atr"]),
        min_support_count=_v(c["min_support_count"]),
        min_room_r=_v(h["min_room_r"]),
        max_stop_pct=_v(r["max_stop_pct"]), max_stop_atr=_v(r["max_stop_atr"]),
        atr_stop_fallback=_v(r["atr_stop_fallback"]),
        fallback_atr_mult=_v(r["fallback_atr_mult"]),
        account_equity=_v(r["account_equity"]), risk_pct=_v(r["risk_pct"]),
        max_position_value=_v(r["max_position_value"]),
        slip_ticks_sizing=_v(r["slip_ticks_sizing"]),
        tick=e["tick"], breakout_buffer_ticks=_v(e["breakout_buffer_ticks"]),
        reward_multiple=_v(e["reward_multiple"]),
        arm_start_et=dt.time(*map(int, sess["start"].split(":"))),
        arm_end_et=dt.time(*map(int, sess["end"].split(":"))))


def variants_from_config(cfg: dict) -> dict[str, Variant]:
    out = {}
    for name, spec in cfg["variants"].items():
        out[name] = Variant(
            name=name, label=spec["label"], gates=tuple(spec["gates"]),
            lanes=bool(spec.get("lanes")), retest=bool(spec.get("retest")),
            late_join=bool(spec.get("late_join")),
            third_trade_half_size=bool(spec.get("third_trade_half_size")))
    return out


def manifest(cfg: dict, extra: dict) -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = "unknown"
    m = dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        git_commit=commit,
        config_sha256=hashlib.sha256(CFG_PATH.read_bytes()).hexdigest(),
        strategy_file=cfg["meta"]["strategy_file"],
        strategy_rev=cfg["meta"]["strategy_rev"],
        seed=cfg["seed"],
        python=sys.version.split()[0],
        cost_scenarios={k: v for k, v in cfg["costs"]["scenarios"].items()},
        timezone="America/New_York",
    )
    m.update(extra)
    return m


def write_manifest(cfg, extra):
    path = RESULTS / "run_manifest.json"
    cur = json.loads(path.read_text()) if path.exists() else {}
    cur.update(manifest(cfg, extra))
    path.write_text(json.dumps(cur, indent=2))


# -------------------------------------------------------------- parquet io --
def save_table(rows: list[dict], name: str):
    import pandas as pd
    df = pd.DataFrame(rows)
    try:
        df.to_parquet(DATA / f"{name}.parquet", index=False)
    except Exception as e:                                      # noqa: BLE001
        print(f"  (parquet unavailable: {e}; csv only)")
    df.to_csv(DATA / f"{name}.csv", index=False)
    return df


def save_results(rows: list[dict], name: str):
    import pandas as pd
    pd.DataFrame(rows).to_csv(RESULTS / f"{name}.csv", index=False)


# ------------------------------------------------------------ stage: universe
def stage_universe(args):
    """Multi-year point-in-time candidate universe from daily bars."""
    cfg = load_config()
    u = cfg["universe"]
    rules = ScanRules(price_min=_v(u["price_min"]), price_max=_v(u["price_max"]),
                      gap_min_pct=_v(u["gap_min_pct"]),
                      min_dollar_volume=_v(u["min_premarket_dollar_volume"]))
    provider = get_provider(args.provider)
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)

    pool_path = DATA / "symbol_pool.json"
    if pool_path.exists() and not args.refresh_pool:
        pool = json.loads(pool_path.read_text())
    else:
        pool = nasdaq_listed()
        pool_path.write_text(json.dumps(pool))
    # -- grouped path: one call per DATE, survivorship-free --------------
    if args.grouped:
        if not hasattr(provider, "grouped_daily"):
            print(f"provider {provider.name} has no grouped_daily; "
                  f"drop --grouped or switch provider"); return

        def prog(day, n, tickers, cands):
            print(f"  {day}  session {n:>4}  {tickers:>6} tickers  "
                  f"{cands:>6} candidate-days so far", flush=True)

        rows = candidate_days_grouped(provider, start, end, rules,
                                      progress=prog)
        _finish_universe(cfg, rules, to_records(rows), args,
                         symbols_scanned=None, provider=provider)
        return

    syms = sorted({p["sym"] for p in pool})
    if args.limit:
        rng = random.Random(cfg["seed"])
        syms = sorted(rng.sample(syms, min(args.limit, len(syms))))
    print(f"universe: {len(syms)} symbols, {start} -> {end}, provider={provider.name}")

    rows, done = [], [0]

    def work(sym):
        try:
            r = candidate_days(provider, [sym], start, end, rules)
        except Exception:                                      # noqa: BLE001
            r = []
        done[0] += 1
        if done[0] % 250 == 0:
            print(f"  {done[0]}/{len(syms)} symbols, {len(rows)} candidate-days")
        return r

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(work, syms):
            rows.extend(r)

    _finish_universe(cfg, rules, to_records(rows), args,
                     symbols_scanned=len(syms), provider=provider)


def _finish_universe(cfg, rules, recs, args, symbols_scanned, provider):
    df = save_table(recs, "candidate_days")
    by_year = {}
    if len(df):
        df["year"] = df["day"].str[:4]
        by_year = df.groupby("year").agg(
            ticker_days=("sym", "size"), sessions=("day", "nunique"),
            names=("sym", "nunique")).reset_index().to_dict("records")
    summary = dict(provider=provider.name,
                   construction="grouped_daily (survivorship-free)" if args.grouped
                   else "symbol list (survivorship-biased snapshot)",
                   symbols_scanned=symbols_scanned, candidate_days=len(recs),
                   sessions=int(df["day"].nunique()) if len(df) else 0,
                   distinct_names=int(df["sym"].nunique()) if len(df) else 0,
                   by_year=by_year,
                   reverse_split_flagged=int(df["reverse_split_ratio"].notna().sum())
                   if len(df) else 0)
    save_results(by_year, "universe_by_year")
    (RESULTS / "universe_summary.json").write_text(json.dumps(summary, indent=2))
    write_manifest(cfg, dict(universe=dict(
        start=args.start, end=args.end,
        rules=rules.__dict__ | {"scan_time_et": str(rules.scan_time_et)},
        **{k: v for k, v in summary.items() if k != "by_year"})))
    print(json.dumps(summary, indent=2)[:2500])


# --------------------------------------------------------------- stage: fetch
def _trading_days(n: int) -> list[dt.date]:
    today = dt.datetime.now(ET).date()
    out, d = [], today
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= dt.timedelta(days=1)
    return sorted(out)


def stage_fetch(args):
    """Pull the minute window that is actually obtainable, for the candidate
    days that fall inside it. Point-in-time selection: a name is fetched
    because it GAPPED, not because it later ran."""
    cfg = load_config()
    provider = get_provider(args.provider)
    days = _trading_days(args.days)
    lo, hi = days[0], days[-1]
    print(f"fetch window {lo} -> {hi} ({len(days)} sessions)")

    cand_path = DATA / "candidate_days.csv"
    if not cand_path.exists():
        print("no candidate_days.csv - run `universe` first"); return
    import pandas as pd
    cd = pd.read_csv(cand_path)
    cd = cd[(cd["day"] >= lo.isoformat()) & (cd["day"] <= hi.isoformat())]
    cd = cd[~cd["reverse_split_ratio"].notna()]          # split artefacts out
    pairs = sorted({(r.sym, r.day) for r in cd.itertuples()})
    print(f"  {len(pairs)} candidate ticker-days inside the minute window")

    ok = [0]

    def work(pair):
        sym, day = pair
        d = dt.date.fromisoformat(day)
        try:
            bars = provider.minute_bars(sym, d, premarket=True)
        except Exception:                                      # noqa: BLE001
            bars = []
        ok[0] += 1
        if ok[0] % 100 == 0:
            print(f"  fetched {ok[0]}/{len(pairs)}")
        return (sym, day, len(bars))

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        res = list(ex.map(work, pairs))
    have = [r for r in res if r[2] > 0]
    print(f"  minute bars present for {len(have)}/{len(res)} ticker-days")
    write_manifest(cfg, dict(minute_window=dict(
        start=lo.isoformat(), end=hi.isoformat(), sessions=len(days),
        ticker_days_requested=len(res), ticker_days_with_bars=len(have))))


# ------------------------------------------------------------ stage: ablation
def stage_ablation(args):
    cfg = load_config()
    params = params_from_config(cfg)
    variants = variants_from_config(cfg)
    provider = get_provider(args.provider)
    rules = ScanRules(price_min=_v(cfg["universe"]["price_min"]),
                      price_max=_v(cfg["universe"]["price_max"]),
                      gap_min_pct=_v(cfg["universe"]["gap_min_pct"]),
                      min_dollar_volume=_v(cfg["universe"]["min_premarket_dollar_volume"]),
                      scan_time_et=dt.time(*map(int, _v(cfg["universe"]["scan_timestamp_et"]).split(":"))))
    cap_pct = _v(cfg["execution"]["stop_limit_cap_pct"])
    cap_ticks = _v(cfg["execution"]["stop_limit_cap_ticks"])
    pairs, lo, hi = _select_candidates(cfg, args.start, args.end, args.days)
    print(f"ablation, {lo} -> {hi}")
    if args.prefetch:
        _prefetch_minute_months(provider, pairs)

    # ---- load bars once, qualify the scanner point-in-time ----------
    def _load(pair):
        sym, day, prev_close = pair
        d = dt.date.fromisoformat(day)
        try:
            bars = provider.minute_bars(sym, d, premarket=True)
        except Exception as e:                                  # noqa: BLE001
            print(f"    skip {sym} {day}: {str(e)[:70]}")
            return None
        if len(bars) < 60:
            return None
        prior = _prior_sessions(provider, sym, d, 3)
        profile = same_time_cum_volume_profile(prior) if prior else None
        q = qualify_intraday(sym, d, bars, prev_close, rules, profile)
        if q is None or not q.qualified_intraday:
            return None
        return (sym, d, bars, prev_close, profile, q.scan_ts, q)

    # a month-chunked provider serves every day from one cached request, so
    # threading it would only multiply rate-limit pressure for no gain
    workers = 1 if hasattr(provider, "minute_month") else args.workers
    with ThreadPoolExecutor(max_workers=workers) as ex:
        raw = [r for r in ex.map(_load, pairs) if r is not None]
    loaded = [r[:6] for r in raw]
    save_table([{k: v for k, v in r[6].__dict__.items()} for r in raw],
               "scanned_ticker_days")
    print(f"  {len(loaded)} ticker-days pass the {rules.scan_time_et} "
          f"point-in-time scanner")

    all_trades, all_setups, all_missed = [], [], []
    policies = ["pessimistic", "optimistic", "exclude"]
    experiments = [("exp1_common_exits", False), ("exp2_full_management", True)]

    for vname, variant in variants.items():
        for cost_name in ("gross", "low", "realistic", "stressed"):
            cost = COST_MODELS[cost_name]
            for policy in policies:
                for exp, is_full in experiments:
                    if exp == "exp2_full_management" and vname != "F":
                        continue
                    for sym, d, bars, prev_close, profile, scan_ts in loaded:
                        r = run_day(sym, d, bars, params, variant, cost, policy,
                                    experiment=exp, prev_close=prev_close,
                                    same_time_profile=profile, scan_ts=scan_ts,
                                    limit_cap_pct=cap_pct, limit_cap_ticks=cap_ticks)
                        all_trades.extend(trade_records(r.trades))
                        all_missed.extend([m.__dict__ for m in r.missed])
                        if (cost_name == "realistic" and policy == "pessimistic"
                                and exp == "exp1_common_exits"):
                            for s in r.observed:
                                row = {k: v for k, v in s.__dict__.items() if k != "gates"}
                                row["variant"] = vname
                                row.update({f"gate_{g}": s.gates.get(g)
                                            for g in GATE_IDS})
                                row["passes_variant"] = s.passes(variant)
                                all_setups.append(row)
        print(f"  variant {vname}: cumulative trades {len(all_trades)}")

    save_table(all_trades, "trades")
    save_table(all_setups, "rejected_setups")
    save_table(all_missed, "missed_entries")
    write_manifest(cfg, dict(ablation=dict(
        candidate_ticker_days=len(pairs), scanned_ticker_days=len(loaded),
        sessions=len({d.isoformat() for _, d, *_ in loaded}),
        trades_rows=len(all_trades), setups_rows=len(all_setups))))
    print(f"wrote {len(all_trades)} trade rows, {len(all_setups)} setup rows")


# --------------------------------------------------------------- stage: report
def _sel(trades, **kw):
    return [t for t in trades
            if all(t.get(k) == v for k, v in kw.items())]


def stage_report(args):
    cfg = load_config()
    import pandas as pd
    tp = DATA / "trades.csv"
    if not tp.exists():
        print("no trades.csv - run `ablation` first"); return
    trades = pd.read_csv(tp).to_dict("records")
    setups = (pd.read_csv(DATA / "rejected_setups.csv").to_dict("records")
              if (DATA / "rejected_setups.csv").exists() else [])
    order = ["A", "B", "C", "D", "E", "F"]
    secondary = ["A", "B", "D_noconf", "E_noconf", "F"]

    base = dict(cost_model="realistic", ambiguity_policy="pessimistic",
                experiment="exp1_common_exits")
    all_variants = order + [v for v in ("D_noconf", "E_noconf")
                            if v in cfg["variants"]]
    per_variant = {v: _sel(trades, variant=v, **base) for v in all_variants}

    # ---- summary + ablation ----------------------------------------
    summary = []
    for v in order:
        t = per_variant[v]
        m = core_metrics(t)
        ci = clustered_bootstrap(t, "expectancy_r", seed=cfg["seed"])
        wci = clustered_bootstrap(t, "win_rate", seed=cfg["seed"])
        m.update(variant=v, label=cfg["variants"][v]["label"],
                 exp_ci_lo=ci["lo"], exp_ci_hi=ci["hi"],
                 win_ci_lo=wci["lo"], win_ci_hi=wci["hi"],
                 bootstrap_days=ci["days"],
                 verdict=verdict(ci, m.get("trades", 0)))
        summary.append(m)
    save_results(summary, "summary")
    save_results(V.ablation_marginals(per_variant, order), "ablation")

    # the shipped strategy's own gate order, without the confluence rung the
    # Pine does not actually contain (see config/strategy.yaml `variants`)
    per_secondary = {v: _sel(trades, variant=v, **base) for v in secondary}
    sec_summary = []
    for v in secondary:
        t2 = per_secondary[v]
        m = core_metrics(t2)
        ci = clustered_bootstrap(t2, "expectancy_r", seed=cfg["seed"])
        m.update(variant=v, label=cfg["variants"][v]["label"],
                 exp_ci_lo=ci["lo"], exp_ci_hi=ci["hi"],
                 verdict=verdict(ci, m.get("trades", 0)))
        sec_summary.append(m)
    save_results(sec_summary, "summary_secondary")
    save_results(V.ablation_marginals(per_secondary, secondary), "ablation_secondary")

    # ---- costs and ambiguity ---------------------------------------
    cost_rows = []
    for v in all_variants:
        for c in ("gross", "low", "realistic", "stressed"):
            for p in ("pessimistic", "optimistic", "exclude"):
                t = _sel(trades, variant=v, cost_model=c, ambiguity_policy=p,
                         experiment="exp1_common_exits")
                m = core_metrics(t)
                m.update(variant=v, cost_model=c, ambiguity_policy=p)
                cost_rows.append(m)
    save_results(cost_rows, "cost_sensitivity")

    # ---- yearly / regime -------------------------------------------
    yearly = []
    for v in all_variants:
        by_y = {}
        for t in per_variant[v]:
            by_y.setdefault(t["day"][:4], []).append(t)
        for y, ts in sorted(by_y.items()):
            m = core_metrics(ts)
            m.update(variant=v, year=y)
            yearly.append(m)
    save_results(yearly, "yearly")
    regime = []
    for v in all_variants:
        for row in V.regime_buckets(per_variant[v]):
            row["variant"] = v
            regime.append(row)
    save_results(regime, "regime")

    # ---- stock-characteristic cuts (brief section 17) ---------------
    cuts = []
    B = {
        "price": ([("2-5", 2, 5), ("5-10", 5, 10), ("10-20", 10, 20)],
                  lambda t: t.get("ctx_price")),
        "gap": ([("10-20", 10, 20), ("20-50", 20, 50), ("50-100", 50, 100),
                 (">100", 100, 1e9)], lambda t: t.get("ctx_gap_pct")),
        "pullback_depth": ([("<20", 0, 20), ("20-35", 20, 35), ("35-50", 35, 50),
                            (">50", 50, 1e9)], lambda t: t.get("ctx_pullback_depth_pct")),
        "pullback_number": ([("1", 1, 2), ("2", 2, 3), ("3+", 3, 99)],
                            lambda t: t.get("ctx_pullback_number")),
        "push_pct": ([("5-8", 5, 8), ("8-15", 8, 15), (">15", 15, 1e9)],
                     lambda t: t.get("ctx_push_pct")),
        "rvol": ([("<2", 0, 2), ("2-5", 2, 5), (">5", 5, 1e9)],
                 lambda t: t.get("ctx_rvol_at_time")),
        "confluence": ([("0", 0, 1), ("1", 1, 2), ("2+", 2, 9)],
                       lambda t: t.get("ctx_confluence_count")),
    }
    for v in all_variants:
        for cut, (buckets, key) in B.items():
            for row in by_bucket(per_variant[v], key, buckets):
                row.update(variant=v, cut=cut)
                cuts.append(row)
    save_results(cuts, "characteristics")

    # ---- rejected-trade analysis (brief section 20) ------------------
    # Counterfactual: run variant A's trades and split them by each gate.
    a_trades = per_variant["A"]
    by_gate = {}
    for g in ("momentum", "confluence", "pb_volume", "hod_room", "halt_band"):
        acc = [t for t in a_trades if _gate_of(setups, t, g) is True]
        rej = [t for t in a_trades if _gate_of(setups, t, g) is False]
        by_gate[g] = dict(accepted=acc, rejected=rej)
    save_results(V.accepted_vs_rejected(by_gate), "rejected_trades")

    # ---- filter overlap (brief section 21) --------------------------
    obs = [s for s in setups if s.get("variant") == "A"]
    overlap_rows = []
    gates = ["momentum", "confluence", "pb_volume", "hod_room", "risk_structural",
             "retracement", "pullback_structure", "halt_band"]
    shaped = [{"gates": {g: s.get(f"gate_{g}") for g in gates}} for s in obs]
    for row in V.gate_overlap(shaped, gates):
        overlap_rows.append(row)
    save_results(overlap_rows, "filter_overlap")

    # ---- splits / holdout -------------------------------------------
    days = sorted({t["day"] for t in trades})
    sp = V.chronological_splits(days, _v(cfg["splits"]["development_frac"]),
                                _v(cfg["splits"]["validation_frac"]),
                                _v(cfg["splits"]["holdout_frac"]))
    hold_rows = []
    for v in all_variants:
        for part in ("development", "validation", "holdout"):
            sel = [t for t in per_variant[v] if t["day"] in set(sp[part])]
            m = core_metrics(sel)
            ci = clustered_bootstrap(sel, seed=cfg["seed"])
            m.update(variant=v, split=part, exp_ci_lo=ci["lo"], exp_ci_hi=ci["hi"],
                     sessions_in_split=len(sp[part]))
            hold_rows.append(m)
    save_results(hold_rows, "holdout")
    (RESULTS / "splits.json").write_text(json.dumps(sp, indent=2))

    # ---- account simulation (brief section 26) ----------------------
    acct = []
    for v in all_variants:
        a = account_simulation(per_variant[v],
                               equity0=_v(cfg["risk"]["account_equity"]),
                               risk_pct=_v(cfg["risk"]["risk_pct"]),
                               max_position_value=_v(cfg["risk"]["max_position_value"]))
        a.pop("curve", None)
        a["variant"] = v
        acct.append(a)
    save_results(acct, "account_simulation")

    (RESULTS / "report_inputs.json").write_text(json.dumps(dict(
        splits=sp, n_trades=len(trades),
        variants={v: len(per_variant[v]) for v in order}), indent=2))
    print(json.dumps({v: core_metrics(per_variant[v]).get("trades", 0)
                      for v in all_variants}, indent=2))


def _gate_of(setups, trade, gate):
    for s in setups:
        if (s.get("sym") == trade["sym"] and s.get("day") == trade["day"]
                and s.get("ts") == trade["setup_ts"] and s.get("variant") == "A"):
            return s.get(f"gate_{gate}")
    return None



# --------------------------------------------------------- stage: sensitivity
def stage_sensitivity(args):
    """brief section 23 - perturb, do not search.

    Run AFTER the frozen A-F experiment. Each parameter is moved through a
    small neighbourhood around its shipped value while everything else stays
    fixed. A robust rule shows a plateau; a fitted one shows a spike on the
    shipped number.

    `max_stop_pct` is first in the list on purpose. The sibling study
    (research/megaday-study/RESULTS.md) measured the population's median stop
    at 3.02% of price against a cap of exactly 3.0 - a cap that is nowhere in
    the corpus, sits on the median, and removes 51% of setups. If that finding
    replicates here, the ablation's absolute level says more about one
    unsourced number than about any of the six variants.
    """
    cfg = load_config()
    base = params_from_config(cfg)
    variants = variants_from_config(cfg)
    provider = get_provider(args.provider)
    rules = _rules(cfg)
    loaded = _load_scanned(provider, cfg, rules, args.days, args.workers, args)
    cost = COST_MODELS["realistic"]

    grid = {
        "max_stop_pct": [1.5, 2.0, 3.0, 4.5, 6.0, 9.0],
        "max_pb_volume_ratio": [0.50, 0.60, 0.70, 0.80, 0.90],
        "max_retracement_pct": [30.0, 40.0, 50.0, 60.0, 70.0],
        "min_push_pct": [3.0, 4.0, 5.0, 6.5, 8.0],
        "min_room_r": [0.0, 0.5, 1.0, 1.5, 2.0],
        "reward_multiple": [1.5, 2.0, 2.5, 3.0, 4.0],
        "min_efficiency": [0.40, 0.50, 0.60, 0.70, 0.80],
        "max_pullback_bars": [2, 3, 4, 5, 6],
        "fallback_atr_mult": [0.5, 1.0, 1.5, 2.0, 3.0],
    }
    rows = []
    for vname in (args.variants or ["A", "E", "F"]):
        variant = variants[vname]
        for pname, values in grid.items():
            for val in values:
                v2 = Variant(**{**variant.__dict__, "override": {pname: val}})
                # the override has to reach the EXECUTION model too, not only
                # the setup detector: reward_multiple and the risk caps live
                # on both sides. Passing the un-overridden base here silently
                # froze every exit-side parameter at its shipped value.
                p2 = v2.p(base)
                trades = []
                for sym, d, bars, prev_close, profile, scan_ts in loaded:
                    r = run_day(sym, d, bars, p2, v2, cost, "pessimistic",
                                prev_close=prev_close, same_time_profile=profile,
                                scan_ts=scan_ts)
                    trades.extend(trade_records(r.trades))
                m = core_metrics(trades)
                ci = clustered_bootstrap(trades, seed=cfg["seed"])
                rows.append(dict(variant=vname, parameter=pname, value=val,
                                 shipped=(val == getattr(base, pname)),
                                 trades=m.get("trades", 0),
                                 expectancy_r=m.get("expectancy_r"),
                                 win_rate=m.get("win_rate"),
                                 profit_factor=m.get("profit_factor"),
                                 max_dd_r=m.get("max_dd_r"),
                                 ci_lo=ci["lo"], ci_hi=ci["hi"]))
            print(f"  {vname} {pname}: done")
    save_results(rows, "sensitivity")
    print(f"wrote {len(rows)} sensitivity rows")


# ------------------------------------------------------------ stage: placebo
def stage_placebo(args):
    """brief sections 24 and 25 - baselines and null tests.

    A real structural edge has to distinguish itself from arbitrary rules on
    the same tape. Four comparisons, all on the identical exit model:
      base_A       variant A as shipped (the simple first pullback)
      pullback_2   the SECOND pullback only, first refused
      pullback_3p  the third and later
      shift_up/down  the trigger moved 5 ticks either way
      random_entry  a random minute in 09:35-11:30, stop 1 ATR below
    """
    cfg = load_config()
    base = params_from_config(cfg)
    variants = variants_from_config(cfg)
    provider = get_provider(args.provider)
    rules = _rules(cfg)
    loaded = _load_scanned(provider, cfg, rules, args.days, args.workers, args)
    cost = COST_MODELS["realistic"]
    A = variants["A"]

    defs = {
        "base_A": Variant(**{**A.__dict__}),
        "pullback_1_only": Variant(**{**A.__dict__,
                                      "gates": A.gates + ("pullback_number",),
                                      "allowed_pullback_numbers": (1,)}),
        "pullback_2_only": Variant(**{**A.__dict__,
                                      "gates": A.gates + ("pullback_number",),
                                      "allowed_pullback_numbers": (2,)}),
        "pullback_3plus": Variant(**{**A.__dict__,
                                     "gates": A.gates + ("pullback_number",),
                                     "allowed_pullback_numbers": tuple(range(3, 40))}),
        "trigger_shift_up_5t": Variant(**{**A.__dict__, "trigger_offset_ticks": 5}),
        "trigger_shift_down_5t": Variant(**{**A.__dict__, "trigger_offset_ticks": -5}),
    }
    rows, ledger = [], []
    for name, variant in defs.items():
        trades = []
        for sym, d, bars, prev_close, profile, scan_ts in loaded:
            r = run_day(sym, d, bars, base, variant, cost, "pessimistic",
                        prev_close=prev_close, same_time_profile=profile,
                        scan_ts=scan_ts)
            trades.extend(trade_records(r.trades))
        for t in trades:
            t["variant"] = name
        ledger.extend(trades)
        m = core_metrics(trades)
        ci = clustered_bootstrap(trades, seed=cfg["seed"])
        m.update(baseline=name, ci_lo=ci["lo"], ci_hi=ci["hi"],
                 verdict=verdict(ci, m.get("trades", 0)))
        rows.append(m)
        print(f"  {name}: {m.get('trades', 0)} trades, "
              f"exp {m.get('expectancy_r', float('nan')):.3f}R")

    # baseline 1: random entry minute on the same qualifying ticker-days
    rows.append(_baseline_random(loaded, base, cost, cfg))
    save_results(rows, "baselines")
    save_table(ledger, "placebo_trades")


def _baseline_random(loaded, params, cost, cfg, n_draws: int = 5):
    """A random minute between 09:35 and 11:30 on a qualifying candidate,
    1-ATR stop, the same T1/runner ladder. If the elaborate pattern cannot
    beat this, the pattern is not where the edge lives."""
    from src.execution import PositionSim
    from src.indicators import SessionState
    rng = random.Random(cfg["seed"])
    trades = []
    for draw in range(n_draws):
        for sym, d, bars, prev_close, profile, scan_ts in loaded:
            st = SessionState(sym, d, prev_close=prev_close,
                              same_time_cum_volume=profile)
            snaps = [st.update(b) for b in bars]
            window = [k for k, s in enumerate(snaps)
                      if dt.time(9, 35) <= s.et.time() < dt.time(11, 30)]
            if len(window) < 10:
                continue
            k = rng.choice(window[:-5])
            s = snaps[k]
            if not s.atr or s.atr <= 0:
                continue
            entry = s.bar.c
            stop = entry - s.atr
            shares = min(int((params.account_equity * params.risk_pct / 100.0)
                             // (entry - stop)),
                         int(params.max_position_value // entry))
            if shares < 1:
                continue
            fake = type("S", (), dict(stop=stop, risk_per_share=entry - stop,
                                      ts=s.bar.ts, et=s.et.isoformat(),
                                      trigger=entry, planned_shares=shares,
                                      kind="random", atr=s.atr))()
            pos = PositionSim(fake, entry, shares, k, s.bar, cost, params,
                              stop_active_same_bar=False, bailout=False)
            for j in range(k + 1, len(snaps)):
                if pos.step(snaps[j], j):
                    break
                if snaps[j].et.time() >= params.arm_end_et:
                    pos.force_flat(snaps[j], "SESSION_FLAT")
                    break
            if pos.closed is None:
                pos.force_flat(snaps[-1], "DAY_END")
            gross = pos.banked
            fees = cost.fee(pos.orders)
            r_unit = pos.rps * pos.shares_open
            trades.append(dict(day=d.isoformat(), net_r=(gross - fees) / r_unit,
                               net_pnl=gross - fees, mfe_r=pos.mfe, mae_r=pos.mae,
                               ambiguous=False, halt_flag=pos.halt,
                               participation_capped=False))
    m = core_metrics(trades)
    ci = clustered_bootstrap(trades, seed=cfg["seed"])
    m.update(baseline=f"random_entry_x{n_draws}", ci_lo=ci["lo"], ci_hi=ci["hi"],
             verdict=verdict(ci, m.get("trades", 0)))
    print(f"  random_entry: {m.get('trades', 0)} trades, "
          f"exp {m.get('expectancy_r', float('nan')):.3f}R")
    return m


def _select_candidates(cfg, start: str | None, end: str | None,
                       days_back: int | None, cap: int | None = None):
    """The candidate ticker-days the intraday study will actually work on.

    Two knobs, both point-in-time and both DISCOVERY dials rather than entry
    gates: the date range, and `max_names_per_session` — the top-N gappers
    of each session, ranked on a gap that is known at 09:30. Reverse-split
    artefacts are dropped here (flagged in the universe table, never
    silently vetoed there).
    """
    import pandas as pd
    cd = pd.read_csv(DATA / "candidate_days.csv")
    if start and end:
        lo, hi = start, end
    else:
        days = _trading_days(days_back or 25)
        lo, hi = days[0].isoformat(), days[-1].isoformat()
    cd = cd[(cd["day"] >= lo) & (cd["day"] <= hi)]
    cd = cd[cd["reverse_split_ratio"].isna()]
    cap = cap if cap is not None else _v(cfg["universe"].get(
        "max_names_per_session", {"value": 0}))
    if cap:
        cd = (cd.sort_values(["day", "gap_pct"], ascending=[True, False])
                .groupby("day", group_keys=False).head(int(cap)))
    pairs = sorted({(r.sym, r.day, r.prev_close) for r in cd.itertuples()})
    print(f"  {len(pairs)} candidate ticker-days, {cd['day'].nunique()} sessions, "
          f"{cd['sym'].nunique()} names  [{lo} -> {hi}, cap {cap or 'none'}/session]")
    return pairs, lo, hi


def _prefetch_minute_months(provider, pairs, workers: int = 1):
    """Warm the month cache before the run.

    On a month-chunked provider this is one request per (ticker, month), so
    a 2,500-ticker-day study costs roughly the number of distinct ticker
    months, not 2,500 — the difference between six hours and a day.
    """
    if not hasattr(provider, "minute_month"):
        return
    months = sorted({(sym, day[:4], day[5:7]) for sym, day, _ in pairs})
    print(f"  prefetching {len(months)} ticker-months "
          f"(~{len(months) / 5 / 60:.1f}h at 5 calls/min)")
    for n, (sym, y, m) in enumerate(months, 1):
        try:
            provider.minute_month(sym, int(y), int(m))
        except Exception as e:                                  # noqa: BLE001
            print(f"    {sym} {y}-{m}: {str(e)[:80]}")
        if n % 25 == 0:
            print(f"    {n}/{len(months)}", flush=True)


def _prior_sessions(provider, sym: str, day: dt.date, n: int) -> list:
    """The n previous sessions' bars, for the RVOL-at-time denominator.

    On a month-chunked provider these are already in the cache the target
    day came from, so they cost nothing. Only prior days are ever read —
    that is what keeps RVOL-at-time free of look-ahead.
    """
    out, d, tried = [], day - dt.timedelta(days=1), 0
    while len(out) < n and tried < 10:
        tried += 1
        if d.weekday() < 5:
            try:
                pb = provider.minute_bars(sym, d, premarket=True)
            except Exception:                                   # noqa: BLE001
                pb = []
            if pb:
                out.append(pb)
        d -= dt.timedelta(days=1)
    return out


def _rules(cfg):
    u = cfg["universe"]
    return ScanRules(price_min=_v(u["price_min"]), price_max=_v(u["price_max"]),
                     gap_min_pct=_v(u["gap_min_pct"]),
                     min_dollar_volume=_v(u["min_premarket_dollar_volume"]),
                     scan_time_et=dt.time(*map(int, _v(u["scan_timestamp_et"]).split(":"))))


def _load_scanned(provider, cfg, rules, days_back: int, workers: int,
                  args_ns=None):
    """Reload the point-in-time-qualified ticker-days used by the ablation."""
    pairs, lo, hi = _select_candidates(cfg, getattr(args_ns, "start", None),
                                       getattr(args_ns, "end", None), days_back)

    def _load(pair):
        sym, day, prev_close = pair
        d = dt.date.fromisoformat(day)
        try:
            bars = provider.minute_bars(sym, d, premarket=True)
        except Exception as e:                                  # noqa: BLE001
            print(f"    skip {sym} {day}: {str(e)[:70]}")
            return None
        if len(bars) < 60:
            return None
        prior = _prior_sessions(provider, sym, d, 3)
        profile = same_time_cum_volume_profile(prior) if prior else None
        q = qualify_intraday(sym, d, bars, prev_close, rules, profile)
        if q is None or not q.qualified_intraday:
            return None
        return (sym, d, bars, prev_close, profile, q.scan_ts)

    workers = 1 if hasattr(provider, "minute_month") else workers
    with ThreadPoolExecutor(max_workers=workers) as ex:
        out = [r for r in ex.map(_load, pairs) if r is not None]
    print(f"  {len(out)} qualified ticker-days loaded")
    return out



# ------------------------------------------------------------ stage: verify
def stage_verify(args):
    """The three decisive tests, run against whatever key is present.

    reports/data_acquisition.md says which free tiers claim what. This stage
    does not trust any of it: it makes the requests and prints what came
    back. Run it the moment a key is added, before any backtest is believed.
    """
    from src.data import NasdaqHaltFeed, PROVIDERS
    name = args.provider or ("polygon" if os.environ.get("POLYGON_API_KEY")
                             or os.environ.get("MASSIVE_API_KEY")
                             else "alpaca" if os.environ.get("ALPACA_API_KEY_ID")
                             else "yahoo")
    prov = PROVIDERS[name]()
    print(f"VERIFYING provider={name} enabled={getattr(prov, 'enabled', True)}\n")
    day = dt.date.fromisoformat(args.day) if args.day else None
    if day is None:
        day = dt.datetime.now(ET).date() - dt.timedelta(days=args.days_back)
        while day.weekday() >= 5:
            day -= dt.timedelta(days=1)

    ok = {}

    # TEST 1 — extended-hours volume. The one that decides everything.
    print(f"[1] pre-market VOLUME on {day} (AAPL)")
    try:
        bars = prov.minute_bars("AAPL", day, premarket=True)
        pm = [b for b in bars if b.et.time() < dt.time(9, 30)]
        withvol = sum(1 for b in pm if b.v > 0)
        print(f"    {len(pm)} pre-market bars, {withvol} carry volume")
        ok["premarket_volume"] = withvol > 0
        print("    -> PASS" if withvol else "    -> FAIL (this is the Yahoo blocker)")
    except Exception as e:                                       # noqa: BLE001
        print(f"    ERROR {e}"); ok["premarket_volume"] = False

    # TEST 2 — delisted retention. The survivorship fix.
    print(f"\n[2] delisted retention")
    hits = 0
    for sym in ("MULN", "BBBYQ", "ATVI", "SIVBQ"):
        try:
            n = len(prov.daily_bars(sym, day - dt.timedelta(days=900), day))
        except Exception:                                        # noqa: BLE001
            n = 0
        print(f"    {sym:<6} {n} daily bars")
        hits += 1 if n else 0
    ok["delisted"] = hits >= 2
    print(f"    -> {'PASS' if ok['delisted'] else 'FAIL'} ({hits}/4 retained)")

    # TEST 3 — history depth for MINUTE bars, which is the study's real limit
    print(f"\n[3] minute-bar history depth")
    for back in (30, 90, 365, 700, 1200):
        d = dt.datetime.now(ET).date() - dt.timedelta(days=back)
        while d.weekday() >= 5:
            d -= dt.timedelta(days=1)
        try:
            n = len(prov.minute_bars("AAPL", d, premarket=True))
        except Exception:                                        # noqa: BLE001
            n = 0
        print(f"    {back:>5}d back ({d}) : {n} bars")
        if n:
            ok["minute_depth_days"] = back

    # TEST 4 — the point-in-time symbol list, if the provider has one
    print(f"\n[4] point-in-time symbol list (delisted included)")
    if hasattr(prov, "tickers_on") and getattr(prov, "enabled", False):
        try:
            rows = prov.tickers_on(day - dt.timedelta(days=365), active=False)
            print(f"    {len(rows)} INACTIVE tickers listed a year ago")
            ok["pit_symbols"] = len(rows) > 0
        except Exception as e:                                   # noqa: BLE001
            print(f"    ERROR {e}"); ok["pit_symbols"] = False
    else:
        print("    not offered by this provider")
        ok["pit_symbols"] = False

    # TEST 5 — halts, which no bar API supplies
    print(f"\n[5] halt feed (free, prospective only)")
    halts = NasdaqHaltFeed.fetch()
    print(f"    {len(halts)} records in the rolling Nasdaq RSS window")
    if halts:
        print(f"    newest: {halts[0]}")
    ok["halts_live"] = bool(halts)

    print("\n" + "-" * 60)
    for k, v in ok.items():
        print(f"  {k:<22} {v}")
    (RESULTS / "provider_verification.json").write_text(json.dumps(
        dict(provider=name, checked_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
             results=ok), indent=2))
    print(f"\nwrote results/provider_verification.json")


# ---------------------------------------------------------------------- cli --
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("universe")
    u.add_argument("--start", required=True)
    u.add_argument("--end", required=True)
    u.add_argument("--limit", type=int, default=0)
    u.add_argument("--workers", type=int, default=12)
    u.add_argument("--provider", default=None)
    u.add_argument("--refresh-pool", action="store_true")
    u.add_argument("--grouped", action="store_true",
                   help="build from grouped daily bars: one call per DATE, "
                        "every ticker that traded, delisted names included")
    u.set_defaults(func=stage_universe)

    f = sub.add_parser("fetch")
    f.add_argument("--days", type=int, default=25)
    f.add_argument("--start", default=None)
    f.add_argument("--end", default=None)
    f.add_argument("--workers", type=int, default=8)
    f.add_argument("--provider", default=None)
    f.set_defaults(func=stage_fetch)

    a = sub.add_parser("ablation")
    a.add_argument("--days", type=int, default=25)
    a.add_argument("--start", default=None)
    a.add_argument("--end", default=None)
    a.add_argument("--workers", type=int, default=8)
    a.add_argument("--provider", default=None)
    a.add_argument("--prefetch", action="store_true",
                   help="warm the ticker-month cache first (one request per "
                        "ticker-month; do this before a long ablation)")
    a.set_defaults(func=stage_ablation)

    sv = sub.add_parser("sensitivity")
    sv.add_argument("--days", type=int, default=25)
    sv.add_argument("--start", default=None)
    sv.add_argument("--end", default=None)
    sv.add_argument("--workers", type=int, default=8)
    sv.add_argument("--variants", nargs="*", default=None)
    sv.add_argument("--provider", default=None)
    sv.set_defaults(func=stage_sensitivity)

    pl = sub.add_parser("placebo")
    pl.add_argument("--days", type=int, default=25)
    pl.add_argument("--start", default=None)
    pl.add_argument("--end", default=None)
    pl.add_argument("--workers", type=int, default=8)
    pl.add_argument("--provider", default=None)
    pl.set_defaults(func=stage_placebo)

    vf = sub.add_parser("verify")
    vf.add_argument("--provider", default=None)
    vf.add_argument("--day", default=None)
    vf.add_argument("--days-back", type=int, default=3)
    vf.set_defaults(func=stage_verify)

    r = sub.add_parser("report")
    r.set_defaults(func=stage_report)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
