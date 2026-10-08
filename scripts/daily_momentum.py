#!/usr/bin/env python3
"""F9 — daily momentum on liquid stocks (addendum 2026-10-08).

New 52-week closing high in an uptrend, bought at the next open, chandelier exit
3 x ATR(20) under the highest close, at most 10 positions, costs per side.

    python3 scripts/daily_momentum.py fetch     # Alpaca daily bars → data/cache/daily (resumable)
    python3 scripts/daily_momentum.py delisted  # + tickers the asset list dropped (resumable)
    python3 scripts/daily_momentum.py run       # the test and its decision
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

START, END = "2015-01-02", "2026-08-21"
CACHE = ROOT / "data" / "cache" / "daily"
OUT = ROOT / "research" / "paper-exercise" / "reports" / "daily_momentum_output.txt"
TRAIN_END, HOLDOUT = "2023-01-01", "2024-01-01"
MIN_PRICE, MIN_DVOL = 10.0, 20e6
HIGH_N, SMA_FAST, SMA_SLOW, ATR_N, RANK_N = 252, 50, 200, 20, 126
R_ATR, MAX_POS, RISK = 3.0, 10, 40.0
SLIP = 0.0005                      # per side, of price: half spread + auction slippage (Approximation)
RANDOM_K, SEED = 20, 20261008
HISTORY = 260                      # sessions of history before a symbol joins the universe
# funds, ETFs/ETNs and their issuers' brands, leveraged products, warrants, units, rights,
# preferreds and notes — whole words, so United, Bright or an ADR's "Depositary Shares" stay
EXCLUDE = re.compile(r"\b(etfs?|etns?|funds?|proshares|direxion|ishares|spdr|grayscale|sprott|leveraged|[23]x|"
                     r"warrants?|units?|rights?|preferred|notes?|series \d|qqq)\b")


# ------------------------------------------------------------------ fetch
def _client():
    import backtest_history as H
    return H.alpaca_client()


def _get(c, path, params):
    for attempt in range(8):
        try:
            return c._get(c.data_base, path, params)
        except Exception as exc:                          # noqa: BLE001
            if attempt < 7 and ("429" in str(exc) or "Remote" in str(exc) or "timed out" in str(exc).lower()
                                or "Connection" in str(exc)):
                time.sleep(10 * (attempt + 1)); continue
            raise


def symbols(c) -> list[str]:
    assets = []
    for status in ("active", "inactive"):
        assets += c._get(c.trading_base, "/v2/assets", {"status": status, "asset_class": "us_equity"})
    keep = []
    for a in assets:
        s, name = a["symbol"], (a.get("name") or "").lower()
        if not (s.isalpha() and s.isupper() and len(s) <= 5):
            continue
        if a.get("exchange") not in ("NYSE", "NASDAQ", "AMEX", "ARCA", "BATS"):
            continue
        if EXCLUDE.search(name):
            continue
        keep.append(s)
    return sorted(set(keep))


def _days(ts: str) -> int:
    return (date.fromisoformat(ts[:10]) - date(1970, 1, 1)).days


def _fetch_chunks(c, syms, prefix) -> int:
    for n, i in enumerate(range(0, len(syms), 100)):
        f = CACHE / f"{prefix}_{n:04d}.npz"
        if f.exists():
            continue
        chunk, token, rows = syms[i:i + 100], None, defaultdict(list)
        while True:
            p = _get(c, "/v2/stocks/bars", {"symbols": ",".join(chunk), "timeframe": "1Day", "start": START,
                                            "end": END, "limit": 10000, "feed": c.feed, "adjustment": "all",
                                            "page_token": token})
            for s, bs in (p.get("bars") or {}).items():
                rows[s] += bs
            token = p.get("next_page_token")
            if not token:
                break
        arrays = {}
        for s, bs in rows.items():
            bs.sort(key=lambda b: b["t"])
            a = np.array([[_days(b["t"]), b["o"], b["h"], b["l"], b["c"], b["v"]] for b in bs], dtype=np.float64)
            if len(a) < HISTORY:
                continue
            dv = np.convolve(a[:, 4] * a[:, 5], np.ones(SMA_FAST) / SMA_FAST, mode="valid")
            if not ((a[SMA_FAST - 1:, 4] >= MIN_PRICE) & (dv >= MIN_DVOL)).any():
                continue                                   # never in the universe: not kept
            arrays[s] = a
        np.savez_compressed(f, **arrays)
        print(f"  {prefix} {n} · {i + len(chunk)}/{len(syms)} · kept {len(arrays)}", flush=True)
    return 0


def fetch() -> int:
    c = _client()
    CACHE.mkdir(parents=True, exist_ok=True)
    syms = symbols(c)
    print(f"{len(syms)} symbols after the name filter", flush=True)
    _fetch_chunks(c, syms, "chunk")
    spy = _get(c, "/v2/stocks/bars", {"symbols": "SPY", "timeframe": "1Day", "start": START, "end": END,
                                      "limit": 10000, "feed": c.feed, "adjustment": "all"})["bars"]["SPY"]
    np.save(CACHE / "SPY.npy", np.array([[_days(b["t"]), b["o"], b["c"]] for b in spy]))
    return 0


def delisted() -> int:
    """Tickers the asset list no longer carries (addendum 2026-10-08, data note): acquired and
    removed names from Alpaca's corporate actions, and bankrupt names whose ticker moved to OTC
    with a Q suffix. Bars come from the SIP feed under the old ticker."""
    c = _client()
    assets = []
    for status in ("active", "inactive"):
        assets += c._get(c.trading_base, "/v2/assets", {"status": status, "asset_class": "us_equity"})
    names = {a["symbol"]: (a.get("name") or "").lower() for a in assets}
    have = set(symbols(c))
    cand, src = set(), defaultdict(int)
    for y in range(2016, 2027):
        token = None
        while True:
            p = _get(c, "/v1/corporate-actions", {"types": "cash_merger,stock_merger,stock_and_cash_merger,"
                                                  "worthless_removal", "start": f"{y}-01-01",
                                                  "end": min(f"{y}-12-31", END), "limit": 1000, "page_token": token})
            for kind, rows in (p.get("corporate_actions") or {}).items():
                for r in rows:
                    sym = r.get("acquiree_symbol") or r.get("symbol") or ""
                    if sym:
                        cand.add(sym); src[f"{y} {kind}"] += 1
            token = p.get("next_page_token")
            if not token:
                break
    for a in assets:
        s = a["symbol"]
        if a.get("exchange") == "OTC" and s.endswith("Q") and 3 <= len(s) <= 6:
            cand.add(s[:-1]); src["OTC Q ticker"] += 1
    keep = sorted(s for s in cand if s.isalpha() and s.isupper() and len(s) <= 5 and s not in have
                  and not EXCLUDE.search(names.get(s, "")))
    print("sources:", dict(sorted(src.items())), flush=True)
    print(f"{len(cand)} candidates · {len(keep)} not already fetched, name filter passed "
          f"({sum(1 for s in keep if not names.get(s))} with no name on file)", flush=True)
    _fetch_chunks(c, keep, "delisted")
    return 0


# ------------------------------------------------------------------ indicators
def sma(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        c = np.cumsum(np.insert(x, 0, 0.0))
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def prep(a):
    d, o, h, l, c, v = a.T
    pc = np.insert(c[:-1], 0, c[0])
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    hi = np.full(len(c), np.nan)
    hi[HIGH_N - 1:] = np.lib.stride_tricks.sliding_window_view(c, HIGH_N).max(axis=1)
    ret = np.full(len(c), np.nan)
    ret[RANK_N:] = c[RANK_N:] / c[:-RANK_N] - 1
    return {"d": d.astype(int), "o": o, "c": c, "atr": sma(tr, ATR_N), "s50": sma(c, SMA_FAST),
            "s200": sma(c, SMA_SLOW), "dv": sma(c * v, SMA_FAST), "hi": hi, "ret": ret}


def comm(sh, px):
    return min(max(1.0, 0.005 * sh), max(1.0, 0.01 * sh * px))


def trade(s, i, slip=SLIP):
    """Signal at index i (close), entry at i+1's open. Returns dict or None."""
    j = i + 1
    if j >= len(s["c"]) or not np.isfinite(s["atr"][i]) or s["atr"][i] <= 0:
        return None
    R = R_ATR * s["atr"][i]
    entry = s["o"][j]
    sh = max(1, int(RISK // R))
    peak, k, flagged = entry, j, False
    while True:
        peak = max(peak, s["c"][k])
        if s["c"][k] < peak - R:
            if k + 1 < len(s["c"]):
                exit_, xk = s["o"][k + 1], k + 1
            else:
                exit_, xk, flagged = s["c"][k], k, True
            break
        if k + 1 >= len(s["c"]):
            exit_, xk, flagged = s["c"][k], k, True
            break
        k += 1
    cost = comm(sh, entry) + comm(sh, exit_) + slip * sh * (entry + exit_)
    gross = (exit_ - entry) / R
    net = (sh * (exit_ - entry) - cost) / (sh * R)
    return {"entry_d": int(s["d"][j]), "exit_d": int(s["d"][xk]), "gross": gross, "net": net,
            "days": xk - j, "open_at_end": flagged}


def iso(d):
    return date.fromordinal(date(1970, 1, 1).toordinal() + int(d)).isoformat()


def month_lb(trades, key="net", alpha=0.05, draws=20000):
    by = defaultdict(lambda: [0.0, 0])
    for t in trades:
        m = t["day"][:7]
        by[m][0] += t[key]; by[m][1] += 1
    if len(by) < 6:
        return float("nan")
    s = np.array([v[0] for v in by.values()]); n = np.array([v[1] for v in by.values()])
    rng = np.random.default_rng(SEED)
    pick = rng.integers(0, len(s), size=(draws, len(s)))
    return float(np.quantile(s[pick].sum(1) / n[pick].sum(1), alpha))


# ------------------------------------------------------------------ run
def run() -> int:
    lines = []

    def pr(x=""):
        print(x, flush=True); lines.append(x)
    data = {}
    for f in sorted(CACHE.glob("chunk_*.npz")) + sorted(CACHE.glob("delisted_*.npz")):
        z = np.load(f)
        for s in z.files:
            if s not in data:
                data[s] = prep(z[s])
    signals = defaultdict(list)          # signal day -> [(rank, sym, i)]
    universe = defaultdict(list)         # signal day -> [(sym, i)]
    for s, a in data.items():
        ok = (a["c"] >= MIN_PRICE) & (a["dv"] >= MIN_DVOL) & np.isfinite(a["s200"]) & np.isfinite(a["hi"])
        ok[:HISTORY - 1] = False                       # index 259 is the 260th session
        idx = np.nonzero(ok[:-1])[0]
        for i in idx:
            universe[int(a["d"][i])].append((s, int(i)))
            if a["c"][i] >= a["hi"][i] and a["c"][i] > a["s50"][i] > a["s200"][i]:
                signals[int(a["d"][i])].append((float(a["ret"][i]), s, int(i)))
    days = sorted(universe)
    pr(f"F9 · addendum 2026-10-08 · {len(data)} symbols kept · {len(days)} sessions {iso(days[0])} → {iso(days[-1])}")
    pr(f"universe: close ≥ ${MIN_PRICE:g}, 50-day $ volume ≥ ${MIN_DVOL / 1e6:g}M · signal: 252-day closing high, "
       f"close > SMA50 > SMA200 · R = {R_ATR:g} ATR(20) · ≤ {MAX_POS} positions · costs IBKR Fixed + {SLIP:.2%}/side")
    open_pos, trades = {}, []
    for d in days:
        for s in [s for s, t in open_pos.items() if t["exit_d"] <= d]:
            del open_pos[s]
        free = MAX_POS - len(open_pos)
        for rank, s, i in sorted(signals.get(d, []), reverse=True):
            if free <= 0:
                break
            if s in open_pos:
                continue
            t = trade(data[s], i)
            if t is None:
                continue
            t.update(sym=s, day=iso(d), i=i)
            open_pos[s] = t
            trades.append(t)
            free -= 1
    rng = random.Random(SEED)
    for t in trades:
        pool = universe[_days(t["day"])]
        rs = []
        for _ in range(RANDOM_K):
            s, i = rng.choice(pool)
            r = trade(data[s], i)
            if r:
                rs.append(r)
        t["rnd_net"] = float(np.mean([r["net"] for r in rs])) if rs else None
        t["diff"] = t["net"] - t["rnd_net"] if rs else None
        hi_cost = trade(data[t["sym"]], t["i"], slip=0.0015)
        t["net_hi"] = hi_cost["net"] if hi_cost else None

    def block(name, ts):
        if not ts:
            pr(f"  {name:<18} n 0"); return {}
        g = np.mean([t["gross"] for t in ts]); n_ = np.mean([t["net"] for t in ts])
        rnd = np.mean([t["rnd_net"] for t in ts if t["rnd_net"] is not None])
        hi = np.mean([t["net_hi"] for t in ts if t["net_hi"] is not None])
        dif = [dict(day=t["day"], d=t["diff"]) for t in ts if t["diff"] is not None]
        lb, lbd = month_lb(ts), month_lb([dict(day=x["day"], net=x["d"]) for x in dif])
        yrs = len({t["day"][:4] for t in ts})
        pr(f"  {name:<18} n {len(ts):>5} · gross {g:+.3f} · net {n_:+.3f} R (lb {lb:+.3f}) · win "
           f"{np.mean([t['net'] > 0 for t in ts]):.0%} · held {np.median([t['days'] for t in ts]):.0f} d median · "
           f"total {sum(t['net'] for t in ts):+.1f} R ({sum(t['net'] for t in ts) / max(1, yrs):+.1f}/yr)")
        pr(f"  {'':<18} random same day {rnd:+.3f} · trade − random lb {lbd:+.3f} · costs 0.15 %/side {hi:+.3f}")
        return {"n": len(ts), "net": n_, "lb": lb, "lbd": lbd}

    tr = [t for t in trades if t["day"] < TRAIN_END]
    g23 = [t for t in trades if t["day"][:4] == "2023"]
    ho = [t for t in trades if t["day"] >= HOLDOUT]
    pr("")
    s_tr = block("train 2016-2022", tr)
    block("2023", g23)
    s_ho = block("holdout 2024-2026", ho)
    for y in ("2024", "2025", "2026"):
        block(f"  {y}", [t for t in ho if t["day"][:4] == y])
    pr(f"  trades still open at the data's end (closed at the last close): {sum(t['open_at_end'] for t in trades)}")
    last = {s: int(a["d"][-1]) for s, a in data.items()}
    gone = [t for t in trades if last[t["sym"]] < _days("2026-08-01")]
    pr(f"  trades in names whose bars end before 2026-08 (delisted or acquired): {len(gone)}"
       + (f" · net {np.mean([t['net'] for t in gone]):+.3f} R" if gone else "")
       + f" · symbols ending early {sum(1 for v in last.values() if v < _days('2026-08-01'))} of {len(data)}")
    spy = np.load(CACHE / "SPY.npy")

    def spy_ret(a, b):
        m = (spy[:, 0] >= _days(a)) & (spy[:, 0] < _days(b))
        x = spy[m]
        return x[-1, 2] / x[0, 1] - 1 if len(x) else float("nan")
    pr(f"\nSPY buy-and-hold (context): train {spy_ret('2016-01-01', TRAIN_END):+.1%} · 2023 "
       f"{spy_ret('2023-01-01', HOLDOUT):+.1%} · holdout {spy_ret(HOLDOUT, '2026-08-22'):+.1%}")
    pr(f"strategy at $40 a trade on a $2,000 account, ignoring the notional cap: train "
       f"{sum(t['net'] for t in tr) * RISK / 2000:+.1%} · holdout {sum(t['net'] for t in ho) * RISK / 2000:+.1%} (simple, not compounded)")
    yrs_pos = sum(1 for y in ("2024", "2025", "2026") if np.mean([t["net"] for t in ho if t["day"][:4] == y] or [-1]) > 0)
    checks = {"holdout net > 0": s_ho.get("net", -1) > 0, "holdout lb > 0": s_ho.get("lb", -1) > 0,
              "≥ 200 holdout trades": s_ho.get("n", 0) >= 200, "2 of 3 years": yrs_pos >= 2,
              "beats random (lb > 0)": s_ho.get("lbd", -1) > 0, "train net > 0": s_tr.get("net", -1) > 0}
    pr("\nDECISION: " + " · ".join(f"{'✓' if v else '✗'} {k}" for k, v in checks.items()) +
       ("  → PASS: design a paper implementation, preregistered separately" if all(checks.values()) else "  → FAIL"))
    OUT.write_text("\n".join(lines) + "\n")
    (OUT.with_suffix(".json")).write_text(json.dumps({"checks": checks, "train": s_tr, "holdout": s_ho}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit({"fetch": fetch, "delisted": delisted, "run": run}[sys.argv[1]]())
