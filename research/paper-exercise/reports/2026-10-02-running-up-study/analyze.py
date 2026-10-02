#!/usr/bin/env python3
"""Summarise events.pkl from replay_alerts.py. Prints tables only."""
import pickle
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
P = Path(__file__).resolve().parent / "events.pkl"
d = pickle.loads(P.read_bytes())
ev = d["events"]
TILE = ("running_up", "squeeze_5_in_5", "squeeze_10_in_10")
print(f"days={len(d['days'])} first={d['days'][0]} last={d['days'][-1]} events={len(ev)}")
syms_days = {(e['day'], e['sym']) for e in ev}
print(f"symbol-days with >=1 tile/HOD event: {len(syms_days)}")

for e in ev:
    t = datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).astimezone(ET)
    e["et"] = t.strftime("%H:%M")
    e["win"] = "pre" if e["et"] < "09:30" else ("am" if e["et"] < "11:30" else "late")


def q(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo = int(k); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def outcome(rows, label):
    rows = [r for r in rows if r["nfwd"] >= 30]
    n = len(rows)
    if not n:
        return f"{label:<38} n=0"
    r30 = [r["ret30"] for r in rows]
    mfe = [r["mfe30"] for r in rows]
    mae = [r["mae30"] for r in rows]
    up5 = sum(1 for x in mfe if x >= 5) / n
    dn5 = sum(1 for x in mae if x <= -5) / n
    pos = sum(1 for x in r30 if x > 0) / n
    return (f"{label:<38} n={n:>6}  ret30 med {q(r30,.5):+6.2f}% mean {st.mean(r30):+6.2f}%  "
            f"P(ret30>0) {pos:5.1%}  MFE30 med {q(mfe,.5):5.2f}%  MAE30 med {q(mae,.5):+6.2f}%  "
            f"P(MFE>=5%) {up5:5.1%}  P(MAE<=-5%) {dn5:5.1%}")


print("\n== A. router outcome per scanner (status, detail) ==")
c = Counter((e["scanner"], e["status"], e["detail"]) for e in ev)
for k, v in sorted(c.items(), key=lambda kv: (kv[0][0], -kv[1])):
    print(f"  {k[0]:<18} {k[1]:<10} {k[2]:<40} {v}")

ru = [e for e in ev if e["scanner"] == "running_up"]
ru_cons = [e for e in ru if e["status"] == "suppressed" and e["detail"].startswith("consolidated")]
print(f"\nrunning_up emitted {len(ru)}; delivered {sum(e['status']=='delivered' for e in ru)}; "
      f"consolidated under another scanner {len(ru_cons)} ({len(ru_cons)/max(1,len(ru)):.1%}); "
      f"cooldown {sum(e['detail']=='cooldown' for e in ru)}")
print("  consolidated-under breakdown:", Counter(e["detail"] for e in ru_cons).most_common())
print("  at_hod among delivered:", Counter(e["at_hod"] for e in ru if e["status"] == "delivered"))
print("  at_hod among consolidated:", Counter(e["at_hod"] for e in ru_cons))

# consumed leg: a consolidated running_up with NO delivered running_up on the same name in the next 10 min
idx = defaultdict(list)
for e in ru:
    if e["status"] == "delivered":
        idx[(e["day"], e["sym"])].append(e["ts"])
def later(e, mins=10):
    t0 = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
    for t in idx[(e["day"], e["sym"])]:
        dt = (datetime.fromisoformat(t.replace("Z", "+00:00")) - t0).total_seconds() / 60
        if 0 < dt <= mins:
            return True
    return False
lost = [e for e in ru_cons if not later(e)]
print(f"  consolidated running_up with no Running Up tile row for that name in the next 10 min: {len(lost)} of {len(ru_cons)}")

vis = [e for e in ev if e["scanner"] in TILE and e["status"] == "delivered"]
print(f"\n== B. tile-visible events (delivered running_up / squeeze_*): {len(vis)} ==")
print("  by scanner:", Counter(e["scanner"] for e in vis).most_common())
print("  by window (ET):", Counter(e["win"] for e in vis).most_common())


def bucket_chg(x):
    if x is None: return "?"
    return "<0%" if x < 0 else "0-5%" if x < 5 else "5-10%" if x < 10 else "10-20%" if x < 20 else "20-50%" if x < 50 else "50%+"


def bucket_move(x):
    if x is None: return "?"
    return "3-4%" if x < 4 else "4-5%" if x < 5 else "5-7.5%" if x < 7.5 else "7.5-10%" if x < 10 else "10%+"


print("  day change (from prev close) at alert:")
for k, v in sorted(Counter(bucket_chg(e["chg"]) for e in vis).items()):
    print(f"    {k:<8} {v:>6}  {v/len(vis):5.1%}")
print("  cascade verdict at alert (float unknown, no news — the desk's common case):")
for k, v in Counter((e["verdict"], e["killed_by"]) for e in vis).most_common():
    print(f"    {str(k):<30} {v:>6}  {v/len(vis):5.1%}")
print("  pillar gate value:")
for k, v in Counter((e["pillar_value"] or "-").split(" —")[0] for e in vis).most_common():
    print(f"    {k:<8} {v:>6}")
gain_ok = [e for e in vis if (e["chg"] or 0) >= 10]
rvol_ok = [e for e in vis if (e["rvol"] or 0) >= 5]
both = [e for e in vis if (e["chg"] or 0) >= 10 and (e["rvol"] or 0) >= 5]
either = [e for e in vis if (e["chg"] or 0) >= 10 or (e["rvol"] or 0) >= 5]
price_ok = [e for e in vis if 2 <= e["last"] <= 20]
print(f"  gain>=10%: {len(gain_ok)} ({len(gain_ok)/len(vis):.1%})   RVOL(daily)>=5: {len(rvol_ok)} ({len(rvol_ok)/len(vis):.1%})   "
      f"both: {len(both)} ({len(both)/len(vis):.1%})   either: {len(either)} ({len(either)/len(vis):.1%})   price $2-20: {len(price_ok)/len(vis):.1%}")
print("  -> pillars gate (need 4/5) would PASS if float AND catalyst both passed: 'either' share; "
      "if only float passed: 'both' share; if neither: never.")

print("\n== C. forward 30-min outcome from the alert bar's close (gross, no costs, no entry rule) ==")
print(outcome(vis, "all tile-visible"))
for name in TILE:
    print(outcome([e for e in vis if e["scanner"] == name], f"  scanner {name}"))
print(outcome(ru_cons, "running_up consolidated (NOT in tile)"))
print("  by 10-min (or 5-min) move at alert:")
for b in ("3-4%", "4-5%", "5-7.5%", "7.5-10%", "10%+"):
    print(outcome([e for e in vis if bucket_move(e["move"]) == b], f"    move {b}"))
print("  by day change at alert:")
for b in ("<0%", "0-5%", "5-10%", "10-20%", "20-50%", "50%+"):
    print(outcome([e for e in vis if bucket_chg(e["chg"]) == b], f"    chg {b}"))
print("  by window:")
for b in ("pre", "am", "late"):
    print(outcome([e for e in vis if e["win"] == b], f"    window {b}"))
print("  by cascade gate state at alert:")
for b in ("pillars", "rising", "price"):
    print(outcome([e for e in vis if e["killed_by"] == b], f"    killed_by {b}"))
print(outcome([e for e in vis if e["killed_by"] is None], "    not killed"))
print("  by pillar inputs the desk can measure:")
print(outcome(both, "    gain>=10 & RVOL>=5"))
G=lambda e:(e["chg"] or 0)>=10
R=lambda e:(e["rvol"] or 0)>=5
print(outcome([e for e in vis if G(e)!=R(e)], "    exactly one of gain/RVOL"))
print(outcome([e for e in vis if not G(e) and not R(e)], "    neither gain>=10 nor RVOL>=5"))
print(outcome([e for e in vis if G(e) and not R(e)], "    gain>=10 only"))
print(outcome([e for e in vis if R(e) and not G(e)], "    RVOL>=5 only"))
print("  by Layer 2 at alert:")
l2 = lambda e: bool(e["above_vwap"]) and bool(e["above_ema9"]) and bool(e["macd_ok"])
print(outcome([e for e in vis if l2(e)], "    VWAP & EMA9 & MACD all true"))
print(outcome([e for e in vis if not l2(e)], "    any Layer 2 false/unknown"))
print("  running_up only, by at_hod:")
print(outcome([e for e in vis if e["scanner"] == "running_up" and e["at_hod"]], "    at HOD (branch _hod)"))
print(outcome([e for e in vis if e["scanner"] == "running_up" and not e["at_hod"]], "    below HOD"))


def best_case(e):
    """The cascade verdict IF float were verified <20M and a catalyst dated today
    existed (both unknowable from this history). Mirrors cascade.py order."""
    if not (2 <= e["last"] <= 20):
        return "REJECT price"
    gain = (e["chg"] or 0) >= 10
    rv = (e["rvol"] or 0) >= 5
    if 3 + gain + rv < 4:
        return "REJECT pillars"
    if e["hod"] and (e["hod"] - e["last"]) / e["hod"] * 100 > 25:
        return "REJECT rising"
    l2 = (e["above_vwap"], e["above_ema9"], e["macd_ok"])
    if any(x is False for x in l2):
        return "WAIT"
    if any(x is None for x in l2):
        return "WATCH"
    return "REVIEW"


print("\n== D. best-case cascade verdict (float verified <20M AND catalyst today assumed) ==")
for k, v in Counter(best_case(e) for e in vis).most_common():
    print(f"  {k:<16} {v:>6}  {v/len(vis):5.1%}")
for k in ("REVIEW", "WAIT", "WATCH", "REJECT pillars", "REJECT rising", "REJECT price"):
    print(outcome([e for e in vis if best_case(e) == k], f"  best-case {k}"))

print("\n== E. noise: tile rows per symbol-day ==")
per = Counter((e["day"], e["sym"]) for e in vis)
vals = sorted(per.values())
print(f"  symbol-days with a tile row: {len(per)}; rows per symbol-day median {q(vals,.5)} p90 {q(vals,.9)} max {vals[-1]}")
print(f"  rows per session-day: median {q(sorted(Counter(e['day'] for e in vis).values()),.5)}")
first = {}
for e in sorted(vis, key=lambda e: e["ts"]):
    first.setdefault((e["day"], e["sym"]), e)
fl = list(first.values())
print(outcome(fl, "  first tile row of the symbol-day"))
print(outcome([e for e in vis if first[(e['day'], e['sym'])] is not e], "  later tile rows"))
