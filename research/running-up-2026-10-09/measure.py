#!/usr/bin/env python3
"""Running Up on the recorded days: what each filter catches, misses and raises falsely.

    python3 research/running-up-2026-10-09/measure.py > research/running-up-2026-10-09/results.txt

Every exported day with the desk's own 1-minute bars for its board and screener
names (`research/daily/<day>/board_bars.csv.gz`, 04:00–12:00 ET) is replayed
through the desk's session builder (`build_session_from_records`), the same code
the live desk runs. Every scanner event is recorded BEFORE the notification
router (a spy on `NotificationRouter.handle`), so each scanner is scored on its
own alerts; the tile as the desk shows it (after the router's cooldown and its
same-moment consolidation) is scored too.

Reconstructed, and so Approximations:
  - previous close and float from the day's `decisions.csv` (the decision's own
    snapshot, as `scripts/fixture_from_export.py` does), else from `screener.csv`
    (price and gap); a name in neither has no previous close and no float;
  - halts: none were exported. A halt is inferred from the bars
    (`knowledge-base/strategies/PARAMETERS.md` §8b: "a halt appears in a minute
    series as a gap in the bars, which is the only signal available from OHLCV
    alone"). In this export the gap is filled: an untraded minute is a row with
    zero volume and open = high = low = close = the last price. A halt is a run
    of at least 4 such minutes (or missing ones) starting 09:30–16:00
    (PLAYBOOK.md: LULD halts only exist then) after 5 straight traded minutes:
    an LULD pause is "5 minutes minimum" (PARAMETERS.md, Halt types), and a
    pause that starts mid-minute leaves 4 empty minutes before the minute the
    reopening prints in. Halted at the first empty minute, resumed at the first
    traded one;
  - no news and no quotes: the catalyst reads UNKNOWN, every name alike.

The ground truth, stated before any scanner was scored and the same for every
scanner (Approximations, not Ross's numbers):
  RUN    a rise of >= 10 % from a low to a high within <= 10 minutes — the
         platform's "Squeeze Up 10% in 10min" branch, the one alert he keeps the
         sound on for (yg5E_mqGFGg @00:19:36) — with the low in $2–20, the high
         printed 07:00–11:30 ET, and >= 50,000 shares traded from the low to the
         high. Consecutive qualifying minutes are one run; the run starts at its
         low and ends at its high.
  MOVE   the looser run used to judge false alarms: >= 5 % within <= 5 minutes
         (the 5-in-5 "pre-alert", yg5E_mqGFGg @00:17:16), low in $2–20, high
         07:00–11:30, >= 10,000 shares from the low to the high. Judged minute
         by minute and never merged: a bounce inside a larger run is a move of
         its own. (The first run of this script merged MOVEs the way it merges
         RUNs, and so called a bounce that made no new high a false alarm —
         139 of the filters' 284. Fixed before any filter was changed.)
A RUN is CAUGHT when the scanner alerted on the name between the run's low and
its high. An alert is a FALSE ALARM when it is in $2–20 and 07:00–11:30 but
inside no MOVE (from its low to two minutes after its high); alerts outside the
band or the window are counted apart, because the band and the window are part
of the filters' definition.

Discovery only, checked on every day: the replay is run a second time with the
filters silenced, and (1) every plan, cascade verdict and card word, and (2)
every alert row the desk's own scanners showed, must be identical.
"""
from __future__ import annotations

import csv
import gzip
import statistics
import sys
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.dashboard import session_builder as SB  # noqa: E402
from momentum_platform.scanners import RunningUpFilters  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
DAILY = ROOT / "research" / "daily"
WINDOW = (time(7, 0), time(11, 30))
BAND = (2.0, 20.0)
RUN = dict(pct=10.0, minutes=10, volume=50_000)
MOVE = dict(pct=5.0, minutes=5, volume=10_000)
TILE_BEFORE = ("running_up", "squeeze_5_in_5", "squeeze_10_in_10")
TILE_AFTER = TILE_BEFORE + ("running_up_filters",)
HOD_TILE = ("hod_momentum", "breakout_52w")
VARIANTS = ("pct_in_n", "vol_surge", "new_hod", "halt_resume")


# --------------------------------------------------------------------- data
def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def load_day(day: str):
    base = DAILY / day
    bars = defaultdict(list)
    for r in csv.DictReader(gzip.open(base / "board_bars.csv.gz", "rt")):
        t = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
        bars[r["symbol"]].append((t, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]),
                                  float(r["volume"] or 0)))
    for rows in bars.values():
        rows.sort()
    refs = {}
    if (base / "decisions.csv").exists():
        for r in csv.DictReader(open(base / "decisions.csv")):
            sym, last, chg = r["symbol"], _f(r.get("last")), _f(r.get("change_pct"))
            if sym in refs or last is None or chg is None or chg <= -100:
                continue
            refs[sym] = {"prev_close": round(last / (1 + chg / 100.0), 4), "float_shares": _f(r.get("float_shares")),
                         "float_quality": r.get("float_quality") or "unknown", "src": "decisions"}
    if (base / "screener.csv").exists():
        for r in csv.DictReader(open(base / "screener.csv")):
            sym, px, gap = r["symbol"], _f(r.get("price")), _f(r.get("gap_pct"))
            if sym in refs or px is None or gap is None or gap <= -100:
                continue
            refs[sym] = {"prev_close": round(px / (1 + gap / 100.0), 4), "float_shares": _f(r.get("float_shares")),
                         "float_quality": "reported" if _f(r.get("float_shares")) else "unknown", "src": "screener"}
    return bars, refs


HALT_EMPTY_MINUTES = 4


def inferred_halts(bars):
    """(symbol, halted at, resumed at or None) from runs of untraded minutes —
    see the module note. A missing minute counts as untraded."""
    one = timedelta(minutes=1)
    out = []
    for sym, rows in bars.items():
        t = [r[0] for r in rows]
        traded = [r[5] > 0 for r in rows]
        i = 5
        while i < len(rows):
            if traded[i] and t[i] - t[i - 1] == one:
                i += 1
                continue
            start = t[i - 1] + one                       # the first untraded minute
            streak = traded[i - 5] and all(traded[k] and t[k] - t[k - 1] == one for k in range(i - 4, i))
            j = i
            while j < len(rows) and not traded[j]:
                j += 1
            resumed = t[j] if j < len(rows) else None
            empty = int(((resumed or t[-1] + one) - start).total_seconds() // 60)
            if streak and empty >= HALT_EMPTY_MINUTES and time(9, 30) <= start.astimezone(ET).time() < time(16, 0):
                out.append((sym, start, resumed))
            i = j + 1
    return out


def records(day, bars, refs, halts):
    recs = [{"type": "news_source", "ok": False}]
    for sym in bars:
        ref = refs.get(sym, {})
        recs.append({"type": "reference", "symbol": sym, "prev_close": ref.get("prev_close"),
                     "float_shares": ref.get("float_shares"),
                     "float_quality": ref.get("float_quality") if ref.get("float_shares") else "unknown",
                     "float_source": f"reconstructed from the day's {ref.get('src')}" if ref else None})
    for sym, h0, h1 in halts:
        recs.append({"type": "halt", "symbol": sym, "ts": h0.isoformat().replace("+00:00", "Z"), "status": "halted"})
        if h1 is not None:
            recs.append({"type": "halt", "symbol": sym, "ts": h1.isoformat().replace("+00:00", "Z"),
                         "status": "trading"})
    for sym, rows in bars.items():
        for t, o, h, l, c, v in rows:
            recs.append({"type": "bar", "tf": "1m", "symbol": sym, "ts": t.isoformat().replace("+00:00", "Z"),
                         "open": o, "high": h, "low": l, "close": c, "volume": v})
    return recs


# ------------------------------------------------------------- the replay
def replay(recs, extra=True):
    """(session, raw events). `extra` adds one RunningUpFilters per trigger,
    each under its own id, after every scanner the desk runs."""
    raw = []

    class Spy(SB.NotificationRouter):
        def handle(self, event):
            raw.append(event)
            return super().handle(event)

    class Engine(SB.ScannerEngine):
        def __init__(self, hot, scanners, router):
            if extra:
                for t in VARIANTS:
                    s = RunningUpFilters(triggers=(t,))
                    s.scanner_id = "ru." + t
                    scanners = list(scanners) + [s]
            super().__init__(hot=hot, scanners=scanners, router=router)

    real_router, real_engine = SB.NotificationRouter, SB.ScannerEngine
    SB.NotificationRouter, SB.ScannerEngine = Spy, Engine
    try:
        s = SB.build_session_from_records(recs, "ru", "ru")
    finally:
        SB.NotificationRouter, SB.ScannerEngine = real_router, real_engine
    return s, raw


# ---------------------------------------------------------- ground truth
def qualifying(rows, pct, minutes):
    """Every minute whose high is >= pct over the lowest low of the `minutes`
    bars ending with it, the high in the window and the low in the band:
    [(minute index, index of that low)]."""
    out = []
    for j, (tj, oj, hj, lj, cj, vj) in enumerate(rows):
        if not (WINDOW[0] <= tj.astimezone(ET).time() < WINDOW[1]):
            continue
        k, i = j, j
        while i >= 0 and tj - rows[i][0] <= timedelta(minutes=minutes - 1):
            if rows[i][3] <= rows[k][3]:
                k = i                                  # the lowest low, the earliest on a tie
            i -= 1
        lo = rows[k][3]
        if lo > 0 and BAND[0] <= lo <= BAND[1] and 100.0 * (hj / lo - 1.0) >= pct:
            out.append((j, k))
    return out


def _shares(rows, k, j):
    return sum(rows[i][5] for i in range(k, j + 1))


def runs(rows, pct, minutes, volume):
    """RUNs on one name. Qualifying minutes <= 2 minutes apart are one run; it
    starts at its first low and ends at its highest high."""
    out, cur = [], None
    for j, k in qualifying(rows, pct, minutes):
        tj, hj = rows[j][0], rows[j][2]
        if cur is not None and (tj - rows[cur["last"]][0]) <= timedelta(minutes=2):
            cur["last"] = j
            if hj > cur["high"]:
                cur["high"], cur["peak_i"] = hj, j
        else:
            if cur is not None:
                out.append(cur)
            cur = {"start_i": k, "low": rows[k][3], "peak_i": j, "high": hj, "last": j}
    if cur is not None:
        out.append(cur)
    keep = []
    for r in out:
        shares = _shares(rows, r["start_i"], r["peak_i"])
        if shares >= volume:
            keep.append({"start": rows[r["start_i"]][0], "low": r["low"], "peak": rows[r["peak_i"]][0],
                         "high": r["high"], "shares": shares})
    return keep


def moves(rows, pct, minutes, volume):
    """MOVEs on one name, one per qualifying minute and never merged — a bounce
    inside a larger run is a move of its own: [(low time, high time)]."""
    return [(rows[k][0], rows[j][0]) for j, k in qualifying(rows, pct, minutes) if _shares(rows, k, j) >= volume]


def in_band_window(a_t, price):
    return BAND[0] <= price <= BAND[1] and WINDOW[0] <= a_t.astimezone(ET).time() < WINDOW[1]


def why_false(sym, t, bars_idx, rows):
    """The first reason, in this order, a false alarm was not a MOVE."""
    j = bars_idx.get(t)
    if j is None:
        return "other"
    i, k = j, j
    while i >= 0 and t - rows[i][0] <= timedelta(minutes=MOVE["minutes"] - 1):
        if rows[i][3] <= rows[k][3]:
            k = i
        i -= 1
    lo, hi = rows[k][3], max(r[2] for r in rows[k:j + 1])
    if lo <= 0 or 100.0 * (hi / lo - 1.0) < MOVE["pct"]:
        return "under 5%"
    if lo < BAND[0]:
        return "low under $2"
    if _shares(rows, k, j) < MOVE["volume"]:
        return "under 10k sh"
    return "other"


FALSE_WHY = ("under 5%", "low under $2", "under 10k sh", "other")


def score(alerts, truth_runs, loose_moves, closes, bars=None, bars_idx=None):
    """alerts: [(symbol, time, price)]."""
    caught, leads, left = 0, [], []
    names_caught = set()
    for sym, rs in truth_runs.items():
        for r in rs:
            hits = sorted(t for s, t, p in alerts if s == sym and r["start"] <= t <= r["peak"])
            if hits:
                caught += 1
                names_caught.add(sym)
                first = hits[0]
                leads.append((first - r["start"]).total_seconds() / 60.0)
                px = closes[sym].get(first)
                if px is not None and r["high"] > r["low"]:
                    left.append(100.0 * (r["high"] - px) / (r["high"] - r["low"]))
    false, outside_band, outside_window, useful = 0, 0, 0, 0
    why = dict.fromkeys(FALSE_WHY, 0)
    for sym, t, p in alerts:
        if not (WINDOW[0] <= t.astimezone(ET).time() < WINDOW[1]):
            outside_window += 1
            continue
        if not (BAND[0] <= p <= BAND[1]):
            outside_band += 1
            continue
        if any(lo_t <= t <= hi_t + timedelta(minutes=2) for lo_t, hi_t in loose_moves.get(sym, [])):
            useful += 1
        else:
            false += 1
            if bars is not None:
                why[why_false(sym, t, bars_idx[sym], bars[sym])] += 1
    return {"caught": caught, "names": names_caught, "lead": leads, "left": left, "false": false,
            "outside_band": outside_band, "outside_window": outside_window, "useful": useful,
            "alerts": len(alerts), "why": why}


def _orphan(scanner_id, also, tile):
    """A row filed under a scanner no tile shows, with a member of `tile`."""
    return (scanner_id != "halt" and scanner_id not in TILE_AFTER + HOD_TILE
            and any(k in tile for k in also))


def tile_rows(rows, tile, orphan_rule):
    """The alerts a tile lists, as the desk's `loggedAlerts` lists them: its
    own scanners' rows, and with the orphan rule (2026-10-09) a row filed under
    a scanner with no tile when one of its members is the tile's."""
    return [x for sid, also, x in rows if sid in tile or (orphan_rule and _orphan(sid, also, tile))]


def _desk_rows(session):
    """Every alert row the desk's own scanners showed, the filters' left out."""
    return sorted((a["symbol"], a["scannerId"], a.get("branch") or "", a["sourceTime"])
                  for f in session["frames"] for a in f["alerts"]
                  if a["scannerId"] != "running_up_filters" and not a["scannerId"].startswith("ru."))


def _decisions(session):
    return ([(p["symbol"], p["armedAt"], p["entry"], p["stop"]) for p in session["plans"]],
            {k: v["verdict"] for k, v in session["cascade"].items()},
            {k: c["verdict"]["word"] for k, c in session["cards"].items()})


def why_missed(sym, r, alerts):
    """Why a RUN got no alert between its low and its high."""
    ts = sorted(t for s, t, p in alerts if s == sym)
    before = [t for t in ts if t < r["start"]]
    after = [t for t in ts if t > r["peak"]]
    if before and r["start"] - before[-1] <= timedelta(minutes=10):
        return "an alert <= 10 min before its low (the leg was already called)"
    if after and after[0] - r["peak"] <= timedelta(minutes=5):
        return "first alert <= 5 min after its high (late)"
    return "no alert from 10 min before its low to 5 min after its high"


MISSED_WHY = ("an alert <= 10 min before its low (the leg was already called)",
              "first alert <= 5 min after its high (late)",
              "no alert from 10 min before its low to 5 min after its high")


def main() -> int:
    days = sorted(p.name for p in DAILY.iterdir() if (p / "board_bars.csv.gz").exists())
    totals = defaultdict(lambda: {"caught": 0, "false": 0, "outside_band": 0, "outside_window": 0,
                                  "useful": 0, "alerts": 0, "leads": [], "left": [], "names": set(),
                                  "why": dict.fromkeys(FALSE_WHY, 0)})
    truth_all, names_all, name_days = 0, 0, 0
    per_day, missed = [], defaultdict(list)
    guard_decisions, guard_rows = True, True
    halts_total, halt_runs, orphans = 0, 0, 0
    for day in days:
        bars, refs = load_day(day)
        halts = inferred_halts(bars)
        halts_total += len(halts)
        recs = records(day, bars, refs, halts)
        s, raw = replay(recs)
        # discovery only: the same day with the filters silenced
        real = SB.RunningUpFilters
        SB.RunningUpFilters = lambda: _Silent()
        try:
            s0, _ = replay(recs, extra=False)
        finally:
            SB.RunningUpFilters = real
        guard_decisions &= _decisions(s) == _decisions(s0)
        guard_rows &= _desk_rows(s) == _desk_rows(s0)
        idx = {sym: {r[0]: i for i, r in enumerate(rows)} for sym, rows in bars.items()}
        closes = {sym: {t: c for t, o, h, l, c, v in rows} for sym, rows in bars.items()}
        truth = {sym: runs(rows, **RUN) for sym, rows in bars.items()}
        loose = {sym: moves(rows, **MOVE) for sym, rows in bars.items()}
        n_truth = sum(len(v) for v in truth.values())
        truth_all += n_truth
        names_all += sum(1 for v in truth.values() if v)
        name_days += len(bars)
        halt_runs += sum(1 for sym, h0, h1 in halts for r in truth.get(sym, [])
                         if h1 is not None and r["start"] <= h1 <= r["peak"])
        raw_by = defaultdict(list)
        for e in raw:
            raw_by[e.scanner].append((e.symbol, e.source_ts, e.values.get("last") or 0.0))
        rows = []
        for f in s["frames"]:
            for a in f["alerts"]:
                t = datetime.fromisoformat(a["sourceTime"].replace("Z", "+00:00"))
                rows.append((a["scannerId"], (a.get("group") or {}).get("also_triggered") or [],
                             (a["symbol"], t, (a.get("values") or {}).get("last") or 0.0)))
        orphans += sum(1 for sid, also, x in rows if _orphan(sid, also, TILE_AFTER))
        groups = {
            "tile before (as shown)": tile_rows(rows, TILE_BEFORE, orphan_rule=False),
            "tile after (as shown)": tile_rows(rows, TILE_AFTER, orphan_rule=True),
            "desk, both tiles, before": tile_rows(rows, TILE_BEFORE + HOD_TILE, orphan_rule=False),
            "desk, both tiles, after": tile_rows(rows, TILE_AFTER + HOD_TILE, orphan_rule=True),
            "tile after, no orphan rule": tile_rows(rows, TILE_AFTER, orphan_rule=False),
            "running_up (10-min uptrend)": raw_by.get("running_up", []),
            "squeeze_5_in_5": raw_by.get("squeeze_5_in_5", []),
            "squeeze_10_in_10": raw_by.get("squeeze_10_in_10", []),
            "hod_momentum (other tile)": raw_by.get("hod_momentum", []),
            "filters, all four": raw_by.get("running_up_filters", []),
        }
        for t in VARIANTS:
            groups["filter " + t] = raw_by.get("ru." + t, [])
        day_line = {"day": day, "names": len(bars), "runs": n_truth, "halts": len(halts)}
        for g, alerts in groups.items():
            sc = score(alerts, truth, loose, closes, bars, idx)
            tot = totals[g]
            for k in ("caught", "false", "outside_band", "outside_window", "useful", "alerts"):
                tot[k] += sc[k]
            tot["leads"] += sc["lead"]
            tot["left"] += sc["left"]
            tot["names"] |= {(day, n) for n in sc["names"]}
            for k, v in sc["why"].items():
                tot["why"][k] += v
            day_line[g] = sc
        per_day.append(day_line)
        for sym, rs in truth.items():
            for r in rs:
                for g in ("tile before (as shown)", "tile after (as shown)", "filters, all four",
                          "desk, both tiles, before", "desk, both tiles, after"):
                    if not any(s_ == sym and r["start"] <= t <= r["peak"] for s_, t, p in groups[g]):
                        missed[g].append((day, sym, r, why_missed(sym, r, groups[g]),
                                          refs.get(sym, {}).get("float_shares"),
                                          refs.get(sym, {}).get("float_quality")))

    print("# Running Up filters on the recorded days — what each catches, misses and raises falsely")
    print(f"# {len(days)} days ({days[0]} … {days[-1]}), {name_days} name-days: every name with the desk's own")
    print("# 1-minute bars (board_bars.csv.gz), replayed through the desk's session builder")
    print(f"# RUN  = >= {RUN['pct']:g}% low->high within <= {RUN['minutes']} min, low ${BAND[0]:g}-{BAND[1]:g}, "
          f"high {WINDOW[0]:%H:%M}-{WINDOW[1]:%H:%M} ET, >= {RUN['volume']:,} shares (Approximation)")
    print(f"# MOVE = >= {MOVE['pct']:g}% within <= {MOVE['minutes']} min, same band/window, >= {MOVE['volume']:,} "
          "shares, per minute — what a false alarm is judged against")
    print(f"# {truth_all} RUNs on {names_all} name-days; {halts_total} halts inferred from runs of >= "
          f"{HALT_EMPTY_MINUTES} untraded minutes, {halt_runs} of them resuming inside a RUN")
    print(f"# orphan rule: {orphans} rows filed under a scanner with no tile (running_down, five_pillars_alert) "
          "with a Running Up member; the tile now lists them")
    print(f"# guard 1: plans, cascade verdicts and card words identical with the filters silenced, "
          f"{len(days)} days: {'YES' if guard_decisions else 'NO — a scanner changed a decision'}")
    print(f"# guard 2: every alert row the desk's own scanners showed is identical with the filters silenced, "
          f"{len(days)} days: {'YES' if guard_rows else 'NO — the filters took a row from another tile'}")
    print()
    print(f"{'scanner':30s} {'RUNs caught':>12s} {'name-days':>10s} {'lead min':>9s} {'run left':>9s} "
          f"{'alerts*':>8s} {'useful':>7s} {'false':>6s} {'false %':>8s} {'out $':>6s} {'out t':>6s}")
    for g, tot in totals.items():
        leads, left = tot["leads"], tot["left"]
        inwin = tot["useful"] + tot["false"]
        print(f"{g:30s} {tot['caught']:5d}/{truth_all:<6d} {len(tot['names']):6d}/{names_all:<3d} "
              f"{(statistics.median(leads) if leads else float('nan')):9.1f} "
              f"{(statistics.median(left) if left else float('nan')):8.0f}% {tot['alerts']:8d} "
              f"{tot['useful']:7d} {tot['false']:6d} "
              f"{(100.0 * tot['false'] / inwin if inwin else float('nan')):7.0f}% "
              f"{tot['outside_band']:6d} {tot['outside_window']:6d}")
    print("  RUNs caught: alerted between the run's low and its high · name-days: with at least one run caught ·")
    print("  lead: minutes from the run's low to the first alert (median) · run left: share of the run's")
    print("  low->high still above the first alert's price (median; 100% = at the low) · alerts*: every alert,")
    print("  any band or hour · useful / false: in $2-20 and 07:00-11:30, inside a MOVE or not · out $ / out t:")
    print("  alerts outside the band / the window")
    print()
    print("## false alarms, by the first reason the alert was not a MOVE")
    print(f"{'scanner':30s} " + " ".join(f"{w:>14s}" for w in FALSE_WHY))
    for g, tot in totals.items():
        print(f"{g:30s} " + " ".join(f"{tot['why'][w]:14d}" for w in FALSE_WHY))
    print("  under 5%: the move from the 5-minute low was smaller (vol_surge fires at 3% in 2 min, new_hod and")
    print("  halt_resume at no size) · low under $2: the alert is in the band, the move started below it ·")
    print("  under 10k sh: fewer than 10,000 shares from the low to the alert · other: a 5% move with the")
    print("  volume whose high printed more than 2 minutes before the alert")
    print()
    print("## per day — RUNs caught, the tile before -> after (false alarms before -> after)")
    for d in per_day:
        b, a = d["tile before (as shown)"], d["tile after (as shown)"]
        print(f"  {d['day']}  names {d['names']:2d}  RUNs {d['runs']:3d}  halts {d['halts']:2d}  "
              f"caught {b['caught']:3d} -> {a['caught']:3d}  false {b['false']:3d} -> {a['false']:3d}")
    print()
    for g in ("tile before (as shown)", "tile after (as shown)", "filters, all four",
              "desk, both tiles, before", "desk, both tiles, after"):
        ms = missed[g]
        print(f"## RUNs the {g.split(' (')[0]} missed: {len(ms)}")
        for w in MISSED_WHY:
            print(f"  {sum(1 for m in ms if m[3] == w):4d}  {w}")
        print()
    for g in ("tile after (as shown)", "desk, both tiles, after"):
        blind = [m for m in missed[g] if m[3] == MISSED_WHY[2]]
        print(f"## {g}: every RUN with no alert from 10 min before its low to 5 min after its high ({len(blind)})")
        for day, sym, r, w, fl, fq in blind:
            one = " · one minute, low and high in the same bar" if r["start"] == r["peak"] else ""
            fls = "float unknown" if not fl else f"float {fl / 1e6:.1f}M {fq}"
            print(f"  {day} {sym:5s} {r['start'].astimezone(ET):%H:%M} {r['low']:.2f} -> "
                  f"{r['peak'].astimezone(ET):%H:%M} {r['high']:.2f} (+{100 * (r['high'] / r['low'] - 1):.0f}%, "
                  f"{int(r['shares']):,} sh) · {fls}{one}")
        print()
    return 0


class _Silent(RunningUpFilters):
    """The filters, switched off: the guard's day without them."""

    def on_snapshot(self, *a, **k):
        return []


if __name__ == "__main__":
    sys.exit(main())
