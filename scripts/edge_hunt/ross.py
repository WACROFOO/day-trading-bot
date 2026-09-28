#!/usr/bin/env python3
"""His trades, rebuilt on the tape (research/ross-trades/).

    python3 scripts/edge_hunt/ross.py collect    # workflow output -> ledger.csv, quote check
    python3 scripts/edge_hunt/ross.py date       # tape-date the rows the text does not date
    python3 scripts/edge_hunt/ross.py rebuild    # minute bars, stated-price check, entry context, bot beside him

Every price comes from Alpaca SIP bars, raw (unadjusted) — the prices he saw.
Nothing here decides a rule; it measures his trades and the bot on the same
symbol-days.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

from edge_hunt.data import ET, minute  # noqa: E402

OUT = ROOT / "research" / "ross-trades"
CACHE = ROOT / "data" / "cache" / "ross"
HIST = ROOT / "data" / "cache" / "history"
ALPACA_START = "2016-01-04"


# ------------------------------------------------------------------ helpers
def norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("…", "...")
    return re.sub(r"[^a-z0-9$.%']+", " ", s).strip()


def quote_found(path: str, quote: str) -> tuple[bool, float]:
    """Is the quote in the file? Exact after normalisation, else the share of
    its 8-word shingles present (captions split lines mid-sentence)."""
    try:
        text = Path(ROOT / path).read_text(errors="ignore")
    except OSError:
        return False, 0.0
    # transcripts: drop [hh:mm:ss] stamps and line breaks
    text = re.sub(r"\[\d\d:\d\d:\d\d\]", " ", text)
    quote = re.sub(r"\[\d\d:\d\d:\d\d\]", " ", quote or "")
    t, q = norm(text), norm(quote)
    if not q:
        return False, 0.0
    if q in t:
        return True, 1.0
    w = q.split()
    if len(w) < 8:
        return False, 0.0
    sh = [" ".join(w[i:i + 8]) for i in range(0, len(w) - 7)]
    frac = sum(1 for x in sh if x in t) / len(sh)
    return frac >= 0.6, round(frac, 2)


# ------------------------------------------------------------------ collect
FIELDS = ["row_id", "register", "path", "file_date", "file_title", "trader", "kind", "ticker_as_said", "ticker",
          "ticker_confidence", "side", "session_date", "date_clue", "recounted_from_other_day", "clock_time",
          "video_ts", "line", "entries", "stop", "exits", "pnl_usd", "pnl_as_said", "outcome", "size_as_said",
          "setup", "entry_reason", "exit_reason", "mistake", "pillars_named", "halt_involved",
          "level2_or_tape_reason", "session_window", "quote", "quote_found", "quote_match", "file_day_pnl"]


def collect(wf_output: Path, batches: Path) -> pd.DataFrame:
    res = json.loads(wf_output.read_text())
    res = res.get("result", res)
    meta = {}
    for b in json.loads(batches.read_text()):
        for f in b:
            meta[f["path"]] = f
    rows, files = [], []
    for bt in res["batches"]:
        for f in (bt or {}).get("files") or []:
            m = meta.get(f["path"], {})
            files.append({"path": f["path"], "register": m.get("register"), "trader": f.get("trader"),
                          "kind": f.get("kind"), "n_trades": len(f.get("trades") or []),
                          "file_date_clues": f.get("file_date_clues", ""), "day_pnl_as_said": f.get("day_pnl_as_said", ""),
                          "watched_not_traded": json.dumps(f.get("watched_not_traded") or [])})
            for t in f.get("trades") or []:
                r = {k: t.get(k, "") for k in FIELDS if k in t}
                r.update({"register": m.get("register"), "path": f["path"], "file_date": m.get("upload_date"),
                          "file_title": m.get("title"), "trader": f.get("trader"), "kind": f.get("kind"),
                          "file_day_pnl": f.get("day_pnl_as_said", "")})
                r["entries"] = json.dumps(t.get("entries") or []); r["exits"] = json.dumps(t.get("exits") or [])
                r["pillars_named"] = json.dumps(t.get("pillars_named") or [])
                ok, frac = quote_found(f["path"], t.get("quote", ""))
                r["quote_found"], r["quote_match"] = ok, frac
                rows.append(r)
    df = pd.DataFrame(rows)
    df.insert(0, "row_id", [f"R{i:05d}" for i in range(len(df))])
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(files).to_csv(OUT / "files.csv", index=False)
    return df[[c for c in FIELDS if c in df.columns]]


# ------------------------------------------------------------------ Alpaca
_client = None
_BOT: dict = {}


def client():
    global _client
    if _client is None:
        from edge_hunt.fetch import Pacer, alpaca
        _client = (alpaca(), Pacer(180))
    return _client


def _get(path, params):
    from edge_hunt.fetch import aget
    c, p = client()
    return aget(c, p, path, params)


def daily(sym: str) -> pd.DataFrame:
    """Raw daily bars 2016-01-04 .. yesterday, cached per symbol."""
    f = CACHE / "daily" / f"{sym}.json"
    if f.exists():
        rows = json.loads(f.read_text())
    else:
        rows, token = [], None
        while True:
            p = _get("/v2/stocks/bars", {"symbols": sym, "timeframe": "1Day", "start": ALPACA_START,
                                         "end": "2026-09-25", "limit": 10000, "adjustment": "raw",
                                         "feed": client()[0].feed, "page_token": token})
            rows += [[r["t"][:10], r["o"], r["h"], r["l"], r["c"], r["v"]] for r in (p.get("bars") or {}).get(sym, []) or []]
            token = p.get("next_page_token")
            if not token:
                break
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(rows))
    return pd.DataFrame(rows, columns=["day", "o", "h", "l", "c", "v"]).drop_duplicates("day").sort_values("day").reset_index(drop=True)


def minutes(sym: str, day: str) -> pd.DataFrame:
    """Raw 1-minute bars 04:00-20:00 ET for one symbol-day, cached."""
    f = CACHE / "min" / f"{day}_{sym}.json"
    if f.exists():
        rows = json.loads(f.read_text())
    else:
        from edge_hunt.fetch import et_utc
        rows, token = [], None
        while True:
            p = _get("/v2/stocks/bars", {"symbols": sym, "timeframe": "1Min", "start": et_utc(day, 4, 0),
                                         "end": et_utc(day, 20, 0), "limit": 10000, "adjustment": "raw",
                                         "feed": client()[0].feed, "page_token": token})
            rows += [[r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]] for r in (p.get("bars") or {}).get(sym, []) or []]
            token = p.get("next_page_token")
            if not token:
                break
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(rows))
    if not rows:
        return pd.DataFrame(columns=["min", "o", "h", "l", "c", "v"])
    noon = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=ET)
    off = int(noon.utcoffset().total_seconds() // 60)
    out = []
    for t, o, h, l, c, v in rows:
        mm = int(t[11:13]) * 60 + int(t[14:16]) + off - 240
        if t[:10] != day:
            mm += 1440
        out.append((mm, o, h, l, c, v))
    return pd.DataFrame(out, columns=["min", "o", "h", "l", "c", "v"]).sort_values("min").reset_index(drop=True)


# ------------------------------------------------------------------ prices
def prices(js: str) -> list[float]:
    try:
        return [float(x["price"]) for x in json.loads(js or "[]") if x.get("price") not in (None, "")]
    except (ValueError, TypeError):
        return []


def parse_clock(s: str) -> int | None:
    """'9:31', '7:05 am', '10:02' -> minutes since 04:00 ET, if plausible."""
    m = re.search(r"(\d{1,2})[:.](\d{2})", s or "")
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if "pm" in (s or "").lower() and hh < 12:
        hh += 12
    if hh < 4 and "pm" not in (s or "").lower():
        hh += 12
    if not (4 <= hh < 20):
        return None
    return minute(hh, mm)


# ------------------------------------------------------------------ dating
def tape_date(df: pd.DataFrame) -> pd.DataFrame:
    """Rows with no session_date: find the session(s) on which the file's
    tickers moved AND every stated price of a ticker lies inside that day's
    range (daily bars, 3 % tolerance for pre-market prints outside the regular
    range). A file whose tickers agree on one day dates all its rows."""
    df = df.copy()
    df["date_source"] = np.where(df["session_date"].astype(str).str.match(r"\d{4}-\d{2}-\d{2}"), "text", "")
    need = df[(df["date_source"] == "") & (df["ticker"].astype(str).str.len() > 0)]
    cands_by_file: dict[str, dict[str, set]] = defaultdict(dict)
    for r in need.itertuples():
        px = prices(r.entries) + prices(r.exits)
        if not px:
            continue
        try:
            d = daily(r.ticker)
        except Exception:                                        # noqa: BLE001
            continue
        if d.empty:
            continue
        d = d.assign(pc=d["c"].shift(1))
        hit = d[(d["l"] * 0.97 <= min(px)) & (d["h"] * 1.03 >= max(px)) & (d["h"] >= 1.15 * d["pc"])]
        if r.file_date and str(r.file_date)[:4].isdigit():
            pass
        cands_by_file[r.path][r.row_id] = set(hit["day"])
    date_of, how = {}, {}
    for path, per_row in cands_by_file.items():
        count = defaultdict(int)
        for s in per_row.values():
            for dd in s:
                count[dd] += 1
        if not count:
            continue
        best = max(count.values())
        tops = [dd for dd, c in count.items() if c == best]
        for rid, s in per_row.items():
            mine = [dd for dd in tops if dd in s]
            if len(mine) == 1 and (best >= 2 or len(s) == 1):
                date_of[rid] = mine[0]
                how[rid] = f"tape: {best} of {len(per_row)} tickers in the file agree" if best >= 2 else "tape: the only matching session"
            elif len(s) == 1:
                date_of[rid] = next(iter(s)); how[rid] = "tape: the only matching session for this ticker"
            else:
                how[rid] = f"undated: {len(s)} candidate sessions"
    df.loc[df["row_id"].isin(date_of), "session_date"] = df["row_id"].map(date_of)
    df.loc[df["row_id"].isin(date_of), "date_source"] = df["row_id"].map(how)
    df.loc[df["row_id"].isin(how) & ~df["row_id"].isin(date_of), "date_source"] = df["row_id"].map(how)
    return df


# ------------------------------------------------------------------ rebuild
def rebuild_row(r, uni_days: dict) -> dict:
    out = {"row_id": r.row_id}
    day, sym = str(r.session_date), str(r.ticker)
    if not re.match(r"\d{4}-\d{2}-\d{2}$", day) or not sym or day < ALPACA_START:
        out["tape"] = "no date" if sym else "no ticker"
        return out
    b = minutes(sym, day)
    if b.empty:
        out["tape"] = "no bars"
        return out
    d = daily(sym)
    prev = d[d["day"] < day].tail(1)
    pc = float(prev["c"].iloc[0]) if len(prev) else float("nan")
    ent, ex = prices(r.entries), prices(r.exits)
    lo, hi = b["l"].min(), b["h"].max()
    printed = [lo - 0.011 <= p <= hi + 0.011 for p in ent + ex]
    out.update({"prev_close": pc, "day_low": lo, "day_high": hi, "prices_stated": len(printed),
                "prices_printed": int(sum(printed)), "tape": "ok" if printed and all(printed) else ("no prices" if not printed else "PRICE NEVER PRINTED")})
    if not ent:
        return out
    e0 = ent[0]
    after = parse_clock(str(r.clock_time)) if r.clock_time else None
    touch = b[(b["l"] - 0.011 <= e0) & (b["h"] + 0.011 >= e0)]
    if after is not None:
        near = touch[(touch["min"] >= after - 3) & (touch["min"] <= after + 5)]
        touch = near if len(near) else touch
    if touch.empty:
        return out
    k = touch.index[0]
    t = int(b.at[k, "min"])
    out["entry_min"] = t
    out["entry_minutes_candidates"] = len(touch)
    pre = b.loc[:k]
    tp = (pre["h"] + pre["l"] + pre["c"]) / 3
    vwap = float((tp * pre["v"]).sum() / max(pre["v"].sum(), 1))
    pm = b[b["min"] < minute(9, 30)]
    pmh = float(pm.loc[pm.index <= k, "h"].max()) if len(pm.loc[pm.index <= k]) else float("nan")
    hod_before = float(b.loc[:k - 1, "h"].max()) if k > 0 else float("nan")
    first10 = b[b["h"] >= 1.10 * pc]
    out.update({
        "entry_price": e0,
        "gain_at_entry": e0 / pc - 1 if pc == pc else float("nan"),
        "vs_vwap": e0 / vwap - 1,
        "vs_pm_high": e0 / pmh - 1 if pmh == pmh else float("nan"),
        "vs_hod_before": e0 / hod_before - 1 if hod_before == hod_before else float("nan"),
        "breakout": bool(hod_before == hod_before and e0 >= hod_before),
        "min_since_first10": t - int(first10["min"].iloc[0]) if len(first10) else float("nan"),
        "cum_vol_at_entry": float(pre["v"].sum()),
        "dv5_at_entry": float((b.loc[max(0, k - 5):k - 1, "c"] * b.loc[max(0, k - 5):k - 1, "v"]).sum()),
        "range1m_med30": float(((b.loc[max(0, k - 30):k, "h"] - b.loc[max(0, k - 30):k, "l"]) / b.loc[max(0, k - 30):k, "c"]).median()),
        "in_universe": sym in uni_days.get(day, set()),
    })
    stop = None
    m = re.search(r"\d+(\.\d+)?", str(r.stop or ""))
    if m and str(r.stop).lower() != "not stated":
        try:
            v = float(m.group(0))
            if 0 < v < e0:
                stop = v
        except ValueError:
            pass
    out["stop_price"] = stop
    try:
        out.update(his_entry_mechanical(sym, day, t, e0, stop))
    except Exception as exc:                                     # noqa: BLE001
        out["mech_error"] = str(exc)[:80]
    key = (sym, day)
    if key not in _BOT:
        try:
            _BOT[key] = bot_on_day(sym, day, pc if pc == pc else float(b["o"].iloc[0]))
        except Exception as exc:                                 # noqa: BLE001
            _BOT[key] = {"bot": f"error {str(exc)[:60]}"}
    bd = _BOT[key]
    out["bot_status"] = bd.get("bot")
    if bd.get("bot") == "ok":
        near = [x for x in bd["plans"] if abs(x["t"] - t) <= 5]
        out.update({"bot_plans_day": bd["n_plans"], "bot_green_filled_day": bd["n_green_filled"],
                    "bot_trades_day": bd["bot_trades"], "bot_net_day": bd["bot_net"],
                    "bot_plan_near_entry": len(near) > 0,
                    "bot_near_red": ";".join(sorted({x["red"] for x in near})) if near else "",
                    "bot_near_green_filled": any(x["red"] == "-" and "net" in x for x in near),
                    "bot_plans_before_entry": sum(1 for x in bd["plans"] if x["t"] < t)})
    if ex:
        avg_ex = float(np.mean(ex))
        out["move_pct"] = avg_ex / float(np.mean(ent)) - 1 if r.side != "short" else float(np.mean(ent)) / avg_ex - 1
        if stop:
            out["r_multiple"] = (avg_ex - float(np.mean(ent))) / (e0 - stop)
        last_ex = ex[-1]
        after_b = b[b["min"] > t]
        hit = after_b[(after_b["l"] - 0.011 <= last_ex) & (after_b["h"] + 0.011 >= last_ex)]
        if len(hit):
            xm = int(hit["min"].iloc[0])
            out["exit_min"] = xm
            out["hold_min"] = xm - t
            nxt = b[(b["min"] > xm) & (b["min"] <= xm + 60)]
            if len(nxt):
                out["after_exit_max_60m"] = float(nxt["h"].max()) / last_ex - 1
                out["after_exit_min_60m"] = float(nxt["l"].min()) / last_ex - 1
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("collect", "date", "rebuild", "daily_all", "pit"))
    ap.add_argument("--wf", help="workflow output file (collect)")
    ap.add_argument("--batches", help="batches json (collect)")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.stage == "pit":
        fetch_pit()
        return 0
    if args.stage == "daily_all":
        syms = symbols_all()
        print(len(syms), "symbols")
        fetch_daily_all(syms)
        return 0
    if args.stage == "collect":
        df = collect(Path(args.wf), Path(args.batches))
        df.to_csv(OUT / "ledger_raw.csv", index=False)
        print(f"{len(df)} rows · quote found {df.quote_found.mean():.0%}")
    elif args.stage == "date":
        df = pd.read_csv(OUT / "ledger_raw.csv", dtype=str, keep_default_na=False)
        df = tape_date(df)
        df.to_csv(OUT / "ledger_dated.csv", index=False)
        print(df["date_source"].str.split(":").str[0].value_counts())
    else:
        df = pd.read_csv(OUT / "ledger_dated.csv", dtype=str, keep_default_na=False)
        uni = defaultdict(set)
        with open(ROOT / "research" / "first-pullback-edge" / "data" / "candidate_days.csv") as f:
            for r in csv.DictReader(f):
                uni[r["day"]].add(r["sym"])
        out = []
        for i, r in enumerate(df.itertuples()):
            try:
                out.append(rebuild_row(r, uni))
            except Exception as exc:                             # noqa: BLE001
                out.append({"row_id": r.row_id, "tape": f"error {str(exc)[:80]}"})
            if i % 100 == 0:
                print(f"  {i}/{len(df)}", flush=True)
        rb = pd.DataFrame(out)
        rb.to_csv(OUT / "rebuild.csv", index=False)
        print(rb["tape"].value_counts())
    return 0



# ------------------------------------------------------------------ the point-in-time universe, stage 1
def symbols_all() -> list[str]:
    sp = Path("/tmp/claude-0/-home-user-day-trading-bot/6b4cf148-a65f-567e-98fc-7d02cdbb6f60/scratchpad")
    syms = set()
    for st in ("active", "inactive"):
        f = sp / f"assets_{st}.json"
        if f.exists():
            for a in json.loads(f.read_text()):
                if a.get("exchange") not in ("OTC", None) and a.get("class", "us_equity") == "us_equity":
                    syms.add(a["symbol"])
    with open(ROOT / "research" / "first-pullback-edge" / "data" / "candidate_days.csv") as f:
        for r in csv.DictReader(f):
            syms.add(r["sym"])
    return sorted(x for x in syms if re.fullmatch(r"[A-Z][A-Z.]{0,5}", x))


def fetch_daily_all(syms: list[str]) -> None:
    """Raw daily bars for many symbols, 100 per request, one cache file per symbol."""
    todo = [s for s in syms if not (CACHE / "daily" / f"{s}.json").exists()]
    (CACHE / "daily").mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        got: dict[str, list] = {s: [] for s in chunk}
        token = None
        while True:
            try:
                p = _get("/v2/stocks/bars", {"symbols": ",".join(chunk), "timeframe": "1Day", "start": ALPACA_START,
                                             "end": "2026-09-25", "limit": 10000, "adjustment": "raw",
                                             "feed": client()[0].feed, "page_token": token})
            except Exception as exc:                             # noqa: BLE001
                bad = re.search(r"invalid symbol: (\S+?)\"", str(exc))
                if bad and bad.group(1) in chunk:
                    chunk.remove(bad.group(1)); got.pop(bad.group(1), None); token = None
                    (CACHE / "daily" / f"{bad.group(1)}.json").write_text("[]")
                    continue
                raise
            for s, rows in (p.get("bars") or {}).items():
                got.setdefault(s, []).extend([[r["t"][:10], r["o"], r["h"], r["l"], r["c"], r["v"]] for r in rows or []])
            token = p.get("next_page_token")
            if not token:
                break
        for s, rows in got.items():
            (CACHE / "daily" / f"{s}.json").write_text(json.dumps(rows))
        print(f"daily {i + len(chunk)}/{len(todo)} · {time.monotonic() - t0:.0f}s", flush=True)



# ------------------------------------------------------------------ the point-in-time universe, stage 2
def fetch_pit(vmin: float = 3e5) -> None:
    """1-minute bars 04:00-12:00 ET for every runner day (a name that traded
    >= +10 % over its previous close, previous close $0.50-25, day volume >= vmin,
    split days removed — data/cache/ross/runner_days.parquet). The day filter
    is only the FETCH superset: any scanner that asks 'up >= 10 % at minute t'
    with cumulative volume <= vmin is fully covered; membership is decided
    point-in-time later, from the bars."""
    from edge_hunt.fetch import et_utc
    a = pd.read_parquet(CACHE / "runner_days.parquet")
    a = a[a["v"] >= vmin]
    out = CACHE / "pit"; out.mkdir(parents=True, exist_ok=True)
    days = sorted(a["day"].unique())
    t0 = time.monotonic()
    for k, d in enumerate(days, 1):
        f = out / f"{d}.json"
        if f.exists():
            continue
        syms = sorted(a.loc[a["day"] == d, "sym"])
        got: dict[str, list] = {}
        for i in range(0, len(syms), 100):
            chunk = syms[i:i + 100]; token = None
            while True:
                p = _get("/v2/stocks/bars", {"symbols": ",".join(chunk), "timeframe": "1Min", "start": et_utc(d, 4, 0),
                                             "end": et_utc(d, 12, 0), "limit": 10000, "adjustment": "raw",
                                             "feed": client()[0].feed, "page_token": token})
                for s, rows in (p.get("bars") or {}).items():
                    got.setdefault(s, []).extend([[r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]] for r in rows or []])
                token = p.get("next_page_token")
                if not token:
                    break
        f.write_text(json.dumps(got))
        if k % 50 == 0:
            print(f"pit {k}/{len(days)} · {time.monotonic() - t0:.0f}s", flush=True)



# ------------------------------------------------------------------ the bot on his symbol-days
_PROXY = None


def _proxy():
    global _PROXY
    if _PROXY is None:
        from edge_hunt.costs import SpreadProxy
        _PROXY = SpreadProxy()
    return _PROXY


def _arrays(b: pd.DataFrame):
    return (b["min"].to_numpy(np.int64), *(np.ascontiguousarray(b[c].to_numpy(float)) for c in ("o", "h", "l", "c", "v")))


def _dv5(m, c, v, k):
    lo = np.searchsorted(m, m[k] - 5, side="left")
    return float((c[lo:k] * v[lo:k]).sum())


def _net(entry, stop, fill, r, orders, stopish, m, c, v, k_in, k_out, pm_in):
    from edge_hunt.costs import cost_r_vec
    px_out = fill + r * (entry - stop)
    hs_in = _proxy().spread(fill, pm_in, _dv5(m, c, v, k_in)) / 2
    hs_out = _proxy().spread(px_out, m[k_out] < minute(9, 30), _dv5(m, c, v, k_out)) / 2
    return r - float(cost_r_vec([entry], [stop], [fill], [px_out], [orders], [stopish], [hs_in], [hs_out])[0])


def bot_on_day(sym: str, day: str, pc: float) -> dict:
    """The desk's detector and gates on one symbol-day, A10 fills (3-minute
    TTL), trail 1 R, flat 11:30, preregistered costs at $20 risk; one position."""
    import backtest_recent as E
    from edge_hunt import engine as G
    b = minutes(sym, day)
    b = b[b["min"] < 720].reset_index(drop=True)
    if len(b) < 20:
        return {"bot": "no bars"}
    base = datetime.fromisoformat(f"{day}T04:00:00").replace(tzinfo=ET)
    rows = [(base + timedelta(minutes=int(r.min)), float(r.o), float(r.h), float(r.l), float(r.c), float(r.v)) for r in b.itertuples()]
    plans = E.plans_for_day(sym, rows, pc, desk_vwap=True, gap_miss=True)
    m, o, h, l, c, v = _arrays(b)
    sp = G.spec(trail=1.0, flat_min=minute(11, 30))
    out, busy = [], -1
    for p in plans:
        t = (p["ts"].hour - 4) * 60 + p["ts"].minute
        k_arm = int(np.searchsorted(m, t, side="right"))
        rec = {"t": t, "entry": p["entry"], "stop": p["stop"], "red": ",".join(p["red"]) or "-", "window": p["window"]}
        if k_arm < len(m):
            fk, fpx, capf = G.stop_limit_fill(m, o, h, l, k_arm, p["entry"], 3, 0.003, 0.01)
            if fk >= 0:
                r, n_o, ke, why, st = G.simulate(m, o, h, l, c, fk, fpx, p["entry"], p["stop"], sp, capf == 0)
                rec.update({"fill_min": int(m[fk]), "exit_min": int(m[ke]), "gross": r,
                            "net": _net(p["entry"], p["stop"], fpx, r, n_o, st, m, c, v, fk, ke, m[fk] < minute(9, 30))})
        out.append(rec)
    green = [x for x in out if x["red"] == "-" and "net" in x]
    taken = []
    for x in sorted(green, key=lambda x: x["fill_min"]):
        if x["fill_min"] > busy:
            taken.append(x); busy = x["exit_min"]
    return {"bot": "ok", "plans": out, "n_plans": len(out), "n_green_filled": len(green),
            "bot_trades": len(taken), "bot_net": float(sum(x["net"] for x in taken)) if taken else 0.0}


def his_entry_mechanical(sym: str, day: str, t: int, e0: float, stated_stop: float | None, draws: int = 20) -> dict:
    """HIS entry minute and price, managed by the bot under three stops —
    his stated stop (when he gave one), the low of the bar before entry − 1c
    (point-in-time structure), and a fixed 3 % — and two exits (trail 1 R,
    fixed 2 R), flat 11:30, preregistered costs at $20 risk. Beside each,
    random market entries in the 30 minutes around his entry on the same
    symbol-day, same stop %, same exit (the timing control)."""
    from edge_hunt import engine as G
    b = minutes(sym, day)
    b = b[b["min"] < 720].reset_index(drop=True)
    m, o, h, l, c, v = _arrays(b)
    k = int(np.searchsorted(m, t, side="left"))
    if k >= len(m) or k < 1:
        return {}
    stops = {"bar": float(l[k - 1]) - 0.01, "pct3": e0 * 0.97}
    if stated_stop and 0 < stated_stop < e0:
        stops["stated"] = stated_stop
    out = {}
    seed = int(hashlib.md5(f"{sym}{day}{t}".encode()).hexdigest()[:7], 16)
    for sname, stop in stops.items():
        if not (0 < stop < e0):
            continue
        out[f"stop_{sname}_pct"] = (e0 - stop) / e0 * 100
        for name, spc in (("trail1", G.spec(trail=1.0, flat_min=minute(11, 30))), ("fixed2", G.spec(target=2.0, flat_min=minute(11, 30)))):
            r, n_o, ke, why, st = G.simulate(m, o, h, l, c, k, e0, e0, stop, spc, True)
            out[f"m_{sname}_{name}_gross"] = r
            out[f"m_{sname}_{name}_net"] = _net(e0, stop, e0, r, n_o, st, m, c, v, k, ke, m[k] < minute(9, 30))
            rr, oo, ss, ff, stp, kk, kx = G.random_entries(m, o, h, l, c, t - 15, t + 16, (e0 - stop) / e0, spc, draws, seed)
            ok = np.flatnonzero(~np.isnan(rr))
            if len(ok):
                out[f"r_{sname}_{name}_gross"] = float(np.mean(rr[ok]))
                out[f"r_{sname}_{name}_net"] = float(np.mean([_net(ff[j], stp[j], ff[j], rr[j], oo[j], ss[j], m, c, v, kk[j], kx[j],
                                                                  m[kk[j]] < minute(9, 30)) for j in ok]))
    return out

if __name__ == "__main__":
    raise SystemExit(main())
