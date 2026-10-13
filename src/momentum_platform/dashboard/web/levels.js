/* Key levels, trend lines and the volume profile for the desk's charts.
   ---------------------------------------------------------------------------
   Pure functions on [t, o, h, l, c, v] bars (t in epoch seconds): no DOM, no
   chart library, so tests/test_chart_levels.py checks them in node and in the
   page. app.js draws what they return.

   Support/resistance and the trend lines are PORTS of this project's own
   TradingView strategy, knowledge-base/tradingview/ross-fp-v4.pine (REV V9.12),
   so the desk draws the lines the owner already reads on TradingView
   (owner, 2026-10-13: "you can use the pine we've developed at its latest
   version"):

   - srFan — V4.1 bands, V7.1 fan, V9.4 "2 clean levels each side", V9.5
     polarity: the last 40 swing highs and the last 40 swing lows (5 bars each
     side, `srPivotLen`) ALL feed both sides; above the price a level is
     resistance, below it support; levels within half an ATR(14) print once;
     the two nearest each side are kept, and the nearest one each side is the
     highlighted band, ± 0.12 ATR (`bandATRfrac`). `touches` — how many swings
     the kept level absorbed — is the desk's addition; the Pine drops them.
   - trendLines — V9.8 tangent, V9.9 day-scoped, V9.10 scored anchors: the
     up-line is the tangent under today's confirmed lows from the best-scored
     swing-low anchor (touches within 0.2 ATR count 2 each, minus the line's
     distance from price in ATR); the down-line mirrors it over the highs. A
     tangent touches structure and never cuts it, so only LIVE price can cross
     it — that is the signal: "downtrend BROKEN ▲", "uptrend LOST ▼".

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
  const TL_TOL_ATR = 0.20;    // ross-fp-v4.pine tolTL = atr * 0.20
  const TL_MIN_BARS = 20;     // ross-fp-v4.pine: `if nB >= 20`

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

  /* ross-fp-v4.pine V9.10's two trend lines over `bars` — today's CONFIRMED
     bars, oldest first (the forming bar is not one) — judged against the live
     `close` and the ATR `a`. Each line: its anchor and touch indices into
     `bars`, the slope per bar, `at(i)` its price at bar index i (i = bars.length
     is the live bar), `now` that price, its touches, and whether live price is
     through it. Null when no candidate has 2 touches and the right slope. */
  function trendLines(bars, close, a) {
    const nB = bars.length;
    if (nB < TL_MIN_BARS || close == null || !(a > 0)) return { up: null, down: null };
    const tol = Math.max(a * TL_TOL_ATR, mintick(close));
    const pick = (vals, up) => {
      // candidate anchors: local extremes (2 bars each side) up to 9 bars back, the last 10, + the day's extreme
      let cand = [];
      for (let i = 2; i <= nB - 9; i++) {
        let ext = true;
        for (let j = Math.max(0, i - 2); j <= Math.min(nB - 1, i + 2); j++)
          if (up ? vals[j] < vals[i] : vals[j] > vals[i]) ext = false;
        if (ext) cand.push(i);
      }
      cand = cand.slice(-10);
      let dayI = 0;
      for (let i = 1; i <= nB - 9; i++) if (up ? vals[i] < vals[dayI] : vals[i] > vals[dayI]) dayI = i;
      cand.push(dayI);
      let best = null;
      for (const anc of cand) {
        let sl = null, tch = -1;
        for (let k = anc + 2; k < nB; k++) {
          const s = (vals[k] - vals[anc]) / (k - anc);
          if (sl === null || (up ? s < sl : s > sl)) { sl = s; tch = k; }
        }
        if (sl === null || tch <= 0 || (up ? sl < 0 : sl > 0)) continue;
        let touches = 1;
        for (let k = anc + 2; k < nB; k++) if (Math.abs(vals[k] - (vals[anc] + sl * (k - anc))) <= tol) touches += 1;
        const now = vals[anc] + sl * (nB - anc);
        const dist = (up ? close - now : now - close) / a;
        const score = touches * 2 - Math.min(Math.max(dist, 0), 20);
        if (touches >= 2 && (best === null || score > best.score)) best = { anchor: anc, touch: tch, slope: sl, touches, score, now };
      }
      if (!best) return null;
      const p0 = vals[best.anchor], anc = best.anchor, sl = best.slope;
      best.price = p0;
      best.at = i => p0 + sl * (i - anc);
      best.through = up ? close < best.now : close > best.now;
      return best;
    };
    return { up: pick(bars.map(b => b[3]), true), down: pick(bars.map(b => b[2]), false) };
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

  const DeskLevels = { ROWS, VALUE_AREA, PIVOT, PIVOTS_KEPT, SR_EACH, SR_DEDUP_ATR, BAND_ATR, TL_TOL_ATR, TL_MIN_BARS,
                       profile, density, pivots, atr, mintick, srFan, trendLines, roundLevels, priorDay,
                       sessionDay, bySession };
  global.DeskLevels = DeskLevels;
  if (typeof module !== "undefined" && module.exports) module.exports = DeskLevels;
})(typeof window !== "undefined" ? window : globalThis);
