#!/usr/bin/env python3
"""The real-quote cost check — research/strategy-candidates/PREREGISTRATION.md, amendment 2026-10-12c.

    python3 scripts/candidates/requote.py              # the check (the Mac: bars cached, Alpaca keys)
    python3 scripts/candidates/requote.py --sample 20  # plumbing on 20 sessions a split; no verdict saved

Rebuilds S2's four close-exit configurations and S2W on train and 2023 from the history
cache (the same code as the five-year run, no random baseline), re-prices every trade under
execution model Q (`quotes.py`), and applies the amendment's rule to Δ = Q net − proxy net on
the chosen configuration. Writes research/strategy-candidates/results/<run>-quotes/ and the
verdict to results/cost_check.json, which `run.py --lead S2W` requires.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from candidates import data as D  # noqa: E402
from candidates import diagnose as G  # noqa: E402
from candidates import protocol as P  # noqa: E402
from candidates import quotes as Q  # noqa: E402
from candidates import sim as S  # noqa: E402
from candidates.rules import FAMILIES, label  # noqa: E402

DELTA_BAND, MAX_UNRESOLVED = 0.05, 0.10                                 # fixed by the amendment
# Alpaca showed CTA/UTP quote sizes as "the number of round lots available at the quoted price"
# until 2025-11-03, in shares after (docs.alpaca.markets/us/changelog/marketdata-bid-and-ask-size-display-change).
# The 2026-10-12 check compared shares with lots; a lot is 100 shares for these $2-20 names.
SHARES_FROM, LOT = "2025-11-03", 100


def displayed_shares(day: str, size: float) -> float:
    return size if day >= SHARES_FROM else size * LOT
VERDICT_FILE = P.RESULTS / "cost_check.json"
NEXT = {
    "holds": "S2W runs as written, plus criterion 8: python3 scripts/candidates/run.py --lead S2W",
    "too_optimistic": "S2's failure stands, harder. S2W runs as written, plus criterion 8: "
                      "python3 scripts/candidates/run.py --lead S2W",
    "too_pessimistic": "Q becomes S2's cost model and S2 is chosen again on train under Q (the amendment's branch); "
                       "S2W does not run on its own — that code is written now that the check landed here",
    "inconclusive": "no branch: too many trades without a quote; the gap is reported and nothing runs",
}


def configs() -> list[tuple[str, dict]]:
    """S2's close-exit configurations, then S2W — the amendment's sample."""
    return ([("S2", c) for c in FAMILIES["S2"].configs if c["exit"] == "close"]
            + [("S2W", c) for c in FAMILIES["S2W"].configs])


def ckey(fam: str, cfg: dict) -> tuple[str, str]:
    return fam, P.config_hash(fam, cfg)


CHOSEN = ckey("S2", {"G": 0.20, "stop": "hod", "exit": "close"})     # the five-year run's train choice


def tkey(t: dict) -> tuple:
    """Trades that share it are executed identically under Q (same order time, entry and stop)."""
    return t["day"], t["sym"], t["sig_min"], t["fill_min"], round(t["stop"], 4)


def decide(rows: list[dict]) -> dict:
    """The amendment's rule on the chosen configuration's trades (train + 2023, trade level)."""
    import numpy as np
    from edge_hunt.protocol import day_bootstrap
    cancelled = sum(1 for r in rows if r["q"].get("cancelled"))
    n = len(rows) - cancelled                              # a cancelled trade is a rule outcome, not missing data
    res = [r for r in rows if r["q"].get("resolved")]
    share = 1 - len(res) / n if n else 1.0
    out = {"n": n, "resolved": len(res), "unresolved_share": share, "cancelled": cancelled}
    if not n or share > MAX_UNRESOLVED:
        return out | {"verdict": "inconclusive"}
    d = np.array([r["q"]["q_net"] - r["net"] for r in res])
    boot = day_bootstrap(np.array([r["day"] for r in res]), d)
    mean, lo, hi = float(d.mean()), float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))
    out |= {"delta": mean, "lo": lo, "hi": hi, "proxy_net": float(np.mean([r["net"] for r in res])),
            "q_net": float(np.mean([r["q"]["q_net"] for r in res])),
            "q0_net": float(np.mean([r["q"]["q0_net"] for r in res]))}
    if mean > DELTA_BAND and lo > 0:
        return out | {"verdict": "too_pessimistic"}
    if mean < -DELTA_BAND and hi < 0:
        return out | {"verdict": "too_optimistic"}
    return out | {"verdict": "holds"}


# ------------------------------------------------------------------ the report
def med(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[len(xs) // 2] if xs else None


def f3(x) -> str:
    return "—" if x is None or x != x else f"{x:+.3f}"


def cents(x) -> str:
    return "—" if x is None else f"{100 * x:.1f}¢"


def q_trades(ts: list[dict]) -> list[dict]:
    """The trades as model Q executed them, for the one-position rule (the exit minute can move)."""
    return [dict(t, net=t["q"]["q_net"], gross=t["q"]["q_gross"], exit_min=t["q"]["exit_min_q"])
            for t in ts if t["q"].get("resolved")]


CELL = "{:>5} {:>7} {:>7} {:>7} │{:>6} {:>7} {:>7}"


def config_head() -> list[str]:
    cols = CELL.format("n", "proxy", "Q", "Q0", "1 pos", "proxy", "Q")
    width = len(cols)
    return [f" {'':<28}│ {'train 2021-2022, R a trade':<{width}} ║ 2023",
            f" {'config':<28}│ {cols} ║ {cols}"]


def config_line(name: str, ts: list[dict]) -> str:
    cells = []
    for split in ("train", "valid"):
        a = [t for t in ts if t["split"] == split]
        res = [t for t in a if t["q"].get("resolved")]
        pp, qp = P.portfolio(a), P.portfolio(q_trades(a))
        cells.append(CELL.format(len(a), f3(G.mean(t["net"] for t in a)), f3(G.mean(t["q"]["q_net"] for t in res)),
                                 f3(G.mean(t["q"]["q0_net"] for t in res)), len(pp), f3(G.mean(t["net"] for t in pp)),
                                 f3(G.mean(t["net"] for t in qp))))
    return f" {name:<28}│ " + " ║ ".join(cells)


def report(run_id: str, src: str, rows: dict, names: dict, dec: dict, unresolved: Counter, n_distinct: int,
           smoke: bool, costs: S.Costs) -> list[str]:
    res = [r for r in rows[CHOSEN] if r["q"].get("resolved")]
    rep = [f"REAL-QUOTE COST CHECK · run {run_id} · git {P.head()} · research/strategy-candidates/PREREGISTRATION.md, "
           "amendment 2026-10-12c",
           f"SOURCE   {src}",
           "MODEL Q  short at the NBBO bid at the order time (+4 s) − 1c · stop: the first valid print ≥ the stop, filled "
           "at max(print, ask) + 1c · otherwise the ask at 15:55:04 + 1c · commission as the proxy run · Q0: no cents"]
    if smoke:
        rep.append("! PLUMBING — a sample of sessions: NOT the check, no verdict saved")
    rep.append(f"SAMPLE   {sum(len(v) for v in rows.values())} trades over {len(rows)} configurations · {n_distinct} "
               "distinct to re-price · unresolved: " + (", ".join(f"{k} {v}" for k, v in unresolved.items()) or "none"))
    verdict = dec["verdict"]
    rep += ["", "THE DECISION — S2 G20·hod·close, train + 2023, trade level",
            f"  proxy net {f3(dec.get('proxy_net'))} · Q net {f3(dec.get('q_net'))} · Q0 net {f3(dec.get('q0_net'))} · "
            f"Δ = Q − proxy {f3(dec.get('delta'))} R (95 % interval {f3(dec.get('lo'))} … {f3(dec.get('hi'))}) "
            f"on {dec['resolved']} of {dec['n']} trades ({100 * dec['unresolved_share']:.0f} % unresolved; "
            f"{dec['cancelled']} more cancelled: the bid already at or above the stop)",
            f"  VERDICT  {verdict.replace('_', ' ')} — the rule: |Δ| ≤ {DELTA_BAND} R or an interval holding 0 → holds; "
            f"over +{DELTA_BAND} with the interval above 0 → too pessimistic; under −{DELTA_BAND} with it below 0 → "
            f"too optimistic; more than {100 * MAX_UNRESOLVED:.0f} % unresolved → inconclusive",
            f"  NEXT     {NEXT[verdict]}"]
    if res:
        prox_in = [costs.proxy.spread(r["entry"], False, r["dv5"]) for r in res]
        real_in = [r["q"]["spread_in"] for r in res]
        bar_st = [r for r in res if r["why"] in ("stop", "trail", "newlow")]
        flipped = sum(1 for r in bar_st if r["q"]["how"] != "stop")
        late = sum(1 for r in bar_st if r["q"]["how"] == "stop" and r["q"]["exit_min_q"] > r["exit_min"])
        dfill = [r["q"]["fill_in"] - r["entry"] for r in res]
        rep += ["", "WHAT THE QUOTES SAY (G20·hod·close; the proxy charges half its spread + 1c a side)",
                f"  spread at entry   real median {cents(med(real_in))} ({100 * med(x / r['entry'] for x, r in zip(real_in, res)):.2f} %"
                f" of price), mean {cents(G.mean(real_in))} · proxy median {cents(med(prox_in))}, mean {cents(G.mean(prox_in))}",
                f"  spread at exit    real median {cents(med(r['q']['spread_out'] for r in res if r['q']['how'] == 'stop'))} "
                f"at the stops · {cents(med(r['q']['spread_out'] for r in res if r['q']['how'] == 'flat'))} at 15:55",
                f"  entry fill        Q's bid − 1c against the bar's open: median {cents(med(dfill))}, mean {cents(G.mean(dfill))}",
                f"  stops             the bars stop {len(bar_st)} trades · the prints confirm {len(bar_st) - flipped} "
                f"({late} later than the bar) · {flipped} held to 15:55 instead: no valid print through the stop after "
                "the order"]
        dims = (("price", lambda r: "$2-5" if r["entry"] < 5 else ("$5-10" if r["entry"] < 10 else "$10+")),
                ("order time", lambda r: "09:35-09:59" if r["sig_min"] < D.minute(9, 55) else "10:00-10:30"),
                ("recent $ volume", lambda r: costs.proxy.key(r["entry"], False, r["dv5"]).split("|")[2]))
        for dim, key in dims:
            g = defaultdict(list)
            for r in res:
                g[key(r)].append(r["q"]["q_net"] - r["net"])
            rep.append(f"  Δ by {dim:<16}" + " · ".join(f"{k} {f3(G.mean(v))} ({len(v)})" for k, v in sorted(g.items())))
        stale_in = sum(1 for r in res if r["q"]["age_in"] > Q.STALE_MS)
        stale_out = sum(1 for r in res if (r["q"]["age_out"] or 0) > Q.STALE_MS)
        big = sum(1 for r in res if r["q"]["bid_size_in"]
                  and S.live_shares(r["entry"], r["stop"] - r["entry"]) > displayed_shares(r["day"], r["q"]["bid_size_in"]))
        rep.append(f"  data              quotes older than 10 s: {stale_in} at entry, {stale_out} at exit · our shares "
                   f"above the displayed bid (round lots × {LOT} before {SHARES_FROM}): {big}")
    rep += ["", "EVERY CONFIGURATION UNDER Q — reported; it decides only in the 'too pessimistic' branch",
            "  n, proxy, Q, Q0: every trade · 1 pos: one position at a time (proxy and Q exits)"] + config_head()
    for k, ts in rows.items():
        rep.append(config_line(names[k], ts))
    return rep


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=str(D.HISTORY))
    ap.add_argument("--no-fetch", action="store_true", help="never fetch a missing session's bars")
    ap.add_argument("--sample", type=int, help="plumbing: a seeded sample of N sessions a split; no verdict saved")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    smoke = bool(args.sample)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ") + "-quotes" + ("-smoke" if smoke else "")
    out_dir = Path(args.out) if args.out else P.RESULTS / run_id
    t0 = time.monotonic()

    tape = make_tape()
    if tape is None:
        print("no Alpaca keys: the check reads real quotes — run it on the Mac (ALPACA_KEY_ID / ALPACA_SECRET_KEY in .env)")
        return 2
    from candidates import run as RUN
    uni = D.universe()
    days = sorted(d for d in uni if D.split_of(d) in ("train", "valid"))
    if smoke:
        rnd = random.Random(RUN.SAMPLE_SEED)
        by = defaultdict(list)
        for d in days:
            by[D.split_of(d)].append(d)
        days = sorted(x for v in by.values() for x in rnd.sample(v, min(args.sample, len(v))))
    hist = D.History(Path(args.cache), fetch=not args.no_fetch)
    cov: dict = {}
    want = defaultdict(list)
    for fam, cfg in configs():
        want[fam].append(cfg)
    got = RUN.collect(D.history_days(uni, hist, days, cov), dict(want), S.Costs(), 0, len(days), "trades")
    rows = {ckey(fam, cfg): got.get(ckey(fam, cfg), []) for fam, cfg in configs()}
    names = {ckey(fam, cfg): ("S2W " if fam == "S2W" else "") + label(fam, cfg) for fam, cfg in configs()}
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = requote_all(tape, rows, t0)
    if rc:
        return rc
    unresolved = Counter(q["unresolved"] for q in _distinct_q(rows).values() if not q.get("resolved"))
    dec = decide(rows[CHOSEN])
    src = (f"Alpaca SIP prints and NBBO quotes · bars {args.cache} · "
           + " · ".join(f"{sp} {c[1]:,}/{c[0]:,} symbol-days with bars" for sp, c in sorted(cov.items())))
    rep = report(run_id, src, rows, names, dec, unresolved, len(_distinct_q(rows)), smoke, S.Costs())
    rep += ["", f"done in {time.monotonic() - t0:.0f} s · files: {_shown(out_dir)}",
            "Paper only. Not in this check: borrow, locates, the previous day's SSR, depth beyond the displayed touch."]
    text = "\n".join(rep)
    print(text)
    (out_dir / "report.txt").write_text(text + "\n")
    verdict = dec | {"run": run_id, "git": P.head(), "utc": P.utc_now(), "smoke": smoke}
    (out_dir / "cost_check.json").write_text(json.dumps(verdict, indent=1))
    if not smoke:
        VERDICT_FILE.parent.mkdir(parents=True, exist_ok=True)
        VERDICT_FILE.write_text(json.dumps(verdict, indent=1))
    write_trades(out_dir / "requoted.csv.gz", rows, names)
    return 0


def make_tape():
    """A Tape on the Alpaca SIP feed, or None without keys."""
    from momentum_platform.datasources.alpaca_source import PLACEHOLDER, client_from_env
    import tick_replay as TR
    client = client_from_env(feed="sip")
    if not client.key_id or not client.secret_key or PLACEHOLDER.match(client.key_id):
        return None
    return Q.Tape(TR.Fetcher(client))


def _distinct_q(rows: dict) -> dict:
    return {tkey(t): t["q"] for ts in rows.values() for t in ts if "q" in t}


def requote_all(tape, rows: dict, t0: float) -> int:
    """Re-price each distinct trade once and attach the result to every configuration's copy."""
    distinct = {}
    for ts in rows.values():
        for t in ts:
            distinct.setdefault(tkey(t), t)
    done = {}
    for i, (k, t) in enumerate(sorted(distinct.items()), 1):
        try:
            done[k] = Q.reprice(tape, t)
        except Exception as exc:                                       # noqa: BLE001
            if "401" in str(exc) or "403" in str(exc):
                print(f"Alpaca refused the request ({exc}): check the keys and the SIP entitlement")
                return 2
            done[k] = {"resolved": False, "unresolved": f"error {type(exc).__name__}"}
        if i % 50 == 0 or i == len(distinct):
            print(f"  re-priced {i}/{len(distinct)} · {tape.fx.requests} print requests · {tape.quote_requests} quote "
                  f"requests · {time.monotonic() - t0:.0f} s", file=sys.stderr, flush=True)
    for ts in rows.values():
        for t in ts:
            t["q"] = done[tkey(t)]
    return 0


def write_trades(path: Path, rows: dict, names: dict) -> None:
    cols = ["config", "split", "day", "sym", "sig_min", "fill_min", "entry", "stop", "why", "net", "dv5", "resolved",
            "how", "bid_in", "ask_in", "age_in", "spread_in", "ask_out", "spread_out", "age_out", "trigger_px",
            "fill_in", "fill_out", "q_gross", "q_net", "q0_net", "exit_min_q", "unresolved"]
    with gzip.open(path, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for k, ts in rows.items():
            for t in ts:
                w.writerow({"config": names[k], **{c: t.get(c) for c in cols[1:11]}, **t.get("q", {})})


def _shown(out_dir: Path):
    p = out_dir.resolve()
    return p.relative_to(ROOT) if p.is_relative_to(ROOT) else p


if __name__ == "__main__":
    raise SystemExit(main())
