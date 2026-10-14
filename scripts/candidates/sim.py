"""Exits, costs and the random-entry baseline for the candidates.

One long manager. A short is managed as a long on mirrored prices (p -> -p: the high
becomes the low), so stops, targets and trails behave the same on both sides; a test
checks the symmetry.

Conventions (`scripts/edge_hunt/engine.py`, research/strategy-candidates/PREREGISTRATION.md §5):
  * R is measured on the planned risk per share, |entry - stop|.
  * The fill bar is the first bar managed. On every bar: an exit decided at the previous
    close fills at this bar's open; flatten at the open once the flat minute is reached;
    the stop in force before the bar is tested first — a bar that opens through it fills
    at its open, and on the fill bar it fills at the stop (the open preceded the entry);
    then the resting limits; then the trail and the new-low stop move for the next bar;
    then a close on the wrong side of the series arms an exit for the next open.
  * The fixed target fills at its price even when a bar opens beyond it (the engine's
    conservative scoring). The VWAP limit fills at the bar's open when the bar opens
    through it, else at its price — so a limit placed on the wrong side of the market
    fills at once, at the open, as a real one would.
  * After a stop-limit fill at its cap (`high_ok` False) the fill bar's high earns nothing.
  * A level target (`res`, `hod`; amendment 2026-10-14) is a resting limit at a price the
    rule fixed at its signal, scored like the fixed target; the caller passes the price.
"""
from __future__ import annotations

import random
import zlib

from candidates.data import RTH, SymbolDay

# exit name -> spec. "level": a resting limit at the series (VWAP of the previous bar) —
# for a short, the buy-to-cover limit at VWAP. "cross": a close on the wrong side of the
# series exits at the next open — for a short, a close back above VWAP.
EXITS = {
    "close": {},
    "fixed2": {"target": 2.0},
    "trail1": {"trail": 1.0},
    "newlow": {"newlow": True},
    "vwap": {"level": True},
    "vwap_reclaim": {"cross": True},
    "res": {"target_px": True},          # the nearest fan resistance above the fill, else 2 R
    "hod": {"target_px": True},          # the high of day at the signal, else 2 R
}
MARKETABLE = {"stop": True, "trail": True, "newlow": True, "cross": True, "flat": True, "end": True,
              "target": False, "level": False}


def manage(m, o, h, l, c, k0, fill, entry, stop, ex, flat_min, high_ok=True, series=None, target_px=None):
    """Manage one long from bar k0 (the fill bar). Returns (R, exit index, reason,
    exit price, MFE R, MAE R). `target_px`: the resting limit of a level target."""
    rps = entry - stop
    n = len(o)
    level = stop
    hi = entry
    best = worst = fill
    prev_low = None
    pending = False
    tgt = (entry + ex["target"] * rps if ex.get("target")
           else target_px if ex.get("target_px") else None)
    trail = ex.get("trail", 0.0)
    newlow = ex.get("newlow", False)
    use_level = bool(ex.get("level")) and series is not None
    use_cross = bool(ex.get("cross")) and series is not None

    def out(px, k, why):
        b = max(best, px)
        w = min(worst, px)
        return (px - fill) / rps, k, why, px, (b - fill) / rps, (w - fill) / rps

    for k in range(k0, n):
        if pending:
            return out(o[k], k, "cross")
        if m[k] >= flat_min:
            return out(o[k], k, "flat")
        stop_now, why = level, ("stop" if level <= stop else "trail")
        if newlow and prev_low is not None and prev_low - 0.01 > stop_now:
            stop_now, why = prev_low - 0.01, "newlow"
        if l[k] <= stop_now:
            px = stop_now if k == k0 else min(stop_now, o[k])
            return out(px, k, why)
        if k == k0 and not high_ok:
            worst = min(worst, l[k])
            prev_low = l[k]
            if use_cross and c[k] < series[k]:
                pending = True
            continue
        if tgt is not None and h[k] >= tgt:
            return out(tgt, k, "target")
        if use_level and k >= 1:
            lv = series[k - 1]
            if h[k] >= lv:
                return out(o[k] if o[k] >= lv else lv, k, "level")
        best = max(best, h[k])
        worst = min(worst, l[k])
        hi = max(hi, h[k])
        if trail:
            level = max(level, hi - trail * rps)
        if use_cross and c[k] < series[k]:
            pending = True
        prev_low = l[k]
    return out(c[n - 1], n - 1, "end")


def _mirror(sd: SymbolDay):
    mr = getattr(sd, "_mirror", None)
    if mr is None:
        mr = ([-x for x in sd.o], [-x for x in sd.l], [-x for x in sd.h], [-x for x in sd.c],
              [-x for x in sd.vwap])
        sd._mirror = mr
    return mr


def run(sd: SymbolDay, side: int, k0: int, fill: float, entry: float, stop: float, exit_name: str,
        flat_min: int, high_ok: bool = True, target_px: float | None = None):
    """One trade on a symbol-day, either side. Returns (R, exit index, reason, exit price,
    MFE R, MAE R) in the trade's own direction."""
    ex = EXITS[exit_name]
    needs = bool(ex.get("level") or ex.get("cross"))
    if ex.get("target_px") and target_px is None:
        raise ValueError(f"exit {exit_name} needs the target price its rule fixed")
    if side > 0:
        return manage(sd.m, sd.o, sd.h, sd.l, sd.c, k0, fill, entry, stop, ex, flat_min, high_ok,
                      sd.vwap if needs else None, target_px)
    mo, mh, ml, mc, mv = _mirror(sd)
    r, k, why, px, mfe, mae = manage(sd.m, mo, mh, ml, mc, k0, -fill, -entry, -stop, ex, flat_min,
                                     high_ok, mv if needs else None,
                                     -target_px if target_px is not None else None)
    return r, k, why, -px, mfe, mae


# ------------------------------------------------------------------ costs
LIVE_RISK, LIVE_NOTIONAL = 40.0, 2000.0          # backtest_recent "live": the owner's sizing


def live_shares(entry: float, rps: float) -> int:
    return max(1, min(int(LIVE_RISK // rps), int(LIVE_NOTIONAL // entry))) if rps > 0 else 0


class Costs:
    """`backtest_recent.cost_r` model "live", split into its parts, either side:
    IBKR fixed commission on both orders (at the entry price), half the proxy spread
    plus one cent on every marketable side (the entry always; the exit unless a resting
    limit), and for shorts a borrow charge in % of the entry price a round trip."""

    def __init__(self):
        from edge_hunt.costs import SpreadProxy
        self.proxy = SpreadProxy()

    def parts(self, entry: float, rps: float, marketable_exit: bool, pm: bool, dv5: float,
              borrow_pct: float = 0.0) -> tuple[float, float, float]:
        """(commission, spread + slippage, borrow) in R."""
        q = live_shares(entry, rps)
        if q <= 0:
            return float("nan"), float("nan"), float("nan")
        half = self.proxy.spread(entry, pm, dv5) / 2
        comm = 2 * min(max(1.0, 0.005 * q), max(1.0, 0.01 * q * entry))
        fric = q * (half + 0.01) * (2 if marketable_exit else 1)
        borrow = q * entry * borrow_pct / 100.0
        d = q * rps
        return comm / d, fric / d, borrow / d


# ------------------------------------------------------------------ the random-entry baseline
def seed_of(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def random_baseline(sd: SymbolDay, side: int, w0: int, w1: int, stop_frac: float, exit_name: str,
                    flat_min: int, costs: Costs, draws: int = 20, seed: int = 0,
                    target_r: float | None = None) -> float | None:
    """Mean net R of `draws` market entries at the open of random bars of this symbol-day
    stamped in [w0, w1), same side, same stop distance (a fraction of the entry), same exit,
    same costs; a level target at the trade's own distance in R (`target_r`). Deterministic
    in `seed`. None when the window holds no bar."""
    idx = [k for k, mm in enumerate(sd.m) if w0 <= mm < w1]
    if not idx or stop_frac <= 0:
        return None
    rnd = random.Random(seed)
    tot, n = 0.0, 0
    for _ in range(draws):
        k = idx[rnd.randrange(len(idx))]
        entry = sd.o[k]
        rps = entry * stop_frac
        stop = entry - rps if side > 0 else entry + rps
        tp = None if target_r is None else entry + side * target_r * rps
        r, ke, why, px, mfe, mae = run(sd, side, k, entry, entry, stop, exit_name, flat_min, target_px=tp)
        cm, sp, _ = costs.parts(entry, rps, MARKETABLE[why], sd.m[k] < RTH, sd.dv5_before(k))
        tot += r - cm - sp
        n += 1
    return tot / n if n else None
