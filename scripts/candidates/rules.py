"""The candidates' entries, as `research/strategy-candidates/PREREGISTRATION.md` §5.

Each generator reads one `SymbolDay` and returns the entries it would have taken:

    Entry(k0, fill, entry, stop, high_ok, sig_k)

`k0` is the fill bar, `entry` the planned price R is measured from (the trigger of a
stop-limit, the fill of a market order), `sig_k` the bar whose close decided it. Nothing
after `sig_k` is read to decide; `tests/test_candidates.py` truncates the bars after the
signal and checks that the same entry comes out.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta

from candidates.data import ET, RTH, SymbolDay, minute

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


@dataclass(frozen=True)
class Entry:
    k0: int
    fill: float
    entry: float
    stop: float
    high_ok: bool
    sig_k: int


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
}
# research/strategy-candidates/PREREGISTRATION.md §6: the families allowed to open a holdout
OPENABLE = ("S1", "S2", "L1")


def signal_key(fam: str, cfg: dict):
    return {"S1": lambda c: c["A"], "S2": lambda c: (c["G"], c["stop"]), "L1": lambda c: c["G"],
            "L3": lambda c: "L3"}[fam](cfg)


def entries(fam: str, sd: SymbolDay, key) -> list[tuple[Entry, str]]:
    if fam == "S1":
        e = s1(sd, key)
    elif fam == "S2":
        e = s2(sd, *key)
    elif fam == "L1":
        e = l1(sd, key)
    else:
        return l3(sd)
    return [(e, "regular")] if e is not None else []


def random_window(fam: str, window: str) -> tuple[int, int]:
    """[w0, w1) of the bars whose open the random baseline may buy or sell."""
    if fam == "S1":
        return minute(10, 1), minute(15, 1)
    if fam == "S2":
        return minute(9, 35), minute(10, 31)
    if fam == "L1":
        return minute(9, 31), minute(11, 21)
    return (minute(7, 1), RTH) if window == "pre-market" else (RTH, minute(11, 21))


def label(fam: str, cfg: dict) -> str:
    if fam == "S1":
        return f"A{cfg['A']}·{cfg['exit']}"
    if fam == "S2":
        return f"G{round(cfg['G'] * 100)}·{cfg['stop']}·{cfg['exit']}"
    if fam == "L1":
        return f"G{round(cfg['G'] * 100)}·{cfg['exit']}"
    return "live·3%·newlow·1loss"
