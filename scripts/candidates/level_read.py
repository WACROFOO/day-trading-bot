#!/usr/bin/env python3
"""The level read-out of research/strategy-candidates/PREREGISTRATION.md, amendment 2026-10-14:
do the desk's levels behave like support and resistance, against the same levels moved by a
random distance? Descriptive — it decides nothing, opens nothing, registers nothing.

    python3 scripts/candidates/level_read.py                  # train + validation, 2021-2023 (the Mac)
    python3 scripts/candidates/level_read.py --source daily   # the exported desk days: a first look, not evidence
    python3 scripts/candidates/level_read.py --sample 30      # plumbing: 30 sessions a split

Never reads a holdout day (2024-2026 stays unread for these levels). The report goes to stdout
and to research/strategy-candidates/results/<run>-levels/ (git-ignored).

A test of a support at bar t (09:30-11:29): the level as drawn from bars before t, the
previous close above level + band, bar t's low at level + band or under; frozen there.
  broke     a close under level − band (bar t's own close included)
  held      a high at level + 1 ATR, from bar t+1 — checked before the close of the same bar:
            a bar's high always prints before its close
  open      neither within 30 bars
Resistance mirrors it. One open test per level, side and placebo flag at a time.
"""
from __future__ import annotations

import argparse
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
from candidates import protocol as P  # noqa: E402
from candidates.rules import day_levels  # noqa: E402
from candidates.sim import seed_of  # noqa: E402
from momentum_platform import levels as LV  # noqa: E402

SAMPLE_SEED = 20261014
WINDOW = (D.minute(9, 30), D.minute(11, 30))     # the bars a test may start on
HORIZON = 30                                      # bars to resolve a test
HELD_ATR = 1.0                                    # held: a move of 1 ATR away from the level
PLACEBO = (0.5, 1.5)                              # the placebo's distance, in ATR, either way
KINDS = ("fan", "trend", "vwap", "round", "pmh", "hod", "fan+")
SIDES = ("support", "resistance")


def levels_at(sd: D.SymbolDay, lv, t: int, pmh: float | None) -> dict:
    """{(kind, side): price} — the levels as drawn from bars 0 … t−1."""
    c1 = sd.c[t - 1]
    fan = lv.fan(t, c1)
    lines = lv.lines(t, c1)
    vw = sd.vwap[t - 1]
    rd = LV.round_levels(c1)
    out = {}
    sup = fan["sup"][0]["price"] if fan["sup"] else None
    res = fan["res"][0]["price"] if fan["res"] else None
    out[("fan", "support")], out[("fan", "resistance")] = sup, res
    out[("trend", "support")] = lines["up"]["now"] if lines["up"] else None
    out[("trend", "resistance")] = lines["down"]["now"] if lines["down"] else None
    out[("vwap", "support")] = out[("vwap", "resistance")] = vw
    out[("round", "support")], out[("round", "resistance")] = rd["below"], rd["above"]
    out[("pmh", "support")] = out[("pmh", "resistance")] = pmh
    out[("hod", "resistance")] = max(sd.h[:t])
    band = fan["band"]

    def confluent(x):
        # "two reasons at one price" (PARAMETERS.md §3 at_support): a whole/half dollar or VWAP in the band
        return x is not None and band is not None and (abs(x - round(x * 2) / 2) <= band or abs(x - vw) <= band)
    out[("fan+", "support")] = sup if confluent(sup) else None
    out[("fan+", "resistance")] = res if confluent(res) else None
    return out


def resolve(sd: D.SymbolDay, t: int, side: str, lvl: float, band: float, a: float) -> tuple[str, int]:
    """(held | broke | open, the bar it resolved on)."""
    h, l, c = sd.h, sd.l, sd.c
    n = len(sd)
    if side == "support":
        if c[t] < lvl - band:
            return "broke", t
        for j in range(t + 1, min(n, t + 1 + HORIZON)):
            if h[j] >= lvl + HELD_ATR * a:
                return "held", j
            if c[j] < lvl - band:
                return "broke", j
    else:
        if c[t] > lvl + band:
            return "broke", t
        for j in range(t + 1, min(n, t + 1 + HORIZON)):
            if l[j] <= lvl - HELD_ATR * a:
                return "held", j
            if c[j] > lvl + band:
                return "broke", j
    return "open", min(n - 1, t + HORIZON)


def tested(sd: D.SymbolDay, t: int, side: str, lvl: float, band: float) -> bool:
    if side == "support":
        return sd.c[t - 1] > lvl + band and sd.l[t] <= lvl + band
    return sd.c[t - 1] < lvl - band and sd.h[t] >= lvl - band


def day_tests(sd: D.SymbolDay) -> list[dict]:
    """Every test of every level, real and placebo, on one symbol-day."""
    lv = day_levels(sd)
    k0, k1 = sd.first_at(WINDOW[0]), sd.first_at(WINDOW[1])
    pm = [sd.h[k] for k in range(k0)]
    pmh = max(pm) if pm else None
    shift = {}
    for kind in KINDS:
        for side in SIDES:
            rnd = random.Random(seed_of(sd.day, sd.sym, kind, side))
            shift[(kind, side)] = rnd.choice((-1, 1)) * rnd.uniform(*PLACEBO)
    busy: dict = {}
    out = []
    for t in range(max(1, k0), k1):
        a = lv.atr_before(t)
        if a is None or a <= 0:
            continue
        band = max(LV.BAND_ATR * a, LV.mintick(sd.c[t - 1]))
        for (kind, side), lvl in levels_at(sd, lv, t, pmh).items():
            if lvl is None:
                continue
            for placebo in (False, True):
                key = (kind, side, placebo)
                if busy.get(key, -1) >= t:
                    continue
                px = lvl + shift[(kind, side)] * a if placebo else lvl
                if px <= 0 or not tested(sd, t, side, px, band):
                    continue
                outcome, at = resolve(sd, t, side, px, band, a)
                busy[key] = at
                out.append({"day": sd.day, "sym": sd.sym, "split": sd.split, "kind": kind, "side": side,
                            "placebo": placebo, "t": sd.m[t], "level": px, "outcome": outcome})
    return out


# ------------------------------------------------------------------ the table
def _rate(h: int, b: int) -> float | None:
    return h / (h + b) if h + b else None


def bootstrap_delta(per_day: dict, draws: int = 2000, seed: int = 7) -> tuple[float | None, float | None]:
    """95 % interval of held % (real) − held % (placebo), resampling trading days."""
    import numpy as np
    days = sorted(per_day)
    if len(days) < 5:
        return None, None
    m = np.array([per_day[d] for d in days], float)          # columns: real held, real broke, placebo held, broke
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(days), size=(draws, len(days)))
    s = m[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = s[:, 0] / (s[:, 0] + s[:, 1]) - s[:, 2] / (s[:, 2] + s[:, 3])
    d = d[~np.isnan(d)]
    if len(d) < draws * 0.9:
        return None, None
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def table(events: list[dict]) -> list[dict]:
    rows = []
    for kind in KINDS:
        for side in SIDES:
            ev = [e for e in events if e["kind"] == kind and e["side"] == side]
            if not ev:
                continue
            per_day = defaultdict(lambda: [0, 0, 0, 0])
            cnt = {False: defaultdict(int), True: defaultdict(int)}
            split = {sp: {False: [0, 0], True: [0, 0]} for sp in ("train", "valid")}
            for e in ev:
                cnt[e["placebo"]][e["outcome"]] += 1
                if e["outcome"] == "open":
                    continue
                col = (2 if e["placebo"] else 0) + (0 if e["outcome"] == "held" else 1)
                per_day[e["day"]][col] += 1
                if e["split"] in split:
                    split[e["split"]][e["placebo"]][0 if e["outcome"] == "held" else 1] += 1
            r, p = cnt[False], cnt[True]
            hr, hp = _rate(r["held"], r["broke"]), _rate(p["held"], p["broke"])
            lo, hi = bootstrap_delta(per_day)
            sd = {sp: (_rate(*v[False]), _rate(*v[True])) for sp, v in split.items()}
            rows.append({"kind": kind, "side": side, "tests": sum(r.values()), "held": hr,
                         "open": r["open"] / sum(r.values()) if sum(r.values()) else None,
                         "p_tests": sum(p.values()), "p_held": hp,
                         "delta": (hr - hp) if hr is not None and hp is not None else None, "lo": lo, "hi": hi,
                         "split": {k: (None if a is None or b is None else a - b) for k, (a, b) in sd.items()},
                         "days": len(per_day)})
    return rows


def pc(x) -> str:
    return "—" if x is None else f"{100 * x:.0f} %"


def pp(x) -> str:
    return "—" if x is None else f"{100 * x:+.1f}"


def report_lines(rows: list[dict]) -> list[str]:
    out = [f" {'level':<6} {'side':<10} │{'tests':>7} {'held':>6} {'open':>6} │{'placebo':>8} {'held':>6} │"
           f" {'Δ held, pts':>11} {'95 % interval':>16} │ {'train Δ':>8} {'valid Δ':>8}"]
    for r in rows:
        ci = "—" if r["lo"] is None else f"[{pp(r['lo'])}, {pp(r['hi'])}]"
        out.append(f" {r['kind']:<6} {r['side']:<10} │{r['tests']:>7} {pc(r['held']):>6} {pc(r['open']):>6} │"
                   f"{r['p_tests']:>8} {pc(r['p_held']):>6} │ {pp(r['delta']):>11} {ci:>16} │"
                   f" {pp(r['split'].get('train')):>8} {pp(r['split'].get('valid')):>8}")
    return out


def reading(rows: list[dict]) -> list[str]:
    """One line a level: better than the placebo, no better, or worse — by the interval."""
    out = []
    for r in rows:
        if r["lo"] is None:
            word = "too few tests to say"
        elif r["lo"] > 0:
            word = "holds MORE often than the same level moved at random"
        elif r["hi"] < 0:
            word = "holds LESS often than the same level moved at random"
        else:
            word = "no different from the same level moved at random"
        out.append(f"   {r['kind']} {r['side']}: {word}")
    return out


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=("history", "daily"), default="history")
    ap.add_argument("--cache", default=str(D.HISTORY))
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--sample", type=int, help="plumbing: N sessions a split")
    ap.add_argument("--out", help="results folder (default research/strategy-candidates/results/<run>-levels)")
    args = ap.parse_args(argv)

    smoke = args.source == "daily" or bool(args.sample)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ") + "-levels" + ("-smoke" if smoke else "")
    out_dir = Path(args.out) if args.out else P.RESULTS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    t0, cov, events = time.monotonic(), {}, []
    if args.source == "history":
        uni = D.universe()
        days = sorted(d for d in uni if D.split_of(d) in ("train", "valid"))       # never a holdout day
        if args.sample:
            rnd = random.Random(SAMPLE_SEED)
            days = sorted(sum((rnd.sample([d for d in days if D.split_of(d) == sp],
                                          min(args.sample, sum(1 for d in days if D.split_of(d) == sp)))
                               for sp in ("train", "valid")), []))
        hist = D.History(Path(args.cache), fetch=not args.no_fetch)
        gen = D.history_days(uni, hist, days, cov)
        source = f"history · Alpaca SIP 1-minute bars, {args.cache} · 2021-2023 only (train + validation)"
    else:
        gen = D.daily_days(cov)
        source = "daily · the exported desk days of research/daily/, 04:00-12:00 bars — FIRST LOOK, not evidence"
    for i, (_day, sds) in enumerate(gen, 1):
        for sd in sds:
            assert sd.split != "holdout", "the level read-out never reads a holdout day"
            events += day_tests(sd)
        if i % 50 == 0:
            print(f"  {i} sessions · {time.monotonic() - t0:.0f} s", file=sys.stderr, flush=True)
    if sum(c[1] for c in cov.values()) == 0:
        print("no symbol-day had bars: run where data/cache/history exists, or with Alpaca keys in .env")
        return 2
    rows = table(events)
    rep = [f"LEVEL READ-OUT · run {run_id} · git {P.head()} · research/strategy-candidates/PREREGISTRATION.md, "
           "amendment 2026-10-14 · descriptive: decides nothing",
           f"SOURCE   {source}"]
    if smoke:
        rep.append("! FIRST LOOK / PLUMBING — not evidence")
    rep += ["COVERAGE " + " · ".join(f"{sp} {c[1]:,} / {c[0]:,} symbol-days with bars" for sp, c in sorted(cov.items())),
            "TEST     support: previous close above level + band, the bar's low at level + band or under (09:30-11:29);"
            " held = a high 1 ATR above first, broke = a close under level − band first, within 30 bars;"
            " resistance mirrored",
            "PLACEBO  the same level moved ±0.5-1.5 ATR (seeded by the symbol-day and the level), tested the same way ·"
            " held % = held / (held + broke) · interval: trading days resampled",
            ""] + report_lines(rows) + ["", " READING"] + reading(rows)
    rep += ["", f"done in {time.monotonic() - t0:.0f} s · {len(events):,} tests · files: {out_dir}",
            "Levels from the symbol-day's own bars (no prior session). Paper only."]
    text = "\n".join(rep)
    print(text)
    (out_dir / "report.txt").write_text(text + "\n")
    (out_dir / "summary.json").write_text(json.dumps({"run": run_id, "smoke": smoke, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
