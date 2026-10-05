"""Step 5: summary.txt from ledger.json (written by analyze.py)."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
L = json.loads((HERE / "ledger.json").read_text())
out = []
pr = lambda s="": out.append(s)  # noqa: E731


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0"


def med(v):
    v = [x for x in v if x is not None]
    return f"{np.median(v):+.1f}" if v else "n/a"


def mean_pct(v):
    v = [x for x in v if x is not None]
    return f"{100 * np.mean(v):.0f}%" if v else "n/a"


def rstats(v):
    v = np.array([x for x in v if x is not None], dtype=float)
    if not len(v):
        return "n 0"
    return (f"n {len(v)} · mean {v.mean():+.2f} R · median {np.median(v):+.2f} R · total {v.sum():+.1f} R · "
            f"win {100 * np.mean(v > 0):.0f}%")


def split(loc):
    return [("all", loc), ("wins", [x for x in loc if x["outcome"] == "win"]),
            ("losses", [x for x in loc if x["outcome"] == "loss"]),
            ("other", [x for x in loc if x["outcome"] not in ("win", "loss")])]


def context(loc):
    pr("CONTEXT AT HIS ENTRY (point-in-time: VWAP from 04:00, high of day through the minute before his)")
    pr("  hod% = distance under the prior high of day (negative = above it, i.e. a new high)")
    for name, g in split(loc):
        if not g:
            continue
        pm = sum(1 for x in g if x["session"] == "pre-market")
        av = sum(1 for x in g if x["above_vwap"])
        band = sum(1 for x in g if 2.0 <= x["ref_px"] <= 20.0)
        nh = sum(1 for x in g if x.get("new_high_minute"))
        pr(f"  {name:<7} n {len(g):>3} · pre-market {pct(pm, len(g))} · above VWAP {pct(av, len(g))} · "
           f"$2-20 {pct(band, len(g))} · his minute made a new high of day {pct(nh, len(g))}")
        pr(f"          medians: gain vs prev close {med([x.get('gain_pct') for x in g])}% · hod% {med([x['dist_hod_pct'] for x in g])} · "
           f"minutes since first +10% print {med([x.get('min_since_10pct') for x in g])}")


def plan_block(loc):
    pr("OUR 1-MINUTE PLAN (rules_audit.plans_for_symbol_day; armed = trigger bar start in [his minute - 5, his minute];"
       " passes = RA.passes(p, RA.BASE))")
    for name, g in split(loc):
        if not g:
            continue
        a = [x for x in g if x.get("plan_armed")]
        ok = [x for x in g if x.get("plan_pass")]
        pr(f"  {name:<7} armed nearby {pct(len(a), len(g))} (chance {mean_pct([x.get('plan_rate_any') for x in g])}) · "
           f"passed every gate {pct(len(ok), len(g))} (chance {mean_pct([x.get('plan_rate_pass') for x in g])}, "
           f"new-high-matched {mean_pct([x.get('plan_rate_pass_matched') for x in g])})")
        if ok:
            filled = [x for x in ok if x.get("plan_filled")]
            pr(f"          passing plans, mode C 'base' gross R: {rstats([x['plan_R_C'] for x in filled])} · unfilled {len(ok) - len(filled)}")
    reds = Counter()
    for x in loc:
        if x.get("plan_armed") and not x.get("plan_pass"):
            why = [w for w in (x.get("plan_red") or "").split("|") if w]
            if x.get("plan_fade", 0) > 25:
                why.append("fade>25%")
            if x.get("plan_stop_pct", 9) < 2:
                why.append("stop<2%")
            if x.get("plan_spread_ratio", 99) < 4:
                why.append("stop<4x spread")
            if not ("07:00" <= x["plan_t"] < "11:20"):
                why.append("time")
            reds.update(why or ["other"])
    pr("  why the armed plan failed (a plan can fail several): " + "; ".join(f"{k} {v}" for k, v in reds.most_common()))


def s_block(loc):
    pr("GREEN-RUN S (green_run gates + runup_micro 10-s pause, 07:00-11:30; near = a fire in [his minute - 3 min, his minute + 1 min])")
    sw = [x for x in loc if x.get("s_status") == "ok"]
    other = Counter(x.get("s_status") for x in loc if x.get("s_status") != "ok")
    pr(f"  rows with an S window: {len(sw)} of {len(loc)}" + (" (no window: " + "; ".join(f"{k} {v}" for k, v in other.items()) + ")" if other else ""))
    for name, g in split(sw):
        if not g:
            continue
        near = [x for x in g if x["s_near"]]
        pr(f"  {name:<7} n {len(g):>3} · S fired near his entry {pct(len(near), len(g))} · chance: any 4-min window "
           f"{mean_pct([x.get('s_p_chance') for x in g])}, minutes matched on new-high {mean_pct([x.get('s_p_chance_matched') for x in g])} "
           f"· S fires {np.mean([x['s_fires_per_hr'] for x in g]):.2f}/h in these windows")
        if near:
            pr(f"          S near his entry, gross R: {rstats([x.get('s_R') for x in near])} · unfilled "
               f"{sum(1 for x in near if x.get('s_how') == 'unfilled')} · his outcome on those: "
               + ", ".join(f"{k} {v}" for k, v in Counter(x['outcome'] for x in near).most_common()))
    pr(f"  a 10-s pause near him refused by an S gate: {sum(1 for x in sw if x.get('s_near_raw_only'))} "
       f"({'; '.join(sorted({x['s_near_raw_why'] for x in sw if x.get('s_near_raw_why')}))}) · "
       f"S fired 3-20 min BEFORE his entry: {sum(1 for x in sw if x.get('s_fires_before'))} rows")


def block(title, loc):
    pr()
    pr("=" * 110)
    pr(title)
    pr("=" * 110)
    context(loc)
    pr()
    plan_block(loc)
    pr()
    s_block(loc)


pr("ROSS CAMERON, JUNE-JULY 2026 RECAP TRADES ON THE SIP TAPE vs OUR TWO SETUPS")
pr("rows: the extraction handed to this run (his words; video id + timestamp each); bars and prints: Alpaca SIP")
pr("files: trades.py (rows) · fetch_bars.py · analyze.py · summarize.py · ledger.csv / ledger.json (one line per row)")
main = [x for x in L if not x.get("alt_date")]
pr()
st = Counter(x["status"] for x in main)
pr(f"ROWS {len(main)}: " + " · ".join(f"{k} {v}" for k, v in st.most_common()))
unl = Counter(x["flag"].split(" (")[0] for x in main if x["status"] == "UNLOCATED")
pr("  UNLOCATED: " + "; ".join(f"{k} {v}" for k, v in unl.most_common()))
for x in main:
    if x["status"] in ("TICKER_MISMATCH", "PRICE_NEVER_PRINTED") or (x["status"] == "UNLOCATED" and "no SIP bars" in x["flag"]):
        pr(f"    {x['date']} {x['raw_ticker']:<10} {x['vid']} [{x['ts']}] {x['status']}: {x['flag']}")
loc = [x for x in main if x["status"] == "LOCATED"]
uniq = {(x["date"], x["sym"], x["entry_min"]) for x in loc}
pr()
pr(f"LOCATED {len(loc)} rows = {len(uniq)} distinct (day, ticker, minute) moments (one move is often told twice: big + small account, or two videos)")
pr("  method: " + "; ".join(f"{k} {v}" for k, v in Counter(x["loc_method"] for x in loc).most_common()))
tiers = Counter(x.get("tier") for x in loc)
pr(f"  tiers: A stated clock time {tiers['A']} · B price visited once, inside <= 5 min {tiers['B']} · "
   f"C ambiguous (price visited again >10 min later, or held in range > 5 min) {tiers['C']}")
pr("  his outcome, located rows: " + "; ".join(f"{k} {v}" for k, v in Counter(x["outcome"] for x in loc).most_common()))
pr("  his outcome, all rows:     " + "; ".join(f"{k} {v}" for k, v in Counter(x["outcome"] for x in main).most_common()))
oob = [x for x in loc if not 2.0 <= x["ref_px"] <= 20.0]
pr(f"  outside the $2-20 band both setups require: {len(oob)} rows (" + ", ".join(f"{x['sym']} {x['ref_px']}" for x in oob) + ")")
pr("  CAVEATS: (1) recap videos: wins come with prices and clock times, losses are often aggregated ('a couple"
   " losses', 'gave back 11,000') without either, so located rows over-represent wins. (2) The task's price rule takes the"
   " FIRST minute holding the price; for a stock rising all morning that is by construction a new-high minute, which"
   " inflates 'above VWAP', 'new high' and S's chance of firing (S needs a new 1-min high). The new-high-matched chance"
   " corrects the S comparison; tier A (clock time) is the unbiased read of context.")

block("ALL LOCATED ROWS (task rule: stated time, else first minute 04:00-12:00 holding the stated price)", loc)
rel = [x for x in loc if x.get("tier") in ("A", "B")]
block("RELIABLE LOCATIONS ONLY (tiers A + B)", rel)
block("CLOCK-TIME LOCATIONS ONLY (tier A: the context read without the price-rule bias)", [x for x in loc if x.get("tier") == "A"])

pr()
pr("=" * 110)
pr("DISTINCT ENTRY MOMENTS (first row of each day/ticker/minute kept)")
seen, U = set(), []
for x in loc:
    k = (x["date"], x["sym"], x["entry_min"])
    if k not in seen:
        seen.add(k); U.append(x)
uw = [x for x in U if x.get("s_status") == "ok"]
pr(f"  n {len(U)} · 1-min plan armed nearby {pct(sum(1 for x in U if x.get('plan_armed')), len(U))} · passed "
   f"{pct(sum(1 for x in U if x.get('plan_pass')), len(U))} · S near {pct(sum(1 for x in uw if x['s_near']), len(uw))} "
   f"(chance {mean_pct([x.get('s_p_chance') for x in uw])}, matched {mean_pct([x.get('s_p_chance_matched') for x in uw])})")
pr(f"  S near, gross R: {rstats([x.get('s_R') for x in uw if x['s_near']])}")
pr(f"  1-min plan passed + filled, mode C gross R: {rstats([x.get('plan_R_C') for x in U if x.get('plan_pass') and x.get('plan_filled')])}")

pr()
pr("=" * 110)
pr("WARM-UP: bars printed since 04:00 before his minute. green_run.minute_context arms only from bar index 30;"
   " indicators.macd needs 35 closes (else the 1-min plan's MACD gate is red)")
for name, g in split(loc) + [("tier A+B", [x for x in loc if x.get("tier") in ("A", "B")])]:
    if not g or name == "other":
        continue
    b = [x["bars_before"] for x in g if x.get("bars_before") is not None]
    pr(f"  {name:<8} n {len(b):>3} · < 30 bars (S cannot arm) {pct(sum(1 for v in b if v < 30), len(b))} · "
       f"< 35 bars (no MACD) {pct(sum(1 for v in b if v < 35), len(b))} · median bars {np.median(b):.0f}")
mw = [x for x in loc if x.get("plan_armed") and "macd" in (x.get("plan_red") or "")]
pr(f"  armed plans refused on MACD: {len(mw)}, of which inside the 35-bar warm-up: {sum(1 for x in mw if x.get('bars_before', 99) < 35)}")
dfile = HERE / "diag_warmup.json"
if dfile.exists():
    D = json.loads(dfile.read_text())
    pr()
    pr("POST-HOC DIAGNOSTIC S0 (diag_warmup.py: S with the 30-bar warm-up removed, all else equal; chosen after seeing the data, decides nothing)")
    for name, g in (("all located", D), ("tier A+B", [d for d in D if d["tier"] in ("A", "B")]),
                    ("wins", [d for d in D if d["outcome"] == "win"]), ("losses", [d for d in D if d["outcome"] == "loss"])):
        g = [d for d in g if d.get("w_s_status") == "ok"]
        near = [d for d in g if d.get("w_s_near")]
        pr(f"  {name:<12} n {len(g):>3} · S0 near {pct(len(near), len(g))} (chance {mean_pct([d.get('w_s_p_chance') for d in g])}, "
           f"matched {mean_pct([d.get('w_s_p_chance_matched') for d in g])}) · S0 gross R near: {rstats([d.get('w_s_R') for d in near])}")
    sp = [d.get("w_s_stop_pct") for d in D if d.get("w_s_near") and d.get("w_s_stop_pct") is not None]
    pr(f"  S/S0 stop width at the fires near his entries (1-min bar low - 1c): median {np.median(sp):.1f}% of price, max {max(sp):.1f}%")

pr()
pr("SENSITIVITY, NOT COUNTED ABOVE: CA8i4Rc2bUY rows re-dated to 2026-07-23 (their prices never printed on 07-24; both printed 07-23,"
   " the day Ts7C0flv-1g recaps ZCMD and EHGO entries)")
for x in L:
    if x["status"] == "LOCATED_ALT_DATE":
        pr(f"  {x['date']} {x['sym']} {x['entry_min']} tier {x.get('tier')} · his {x['outcome']} at {x['ref_px']} · plan armed "
           f"{x.get('plan_armed')} passed {x.get('plan_pass')} R(C) {x.get('plan_R_C')} · S {x.get('s_status')} near {x.get('s_near')} · {x['flag']}")

pr()
pr("PER LOCATED ROW (t = tier; plan: - none armed, arm = armed but a gate failed, PASS = every gate; S: near / - / n/a)")
pr(f"  {'day':<10} {'sym':<5} {'min':<5} t {'his':<10} {'$px':>6} {'gain%':>6} {'vwap':>5} {'hod%':>6} {'m10':>4} "
   f"{'plan':<5} {'planR':>6} {'S':<5} {'S R':>6} {'p(S)':>5} {'pm(S)':>5}  video [ts]")
for x in loc:
    plan = ("PASS" if x.get("plan_pass") else "arm") if x.get("plan_armed") else "-"
    pR = f"{x['plan_R_C']:+.2f}" if x.get("plan_pass") and x.get("plan_R_C") is not None else ""
    s = ("near" if x.get("s_near") else "-") if x.get("s_status") == "ok" else "n/a"
    sr = f"{x['s_R']:+.2f}" if x.get("s_R") is not None else ("unf" if x.get("s_how") == "unfilled" else "")
    g = x.get("gain_pct")
    m10 = x.get("min_since_10pct")
    pc, pm = x.get("s_p_chance"), x.get("s_p_chance_matched")
    pr(f"  {x['date']:<10} {x['sym']:<5} {x['entry_min']:<5} {x.get('tier')} {x['outcome']:<10} {x['ref_px']:>6.2f} "
       f"{'' if g is None else g:>6} {'above' if x['above_vwap'] else 'below':>5} {x['dist_hod_pct']:>6.1f} {'' if m10 is None else m10:>4} "
       f"{plan:<5} {pR:>6} {s:<5} {sr:>6} {'' if pc is None else pc:>5} {'' if pm is None else pm:>5}  {x['vid']} [{x['ts']}]")
pr()
pr("FIVE INSTRUCTIVE CASES (fields straight from the ledger; S0 from diag_warmup.json)")
D0 = {(d["date"], d["sym"], d["entry_min"]): d for d in json.loads((HERE / "diag_warmup.json").read_text())} if (HERE / "diag_warmup.json").exists() else {}
for vid, ts, why in (("ut9nmRP3ENY", "00:06:42", "the 1-min plan agrees with him"),
                     ("A7acrZyX9VU", "00:04:47", "the gates refuse his best-paid trade"),
                     ("YkEOx0ZWlWc", "00:04:40", "both setups blind in the first 30 bars"),
                     ("hUb-n3kzqjI", "00:02:44", "the same blindness keeps us out of his FOMO loss"),
                     ("vcfpJWEqaTU", "00:09:02", "S fires with him, on a 45 % stop")):
    x = next(r for r in loc if r["vid"] == vid and r["ts"] == ts)
    d = D0.get((x["date"], x["sym"], x["entry_min"]), {})
    pr(f"  {x['date']} {x['sym']} — {why} · {vid} [{ts}] · tier {x['tier']}")
    pr(f"    him: {x['setup']} · px {x['px']} · {x['outcome']} {x['pnl']} · tape minute {x['entry_min']} bar o/h/l/c {x['bar']} · "
       f"{x['bars_before']} bars since first print {x['first_bar']} · gain {x.get('gain_pct')}% · VWAP {x['vwap']} · hod% {x['dist_hod_pct']}")
    if x.get("plan_armed"):
        pr(f"    1-min plan: armed {x['plan_t']} trigger {x['plan_entry']} stop {x['plan_stop']} ({x['plan_stop_pct']}%) · red [{x.get('plan_red')}] · "
           f"fade {x['plan_fade']}% · stop/spread {x['plan_spread_ratio']} · passes {x['plan_pass']} · mode C R {x.get('plan_R_C')}")
    else:
        pr(f"    1-min plan: none armed in the 5 min before (plans that day {x['plans_day']}, passing {x['plans_day_pass']})")
    if x.get("s_near"):
        pr(f"    S: fired {x['s_t']} entry {x['s_entry']} stop {x['s_stop']} ({x['s_stop_pct']}%) · fill {x.get('s_fill')} exit {x.get('s_exit')} "
           f"({x.get('s_how')}) · {x.get('s_R')} R · chance {x['s_p_chance']} / matched {x['s_p_chance_matched']}")
    else:
        pr(f"    S: no fire near · {x.get('s_fires')} fires in {x.get('s_window')} · chance {x.get('s_p_chance')}")
    if d.get("w_s_near") and not x.get("s_near"):
        pr(f"    S0 (warm-up removed, post hoc): fired {d['w_s_t']} entry {d['w_s_entry']} stop {d['w_s_stop']} ({d['w_s_stop_pct']}%) · {d.get('w_s_R')} R")
(HERE / "summary.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
