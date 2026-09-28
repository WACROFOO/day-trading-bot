#!/usr/bin/env python3
"""The decomposition of research/ross-trades/: his trades against the bot's,
factor by factor. Reads ledger_dated.csv + rebuild.csv (+ selection.csv when
the point-in-time universe is built) and prints every table the report uses.

    python3 scripts/edge_hunt/ross_analysis.py > research/ross-trades/results/analysis.txt
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from edge_hunt.protocol import day_bootstrap  # noqa: E402

OUT = ROOT / "research" / "ross-trades"


def load() -> pd.DataFrame:
    led = pd.read_csv(OUT / "ledger_dated.csv", dtype=str, keep_default_na=False)
    rb = pd.read_csv(OUT / "rebuild.csv")
    d = led.merge(rb, on="row_id", how="left")
    for c in ("pnl_usd",):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["own"] = (d["trader"].str.lower().str.contains("ross")) & (d["kind"].isin(["own-trades", "mixed"]))
    d["has_price"] = d["entries"].str.contains('"price": ')
    sel = OUT / "selection.csv"
    if sel.exists():
        d = d.merge(pd.read_csv(sel), on="row_id", how="left")
    return d


def ci(x, days) -> str:
    x = np.asarray(x, float); ok = ~np.isnan(x)
    if ok.sum() < 5:
        return ""
    b = day_bootstrap(np.asarray(days)[ok], x[ok], 5000)
    return f"[{np.quantile(b, 0.025):+.3f}, {np.quantile(b, 0.975):+.3f}]"


def main() -> int:
    d = load()
    pd.set_option("display.width", 200)
    print("1. THE LEDGER")
    print(f"  rows {len(d)} · his own {int(d.own.sum())} · by register {d[d.own].register.value_counts().to_dict()}")
    o = d[d.own]
    n_dated = int(o.session_date.str.match(r"\d{4}").sum())
    print(f"  with a stated entry price {int(o.has_price.sum())} · dated {n_dated} "
          f"(text {int((o.date_source == 'text').sum())}, tape {int(o.date_source.str.startswith('tape').sum())}) · "
          f"rebuilt on the tape {int((o.tape == 'ok').sum())} · stated price NEVER printed {int((o.tape == 'PRICE NEVER PRINTED').sum())} · "
          f"recounted from another day {int((o.recounted_from_other_day == 'True').sum())}")
    print(f"  outcome as he states it: {o.outcome.value_counts().to_dict()}")
    print(f"  by register × outcome:\n{pd.crosstab(o.register, o.outcome).to_string()}")

    print("\n2. HIS RESULTS, AS STATED ($)")
    p = o.dropna(subset=["pnl_usd"])
    w, l_ = p[p.pnl_usd > 0], p[p.pnl_usd < 0]
    print(f"  trades with a $ P&L {len(p)} · win rate {len(w) / max(len(w) + len(l_), 1):.0%} · avg win ${w.pnl_usd.mean():,.0f} · "
          f"avg loss ${-l_.pnl_usd.mean():,.0f} · win/loss {w.pnl_usd.mean() / -l_.pnl_usd.mean():.2f} · total ${p.pnl_usd.sum():,.0f}")
    for reg, g in p.groupby("register"):
        ww, ll = g[g.pnl_usd > 0], g[g.pnl_usd < 0]
        if len(ww) and len(ll):
            print(f"  {reg:<12} n {len(g):>4} win {len(ww) / (len(ww) + len(ll)):.0%} · win/loss {ww.pnl_usd.mean() / -ll.pnl_usd.mean():.2f} · total ${g.pnl_usd.sum():,.0f}")
    srt = p.pnl_usd.sort_values(ascending=False)
    top = srt.head(max(1, len(srt) // 10)).sum()
    print(f"  concentration: the top 10 % of trades make ${top:,.0f} of ${srt.sum():,.0f} "
          f"({top / srt.sum():.0%} of the net); without them the rest net ${srt.sum() - top:,.0f}")

    r = o[o.tape == "ok"].copy()
    print(f"\n3. WHERE HIS ENTRIES SIT (rebuilt on the tape, n {len(r)})")
    for c, lab in (("gain_at_entry", "gain over previous close"), ("vs_vwap", "above VWAP"),
                   ("vs_hod_before", "vs high of day before the entry"), ("vs_pm_high", "vs pre-market high"),
                   ("min_since_first10", "minutes since first +10 %"), ("range1m_med30", "1-min range, median of 30 bars")):
        x = pd.to_numeric(r[c], errors="coerce").dropna()
        if len(x):
            print(f"  {lab:<36} median {x.median():+.3f} · IQR {x.quantile(.25):+.3f} .. {x.quantile(.75):+.3f} (n {len(x)})")
    em = pd.to_numeric(r.entry_min, errors="coerce")
    print(f"  breakout (entry >= high of day so far) {r.breakout.astype(str).eq('True').mean():.0%} · "
          f"pre-market {(em < 330).mean():.0%} · 07:00-08:00 {((em >= 180) & (em < 240)).mean():.0%} · "
          f"09:30-10:30 {((em >= 330) & (em < 390)).mean():.0%} · after 10:30 {(em >= 390).mean():.0%}")
    ep = pd.to_numeric(r.entry_price, errors="coerce")
    print(f"  price: under $2 {(ep < 2).mean():.0%} · $2-5 {((ep >= 2) & (ep < 5)).mean():.0%} · $5-10 {((ep >= 5) & (ep < 10)).mean():.0%} · "
          f"$10-20 {((ep >= 10) & (ep < 20)).mean():.0%} · over $20 {(ep >= 20).mean():.0%}")
    print(f"  in the bot's 09:30-gap universe that day: {r.in_universe.astype(str).eq('True').mean():.0%}")
    if "rank_dv" in r:
        for c in ("rank_gain", "rank_dv", "rank_vol5", "n_runners"):
            x = pd.to_numeric(r[c], errors="coerce").dropna()
            if len(x):
                print(f"  point-in-time {c:<10} median {x.median():.0f} · share at rank 1 {(x == 1).mean():.0%} · top 3 {(x <= 3).mean():.0%} (n {len(x)})")

    print("\n4. STOPS")
    st = pd.to_numeric(r.stop_price, errors="coerce")
    stp = (ep - st) / ep * 100
    print(f"  stated stops {int(st.notna().sum())} of {len(r)} · width median {stp.median():.1f} % · in cents median {(ep - st).median():.2f}")
    for s in ("stated", "bar", "pct3"):
        c = f"stop_{s}_pct"
        if c in r:
            x = pd.to_numeric(r[c], errors="coerce").dropna()
            print(f"  {s:<7} stop width median {x.median():.1f} %  (n {len(x)})")

    print("\n5. SIZING AND EXITS")
    hm = pd.to_numeric(r.hold_min, errors="coerce").dropna()
    print(f"  hold minutes median {hm.median():.0f} · IQR {hm.quantile(.25):.0f}-{hm.quantile(.75):.0f} (n {len(hm)})")
    mv = pd.to_numeric(r.move_pct, errors="coerce").dropna()
    print(f"  price move entry -> exits: median {mv.median():+.2%} · mean {mv.mean():+.2%} · positive {(mv > 0).mean():.0%} (n {len(mv)})")
    ax = pd.to_numeric(r.after_exit_max_60m, errors="coerce").dropna()
    an = pd.to_numeric(r.after_exit_min_60m, errors="coerce").dropna()
    print(f"  60 min after his last exit: max above it median {ax.median():+.1%} · min below it median {an.median():+.1%}")
    print(f"  adds/scales: rows with >1 entry {(o.entries.str.count('price_as_said') > 1).mean():.0%} · >1 exit {(o.exits.str.count('price_as_said') > 1).mean():.0%}")

    print("\n6. WALKING AWAY")
    per = o.groupby("path").size()
    print(f"  trades described per file: median {per.median():.0f} · mean {per.mean():.1f}")

    print("\n7. WHAT BARS CANNOT SEE")
    print(f"  entry or exit reason cites Level 2 / tape: {o.level2_or_tape_reason.astype(str).eq('True').mean():.0%} of his trades · "
          f"halt involved {o.halt_involved.astype(str).eq('True').mean():.0%}")
    print(f"  setups named: {o.setup.str.lower().value_counts().head(12).to_dict()}")

    print("\n8. THE BOT ON HIS SYMBOL-DAYS")
    b = r[r.bot_status == "ok"]
    print(f"  a desk plan within 5 min of his entry {b.bot_plan_near_entry.astype(str).eq('True').mean():.0%} · "
          f"and all gates green & filled {b.bot_near_green_filled.astype(str).eq('True').mean():.0%}")
    reds = b.bot_near_red.dropna().astype(str).str.split(";").explode().str.split(",").explode()
    print(f"  gates red near his entry: {reds[reds.ne('') & reds.ne('-') & reds.ne('nan')].value_counts().to_dict()}")
    bd = b.drop_duplicates(["ticker", "session_date"])
    print(f"  bot on his symbol-days (one position): trades {int(pd.to_numeric(bd.bot_trades_day).sum())} · "
          f"net {pd.to_numeric(bd.bot_net_day).sum():+.1f} R over {len(bd)} symbol-days")

    print("\n9. HIS ENTRY, THE BOT'S EXECUTION (net R, preregistered costs at $20 risk)")
    for s in ("stated", "bar", "pct3"):
        for e in ("trail1", "fixed2"):
            c = f"m_{s}_{e}_net"
            if c not in r:
                continue
            x = r[[c, f"r_{s}_{e}_net", f"m_{s}_{e}_gross", "session_date", "register"]].copy()
            x[c] = pd.to_numeric(x[c], errors="coerce"); x[f"r_{s}_{e}_net"] = pd.to_numeric(x[f"r_{s}_{e}_net"], errors="coerce")
            x = x.dropna(subset=[c])
            if len(x) < 3:
                continue
            diff = x[c] - x[f"r_{s}_{e}_net"]
            print(f"  stop {s:<7} exit {e:<7} n {len(x):>4} · his entry {x[c].mean():+.3f} {ci(x[c], x.session_date)} · "
                  f"gross {pd.to_numeric(x[f'm_{s}_{e}_gross']).mean():+.3f} · random same name ±15 min {x[f'r_{s}_{e}_net'].mean():+.3f} · "
                  f"his minus random {diff.mean():+.3f} {ci(diff, x.session_date)}")
    for reg, g in r.groupby("register"):
        c = "m_bar_trail1_net"
        x = pd.to_numeric(g[c], errors="coerce").dropna()
        y = pd.to_numeric(g["r_bar_trail1_net"], errors="coerce").dropna()
        if len(x):
            print(f"  by register {reg:<12} his entry (bar stop, trail 1 R) {x.mean():+.3f} (n {len(x)}) · random same name {y.mean():+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
