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
def simulate(minute, o, h, l, c, k0, fill, entry, stop, sp, fill_high_ok=True):
    """Manage one long from bar index k0 (the fill bar). Returns
    (gross R, orders, exit bar index, exit reason, stop-side exit flag).

    The fill bar: its low is assumed to come AFTER the fill (pessimistic),
    but a stop hit there fills AT the stop — the bar's open preceded the buy
    and cannot be the exit. When the fill was a return to the cap
    (`fill_high_ok` False) the bar's high may have printed before the buy,
    so it earns no target and moves no trail."""
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
            px = stop_now if k == k0 else min(stop_now, o[k])
            realised += qty * (px - fill); orders += 1
            return realised / rps, orders, k, R_STOP, 1
        if k == k0 and not fill_high_ok:
            prev_low = l[k]
            continue
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
def stop_limit_fill(minute, o, h, l, k_arm, trigger, ttl_min, cap_pct, cap_min):
    """A10: a buy stop-limit armed at the close of bar k_arm-1, live for
    `ttl_min` MINUTES (the desk cancels after 3 minutes, however sparse the
    bars). Touch = high >= trigger: filled at the trigger, or at the open when
    the bar opens between trigger and cap. A bar opening above the cap leaves
    a resting buy limit at the cap: filled at the cap if that bar or a later
    one inside the TTL trades down to it — at a later bar's open when it opens
    below the cap. Returns (fill bar, price, cap-return flag); fill bar -1 =
    never touched, -2 = touched above the cap and never came back."""
    cap = trigger + max(cap_min, trigger * cap_pct)
    n = len(o)
    t0 = minute[k_arm - 1] if k_arm >= 1 else minute[0] - 1
    for k in range(k_arm, n):
        if minute[k] > t0 + ttl_min:
            break
        if h[k] >= trigger:
            if o[k] > cap:
                for j in range(k, n):
                    if minute[j] > t0 + ttl_min:
                        break
                    if l[j] <= cap:
                        if j > k and o[j] <= cap:
                            return j, o[j], 1
                        return j, cap, 1
                return -2, np.nan, 0
            if o[k] > trigger:
                return k, o[k], 0
            return k, trigger, 0
    return -1, np.nan, 0


@njit(cache=True)
def random_entries(minute, o, h, l, c, w0, w1, stop_pct, sp, draws, seed):
    """Market buys at the OPEN of `draws` random bars whose minute is in
    [w0, w1), stop at fill x (1 - stop_pct), same exit spec. Returns arrays
    (gross R, orders, stop-side flag, fill, stop, entry index, exit index).
    Deterministic in seed."""
    idx = np.empty(len(o), np.int64); m = 0
    for k in range(len(o)):
        if minute[k] >= w0 and minute[k] < w1:
            idx[m] = k; m += 1
    out_r = np.full(draws, np.nan); out_o = np.zeros(draws); out_s = np.zeros(draws)
    out_f = np.full(draws, np.nan); out_st = np.full(draws, np.nan)
    out_k = np.full(draws, -1, np.int64); out_ke = np.full(draws, -1, np.int64)
    if m == 0:
        return out_r, out_o, out_s, out_f, out_st, out_k, out_ke
    np.random.seed(seed)
    for d in range(draws):
        k = idx[np.random.randint(0, m)]
        fill = o[k]
        stop = fill * (1.0 - stop_pct)
        if fill - stop <= 0:
            continue
        r, n_o, ke, why, stopish = simulate(minute, o, h, l, c, k, fill, fill, stop, sp)
        out_r[d] = r; out_o[d] = n_o; out_s[d] = stopish; out_f[d] = fill; out_st[d] = stop
        out_k[d] = k; out_ke[d] = ke
    return out_r, out_o, out_s, out_f, out_st, out_k, out_ke


@njit(cache=True)
def simulate_many(minute, o, h, l, c, starts, ends, k0s, fills, entries, stops, sp, high_ok):
    """`simulate` over many trades. k0s are relative to each [start, end)
    slice; the returned exit index is absolute."""
    n = len(starts)
    R = np.full(n, np.nan); orders = np.zeros(n, np.int64); kex = np.zeros(n, np.int64)
    why = np.zeros(n, np.int64); stopish = np.zeros(n, np.int64)
    for j in range(n):
        s, e = starts[j], ends[j]
        if k0s[j] < 0 or s + k0s[j] >= e or entries[j] - stops[j] <= 0:
            continue
        r, no, k, w, st = simulate(minute[s:e], o[s:e], h[s:e], l[s:e], c[s:e], k0s[j], fills[j],
                                   entries[j], stops[j], sp, high_ok[j] > 0)
        R[j] = r; orders[j] = no; kex[j] = s + k; why[j] = w; stopish[j] = st
    return R, orders, kex, why, stopish


# ------------------------------------------------------------------ entry generators
@njit(cache=True)
def pmh_break(minute, o, h, l, c, w0, w1, min_age, near, lookback):
    """Pre-market-high break (F2): at the close of bar t in [w0, w1), when the
    running high since 04:00 is >= min_age bars old and the close is within
    `near` of it, arm a buy stop-limit at high + 1c for three bars; stop under
    the lowest low of the last `lookback` bars. First fill only.
    Returns (arm bar, trigger, stop, fill bar, fill price, cap flag) or arm = -1."""
    n = len(o)
    hi = -1.0; hi_k = -1
    for t in range(n):
        if h[t] > hi:
            hi = h[t]; hi_k = t
        if minute[t] < w0 or minute[t] >= w1:
            continue
        if minute[t] - minute[hi_k] < min_age or c[t] < (1.0 - near) * hi:
            continue
        trig = hi + 0.01
        if trig < 2.0 or trig > 20.0:
            continue
        lo = l[t]
        for j in range(max(0, t - lookback + 1), t + 1):
            lo = min(lo, l[j])
        stop = lo - 0.01
        if stop >= trig or stop <= 0:
            continue
        fk, fpx, capf = stop_limit_fill(minute, o, h, l, t + 1, trig, 3, 0.003, 0.01)
        if fk >= 0:
            return t, trig, stop, fk, fpx, capf
    return -1, 0.0, 0.0, -1, 0.0, 0


@njit(cache=True)
def orb(minute, o, h, l, c, or0, or1, until):
    """Opening-range breakout (H5.1): the range is bars [or0, or1); a buy
    stop-limit at its high + 1c rests from or1 until `until`. Returns
    (arm bar, trigger, stop, fill bar, fill price, green, cap flag) or arm = -1."""
    n = len(o)
    first = -1; last = -1; hi = -1.0; lo = 1e18
    for k in range(n):
        if minute[k] >= or0 and minute[k] < or1:
            if first < 0:
                first = k
            last = k
            hi = max(hi, h[k]); lo = min(lo, l[k])
    if first < 0 or minute[first] != or0:
        return -1, 0.0, 0.0, -1, 0.0, 0, 0
    green = 1 if c[last] > o[first] else 0
    k_arm = last + 1
    trig = hi + 0.01; stop = lo - 0.01
    if k_arm >= n or minute[k_arm] >= until or trig < 2.0 or trig > 20.0 or stop <= 0:
        return last, trig, stop, -1, 0.0, green, 0
    fk, fpx, capf = stop_limit_fill(minute, o, h, l, k_arm, trig, until - 1 - minute[last], 0.003, 0.01)
    return last, trig, stop, fk, fpx, green, capf


@njit(cache=True)
def vwap_test(minute, o, h, l, c, v, pc, w0, w1, gain, above_n, touch):
    """First VWAP test (H5.2): VWAP anchored 04:00 on close x volume. At bar t
    in [w0, w1): up >= gain on the previous close, the previous `above_n`
    closes above their VWAP, this bar's low within `touch` of VWAP and its
    close above it -> buy stop-limit at its high + 1c for three bars, stop
    under its low. First fill only."""
    n = len(o)
    vw = np.empty(n); sv = 0.0; spv = 0.0
    for k in range(n):
        sv += v[k]; spv += c[k] * v[k]
        vw[k] = spv / sv if sv > 0 else c[k]
    for t in range(above_n, n):
        if minute[t] < w0 or minute[t] >= w1:
            continue
        if c[t] / pc - 1.0 < gain:
            continue
        ok = True
        for j in range(t - above_n, t):
            if c[j] <= vw[j]:
                ok = False
                break
        if not ok:
            continue
        if l[t] <= vw[t] * (1.0 + touch) and c[t] > vw[t]:
            trig = h[t] + 0.01; stop = l[t] - 0.01
            if trig < 2.0 or trig > 20.0 or stop <= 0 or stop >= trig:
                continue
            fk, fpx, capf = stop_limit_fill(minute, o, h, l, t + 1, trig, 3, 0.003, 0.01)
            if fk >= 0:
                return t, trig, stop, fk, fpx, capf
    return -1, 0.0, 0.0, -1, 0.0, 0


@njit(cache=True)
def fills_many(minute, o, h, l, starts, ends, plan_mins, triggers, ttl_min):
    """A10 fills for many plans armed at the close of their plan minute.
    Returns (fill bar relative to its slice or -1/-2, fill price, cap flag)."""
    n = len(starts)
    fk = np.full(n, -1, np.int64); fp = np.full(n, np.nan); cf = np.zeros(n, np.int64)
    for j in range(n):
        s, e = starts[j], ends[j]
        mm = minute[s:e]
        k_arm = 0
        while k_arm < e - s and mm[k_arm] <= plan_mins[j]:
            k_arm += 1
        if k_arm >= e - s or k_arm == 0:
            continue
        a, b, c = stop_limit_fill(mm, o[s:e], h[s:e], l[s:e], k_arm, triggers[j], ttl_min, 0.003, 0.01)
        fk[j] = a; fp[j] = b; cf[j] = c
    return fk, fp, cf
