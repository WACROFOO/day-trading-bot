/* Key levels, trend lines and the volume profile for the desk's charts.
   ---------------------------------------------------------------------------
   Pure functions on [t, o, h, l, c, v] bars (t in epoch seconds): no DOM, no
   chart library, so tests/test_chart_levels.py checks them in node and in the
   page. app.js draws what they return.

   Support/resistance is a PORT of this project's own TradingView strategy,
   knowledge-base/tradingview/ross-fp-v4.pine (REV V9.12), so the desk draws
   the levels the owner already reads on TradingView (owner, 2026-10-13: "you
   can use the pine we've developed at its latest version"):

   - srFan — V4.1 bands, V7.1 fan, V9.4 "2 clean levels each side", V9.5
     polarity: the last 40 swing highs and the last 40 swing lows (5 bars each
     side, `srPivotLen`) ALL feed both sides; above the price a level is
     resistance, below it support; levels within half an ATR(14) print once;
     the two nearest each side are kept, and the nearest one each side is the
     highlighted band, ± 0.12 ATR (`bandATRfrac`). `touches` — how many swings
     the kept level absorbed — is the desk's addition; the Pine drops them.

   The trend lines are NOT the Pine's any more (2026-10-14). Its V9.8–V9.10
   tangent was ported on 2026-10-13 and the owner's next recording showed why
   the Pine needed four revisions for them: re-anchored on every bar, so the
   lines jumped; anchored on the session's first print, under a gap (GRML
   5-minute, 04:00 pre-gap low); tangent to two neighbouring bars from the
   high of the day. trendLines below is the two-swing method of the public
   TradingView script "Trend Lines v2" (LonesomeTheBlue, open source), written
   here from its published description, no code copied — see trendLines.

   The volume profile's settings are the ones the corpus's volume-profile
   class sets up: "visible range", "value area volume is 70 row size 24 volume
   up versus down" — "the standard settings that come when you first load it
   up" (wC2Bbf6OMFQ [00:05:37]-[00:06:14]); the class runs it on the 5-minute
   chart, kept zoomed out (wC2Bbf6OMFQ [00:07:36]). One-minute bars only say
   how much traded between their low and high, so each bar's volume is spread
   evenly over the price rows its range covers: an approximation of what the
   prints would show.

   Levels and lines describe where trading happened. Whether price turns or
   breaks out there is NOT measured on this desk: a place to watch, never a
   signal to act.
*/
(function (global) {
  "use strict";

  const ROWS = 24;            // wC2Bbf6OMFQ [00:06:05]: "row size 24"
  const VALUE_AREA = 0.70;    // wC2Bbf6OMFQ [00:06:02]: "value area volume is 70"
  const PIVOT = 5;            // ross-fp-v4.pine srPivotLen: "Pivot strength (bars each side)"
  const PIVOTS_KEPT = 40;     // ross-fp-v4.pine: pivHighs / pivLows hold the last 40 each
  const SR_EACH = 2;          // ross-fp-v4.pine maxSRlines: "2 = clean"
  const SR_DEDUP_ATR = 0.5;   // ross-fp-v4.pine tolSR = atr * 0.5
  const BAND_ATR = 0.12;      // ross-fp-v4.pine bandATRfrac
  const TL_TOL_ATR = 0.20;    // ross-fp-v4.pine tolTL = atr * 0.20: a swing this close to a line touches it
  const TL_SWINGS = 10;       // "Trend Lines v2": the last 10 swings of each kind are searched
  const TL_KEEP_BROKEN = 20;  // a line broken within the last 20 bars stays drawn, at its break

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

  /* Swing highs and lows, in time order: a high above the `left` bars before
     it and not below the `right` bars after it (and the mirror for lows) —
     Pine's ta.pivothigh / ta.pivotlow shape; how Pine breaks an exact tie is
     not documented, this keeps a high over equal highs to its right. The
     newest `right` bars can never be swings yet: no look-ahead. */
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

  /* Pine's ta.atr(n): the true range (high - low on the first bar), averaged
     Wilder's way — the simple mean of the first n, then rma. The value at the
     last bar; null with fewer than n bars. */
  function atr(bars, n) {
    n = n || 14;
    if (!bars || bars.length < n) return null;
    let sum = 0, a = null;
    for (let i = 0; i < bars.length; i++) {
      const b = bars[i];
      const tr = i === 0 ? b[2] - b[3]
        : Math.max(b[2] - b[3], Math.abs(b[2] - bars[i - 1][4]), Math.abs(b[3] - bars[i - 1][4]));
      if (i < n) { sum += tr; if (i === n - 1) a = sum / n; }
      else a = (a * (n - 1) + tr) / n;
    }
    return a;
  }

  /* A US stock's minimum tick: a cent from $1, a hundredth of a cent under. */
  function mintick(price) { return price >= 1 ? 0.01 : 0.0001; }

  /* ross-fp-v4.pine's S/R fan (see the header): `close` is the live price,
     `a` the ATR at the live bar. Levels nearest first on each side. */
  function srFan(bars, close, a, opts) {
    opts = opts || {};
    const each = opts.each || SR_EACH, keep = opts.keep || PIVOTS_KEPT;
    if (!bars.length || close == null || !(a > 0)) return { res: [], sup: [], band: null, atr: a || null };
    const piv = pivots(bars, opts.pivot || PIVOT, opts.pivot || PIVOT);
    const all = piv.filter(p => p.kind === "high").slice(-keep)
      .concat(piv.filter(p => p.kind === "low").slice(-keep));      // Pine: pivHighs, then pivLows
    const tol = a * SR_DEDUP_ATR;
    const side = above => {
      const out = [];
      for (const p of all) {
        if (!(above ? p.price > close : p.price < close)) continue;
        const dup = out.find(o => Math.abs(o.price - p.price) <= tol);
        if (dup) { dup.touches += 1; dup.highs += p.kind === "high" ? 1 : 0; dup.lows += p.kind === "low" ? 1 : 0; continue; }
        out.push({ price: p.price, touches: 1, highs: p.kind === "high" ? 1 : 0, lows: p.kind === "low" ? 1 : 0 });
      }
      out.sort((x, y) => above ? x.price - y.price : y.price - x.price);
      return out.slice(0, each);
    };
    return { res: side(true), sup: side(false), band: Math.max(a * BAND_ATR, mintick(close)), atr: a };
  }

  /* Trend lines through two swings. `bars` are the CONFIRMED bars, oldest
     first — the forming bar is not one; its index, bars.length, is the live
     bar, and `close` its price. `a` is the ATR at the live bar. Options:
     `from`, the index where today's session starts (anchors are today's
     swings only, ross-fp-v4 V9.9: never an overnight print), and `pivot`.

     The method of "Trend Lines v2" (LonesomeTheBlue, TradingView, open
     source) as its description states it: take the last 10 swing highs and
     the last 10 swing lows, search from the newest, keep a line only where one
     is possible and say whether it is broken. Here:
       - a swing is a confirmed pivot, 5 bars each side — the swings the S/R
         fan reads, so both tools stand on the same points;
       - a down-line joins an older swing high to a LOWER newer one, an
         up-line an older swing low to a HIGHER newer one — two swings at
         least six bars apart, never two neighbouring bars;
       - it is possible only if no candle CLOSES through it between its two
         swings and no swing of its kind pierces it by more than 0.2 ATR there
         (wicks may poke through; a close may not — the public scripts' rule);
       - after its second swing, the first candle closing through it BREAKS
         it: "downtrend BROKEN ▲" (the breakout), "uptrend LOST ▼";
       - searched newest swing first, each with its newest possible partner
         first: the first unbroken line is the line; a line broken in the last
         20 bars is kept too, drawn to its break.
     A line moves only when a new swing confirms or a candle closes through
     it — never on a tick. Live price beyond an unbroken line is `through`:
     breaking, not yet broken.

     Returns { up, down, upBroken, downBroken }; each line or null:
     { a, b, pa, pb, slope, at(i), touches, brokeAt, breakPrice, now, through }
     — indices into `bars`, `at(i)` the line's price at bar i, `now` at the
     live bar, `touches` the swings of its kind within 0.2 ATR of it. */
  function trendLines(bars, close, a, opts) {
    opts = opts || {};
    const none = { up: null, down: null, upBroken: null, downBroken: null };
    const P = opts.pivot || PIVOT, from = Math.max(0, opts.from || 0);
    const keep = opts.keep == null ? TL_KEEP_BROKEN : opts.keep;
    const n = bars.length;
    if (n < 2 * P + 2 || close == null || !(a > 0)) return none;
    const tol = Math.max(a * TL_TOL_ATR, mintick(close));
    const piv = pivots(bars, P, P).filter(p => p.i >= from);
    const side = up => {
      const sw = piv.filter(p => p.kind === (up ? "low" : "high")).slice(-TL_SWINGS);
      const beyond = (v, line, by) => up ? v < line - by : v > line + by;
      let intact = null, broken = null;
      for (let bi = sw.length - 1; bi >= 1 && !intact; bi--) {
        const B = sw[bi];
        for (let ai = bi - 1; ai >= 0; ai--) {
          const A = sw[ai];
          if (up ? !(A.price < B.price) : !(A.price > B.price)) continue;
          const slope = (B.price - A.price) / (B.i - A.i);
          const at = i => A.price + slope * (i - A.i);
          let ok = true;
          for (let k = A.i + 1; k < B.i && ok; k++) if (beyond(bars[k][4], at(k), 1e-9)) ok = false;
          for (let k = ai + 1; k < bi && ok; k++) if (beyond(sw[k].price, at(sw[k].i), tol)) ok = false;
          if (!ok) continue;
          let brokeAt = null;
          for (let k = B.i + 1; k < n; k++) if (beyond(bars[k][4], at(k), 1e-9)) { brokeAt = k; break; }
          const end = brokeAt == null ? n : brokeAt;
          const touches = sw.filter(p => p.i >= A.i && p.i <= end && Math.abs(p.price - at(p.i)) <= tol).length;
          const now = at(n);
          const line = { a: A.i, b: B.i, pa: A.price, pb: B.price, slope, at, touches, brokeAt,
                         breakPrice: brokeAt == null ? null : at(brokeAt), now,
                         through: brokeAt == null && beyond(close, now, 1e-9) };
          if (brokeAt == null) { intact = line; break; }
          if (n - brokeAt <= keep && (!broken || brokeAt > broken.brokeAt)) broken = line;
        }
      }
      return { intact, broken };
    };
    const u = side(true), d = side(false);
    return { up: u.intact, down: d.intact, upBroken: u.broken, downBroken: d.broken };
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

  const DeskLevels = { ROWS, VALUE_AREA, PIVOT, PIVOTS_KEPT, SR_EACH, SR_DEDUP_ATR, BAND_ATR, TL_TOL_ATR, TL_SWINGS,
                       TL_KEEP_BROKEN,
                       profile, density, pivots, atr, mintick, srFan, trendLines, roundLevels, priorDay,
                       sessionDay, bySession };
  global.DeskLevels = DeskLevels;
  if (typeof module !== "undefined" && module.exports) module.exports = DeskLevels;
})(typeof window !== "undefined" ? window : globalThis);
