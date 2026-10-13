/* Key levels and the volume profile for the desk's charts (2026-10-13).
   ---------------------------------------------------------------------------
   Pure functions on [t, o, h, l, c, v] bars (t in epoch seconds): no DOM, no
   chart library, so tests/test_chart_levels.py checks them in node and in the
   page. app.js draws what they return.

   Every number here is an APPROXIMATION and says where it comes from:

   - The volume profile's settings are the ones the corpus's volume-profile
     class sets up: "visible range", "value area volume is 70 row size 24
     volume up versus down" — "the standard settings that come when you first
     load it up" (wC2Bbf6OMFQ [00:05:37]-[00:06:14]). That class runs it on
     the 5-minute chart, kept zoomed out (wC2Bbf6OMFQ [00:07:36]).
   - True volume-at-price needs every print. One-minute bars only say how much
     traded between their low and high, so each bar's volume is spread evenly
     over the price rows its range covers. Up volume is a bar that closed at
     or above its open.
   - A support/resistance zone is where swing highs and lows cluster. The
     project's rule (knowledge-base/strategies/FILTERS.md, `at_support`)
     names the components — moving average, whole/half dollar, daily level,
     flipped resistance, VWAP — but no swing width and no tolerance:
     PARAMETERS.md §3 calls the tolerance "unstated" and says to sweep
     0.1-0.5 % of price. A cluster here joins swings within the larger of
     TOL of price and half the median bar range (RANGE_SHARE): on a small cap
     moving 1-2 % a five-minute bar, 0.3 % of price would never join two
     swings a few cents apart. PIVOT, TOL and RANGE_SHARE are this desk's
     picks, untested.
   - Levels describe where trading happened. Whether price bounces there is
     NOT measured on this desk: a band is a place to watch, never a signal.
*/
(function (global) {
  "use strict";

  const ROWS = 24;            // wC2Bbf6OMFQ [00:06:05]: "row size 24"
  const VALUE_AREA = 0.70;    // wC2Bbf6OMFQ [00:06:02]: "value area volume is 70"
  const PIVOT = 5;            // bars each side of a swing high/low — this desk's pick
  const TOL = 0.003;          // 0.3 % of price, the middle of PARAMETERS.md §3's 0.1-0.5 % sweep
  const RANGE_SHARE = 0.5;    // or half the median bar range, whichever is larger
  const MIN_TOUCHES = 2;      // a single swing is a point, not a level

  /* The volume profile of `bars`: `rows` price rows between the lowest low
     and the highest high, each with its up and down volume; the point of
     control (the row with the most volume, its middle price) and the value
     area (rows added around the POC, the larger neighbour first, until
     `valueArea` of the volume is inside). Null when nothing traded. */
  function profile(bars, opts) {
    opts = opts || {};
    const n = Math.max(1, Math.round(opts.rows || ROWS));
    const share = opts.valueArea || VALUE_AREA;
    let lo = Infinity, hi = -Infinity;
    for (const b of bars) {
      if (!(b[5] > 0)) continue;
      if (b[3] < lo) lo = b[3];
      if (b[2] > hi) hi = b[2];
    }
    if (!isFinite(lo) || !isFinite(hi)) return null;
    if (hi - lo < 1e-9) hi = lo + 0.01;          // one price all session: one cent of range
    const step = (hi - lo) / n;
    const up = new Array(n).fill(0), down = new Array(n).fill(0);
    const row = p => Math.min(n - 1, Math.max(0, Math.floor((p - lo) / step)));
    let total = 0;
    for (const b of bars) {
      const v = b[5];
      if (!(v > 0)) continue;
      const side = b[4] >= b[1] ? up : down;
      const l = b[3], h = b[2];
      total += v;
      if (h - l < 1e-12) { side[row(l)] += v; continue; }
      const i0 = row(l), i1 = row(h);
      for (let i = i0; i <= i1; i++) {
        const a = Math.max(l, lo + i * step), z = Math.min(h, lo + (i + 1) * step);
        if (z > a) side[i] += v * (z - a) / (h - l);
      }
    }
    const vol = up.map((u, i) => u + down[i]);
    let poc = 0;
    for (let i = 1; i < n; i++) if (vol[i] > vol[poc]) poc = i;
    let a = poc, z = poc, inside = vol[poc];
    while (inside < total * share && (a > 0 || z < n - 1)) {
      const below = a > 0 ? vol[a - 1] : -1, above = z < n - 1 ? vol[z + 1] : -1;
      if (above >= below) { z += 1; inside += vol[z]; } else { a -= 1; inside += vol[a]; }
    }
    return {
      lo, hi, step, total,
      rows: vol.map((v, i) => ({ lo: lo + i * step, hi: lo + (i + 1) * step, up: up[i], down: down[i], total: v })),
      pocRow: poc, poc: lo + (poc + 0.5) * step,
      vaFrom: a, vaTo: z, val: lo + a * step, vah: lo + (z + 1) * step,
    };
  }

  /* Volume inside [p0, p1] as a multiple of the profile's average density
     (volume per dollar over its whole range): above 1, more traded there than
     on an average stretch of the same height. */
  function density(prof, p0, p1) {
    if (!prof || !(prof.total > 0) || !(p1 > p0)) return null;
    let v = 0;
    for (const r of prof.rows) {
      const a = Math.max(p0, r.lo), z = Math.min(p1, r.hi);
      if (z > a) v += r.total * (z - a) / (r.hi - r.lo);
    }
    return (v / (p1 - p0)) / (prof.total / (prof.hi - prof.lo));
  }

  /* Swing highs and lows: a high above the `left` bars before it and not below
     the `right` bars after it (and the mirror for lows). The newest `right`
     bars can never be swings yet — no look-ahead. */
  function pivots(bars, left, right) {
    left = left == null ? PIVOT : left; right = right == null ? PIVOT : right;
    const out = [];
    for (let i = left; i + right < bars.length; i++) {
      let high = true, low = true;
      for (let j = i - left; j <= i + right && (high || low); j++) {
        if (j === i) continue;
        if (j < i ? bars[j][2] >= bars[i][2] : bars[j][2] > bars[i][2]) high = false;
        if (j < i ? bars[j][3] <= bars[i][3] : bars[j][3] < bars[i][3]) low = false;
      }
      if (high) out.push({ i, t: bars[i][0], price: bars[i][2], kind: "high" });
      if (low) out.push({ i, t: bars[i][0], price: bars[i][3], kind: "low" });
    }
    return out;
  }

  /* The median high-low range of `bars`: how far one bar usually travels. */
  function medianRange(bars) {
    const r = bars.map(b => b[2] - b[3]).filter(x => x > 0).sort((a, b) => a - b);
    return r.length ? r[r.length >> 1] : 0;
  }

  /* Support/resistance zones: a swing joins a cluster when it sits within the
     larger of `tol` × price and `rangeShare` × the median bar range of the
     cluster's mean; a zone needs `minTouches` swings. `flip` marks a zone with
     both highs and lows in it — resistance that became support, or the
     reverse (FILTERS.md: "flipped resistance"). Sorted by price. */
  function zones(bars, opts) {
    opts = opts || {};
    const tol = opts.tol || TOL, minT = opts.minTouches || MIN_TOUCHES;
    const byRange = (opts.rangeShare == null ? RANGE_SHARE : opts.rangeShare) * medianRange(bars);
    const reach = price => Math.max(tol * price, byRange);
    const ps = pivots(bars, opts.left, opts.right).sort((x, y) => x.price - y.price);
    const groups = [];
    let cur = null;
    for (const p of ps) {
      const mean = cur ? cur.sum / cur.members.length : null;
      if (cur && Math.abs(p.price - mean) <= reach(mean)) {
        cur.members.push(p); cur.sum += p.price;
      } else {
        cur = { members: [p], sum: p.price }; groups.push(cur);
      }
    }
    const all = groups.map(g => {
      const price = g.sum / g.members.length;
      const prices = g.members.map(m => m.price);
      const half = Math.max(reach(price) / 2, (Math.max(...prices) - Math.min(...prices)) / 2);
      const highs = g.members.filter(m => m.kind === "high").length;
      return { price, lo: price - half, hi: price + half, touches: g.members.length,
               highs, lows: g.members.length - highs, last: Math.max(...g.members.map(m => m.t)) };
    });
    // Neighbours whose bands overlap are one zone, not two labels on top of each other.
    const merged = [];
    for (const z of all) {
      const prev = merged[merged.length - 1];
      if (prev && z.lo <= prev.hi) {
        const n = prev.touches + z.touches;
        prev.price = (prev.price * prev.touches + z.price * z.touches) / n;
        prev.lo = Math.min(prev.lo, z.lo); prev.hi = Math.max(prev.hi, z.hi);
        prev.touches = n; prev.highs += z.highs; prev.lows += z.lows; prev.last = Math.max(prev.last, z.last);
      } else merged.push(z);
    }
    return merged.filter(z => z.touches >= minT)
      .map(z => Object.assign(z, { flip: z.highs > 0 && z.lows > 0 }));
  }

  /* The nearest whole or half dollar strictly below and above `price`. */
  function roundLevels(price) {
    if (!(price > 0)) return { below: null, above: null };
    const below = Math.ceil(price * 2 - 1e-9) / 2 - 0.5;
    const above = Math.floor(price * 2 + 1e-9) / 2 + 0.5;
    return { below: below > 0 ? below : null, above };
  }

  /* The last completed daily bar before `todayIso`: the prior day's high,
     low and close (daily bars are the regular session's). */
  function priorDay(daily, todayIso) {
    let best = null;
    for (const b of daily || []) if (b && b.d < todayIso && b.c && (!best || b.d > best.d)) best = b;
    return best ? { d: best.d, h: best.h, l: best.l, c: best.c } : null;
  }

  const ET_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York",
                                                     year: "numeric", month: "2-digit", day: "2-digit" });
  /* The New York date of an epoch-seconds stamp: the session a bar belongs to
     (04:00-20:00 ET never crosses midnight). */
  function sessionDay(t) { return ET_DAY.format(new Date(t * 1000)); }

  /* Index runs of `bars`, one per session day, in order. */
  function bySession(bars) {
    const out = [];
    let cur = null;
    for (let i = 0; i < bars.length; i++) {
      const d = sessionDay(bars[i][0]);
      if (!cur || cur.day !== d) { cur = { day: d, from: i, to: i }; out.push(cur); }
      else cur.to = i;
    }
    return out;
  }

  const DeskLevels = { ROWS, VALUE_AREA, PIVOT, TOL, RANGE_SHARE, MIN_TOUCHES,
                       profile, density, pivots, medianRange, zones, roundLevels, priorDay, sessionDay, bySession };
  global.DeskLevels = DeskLevels;
  if (typeof module !== "undefined" && module.exports) module.exports = DeskLevels;
})(typeof window !== "undefined" ? window : globalThis);
