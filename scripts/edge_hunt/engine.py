"""Exit simulation, stop-limit entries and the random-entry baseline, on the
compact store's arrays. numba when installed, plain Python otherwise — the
same code either way, so results do not depend on it.

Conventions (identical to `scripts/ablation_history.py`, the ten-year study):
  * R is measured on the planned risk per share, trigger − stop.
  * The fill bar is the first bar managed. On every bar: flatten at the open
    once the flat minute is reached; the stop in force before the bar is
    tested first (a bar that OPENS through it fills at the open); then the
    target or ladder; then the high, the trail and break-even move for the
    next bar.
  * Nothing reads a bar after the one being managed.
"""
from __future__ import annotations

import numpy as np

try:
    from numba import njit
except Exception:                                                    # noqa: BLE001
    def njit(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda f: f

# spec vector layout
TARGET, TRAIL, BE_AT, LAD1, LAD2, NEWLOW, BAIL, FLATMIN, TIMESTOP = range(9)
NSPEC = 9

# exit reasons
R_STOP, R_TARGET, R_FLAT, R_END, R_BAIL, R_TIME = range(6)


def spec(target=0.0, trail=0.0, be_at=0.0, ladder=(0.0, 0.0), newlow=False, bail=False,
         flat_min=450, time_stop=0) -> np.ndarray:
    """flat_min: minutes since 04:00 ET (450 = 11:30, 720 = 16:00)."""
    s = np.zeros(NSPEC)
    s[TARGET], s[TRAIL], s[BE_AT] = target, trail, be_at
    s[LAD1], s[LAD2] = ladder
    s[NEWLOW], s[BAIL], s[FLATMIN], s[TIMESTOP] = float(newlow), float(bail), flat_min, time_stop
    return s


@njit(cache=True)
def simulate(minute, o, h, l, c, k0, fill, entry, stop, sp):
    """Manage one long from bar index k0 (the fill bar). Returns
    (gross R, orders, exit bar index, exit reason, stop-side exit flag)."""
    rps = entry - stop
    level = stop
    hi = entry
    qty, realised, orders, lad = 1.0, 0.0, 0, 0
    prev_low = -1.0
    n = len(o)
    for k in range(k0, n):
        if minute[k] >= sp[FLATMIN]:
            realised += qty * (o[k] - fill); orders += 1
            return realised / rps, orders, k, R_FLAT, 1
        stop_now = level
        if sp[NEWLOW] > 0 and prev_low > 0 and k > k0:
            stop_now = max(stop_now, prev_low - 0.01)
        if l[k] <= stop_now:
            px = min(stop_now, o[k])
            realised += qty * (px - fill); orders += 1
            return realised / rps, orders, k, R_STOP, 1
        if sp[LAD1] > 0:
            t1 = entry + sp[LAD1] * rps
            t2 = entry + sp[LAD2] * rps
            if lad == 0 and h[k] >= t1:
                realised += 0.5 * (t1 - fill); qty -= 0.5; orders += 1; lad = 1
                level = max(level, entry)
            if lad == 1 and h[k] >= t2:
                realised += 0.25 * (t2 - fill); qty -= 0.25; orders += 1; lad = 2
        elif sp[TARGET] > 0 and h[k] >= entry + sp[TARGET] * rps:
            realised += qty * (entry + sp[TARGET] * rps - fill); orders += 1
            return realised / rps, orders, k, R_TARGET, 0
        hi = max(hi, h[k])
        if sp[TRAIL] > 0:
            level = max(level, hi - sp[TRAIL] * rps)
        if sp[LAD1] > 0 and lad >= 2:
            level = max(level, hi - rps)
        if sp[BE_AT] > 0 and hi >= entry + sp[BE_AT] * rps:
            level = max(level, entry)
        if sp[BAIL] > 0 and k == k0 + 1 and hi < entry + 0.5 * rps:
            realised += qty * (c[k] - fill); orders += 1
            return realised / rps, orders, k, R_BAIL, 1
        if sp[TIMESTOP] > 0 and minute[k] - minute[k0] >= sp[TIMESTOP] and hi < entry + 1.0 * rps:
            realised += qty * (c[k] - fill); orders += 1
            return realised / rps, orders, k, R_TIME, 1
        prev_low = l[k]
    realised += qty * (c[n - 1] - fill); orders += 1
    return realised / rps, orders, n - 1, R_END, 1


@njit(cache=True)
def stop_limit_fill(o, h, l, k_arm, trigger, ttl, cap_pct, cap_min):
    """A10: a buy stop-limit armed after bar k_arm−1, live for `ttl` bars.
    Returns (fill bar index, fill price) or (-1, nan) — gap_missed flagged by
    a fill index of -2. Touch = high >= trigger. A bar opening above the cap
    rests at the cap and fills only if the low comes back to it within the TTL."""
    cap = trigger + max(cap_min, trigger * cap_pct)
    n = len(o)
    for k in range(k_arm, min(n, k_arm + ttl)):
        if h[k] >= trigger:
            if o[k] > cap:
                for j in range(k, min(n, k_arm + ttl)):
                    if l[j] <= cap:
                        return j, cap
                return -2, np.nan
            if o[k] > trigger:
                return k, o[k]
            return k, trigger
    return -1, np.nan


@njit(cache=True)
def random_entries(minute, o, h, l, c, w0, w1, stop_pct, sp, draws, seed):
    """Market buys at the OPEN of `draws` random bars whose minute is in
    [w0, w1), stop at fill × (1 − stop_pct), same exit spec. Returns arrays
    (gross R, orders, stop-side flag, fill, stop). Deterministic in seed."""
    idx = np.empty(len(o), np.int64); m = 0
    for k in range(len(o)):
        if minute[k] >= w0 and minute[k] < w1:
            idx[m] = k; m += 1
    out_r = np.full(draws, np.nan); out_o = np.zeros(draws); out_s = np.zeros(draws)
    out_f = np.full(draws, np.nan); out_st = np.full(draws, np.nan)
    if m == 0:
        return out_r, out_o, out_s, out_f, out_st
    np.random.seed(seed)
    for d in range(draws):
        k = idx[np.random.randint(0, m)]
        fill = o[k]
        stop = fill * (1.0 - stop_pct)
        if fill - stop <= 0:
            continue
        r, n_o, ke, why, stopish = simulate(minute, o, h, l, c, k, fill, fill, stop, sp)
        out_r[d] = r; out_o[d] = n_o; out_s[d] = stopish; out_f[d] = fill; out_st[d] = stop
    return out_r, out_o, out_s, out_f, out_st
