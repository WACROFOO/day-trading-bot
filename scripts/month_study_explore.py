#!/usr/bin/env python3
"""Month study, read AFTER the preregistered verdict: every greedy step on the holdout,
the best found's trades by name, its concentration. Chooses nothing.

    python3 scripts/month_study_explore.py research/month-study/exploratory.json
"""
import json, sys, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import month_study as M
res = json.loads((ROOT / "research/month-study/results.json").read_text())
uni = M.load_universe(M.DAILY, M.SINCE, M.UNTIL)
client = M.H.alpaca_client()
syms = sorted({s for v in uni.values() for s in v})
from datetime import date, timedelta
d0 = (date.fromisoformat(min(uni)) - timedelta(days=60)).isoformat()
dl = M.fetch_daily(client, syms, d0, max(uni))
info = {"daily": {(d, s): M.prev_and_adv(dl.get(s) or [], d) for d, v in uni.items() for s in v},
        "news": M.fetch_news(client, syms, (date.fromisoformat(min(uni)) - timedelta(days=1)).isoformat(), max(uni)),
        "sec": {}}
rows_by = {}
plans = M.build_plans(client, uni, M.DAILY, "bot", info, rows_by)
sel = [p for p in plans if p["day"] <= M.SEL_END]; hold = [p for p in plans if p["day"] >= M.HOLD_START]
out = {"steps_on_holdout": [], "best_trades": []}
for s in res["greedy"]["steps"]:
    cfg = {k: v for k, v in s["config"].items()}
    h = M.evaluate(hold, cfg, s["exit"])
    out["steps_on_holdout"].append({"label": s["label"], "exit": s["exit"], "sel_n": s["n"], "sel_mean": s["mean"],
                                    "sel_total": s["total"], "hold_n": h["n"], "hold_mean": h["mean"], "hold_total": h["total"]})
    print(f"{s['label']:<44} {s['exit']:<5} sel n {s['n']:>4} {s['mean']:+.3f} ({s['total']:+.1f}) | hold n {h['n']:>3} "
          f"{(h['mean'] if h['mean'] is not None else float('nan')):+.3f} ({h['total']:+.1f})")
best = res["best"]; cfg = best["config"]; ex = best["exit"]
for p in sorted([p for p in plans if p["touched"] and M.passes(p, cfg)], key=lambda p: (p["day"], p["t"])):
    out["best_trades"].append({"day": p["day"], "t": p["t"], "sym": p["sym"], "entry": p["entry"], "stop": p["stop"],
                               "stop_pct": p["stop_pct"], "gross": p[ex], "net": p[ex + "_net"], "why": p[ex + "_why"],
                               "set": "selection" if p["day"] <= M.SEL_END else "holdout"})
by_sym = {}
for t in out["best_trades"]:
    by_sym.setdefault(t["sym"], []).append(t["net"])
print("\nbest found, trades by symbol (net R):")
for s, v in sorted(by_sym.items(), key=lambda kv: -sum(kv[1])):
    print(f"  {s:<6} n {len(v):>2}  total {sum(v):+6.2f}")
nets = [t["net"] for t in out["best_trades"] if t["set"] == "selection"]
top = sorted(nets, reverse=True)
print("\nselection: total", round(sum(nets), 2), "· without its best trade", round(sum(top[1:]), 2),
      "· without its best two", round(sum(top[2:]), 2))
out["concentration"] = {"total": round(sum(nets), 2), "without_best": round(sum(top[1:]), 2), "without_best2": round(sum(top[2:]), 2)}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=str))
