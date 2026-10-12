#!/usr/bin/env python3
"""Run the strategy candidates of `research/strategy-candidates/PREREGISTRATION.md`.

    python3 scripts/candidates/run.py                  # the preregistered run (the Mac: bars + keys)
    python3 scripts/candidates/run.py --source daily   # smoke test on research/daily: plumbing, not evidence
    python3 scripts/candidates/run.py --sample 30      # plumbing on 30 sessions a split; opens nothing
    python3 scripts/candidates/run.py --lead S2W       # a lead, by its amendment's gates (2026-10-12b)

The report goes to stdout (paste it back); progress goes to stderr. Files go to
`research/strategy-candidates/results/<run>/` — git-ignored, so `scripts/update.sh` leaves
them alone: report.txt, summary.json, trades.csv.gz, registry.jsonl. A family whose chosen
configuration passes its validation gate opens its holdout in this run, once: the opening is
written to `results/holdout_ledger.jsonl` before a holdout row is read.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from candidates import data as D  # noqa: E402
from candidates import diagnose as G  # noqa: E402
from candidates import protocol as P  # noqa: E402
from candidates import sim as S  # noqa: E402
from candidates.rules import FAMILIES, LEADS, OPENABLE, entries, label, random_window, signal_key  # noqa: E402

SAMPLE_SEED = 20261012
CAND_MAX = 120
TRADE_COLS = ("fam", "hash", "label", "split", "day", "sym", "window", "sig_min", "fill_min", "exit_min", "entry",
              "fill", "stop", "risk_pct", "gross", "comm", "spread", "net", "why", "exit_px", "mfe", "mae", "rnd",
              "gap", "dv20", "dv5", "sig_px")


# ------------------------------------------------------------------ trades
def trade(fam: str, cfg: dict, sd: D.SymbolDay, e, window: str, costs: S.Costs, draws: int) -> dict:
    F = FAMILIES[fam]
    r, ke, why, px, mfe, mae = S.run(sd, F.side, e.k0, e.fill, e.entry, e.stop, cfg["exit"], F.flat, e.high_ok)
    risk = abs(e.entry - e.stop)
    cm, sp, _ = costs.parts(e.entry, risk, S.MARKETABLE[why], sd.m[e.k0] < D.RTH, sd.dv5_before(e.k0))
    w0, w1 = random_window(fam, window)
    rnd = (S.random_baseline(sd, F.side, w0, w1, risk / e.entry, cfg["exit"], F.flat, costs, draws,
                             S.seed_of(sd.day, sd.sym, e.k0)) if draws else None)
    # for the real-quote check (quotes.py): the minutes whose bar traded through a short's stop, from the
    # fill bar to the flat — a valid print through the stop can only be in one of them
    cand = ([sd.m[k] for k in range(e.k0, len(sd)) if sd.m[k] < F.flat and sd.h[k] >= e.stop][:CAND_MAX]
            if F.side < 0 else [])
    return {"fam": fam, "hash": P.config_hash(fam, cfg), "label": label(fam, cfg), "split": sd.split,
            "day": sd.day, "sym": sd.sym, "window": window, "sig_min": sd.m[e.sig_k], "fill_min": sd.m[e.k0],
            "exit_min": sd.m[ke], "entry": e.entry, "fill": e.fill, "stop": e.stop, "risk": risk,
            "risk_pct": 100.0 * risk / e.entry, "gross": r, "comm": cm, "spread": sp, "net": r - cm - sp,
            "why": why, "exit_px": px, "mfe": mfe, "mae": mae, "rnd": rnd, "gap": sd.gap(), "dv20": sd.dv20,
            "dv5": sd.dv5_before(e.k0), "sig_px": sd.c[e.sig_k], "cand": cand}


def collect(gen, wanted: dict, costs: S.Costs, draws: int, total: int | None = None, tag: str = "") -> dict:
    """{(family, hash): [trade]} over the sessions `gen` yields, for `wanted` {family: [cfg]}."""
    groups = {}
    for fam, cfgs in wanted.items():
        g = defaultdict(list)
        for cfg in cfgs:
            g[signal_key(fam, cfg)].append(cfg)
        groups[fam] = g
    out = defaultdict(list)
    t0 = time.monotonic()
    for i, (_day, sds) in enumerate(gen, 1):
        for sd in sds:
            for fam, g in groups.items():
                for key, cfgs in g.items():
                    for e, window in entries(fam, sd, key):
                        for cfg in cfgs:
                            out[(fam, P.config_hash(fam, cfg))].append(trade(fam, cfg, sd, e, window, costs, draws))
        if total and (i % 50 == 0 or i == total):
            print(f"  {tag} {i}/{total} sessions · {time.monotonic() - t0:.0f} s", file=sys.stderr, flush=True)
    return out


def evaluate(fam: str, got: dict) -> tuple[list[dict], dict | None, dict]:
    """Every configuration on train and validation; the choice on train; the gate."""
    F = FAMILIES[fam]
    rows = []
    for cfg in F.configs:
        h = P.config_hash(fam, cfg)
        ts = got.get((fam, h), [])
        tr_all = [t for t in ts if t["split"] == "train"]
        va_all = [t for t in ts if t["split"] == "valid"]
        tr, va = P.portfolio(tr_all, F.reference), P.portfolio(va_all, F.reference)
        rows.append({"family": fam, "cfg": cfg, "hash": h, "label": label(fam, cfg), "signals": (len(tr_all), len(va_all)),
                     "train": G.stats(tr), "valid": G.stats(va), "tr": tr, "va": va})
    if F.reference:
        return rows, None, {"passed": False, "why": "reference only — never opens the holdout"}
    elig = [r for r in rows if r["train"].get("n", 0) >= P.MIN_TRAIN]
    if not elig:
        best = max((r["train"].get("n", 0) for r in rows), default=0)
        return rows, None, {"passed": False, "why": f"too few train trades (best {best} < {P.MIN_TRAIN}): fails for lack of trades"}
    chosen = max(elig, key=lambda r: r["train"]["net"])
    v = chosen["valid"]
    if v.get("n", 0) < P.MIN_VALID:
        return rows, chosen, {"passed": False, "why": f"validation has {v.get('n', 0)} trades (< {P.MIN_VALID}): gate not met"}
    if v["net"] <= 0:
        return rows, chosen, {"passed": False, "why": f"validation {v['net']:+.3f} R on {v['n']}: gate not met"}
    return rows, chosen, {"passed": True, "why": f"validation {v['net']:+.3f} R on {v['n']}: gate passed"}


# ------------------------------------------------------------------ formatting
def f3(x) -> str:
    return "—" if x is None or x != x else f"{x:+.3f}"


def c3(x) -> str:
    return "—" if x is None or x != x else f"{x:.3f}"


def pct(x) -> str:
    return "—" if x is None or x != x else f"{100 * x:.0f} %"


def row_line(r: dict) -> str:
    t, v = r["train"], r["valid"]
    sig = f"{r['signals'][0]}/{r['signals'][1]}"
    cost = (t["comm"] + t["spread"]) if t.get("n") else None
    return (f" {r['label']:<22}{sig:>11} │{t.get('n', 0):>6} {f3(t.get('net')):>7} {f3(t.get('gross')):>7} "
            f"{c3(cost):>6} {f3(t.get('vs_rnd')):>7} │{v.get('n', 0):>6} {f3(v.get('net')):>7} {f3(v.get('gross')):>7}")


def why_block(fam: str, r: dict) -> list[str]:
    s = r["train"]
    if not s.get("n"):
        return ["   no train trades to diagnose"]
    rd = [(t["day"], t["net"] - t["rnd"]) for t in r["tr"] if t.get("rnd") is not None]
    lb = P.lower_bound([x[0] for x in rd], [x[1] for x in rd], 0.025, draws=5000) if len(rd) >= 5 else float("nan")
    whys = " · ".join(f"{k} {pct(v)}" for k, v in s["why"].items())
    out = [f" WHY (train, {r['label']})  gross {f3(s['gross'])} − commission {c3(s['comm'])} − spread+1c {c3(s['spread'])}"
           f" = net {f3(s['net'])}",
           f"     win {pct(s['win'])} · avg win {f3(s['avg_win'])} · avg loss {f3(s['avg_loss'])} · MFE median "
           f"{s['mfe_med']:.2f} R · reached +1 R {pct(s['mfe1'])} (gave it all back {pct(s['gave_back'])})",
           f"     without the best 5 % {f3(s['wo_top5'])} · beyond −1 R: {s['beyond1']} · worst {s['worst']:+.2f} · exits: {whys}",
           f"     random entries, same names {f3(s['rnd'])} → trade − random {f3(s['vs_rnd'])} (95 % lower bound {f3(lb)})"]
    for i, line in enumerate(G.reading(s)):
        out.append((" READING · " if i == 0 else "           ") + line)
    if FAMILIES[fam].side < 0:
        be = P.break_even_borrow(r["tr"])
        be_s = (f"break-even at {be:.3f} % of price a round trip" if be is not None and be > 0
                else "no break-even: negative before any borrow")
        sweep = " / ".join(f3(G.mean(P.with_borrow(r["tr"], b))) for b in P.BORROW_SWEEP)
        out.append(f" BORROW  {be_s} (criterion 6 needs ≥ {P.BORROW_MIN_PCT} %) · net with borrow at "
                   f"{' / '.join(str(b) for b in P.BORROW_SWEEP)} % of price: {sweep}")
    yrs = " · ".join(f"{y} {f3(m)} ({n})" for y, (m, n) in s["years"].items())
    vy = " · ".join(f"{y} {f3(m)} ({n})" for y, (m, n) in r["valid"].get("years", {}).items())
    out.append(f" YEARS   train {yrs}" + (f" │ validation {vy}" if vy else ""))
    return out


def lead_lines(rows: list[dict]) -> list[str]:
    found = []
    for r in rows:
        for dim, b, mt, nt, mv, nv in G.leads(r["tr"], r["va"]):
            found.append((min(mt, mv), f"   {r['label']:<22} {dim} {b:<9} train {f3(mt)} ({nt}) | valid {f3(mv)} ({nv})"))
    found.sort(key=lambda x: -x[0])
    head = " WHERE   leads — slices positive on train (≥ 100) AND validation (≥ 30), hypotheses for the next round:"
    return [head] + ([x[1] for x in found[:5]] if found else ["   none"])


def holdout_lines(res: dict) -> list[str]:
    a = res["adoption"]
    yrs = " · ".join(f"{y} {f3(m)} ({n})" for y, (m, n) in a["years"].items())
    out = [f" HOLDOUT {'re-read' if res['ledger'].get('reread') else 'opened'} {res['ledger']['utc']} (ledger first) · "
           f"{res['label']} · n {a['n']} · mean {f3(a['mean'])} · lower bound {f3(a['lb'])} at α {a['alpha']:.2%}",
           f"     {yrs} · trade − random {f3(a['vs_random'])} (lb {f3(a['vs_random_lb'])}) · "
           f"2016-2020 {f3(a['older_mean'])} ({a['older_n']}) · break-even borrow {c3(a['break_even_borrow'])} %",
           "     " + " · ".join(("✓ " if ok else "✗ ") + k for k, ok in a["checks"].items())]
    if a.get("real") is not None:
        rq = a["real"]
        out.append(f"     real quotes (criterion 8): mean net {f3(rq.get('mean'))} on {rq.get('resolved', 0)} of "
                   f"{rq.get('n', 0)} trades re-priced" + (f" — {rq['why']}" if rq.get("why") else ""))
    failed = [k.split(" ")[0] for k, ok in a["checks"].items() if not ok]
    out.append(" → PASSES every criterion — a shadow line and the owner's decision, never a switch" if a["adopted"]
               else f" → NOT ADOPTED (criteria {', '.join(failed)})")
    return out


# ------------------------------------------------------------------ a lead (amendment 2026-10-12b)
def lead_gates(s_tr: dict, s_va: dict, s_old: dict | None) -> tuple[bool, str, bool | None, str]:
    """Gate 1: the rule positive on train AND validation, >= MIN_VALID trades each. Gate 2:
    2016-2020 positive, >= MIN_VALID trades. (None, "") for gate 2 when it was not read."""
    n_tr, n_va = s_tr.get("n", 0), s_va.get("n", 0)
    ok1 = n_tr >= P.MIN_VALID and n_va >= P.MIN_VALID and s_tr["net"] > 0 and s_va["net"] > 0
    why1 = (f"train {f3(s_tr.get('net'))} on {n_tr} · validation {f3(s_va.get('net'))} on {n_va}"
            + ("" if ok1 else f" — needs both > 0 with ≥ {P.MIN_VALID} trades"))
    if s_old is None:
        return ok1, why1, None, ""
    n_o = s_old.get("n", 0)
    ok2 = n_o >= P.MIN_VALID and s_old["net"] > 0
    why2 = f"2016-2020 {f3(s_old.get('net'))} on {n_o}" + ("" if ok2 else f" — needs > 0 with ≥ {P.MIN_VALID} trades")
    return ok1, why1, ok2, why2


def period_line(name: str, s: dict) -> str:
    if not s.get("n"):
        return f" {name:<22}{0:>6}  —"
    return (f" {name:<22}{s['n']:>6} {f3(s['net']):>7} {f3(s['gross']):>7} {c3(s['comm'] + s['spread']):>6} "
            f"{f3(s.get('vs_rnd')):>7} {pct(s['win']):>6} {s['mfe_med']:>7.2f}")


def real_quotes(port: list[dict]) -> dict:
    """Criterion 8 (amendment 2026-10-12c): the holdout portfolio's trades re-priced under Q."""
    from candidates import quotes as Q
    from candidates import requote as RQ
    tape = RQ.make_tape()
    if tape is None:
        return {"n": len(port), "resolved": 0, "mean": None, "why": "no Alpaca keys"}
    qs = [Q.reprice(tape, t) for t in port]
    ok = [q["q_net"] for q in qs if q.get("resolved")]
    return {"n": len(port), "resolved": len(ok), "mean": (sum(ok) / len(ok)) if ok else None}


def run_lead(args, fam: str) -> int:
    F = FAMILIES[fam]
    parent, cfg = F.lead_of, F.configs[0]
    h = P.config_hash(parent, cfg)                      # registered and opened under the parent family
    key = (fam, P.config_hash(fam, cfg))
    smoke = args.source == "daily" or bool(args.sample)
    if not smoke:                                       # amendment 2026-10-12c: the cost check decides first
        v = P.cost_verdict()
        if v is None:
            print("The real-quote cost check has not run: python3 scripts/candidates/requote.py first "
                  "(PREREGISTRATION.md, amendment 2026-10-12c). S2W waits for its verdict.")
            return 2
        if v["verdict"] not in ("holds", "too_optimistic"):
            print(f"The cost check's verdict is '{v['verdict']}' (run {v.get('run')}): by amendment 2026-10-12c S2W "
                  "does not run on its own.")
            return 2
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ") + f"-{fam.lower()}" + ("-smoke" if smoke else "")
    out_dir = Path(args.out) if args.out else P.RESULTS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    costs, cov, t0 = S.Costs(), {}, time.monotonic()
    want = {fam: [cfg]}
    if args.source == "history":
        uni = D.universe()
        days = {sp: sorted(d for d in uni if D.split_of(d) == sp) for sp in ("train", "valid", "holdout")}
        if args.sample:
            rnd = random.Random(SAMPLE_SEED)
            days = {sp: sorted(rnd.sample(v, min(args.sample, len(v)))) for sp, v in days.items()}
        hist = D.History(Path(args.cache), fetch=not args.no_fetch)
        tv = days["train"] + days["valid"]
        got = collect(D.history_days(uni, hist, tv, cov), want, costs, args.draws, len(tv), "train+valid")
        source = f"history · Alpaca SIP 1-minute bars, {args.cache} (fetch {'on' if hist.client else 'off'})"
    else:
        got = collect(D.daily_days(cov), want, costs, args.draws, None, "daily")
        source = "daily · the exported desk days of research/daily/ — smoke"
    if sum(c[1] for c in cov.values()) == 0:
        print("no symbol-day had bars: run where data/cache/history exists, or with Alpaca keys in .env")
        return 2
    ts = got.get(key, [])
    tr = P.portfolio([t for t in ts if t["split"] == "train"])
    va = P.portfolio([t for t in ts if t["split"] == "valid"])
    s_tr, s_va = G.stats(tr), G.stats(va)
    ok1, why1, _, _ = lead_gates(s_tr, s_va, None)
    old, s_old, ok2, why2, adopt, led = [], None, None, "", None, None
    if ok1 and not smoke:
        uni_old = D.universe(*D.OLDER)
        got_o = collect(D.history_days(uni_old, hist, None, cov), want, costs, 0, len(uni_old), "2016-2020")
        old = P.portfolio(got_o.get(key, []))
        s_old = G.stats(old)
        _, _, ok2, why2 = lead_gates(s_tr, s_va, s_old)
        got.setdefault(key, []).extend(got_o.get(key, []))
        if ok2:
            try:
                led = P.open_holdout(parent, cfg, P.n_configs(parent) + 1, G.compact(s_tr), G.compact(s_va))
            except P.HoldoutAlreadyOpened as exc:
                why2 += f" · ✗ {exc}"
            if led is not None:
                got_h = collect(D.history_days(uni, hist, days["holdout"], cov), want, costs, args.draws,
                                len(days["holdout"]), "holdout")
                port = P.portfolio(got_h.get(key, []))
                adopt = P.adoption(port, F.side, old, real=real_quotes(port))
                P.record_result(parent, adopt | {"hash": h, "lead": fam})
                got[key].extend(got_h.get(key, []))

    rep = [f"STRATEGY CANDIDATES · LEAD {fam} · run {run_id} · git {P.head()} · "
           "research/strategy-candidates/PREREGISTRATION.md, amendment 2026-10-12b",
           f"SOURCE   {source}"]
    if smoke:
        rep.append("! SMOKE — plumbing only, NOT evidence: nothing is opened and nothing enters the registry")
    rep += ["COVERAGE " + " · ".join(f"{sp} {c[1]:,} / {c[0]:,} symbol-days with bars" for sp, c in sorted(cov.items())),
            "COSTS    live: $40 risk, ≤ $2,000 a position, IBKR fixed both orders, half the proxy spread + 1c a "
            f"marketable side; borrow not charged (BORROW below) · random baseline {args.draws} entries a trade",
            f"RULE     {F.name} — one configuration, registered under {parent}",
            "",
            f" {'period':<22}{'n':>6} {'net':>7} {'gross':>7} {'cost':>6} {'vs rnd':>7} {'win':>6} {'MFE med':>7}",
            period_line("train 2021-2022", s_tr), period_line("validation 2023", s_va)]
    if s_old is not None:
        rep.append(period_line("2016-2020 (gate 2)", s_old))
    rep.append(f" GATE 1  {'✓' if ok1 else '✗'} {why1}")
    if ok2 is not None:
        rep.append(f" GATE 2  {'✓' if ok2 else '✗'} {why2}")
    if adopt is None:
        rep.append(" HOLDOUT shut — " + ("a gate failed" if ok1 is False or ok2 is False
                                         else "smoke run" if smoke else "the opening was refused"))
    row = {"family": parent, "hash": h, "config": cfg, "label": label(fam, cfg), "lead": fam, "tr": tr, "va": va,
           "train": s_tr, "valid": s_va, "signals": (len([t for t in ts if t["split"] == "train"]),
                                                     len([t for t in ts if t["split"] == "valid"]))}
    rep += why_block(fam, row)
    if adopt is not None:
        rep += ["", f"━━ {parent} · holdout, through its lead {fam} ━━"] + holdout_lines(
            {"label": row["label"], "ledger": led, "adoption": adopt})
    reg = {"family": parent, "hash": h, "config": cfg, "label": row["label"], "lead": fam, "run": run_id,
           "git": P.head(), "source": args.source, "smoke": smoke, "utc": P.utc_now(),
           "train": G.compact(s_tr), "valid": G.compact(s_va), "older": G.compact(s_old) if s_old else None,
           "gate1": ok1, "gate2": ok2, "holdout": adopt}
    P.register([reg], out_dir / "registry.jsonl")
    if not smoke:
        P.register([reg], P.LOCAL_REGISTRY)
    t, v = reg["train"], reg["valid"]
    o = reg["older"] or {}
    rep += ["", "REGISTRY (one line; the committed registry.jsonl is rebuilt from it)",
            f"REG {parent} {h} {row['label']} lead {fam} tr {t.get('n', 0)} {f3(t.get('net'))} {f3(t.get('gross'))} "
            f"va {v.get('n', 0)} {f3(v.get('net'))} {f3(v.get('gross'))} old {o.get('n', 0)} {f3(o.get('net'))} "
            f"{f3(o.get('gross'))}" + (f" holdout {adopt['n']} {f3(adopt['mean'])} "
                                       f"{'ADOPTED' if adopt['adopted'] else 'not adopted'}" if adopt else ""),
            "", f"done in {time.monotonic() - t0:.0f} s · files: {_shown(out_dir)}",
            "Paper only. Not testable here: Level 2, borrow availability and fees, locates, halts as such, "
            "the previous day's SSR, ten-second structure."]
    _write(out_dir, rep, {"lead": fam, "registry": reg}, got)
    return 0


def _shown(out_dir: Path):
    p = out_dir.resolve()
    return p.relative_to(ROOT) if p.is_relative_to(ROOT) else p


def _write(out_dir: Path, rep: list[str], summary: dict, got: dict) -> None:
    text = "\n".join(rep)
    print(text)
    (out_dir / "report.txt").write_text(text + "\n")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    with gzip.open(out_dir / "trades.csv.gz", "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=TRADE_COLS, extrasaction="ignore")
        w.writeheader()
        for ts in got.values():
            for t in ts:
                w.writerow({k: (round(x, 5) if isinstance(x, float) else x) for k, x in t.items()})


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=("history", "daily"), default="history")
    ap.add_argument("--families", default="S1,S2,L1,L3")
    ap.add_argument("--cache", default=str(D.HISTORY), help="the Alpaca SIP 1-minute history cache")
    ap.add_argument("--no-fetch", action="store_true", help="never fetch a missing session")
    ap.add_argument("--draws", type=int, default=20, help="random entries a trade (preregistered: 20)")
    ap.add_argument("--sample", type=int, help="plumbing: a seeded sample of N sessions a split; opens nothing")
    ap.add_argument("--out", help="results folder (default research/strategy-candidates/results/<run>)")
    ap.add_argument("--lead", choices=LEADS, help="test a lead by its amendment's gates, alone")
    args = ap.parse_args(argv)

    if args.lead:
        return run_lead(args, args.lead)
    fams = [f.strip() for f in args.families.split(",") if f.strip()]
    for f in fams:
        if f not in FAMILIES or f in LEADS:
            ap.error(f"unknown family {f} (S1, S2, L1, L3; L2 is not re-run; a lead runs only with --lead)")
    smoke = args.source == "daily" or bool(args.sample)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ") + ("-smoke" if smoke else "")
    out_dir = Path(args.out) if args.out else P.RESULTS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    costs = S.Costs()
    t0 = time.monotonic()
    cov: dict = {}

    wanted = {f: list(FAMILIES[f].configs) for f in fams}
    hist = None
    if args.source == "history":
        uni = D.universe()
        days = {sp: sorted(d for d in uni if D.split_of(d) == sp) for sp in ("train", "valid", "holdout")}
        if args.sample:
            rnd = random.Random(SAMPLE_SEED)
            days = {sp: sorted(rnd.sample(v, min(args.sample, len(v)))) for sp, v in days.items()}
        hist = D.History(Path(args.cache), fetch=not args.no_fetch)
        tv = days["train"] + days["valid"]
        print(f"train + validation: {len(tv)} sessions · fetch {'on' if hist.client else 'off'}", file=sys.stderr)
        got = collect(D.history_days(uni, hist, tv, cov), wanted, costs, args.draws, len(tv), "train+valid")
        source = (f"history · Alpaca SIP 1-minute bars, {args.cache} (fetch {'on' if hist.client else 'off'}) · "
                  f"universe candidate_days.csv {D.WINDOW[0]} → {D.WINDOW[1]}")
    else:
        got = collect(D.daily_days(cov), wanted, costs, args.draws, None, "daily")
        source = "daily · the exported desk days of research/daily/, 04:00-12:00 bars, prev close as exported"

    have = sum(c[1] for c in cov.values())
    if have == 0:
        print("no symbol-day had bars: run where data/cache/history exists, or with Alpaca keys in .env")
        return 2

    rep = [f"STRATEGY CANDIDATES · run {run_id} · git {P.head()} · research/strategy-candidates/PREREGISTRATION.md",
           f"SOURCE   {source}"]
    if smoke:
        rep.append("! SMOKE — plumbing only, NOT evidence: nothing is opened and nothing enters the registry")
    rep.append("COVERAGE " + " · ".join(f"{sp} {c[1]:,} / {c[0]:,} symbol-days with bars" for sp, c in sorted(cov.items()))
               + " · the holdout is read only where a family opens it below")
    rep.append("COSTS    live: $40 risk, ≤ $2,000 a position, IBKR fixed both orders, half the proxy spread + 1c a "
               "marketable side; shorts before borrow (sweep in BORROW) · random baseline "
               f"{args.draws} entries a trade, same name-day")
    rep.append("TABLE    signals = trades before the one-position rule (train/valid) · n, net, gross, cost, vs rnd = "
               "the one-position portfolio, R a trade")

    summary, reg_rows, status, opened = {}, [], [], {}
    for fam in fams:
        F = FAMILIES[fam]
        rows, chosen, gate = evaluate(fam, got)
        side = "short" if F.side < 0 else "long"
        rep += ["", f"━━ {fam} · {F.name} · {side} · {len(F.configs)} configuration(s) ━━",
                f" {'config':<22}{'signals':>11} │{'n':>6} {'net':>7} {'gross':>7} {'cost':>6} {'vs rnd':>7} │"
                f"{'n':>6} {'net':>7} {'gross':>7}",
                f" {'':<33} │ {'train':<36}│ validation"]
        rep += [row_line(r) for r in rows]
        if F.reference:
            for w in ("pre-market", "regular"):
                tw = G.stats([t for t in rows[0]["tr"] if t["window"] == w])
                vw = G.stats([t for t in rows[0]["va"] if t["window"] == w])
                flag = " — FLATTERED: the universe knows the 09:30 open" if w == "pre-market" else ""
                rep.append(f"   {w:<11} train {f3(tw.get('net'))} ({tw.get('n', 0)}) · valid {f3(vw.get('net'))} "
                           f"({vw.get('n', 0)}){flag}")
            rep += why_block(fam, rows[0])
            status.append(f"  {fam}  reference · train {f3(rows[0]['train'].get('net'))} ({rows[0]['train'].get('n', 0)})"
                          f" · validation {f3(rows[0]['valid'].get('net'))} ({rows[0]['valid'].get('n', 0)})")
        else:
            if chosen is not None:
                rep.append(f" → chosen {chosen['label']} (best train net among n ≥ {P.MIN_TRAIN}) · "
                           f"{'✓' if gate['passed'] else '✗'} {gate['why']}")
                rep += why_block(fam, chosen)
            else:
                rep.append(f" → ✗ {gate['why']}")
                rep += why_block(fam, max(rows, key=lambda r: r["train"].get("n", 0)))
            rep += lead_lines(rows)
        for r in rows:
            reg_rows.append({"family": fam, "hash": r["hash"], "config": r["cfg"], "label": r["label"], "run": run_id,
                             "git": P.head(), "source": args.source, "smoke": smoke, "utc": P.utc_now(),
                             "train": G.compact(r["train"]), "valid": G.compact(r["valid"]),
                             "signals": list(r["signals"]), "chosen": chosen is not None and r is chosen})
        summary[fam] = {"gate": gate, "chosen": chosen["hash"] if chosen else None,
                        "rows": [{k: v for k, v in r.items() if k not in ("tr", "va")} for r in rows]}
        if not F.reference:
            if gate["passed"] and fam in OPENABLE and not smoke:
                opened[fam] = chosen
            elif not gate["passed"]:
                status.append(f"  {fam}  ✗ {gate['why']} · holdout shut")
            else:
                status.append(f"  {fam}  ✓ gate passed · smoke run: holdout NOT opened")

    # the registry first, so an opening counts every configuration of this run
    P.register(reg_rows, out_dir / "registry.jsonl")
    if not smoke:
        P.register(reg_rows, P.LOCAL_REGISTRY)

    # the holdout: ledger first, then the chosen configuration only, then 2016-2020
    if opened:
        led = {}
        for fam, ch in list(opened.items()):
            try:
                led[fam] = P.open_holdout(fam, ch["cfg"], P.n_configs(fam), G.compact(ch["train"]), G.compact(ch["valid"]))
            except P.HoldoutAlreadyOpened as exc:
                status.append(f"  {fam}  ✗ {exc}")
                del opened[fam]
        want = {fam: [ch["cfg"]] for fam, ch in opened.items()}
        if want:
            got_h = collect(D.history_days(uni, hist, days["holdout"], cov), want, costs, args.draws,
                            len(days["holdout"]), "holdout")
            uni_old = D.universe(*D.OLDER)
            cov_old: dict = {}
            got_o = collect(D.history_days(uni_old, hist, None, cov_old), want, costs, 0, len(uni_old), "2016-2020")
            for fam, ch in opened.items():
                F = FAMILIES[fam]
                port = P.portfolio(got_h.get((fam, ch["hash"]), []))
                older = P.portfolio(got_o.get((fam, ch["hash"]), []))
                a = P.adoption(port, F.side, older)
                res = {"label": ch["label"], "ledger": led[fam], "adoption": a}
                P.record_result(fam, {k: v for k, v in a.items()} | {"hash": ch["hash"]})
                summary[fam]["holdout"] = a
                rep += ["", f"━━ {fam} · holdout ━━"] + holdout_lines(res)
                status.append(f"  {fam}  ✓ gate passed → holdout {'PASSES' if a['adopted'] else 'NOT ADOPTED'} "
                              f"({f3(a['mean'])} R on {a['n']})")
                got.setdefault((fam, ch["hash"]), []).extend(got_h.get((fam, ch["hash"]), []) + got_o.get((fam, ch["hash"]), []))

    rep += ["", "STATUS"] + status
    rep += ["", "REGISTRY (one line a configuration; the committed registry.jsonl is rebuilt from these)"]
    for r in reg_rows:
        t, v = r["train"], r["valid"]
        rep.append(f"REG {r['family']} {r['hash']} {r['label']} tr {t.get('n', 0)} {f3(t.get('net'))} "
                   f"{f3(t.get('gross'))} va {v.get('n', 0)} {f3(v.get('net'))} {f3(v.get('gross'))}"
                   + (" chosen" if r["chosen"] else ""))
    rep += ["", f"done in {time.monotonic() - t0:.0f} s · files: {_shown(out_dir)}",
            "Paper only. Not testable here: Level 2, borrow availability and fees, locates, halts as such, "
            "the previous day's SSR, ten-second structure."]
    _write(out_dir, rep, summary, got)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
