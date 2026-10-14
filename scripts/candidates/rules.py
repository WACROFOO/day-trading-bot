"""The candidates' entries, as `research/strategy-candidates/PREREGISTRATION.md` §5.

Each generator reads one `SymbolDay` and returns the entries it would have taken:

    Entry(k0, fill, entry, stop, high_ok, sig_k, targets)

`k0` is the fill bar, `entry` the planned price R is measured from (the trigger of a
stop-limit, the fill of a market order), `sig_k` the bar whose close decided it, `targets`
the level-based take-profit prices a rule fixed at its signal ((exit name, price or None),
amendment 2026-10-14). Nothing after `sig_k` is read to decide (the fill bar's open aside);
`tests/test_candidates.py` truncates the bars after the fill and checks that the same entry
comes out.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta

from candidates.data import ET, RTH, SymbolDay, minute
from momentum_platform import levels as LV

UP_MIN = 0.10                       # the real-time condition: up >= 10 % at the signal
SSR_DROP = 0.10                     # Rule 201: a print 10 % under the previous close
RISK_BAND = (0.02, 0.20)            # shorts: the stop 2-20 % above the entry
FLAT_SHORT = minute(15, 55)
FLAT_LONG = minute(11, 30)

S1_WIN = (minute(10, 0), minute(15, 0))
S2_PM_VOL = 2_000_000               # ZfwTJAMLroA [13:21], via knowledge-base/strategies/PARAMETERS.md
S2_SLOTS = tuple(range(minute(9, 30), minute(10, 30), 5))
L1_WIN = (minute(9, 30), minute(11, 20))
L1_MAX_PB, L1_MAX_DEPTH, L1_STOP_X, L1_MIN_STOP = 5, 0.5, 2.0, 0.02
L3_MIN_STOP_PCT = 3.0
S2W_BAND = (0.10, 0.20)             # amendment 2026-10-12b: S2's lead, the stop 10-20 % above
# amendment 2026-10-14, the levels round: L4 trend-line break, L5 support hold, L6 resistance break
LV_WIN = (minute(9, 30), minute(11, 20))     # the signal bar 09:30-11:19, as L1
LV_BAND = (0.02, 0.20)                       # the stop 2-20 % under the signal close
LV_STOP_ATR = 0.5                            # `level`: half an ATR under the level (Pine tolSR)


@dataclass(frozen=True)
class Entry:
    k0: int
    fill: float
    entry: float
    stop: float
    high_ok: bool
    sig_k: int
    targets: tuple = ()


def _risk_ok(px: float, stop: float) -> bool:
    """The short's stop distance, judged at the signal close `px` — the decision cannot
    know the next bar's open it will fill at."""
    risk = stop - px
    return RISK_BAND[0] * px <= risk <= RISK_BAND[1] * px


# ------------------------------------------------------------------ S1 afternoon fade (short)
def s1(sd: SymbolDay, age_min: int) -> Entry | None:
    m, o, h, l, c, vw, pc = sd.m, sd.o, sd.h, sd.l, sd.c, sd.vwap, sd.pc
    n = len(sd)
    hod, hod_m = -1.0, -1
    for k in range(n):
        if h[k] > hod:
            hod, hod_m = h[k], m[k]
        if l[k] <= (1 - SSR_DROP) * pc:
            return None                                  # the short-sale restriction from here on
        if not (S1_WIN[0] <= m[k] < S1_WIN[1]) or k == 0 or k + 1 >= n:
            continue
        if c[k] < (1 + UP_MIN) * pc or m[k] - hod_m < age_min:
            continue
        if not (c[k - 1] >= vw[k - 1] and c[k] < vw[k]):
            continue
        stop = hod + 0.01
        if _risk_ok(c[k], stop):
            if o[k + 1] >= stop:
                continue                                 # opened through the stop: cancelled, keep scanning
            return Entry(k + 1, o[k + 1], o[k + 1], stop, True, k)
    return None


# ------------------------------------------------------------------ S2 crowded-gapper fade (short)
def s2(sd: SymbolDay, gap_min: float, stop_kind: str) -> Entry | None:
    gap = sd.gap()
    if gap is None or gap < gap_min:
        return None
    m, o, h, l, c, vw, pc = sd.m, sd.o, sd.h, sd.l, sd.c, sd.vwap, sd.pc
    n = len(sd)
    k930 = sd.first_at(RTH)
    if sum(sd.v[:k930]) < S2_PM_VOL:
        return None
    floor = (1 - SSR_DROP) * pc
    if any(l[j] <= floor for j in range(k930)):
        return None
    for s in S2_SLOTS:
        a, b = sd.first_at(s), sd.first_at(s + 5)          # the 5-minute bar is bars [a, b)
        if any(l[j] <= floor for j in range(a, b)):
            return None
        if a >= b:
            continue
        o5, c5, h5 = o[a], c[b - 1], max(h[a:b])
        if not (c5 < o5 and c5 > vw[b - 1] and c5 >= (1 + UP_MIN) * pc):
            continue
        if b >= n or m[b] >= FLAT_SHORT:
            return None
        stop = (max(h[:b]) if stop_kind == "hod" else h5) + 0.01
        if _risk_ok(c5, stop):
            if o[b] >= stop:                               # filled at the next bar's open, unless through the stop
                continue
            return Entry(b, o[b], o[b], stop, True, b - 1)
    return None


def s2w(sd: SymbolDay) -> Entry | None:
    """S2's lead (amendment 2026-10-12b): S2 G20·hod's trade, kept only when its stop is
    10-20 % above the 5-minute close; otherwise the symbol-day is skipped — the slice the
    lead was read on, not a new scan."""
    e = s2(sd, 0.20, "hod")
    if e is None:
        return None
    px = sd.c[e.sig_k]
    return e if S2W_BAND[0] * px <= e.stop - px <= S2W_BAND[1] * px else None


# ------------------------------------------------------------------ L1 real-time new-high dip (long)
def l1(sd: SymbolDay, gain_min: float) -> Entry | None:
    m, o, h, l, c, pc = sd.m, sd.o, sd.h, sd.l, sd.c, sd.pc
    n = len(sd)
    hod = -1.0
    st = None                                              # [impulse bar, leg low, pullback low, red seen]
    armed = None                                           # (live minute, trigger, stop, signal bar)
    for k in range(n):
        if armed is not None:
            live, trig, stop, sk = armed
            armed = None
            if m[k] == live and h[k] >= trig:              # A10: stop-limit, cap + max(1c, 0.3 %)
                cap = trig + max(0.01, 0.003 * trig)
                if o[k] > cap:
                    if l[k] <= cap:
                        return Entry(k, cap, trig, stop, False, sk)
                elif o[k] > trig:
                    return Entry(k, o[k], trig, stop, True, sk)
                else:
                    return Entry(k, trig, trig, stop, True, sk)
        if h[k] > hod:
            hod = h[k]
            st = [k, min(l[max(0, k - 14):k + 1]), float("inf"), False] if c[k] >= (1 + gain_min) * pc else None
            continue
        if st is None:
            continue
        if k - st[0] > L1_MAX_PB:
            st = None
            continue
        st[2] = min(st[2], l[k])
        st[3] = st[3] or c[k] < o[k]
        depth, leg = hod - st[2], hod - st[1]
        if depth <= 0 or depth > L1_MAX_DEPTH * leg:
            st = None
            continue
        if not st[3] or not (L1_WIN[0] <= m[k] < L1_WIN[1]) or c[k] < (1 + UP_MIN) * pc or k + 1 >= n:
            continue
        trig = h[k] + 0.01
        if L1_STOP_X * depth < L1_MIN_STOP * trig:
            continue
        armed = (m[k] + 1, trig, trig - L1_STOP_X * depth, k)
    return None


# ------------------------------------------------------------------ L4-L6 the desk's levels (long)
def day_levels(sd: SymbolDay) -> LV.DayLevels:
    """The desk's levels for every bar of the symbol-day (src/momentum_platform/levels.py,
    the port of levels.js), built once."""
    lv = getattr(sd, "_levels", None)
    if lv is None:
        lv = LV.DayLevels(list(zip(sd.m, sd.o, sd.h, sd.l, sd.c, sd.v)))
        sd._levels = lv
    return lv


def levels_signal(sd: SymbolDay, fam: str, k: int) -> float | None:
    """The level bar k's close acts on, or None — amendment 2026-10-14. Levels are the ones
    drawn from bars 0 … k−1; bar k's close decides.
      L4  the intact down-line exists and bar k closes above it: the line's price at bar k
      L5  the fan's nearest support S: bar k's low inside S ± band, its close above S and
          at or above its open (Pine V5's retest touch, V8's two-sided band): S
      L6  the fan's nearest resistance R: bar k closes above R + band: R"""
    lv = day_levels(sd)
    if fam == "L4":
        ln = lv.lines(k, sd.c[k])["down"]
        return ln["now"] if ln is not None and ln["through"] else None
    fan = lv.fan(k, sd.c[k - 1])
    band = fan["band"]
    if fam == "L5":
        if not fan["sup"]:
            return None
        s = fan["sup"][0]["price"]
        ok = s - band <= sd.l[k] <= s + band and sd.c[k] > s and sd.c[k] >= sd.o[k]
        return s if ok else None
    if not fan["res"]:
        return None
    r = fan["res"][0]["price"]
    return r if sd.c[k] > r + band else None


def levels_entry(sd: SymbolDay, fam: str, stop_kind: str) -> Entry | None:
    """L4 / L5 / L6: the first signal bar 09:30-11:19, up >= 10 %, whose stop is 2-20 % under
    its close and whose next bar opens above the stop: a market buy at that open. Targets
    fixed at the signal: `res` the nearest fan resistance above the fill (levels drawn on
    bars 0 … k), `hod` the high of day as of bar k when above the fill; None → 2 R."""
    m, o, h, l, c, pc = sd.m, sd.o, sd.h, sd.l, sd.c, sd.pc
    n = len(sd)
    lv = day_levels(sd)
    hod = float("-inf")
    for k in range(n - 1):
        hod = max(hod, h[k])
        if k == 0 or not (LV_WIN[0] <= m[k] < LV_WIN[1]) or c[k] < (1 + UP_MIN) * pc:
            continue
        a = lv.atr_before(k)
        if a is None or a <= 0:
            continue
        level = levels_signal(sd, fam, k)
        if level is None:
            continue
        stop = (min(l[max(0, k - 4):k + 1]) if stop_kind == "bars5" else level - LV_STOP_ATR * a) - 0.01
        risk = c[k] - stop
        if not (LV_BAND[0] * c[k] <= risk <= LV_BAND[1] * c[k]):
            continue
        if m[k + 1] >= FLAT_LONG or o[k + 1] <= stop:
            continue                                         # past the flat, or opened through the stop
        fill = o[k + 1]
        res = next((x["price"] for x in lv.fan(k + 1, c[k])["res"] if x["price"] > fill), None)
        return Entry(k + 1, fill, fill, stop, True, k, (("res", res), ("hod", hod if hod > fill else None)))
    return None


# ------------------------------------------------------------------ L3 the reference long
def l3(sd: SymbolDay) -> list[tuple[Entry, str]]:
    """The desk's detector plans (`backtest_recent.plans_for_day`: VWAP with pre-market
    volume, A10 fills), all six gates green, up >= 10 % at the plan bar, stop >= 3 %.
    Returns (entry, "pre-market" | "regular") for every filled plan."""
    import backtest_recent as E
    E.PM_START, E.CUTOFF, E.FLAT = dtime(7, 0), dtime(11, 20), dtime(11, 30)   # the live window
    base = datetime.fromisoformat(f"{sd.day}T04:00:00").replace(tzinfo=ET)
    rows = [(base + timedelta(minutes=mm), o, h, l, c, v)
            for mm, o, h, l, c, v in zip(sd.m, sd.o, sd.h, sd.l, sd.c, sd.v)]
    idx = {mm: k for k, mm in enumerate(sd.m)}
    fills = {}

    def hook(rec, ent, fill):
        fills[(rec["t"], rec["entry"], rec["stop"])] = (ent[0][0], fill)

    out = []
    for p in E.plans_for_day(sd.sym, rows, sd.pc, desk_vwap=True, gap_miss=True, hook=hook):
        if p["red"] or not p["touched"] or p["gain"] is None or p["gain"] < UP_MIN:
            continue
        if p["stop_pct"] < L3_MIN_STOP_PCT:
            continue
        t_in, fill = fills[(p["t"], p["entry"], p["stop"])]
        k0 = idx[(t_in.hour - 4) * 60 + t_in.minute]
        sig_k = idx[(p["ts"].hour - 4) * 60 + p["ts"].minute]
        # a fill at the cap came back to it (the plan's entry is rounded to 4 decimals, hence the slack)
        high_ok = abs(fill - E.entry_cap(p["entry"])) > 5e-4
        out.append((Entry(k0, fill, p["entry"], p["stop"], high_ok, sig_k), p["window"]))
    return out


# ------------------------------------------------------------------ the families
@dataclass(frozen=True)
class Family:
    key: str
    name: str
    side: int
    flat: int
    configs: tuple
    reference: bool = False
    lead_of: str = ""               # a lead tested on its parent family's holdout (registered under it)


FAMILIES = {
    "S1": Family("S1", "afternoon fade", -1, FLAT_SHORT,
                 tuple({"A": a, "exit": e} for a in (30, 60) for e in ("close", "fixed2", "vwap_reclaim"))),
    "S2": Family("S2", "crowded-gapper fade", -1, FLAT_SHORT,
                 tuple({"G": g, "stop": s, "exit": e} for g in (0.20, 0.40) for s in ("hod", "bar5")
                       for e in ("vwap", "close"))),
    "L1": Family("L1", "real-time new-high dip", 1, FLAT_LONG,
                 tuple({"G": g, "exit": e} for g in (0.30, 0.50) for e in ("trail1", "fixed2", "newlow"))),
    "L3": Family("L3", "reference: live entry + stop >= 3 % + new-low exit + done after a loss", 1, FLAT_LONG,
                 ({"ref": "live+stop3+newlow+done_after_loss", "exit": "newlow"},), reference=True),
    "S2W": Family("S2W", "S2's lead: G20·hod·close, kept when the stop is 10-20 % above (amendment 2026-10-12b)",
                  -1, FLAT_SHORT, ({"G": 0.20, "stop": "hod", "exit": "close", "band": [0.10, 0.20]},), lead_of="S2"),
}
LEVEL_CONFIGS = tuple({"stop": s, "exit": e} for s in ("bars5", "level") for e in ("fixed2", "trail1", "res", "hod"))
FAMILIES.update({
    "L4": Family("L4", "trend-line break: a close above the desk's down-line", 1, FLAT_LONG, LEVEL_CONFIGS),
    "L5": Family("L5", "support hold: the fan's nearest support touched and held", 1, FLAT_LONG, LEVEL_CONFIGS),
    "L6": Family("L6", "resistance break: a close above the fan's nearest resistance", 1, FLAT_LONG, LEVEL_CONFIGS),
})
LEVEL_FAMILIES = ("L4", "L5", "L6")
LEADS = ("S2W",)                    # run only with --lead, never in the main run
# research/strategy-candidates/PREREGISTRATION.md §6, and amendment 2026-10-14: the families allowed
# to open a holdout, by round. α is corrected over a round's families: round 1's three failed their
# gates and can never open, so the levels round counts its own three.
ROUNDS = (("S1", "S2", "L1"), LEVEL_FAMILIES)
OPENABLE = tuple(f for r in ROUNDS for f in r)


def signal_key(fam: str, cfg: dict):
    if fam in LEVEL_FAMILIES:
        return cfg["stop"]                       # the stop decides which signal is taken (its 2-20 % band)
    return {"S1": lambda c: c["A"], "S2": lambda c: (c["G"], c["stop"]), "L1": lambda c: c["G"],
            "L3": lambda c: "L3", "S2W": lambda c: "S2W"}[fam](cfg)


def entries(fam: str, sd: SymbolDay, key) -> list[tuple[Entry, str]]:
    if fam == "S1":
        e = s1(sd, key)
    elif fam == "S2":
        e = s2(sd, *key)
    elif fam == "L1":
        e = l1(sd, key)
    elif fam == "S2W":
        e = s2w(sd)
    elif fam in LEVEL_FAMILIES:
        e = levels_entry(sd, fam, key)
    else:
        return l3(sd)
    return [(e, "regular")] if e is not None else []


def random_window(fam: str, window: str) -> tuple[int, int]:
    """[w0, w1) of the bars whose open the random baseline may buy or sell."""
    if fam == "S1":
        return minute(10, 1), minute(15, 1)
    if fam in ("S2", "S2W"):
        return minute(9, 35), minute(10, 31)
    if fam == "L1" or fam in LEVEL_FAMILIES:
        return minute(9, 31), minute(11, 21)
    return (minute(7, 1), RTH) if window == "pre-market" else (RTH, minute(11, 21))


def label(fam: str, cfg: dict) -> str:
    if fam == "S1":
        return f"A{cfg['A']}·{cfg['exit']}"
    if fam == "S2":
        return f"G{round(cfg['G'] * 100)}·{cfg['stop']}·{cfg['exit']}"
    if fam == "L1":
        return f"G{round(cfg['G'] * 100)}·{cfg['exit']}"
    if fam == "S2W":
        return "G20·hod·close·stop10-20"
    if fam in LEVEL_FAMILIES:
        return f"{cfg['stop']}·{cfg['exit']}"
    return "live·3%·newlow·1loss"
