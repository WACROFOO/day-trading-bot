/* Momentum Workstation — replay shell.
   One selected symbol drives every panel. Charts keep their own intervals.
   Nothing here places an order; scanner rows are research candidates. */
(function () {
"use strict";
const S = window.__SESSION__;
if (!S) { document.body.innerHTML = "<p style='padding:20px'>session.js failed to load</p>"; return; }

const COL = {};
S.rowColumns.forEach((c, i) => COL[c] = i);
const SYMS = S.symbols, FRAMES = S.frames, BARS = S.bars;
const OPEN_INDEX = FRAMES.findIndex(f => f.session === "regular");
const LIST_IDS = ["five_pillars_list"];
const ALERT_TILES = {
  running_up: { id: "running_up", title: "Running Up · live uptrend",
                note: "Acceleration before a new high. Fires in premarket and regular hours.",
                scanners: ["running_up", "squeeze_5_in_5", "squeeze_10_in_10"] },
  hod_momentum: { id: "hod_momentum", title: "Small Cap · High of Day Momentum",
                  note: "New high plus momentum — not every high-of-day print. Branch labels the float/RVOL band.",
                  scanners: ["hod_momentum", "breakout_52w"] },
};
// Three cards, in funnel order: candidates -> acceleration -> breakout.
const DOCK_ORDER = ["five_pillars_list", "running_up", "hod_momentum"];

const state = {
  frame: 0, playing: false, speed: 4, selected: null, locked: false,
  frozen: {}, openRow: null, openAlert: null, riskDollars: "",
  sound: false, focusTile: LIST_IDS[0], focusRow: 0, prevRowKeys: {},
};

/* ── formatting ─────────────────────────────────────────────────────── */
const $ = s => document.querySelector(s);
const el = (t, c, txt) => { const n = document.createElement(t); if (c) n.className = c; if (txt != null) n.textContent = txt; return n; };
const fx = (v, d = 2) => v == null ? "—" : Number(v).toFixed(d);
const pct = v => v == null ? "—" : (v >= 0 ? "+" : "") + v.toFixed(1) + "%";
const vol = v => v == null ? "—" : v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : v >= 1e3 ? Math.round(v / 1e3) + "k" : String(v);
const dirClass = v => v == null ? "flat" : v > 0.05 ? "up" : v < -0.05 ? "down" : "flat";
const etTime = iso => new Date(iso).toLocaleTimeString("en-US", { timeZone: "America/New_York", hour12: false, hour: "2-digit", minute: "2-digit" });
const etClock = iso => new Date(iso).toLocaleTimeString("en-US", { timeZone: "America/New_York", hour12: false });
const rowObj = a => { const o = {}; S.rowColumns.forEach((c, i) => o[c] = a[i]); return o; };

/* ── derived series ─────────────────────────────────────────────────── */
function barsUpTo(sym, idx) { const b = BARS[sym] || []; return b.slice(0, Math.min(idx + 1, b.length)); }
function agg(bars, n) {
  const out = [];
  for (let i = 0; i < bars.length; i += n) {
    const c = bars.slice(i, i + n); if (!c.length) break;
    out.push([c[0][0], c[0][1], Math.max(...c.map(x => x[2])), Math.min(...c.map(x => x[3])), c[c.length - 1][4], c.reduce((s, x) => s + x[5], 0)]);
  }
  return out;
}
function ema(vals, n) {
  const k = 2 / (n + 1); const out = []; let prev = null;
  vals.forEach((v, i) => { prev = i === 0 ? v : v * k + prev * (1 - k); out.push(i + 1 < n ? null : prev); });
  return out;
}
function vwap(bars) {
  let pv = 0, vv = 0;
  return bars.map(b => { const tp = (b[2] + b[3] + b[4]) / 3; pv += tp * b[5]; vv += b[5]; return vv ? pv / vv : b[4]; });
}
function activePlan(sym, t) {
  const p = (S.plans || []).filter(x => x.symbol === sym && x.armedAt <= t);
  return p.length ? p[p.length - 1] : null;
}
function alertsUpTo(idx) {
  const out = [];
  for (let i = 0; i <= idx && i < FRAMES.length; i++) FRAMES[i].alerts.forEach(a => out.push(a));
  return out;
}

/* ── charts ──────────────────────────────────────────────────────────
   Primary renderer is TradingView's Lightweight Charts (real crosshair,
   price/time scales, zoom and pan). If the library is unavailable — offline,
   blocked CDN — every pane falls back to a built-in canvas renderer so the
   workspace is never blank. Neither library supplies market data; that comes
   from the session (replay fixture today, a licensed feed later). */
const TV = window.LightweightCharts || null;

const PALETTE = {
  bg: "#0b1119", text: "#93a4b8", grid: "#141d27", border: "#1d2836",
  up: "#2ad17f", down: "#ff5f6e", vwap: "#c39bff", ema9: "#4dd2ff",
  ema20: "#ff9ad2", ema200: "#ffb648", hod: "#ffc247", h52: "#c39bff",
  entry: "#22c7e8", stop: "#ff5f6e", target: "#2ad17f",
};

function makePane(hostId, daily) {
  const host = document.getElementById(hostId);
  if (!TV) return canvasPane(host);
  const chart = TV.createChart(host, {
    width: host.clientWidth || 400, height: host.clientHeight || 200,
    layout: { background: { color: PALETTE.bg }, textColor: PALETTE.text,
              fontFamily: '"IBM Plex Mono", ui-monospace, monospace', fontSize: 10 },
    grid: { vertLines: { color: PALETTE.grid }, horzLines: { color: PALETTE.grid } },
    rightPriceScale: { borderColor: PALETTE.border, scaleMargins: { top: 0.08, bottom: 0.26 } },
    timeScale: { borderColor: PALETTE.border, timeVisible: !daily, secondsVisible: false,
                 rightOffset: 2, barSpacing: daily ? 3 : 5 },
    crosshair: { mode: TV.CrosshairMode ? TV.CrosshairMode.Normal : 0 },
    handleScale: true, handleScroll: true,
  });
  const candles = chart.addCandlestickSeries({
    upColor: PALETTE.up, downColor: PALETTE.down, borderVisible: false,
    wickUpColor: PALETTE.up, wickDownColor: PALETTE.down,
  });
  const volume = chart.addHistogramSeries({
    priceFormat: { type: "volume" }, priceScaleId: "vol", color: "#1c6b47",
  });
  chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
  const lines = {};
  const lineFor = key => (lines[key] = lines[key] ||
    chart.addLineSeries({ color: PALETTE[key], lineWidth: 1, priceLineVisible: false,
                          lastValueVisible: false, crosshairMarkerVisible: false }));
  let priceLines = [];

  return {
    engine: "tradingview",
    resize() { chart.applyOptions({ width: host.clientWidth, height: host.clientHeight }); },
    render(bars, opts) {
      if (!bars.length) { candles.setData([]); volume.setData([]); return; }
      const t = i => daily ? bars[i].d : bars[i][0];
      const rows = bars.map((b, i) => daily
        ? { time: b.d, open: b.o, high: b.h, low: b.l, close: b.c }
        : { time: b[0], open: b[1], high: b[2], low: b[3], close: b[4] });
      candles.setData(rows);
      volume.setData(bars.map((b, i) => ({
        time: rows[i].time, value: daily ? b.v : b[5],
        color: rows[i].close >= rows[i].open ? "#1c6b4788" : "#7a2b3488",
      })));
      const closes = rows.map(r => r.close);
      const put = (key, series) => {
        if (!series) { if (lines[key]) lines[key].setData([]); return; }
        lineFor(key).setData(series.map((v, i) => v == null ? null : { time: rows[i].time, value: v })
                                   .filter(Boolean));
      };
      put("vwap", opts.vwap ? vwap(bars) : null);
      put("ema9", opts.ema9 ? ema(closes, 9) : null);
      put("ema20", opts.ema20 ? ema(closes, 20) : null);
      put("ema200", opts.ema200 ? ema(closes, 200) : null);
      priceLines.forEach(l => candles.removePriceLine(l));
      priceLines = [];
      const mark = (price, color, title) => {
        if (price == null) return;
        priceLines.push(candles.createPriceLine({
          price: price, color: color, lineWidth: 1,
          lineStyle: TV.LineStyle ? TV.LineStyle.Dashed : 2,
          axisLabelVisible: true, title: title,
        }));
      };
      if (opts.plan) {
        mark(opts.plan.target, PALETTE.target, "TARGET");
        mark(opts.plan.entry, PALETTE.entry, "ENTRY");
        mark(opts.plan.stop, PALETTE.stop, "STOP");
      }
      mark(opts.hod, PALETTE.hod, "HOD");
      mark(opts.h52, PALETTE.h52, "52w");
    },
  };
}

/* Canvas fallback — same inputs, no dependency. */
function canvasPane(host) {
  const canvas = document.createElement("canvas");
  canvas.style.width = "100%";
  host.appendChild(canvas);
  return {
    engine: "canvas",
    resize() { canvas.style.height = host.clientHeight + "px"; },
    render(bars, opts) {
      canvas.setAttribute("height", String(Math.max(80, host.clientHeight)));
      drawChart(canvas, bars.length && bars[0].d
        ? bars.map(b => [0, b.o, b.h, b.l, b.c, b.v]) : bars, opts);
    },
  };
}

function drawChart(canvas, bars, opts) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || canvas.parentElement.clientWidth || 600;
  const h = Number(canvas.getAttribute("height")) || 200;
  canvas.width = w * dpr; canvas.height = h * dpr;
  const g = canvas.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  g.fillStyle = PALETTE.bg; g.fillRect(0, 0, w, h);
  if (!bars.length) {
    g.fillStyle = "#63748a"; g.font = "11px system-ui";
    g.fillText("no bars yet", 12, h / 2); return;
  }
  const padL = 4, padR = 50, padT = 6, volH = Math.round(h * 0.18), padB = 12;
  const plotH = h - padT - volH - padB, plotW = w - padL - padR;
  const N = bars.length, bw = Math.max(1, Math.min(8, plotW / N * 0.7)), step = plotW / N;
  const extras = [];
  if (opts.plan) extras.push(opts.plan.entry, opts.plan.stop, opts.plan.target);
  if (opts.hod) extras.push(opts.hod);
  if (opts.h52) extras.push(opts.h52);
  let lo = Math.min(...bars.map(b => b[3]), ...extras);
  let hi = Math.max(...bars.map(b => b[2]), ...extras);
  const pad = (hi - lo) * 0.08 || hi * 0.02; lo -= pad; hi += pad;
  const y = p => padT + plotH - (p - lo) / (hi - lo) * plotH;
  const x = i => padL + i * step + step / 2;
  const maxV = Math.max(...bars.map(b => b[5]), 1);
  g.font = "9px ui-monospace,monospace"; g.textAlign = "left";
  for (let i = 0; i <= 3; i++) {
    const p = lo + (hi - lo) * i / 3, yy = y(p);
    g.strokeStyle = PALETTE.grid; g.beginPath(); g.moveTo(padL, yy); g.lineTo(padL + plotW, yy); g.stroke();
    g.fillStyle = "#63748a"; g.fillText(p.toFixed(2), padL + plotW + 5, yy + 3);
  }
  bars.forEach((b, i) => {
    const vh = b[5] / maxV * (volH - 3);
    g.fillStyle = b[4] >= b[1] ? "#1c6b47" : "#7a2b34";
    g.fillRect(x(i) - bw / 2, padT + plotH + volH - vh, bw, vh);
  });
  if (opts.plan) {
    const spec = [["TARGET", opts.plan.target, PALETTE.target], ["ENTRY", opts.plan.entry, PALETTE.entry],
                  ["STOP", opts.plan.stop, PALETTE.stop]].sort((a, b) => b[1] - a[1]);
    let lastY = -99;
    spec.forEach(([name, price, col]) => {
      g.strokeStyle = col; g.setLineDash([4, 3]); g.beginPath();
      g.moveTo(padL, y(price)); g.lineTo(padL + plotW, y(price)); g.stroke(); g.setLineDash([]);
      let ly = y(price) - 2; if (ly - lastY < 11) ly = lastY + 11; lastY = ly;
      const label = name + " " + price.toFixed(2);
      g.font = "8px ui-monospace,monospace";
      g.fillStyle = "#0b1119cc"; g.fillRect(padL + 1, ly - 7, g.measureText(label).width + 5, 9);
      g.fillStyle = col; g.fillText(label, padL + 3, ly);
    });
  }
  const hline = (p, col, label) => {
    if (p == null) return;
    g.strokeStyle = col; g.setLineDash([2, 3]); g.beginPath();
    g.moveTo(padL, y(p)); g.lineTo(padL + plotW, y(p)); g.stroke(); g.setLineDash([]);
    g.fillStyle = col; g.font = "8px ui-monospace,monospace"; g.textAlign = "right";
    g.fillText(label, padL + plotW - 3, y(p) - 2); g.textAlign = "left";
  };
  hline(opts.hod, PALETTE.hod, "HOD " + fx(opts.hod));
  hline(opts.h52, PALETTE.h52, "52w " + fx(opts.h52));
  bars.forEach((b, i) => {
    const col = b[4] >= b[1] ? PALETTE.up : PALETTE.down;
    g.strokeStyle = col; g.fillStyle = col; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x(i), y(b[2])); g.lineTo(x(i), y(b[3])); g.stroke();
    const yo = y(b[1]), yc = y(b[4]);
    g.fillRect(x(i) - bw / 2, Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
  });
  const line = (series, col) => {
    g.strokeStyle = col; g.lineWidth = 1.2; g.beginPath(); let started = false;
    series.forEach((v, i) => { if (v == null) return; const px = x(i), py = y(v);
      started ? g.lineTo(px, py) : (g.moveTo(px, py), started = true); });
    g.stroke();
  };
  const closes = bars.map(b => b[4]);
  if (opts.vwap) line(vwap(bars), PALETTE.vwap);
  if (opts.ema9) line(ema(closes, 9), PALETTE.ema9);
  if (opts.ema20) line(ema(closes, 20), PALETTE.ema20);
  if (opts.ema200) line(ema(closes, 200), PALETTE.ema200);
}

/* ── pillar chips (computed in the browser from published thresholds) ── */
function pillarChecks(row, meta) {
  const T = S.pillarThresholds;
  const f = meta.floatShares, quality = meta.floatQuality;
  return [
    { k: "P", name: "price $" + T.priceMin + "–$" + T.priceMax, v: row.price, ok: row.price >= T.priceMin && row.price <= T.priceMax },
    { k: "G", name: "gain ≥ " + T.gainMinPct + "%", v: pct(row.changePct), ok: (row.changePct || 0) >= T.gainMinPct },
    { k: "R", name: "daily RVOL ≥ " + T.rvolMin + "×", v: fx(row.rvolDaily) + "×", ok: (row.rvolDaily || 0) >= T.rvolMin },
    {
      k: "F", name: "float < " + (T.floatMaxShares / 1e6) + "M",
      v: quality === "verified" ? (f / 1e6).toFixed(1) + "M" : quality === "unknown" ? "unknown" : (f / 1e6).toFixed(1) + "M proxy",
      ok: quality === "verified" && f < T.floatMaxShares,
    },
  ];
}
function newsFor(sym, nowMs) {
  const items = (SYMS[sym] && SYMS[sym].news) || [];
  const visible = items.filter(n => new Date(n.firstObservedAt).getTime() <= nowMs);
  if (!visible.length) return null;
  const n = visible[visible.length - 1];
  const ageMin = (nowMs - new Date(n.publishedAt).getTime()) / 60000;
  const flame = ageMin <= 120 ? "red" : ageMin <= 720 ? "orange" : ageMin <= 1440 ? "yellow" : null;
  return { item: n, ageMin, flame };
}

/* ── tiles ──────────────────────────────────────────────────────────── */
function tileShell(id, title, kind, stateLabel, note, onFreeze) {
  const t = el("div", "tile" + (kind === "alert" ? " alert-tile" : "") + (state.focusTile === id ? " focused" : ""));
  t.dataset.tile = id;
  const head = el("div", "tile-head");
  head.appendChild(el("span", "tile-title", title));
  const st = el("span", "tile-state " + (stateLabel === "FROZEN" ? "frozen" : "replay"), stateLabel);
  st.dataset.state = stateLabel;
  head.appendChild(st);
  head.appendChild(el("span", "tile-age", etTime(FRAMES[state.frame].ts)));
  if (kind === "list") {
    const fz = el("button", "icon-btn", "❄");
    fz.title = "Freeze visible order (Space)";
    fz.setAttribute("aria-pressed", String(!!state.frozen[id]));
    fz.onclick = e => { e.stopPropagation(); onFreeze(); };
    head.appendChild(fz);
  } else {
    const snd = el("button", "icon-btn", "🔔");
    snd.title = "Alert sound for this tile — notification only, never a filter";
    snd.setAttribute("aria-pressed", "true");
    snd.onclick = e => { e.stopPropagation(); snd.setAttribute("aria-pressed", snd.getAttribute("aria-pressed") === "true" ? "false" : "true"); };
    head.appendChild(snd);
  }
  head.onclick = () => { state.focusTile = id; render(); };
  t.appendChild(head);
  if (note) t.appendChild(el("div", "tile-note", note));
  return t;
}

function flameFor(symbol, nowMs) {
  const nf = newsFor(symbol, nowMs);
  const el_ = el("i", "flame " + (nf && nf.flame ? nf.flame : "none"));
  el_.title = nf ? "news " + Math.round(nf.ageMin) + " min old — recency only, not quality"
                 : "no qualifying headline in the last 24h";
  return el_;
}

function renderListTile(id, frame) {
  const meta = S.listMeta[id] || { title: id, metric: "", note: "" };
  const rows = (frame.lists[id] || []).map(rowObj);
  const froz = state.frozen[id];
  const nowMs = new Date(frame.ts).getTime();
  let ordered = rows, pending = 0;
  if (froz) {
    const byS = {}; rows.forEach(r => byS[r.symbol] = r);
    ordered = froz.order.map(s => byS[s]).filter(Boolean);
    pending = rows.filter(r => froz.order.indexOf(r.symbol) === -1).length;
  }
  const tile = tileShell(id, meta.title, "list", froz ? "FROZEN" : "REPLAY", meta.note, () => {
    state.frozen[id] = froz ? null : { order: rows.map(r => r.symbol) };
    if (!state.frozen[id]) delete state.frozen[id];
    render();
  });
  const cols = el("div", "tile-cols list-cols");
  ["Symbol / news", "Price", "Chg", "RVOL", "Float"].forEach(c => cols.appendChild(el("span", null, c)));
  tile.appendChild(cols);
  const body = el("div", "tile-rows");
  if (!ordered.length)
    body.appendChild(el("div", "empty", "No symbol currently meets all four technical pillars. An empty list is a real answer."));
  const prevKeys = state.prevRowKeys[id] || [];
  ordered.forEach((r, i) => {
    const sym = SYMS[r.symbol] || {};
    const tr = el("div", "trow list-row" + (state.selected === r.symbol ? " sel" : "") +
      (prevKeys.indexOf(r.symbol) === -1 && state.frame > 0 ? " fresh" : ""));
    tr.dataset.symbol = r.symbol; tr.setAttribute("role", "button"); tr.tabIndex = 0;
    const s = el("span", "tsym");
    s.appendChild(el("b", null, r.symbol));
    s.appendChild(flameFor(r.symbol, nowMs));
    if (sym.floatQuality && sym.floatQuality !== "verified")
      s.appendChild(el("span", "pill unknown", sym.floatQuality === "unknown" ? "?" : "proxy"));
    if (r.spread != null && r.price && r.spread / r.price > 0.01)
      s.appendChild(el("span", "pill warn", "sprd"));
    tr.appendChild(s);
    tr.appendChild(el("span", null, fx(r.price)));
    tr.appendChild(el("span", dirClass(r.changePct), pct(r.changePct)));
    tr.appendChild(el("span", null, fx(r.rvolDaily) + "×"));
    tr.appendChild(el("span", "muted", sym.floatShares ? (sym.floatShares / 1e6).toFixed(1) + "M" : "—"));
    tr.onclick = () => { toggleReasons(id, r.symbol); select(r.symbol, id, i); };
    tr.onkeydown = e => { if (e.key === "Enter") { select(r.symbol, id, i); e.preventDefault(); } };
    body.appendChild(tr);
    if (state.openRow === id + "|" + r.symbol) body.appendChild(reasonsDrawer(r, sym, id));
  });
  state.prevRowKeys[id] = ordered.map(r => r.symbol);
  tile.appendChild(body);
  if (pending) tile.appendChild(el("div", "pending",
    pending + " new candidate" + (pending > 1 ? "s" : "") + " waiting — unfreeze to apply"));
  return tile;
}

function reasonsDrawer(r, sym, listId) {
  const d = el("div", "reasons");
  const head = el("div", "reason");
  head.appendChild(el("span", "reason-name", "Why this row is here — " + (S.definitionVersions[listId] || listId)));
  d.appendChild(head);
  if (listId === "five_pillars_list") {
    pillarChecks(r, sym).forEach(c => {
      const row = el("div", "reason");
      row.appendChild(el("span", c.ok ? "ok" : "no", c.ok ? "PASS" : "FAIL"));
      row.appendChild(el("span", "reason-name", c.name));
      row.appendChild(el("span", null, String(c.v)));
      row.appendChild(el("span", "ev confirmed", "confirmed course"));
      d.appendChild(row);
    });
    const n = el("div", "reason");
    n.appendChild(el("span", "reason-name", "news / catalyst — displayed, never a gate (Confirmed platform)"));
    d.appendChild(n);
    [["gap %", pct(r.gapPct)], ["5m RVOL", fx(r.rvol5m) + "×"], ["5m volume", vol(r.volume5m)],
     ["volume", vol(r.volume)], ["position in range", r.rangePos != null ? (r.rangePos * 100).toFixed(0) + "%" : "—"],
     ["spread", "$" + fx(r.spread, 3)]].forEach(([lab, val]) => {
      const row = el("div", "reason");
      row.appendChild(el("span", "reason-name", lab));
      row.appendChild(el("span", null, String(val)));
      d.appendChild(row);
    });
  } else {
    const row = el("div", "reason");
    row.appendChild(el("span", "ok", "RANK"));
    row.appendChild(el("span", "reason-name", (S.listMeta[listId] || {}).metric + " — " + (S.listMeta[listId] || {}).note));
    row.appendChild(el("span", "ev approximation", "approximation"));
    d.appendChild(row);
  }
  return d;
}

function sessionOf(iso) {
  const hhmm = new Date(iso).toLocaleTimeString("en-US",
    { timeZone: "America/New_York", hour12: false, hour: "2-digit", minute: "2-digit" });
  return hhmm < "09:30" ? "PM" : hhmm < "16:00" ? "RTH" : "AH";
}
const BRANCH_SHORT = {
  low_float: "LF", medium_float: "MF", high_rvol: "HR", medium_rvol: "MR",
  price_20_plus: "20+", price_under_20: "<20",
};
function shortBranch(branch, scannerId) {
  if (!branch) return scannerId.replace(/_/g, " ").replace("running ", "run ");
  return branch.split("_").reduce((acc, _, i, parts) => acc, null) ||
    branch.replace(/low_float/, "LF").replace(/medium_float/, "MF")
          .replace(/high_rvol/, "HR").replace(/medium_rvol/, "MR")
          .replace(/price_20_plus/, "20+").replace(/price_under_20/, "<20")
          .replace(/_/g, "·");
}

function renderAlertTile(cfg, idx) {
  const all = alertsUpTo(idx).filter(a => cfg.scanners.indexOf(a.scannerId) >= 0).reverse().slice(0, 60);
  const tile = tileShell(cfg.id, cfg.title, "alert", "REPLAY", cfg.note);
  const cols = el("div", "tile-cols alert-cols");
  ["Time", "Symbol / news", "Price", "Chg", "Strategy"].forEach(c => cols.appendChild(el("span", null, c)));
  tile.appendChild(cols);
  const body = el("div", "tile-rows");
  if (!all.length) body.appendChild(el("div", "empty", "No events yet."));
  all.forEach(a => {
    const tr = el("div", "trow alert-row" + (state.selected === a.symbol ? " sel" : ""));
    tr.appendChild(el("span", "tl-time", etTime(a.sourceTime)));
    const mid = el("span", "tsym");
    mid.appendChild(el("b", null, a.symbol));
    // The alert carries the flame observed AT the alert, which is the honest
    // record even when the news feed caught up minutes later.
    const fl = el("i", "flame " + (a.news && a.news.flame ? a.news.flame : "none"));
    fl.title = a.news ? "news " + a.news.age_minutes + " min old at alert time" : "no headline at alert time";
    mid.appendChild(fl);
    const ses = sessionOf(a.sourceTime);
    mid.appendChild(el("span", "pill ses " + ses.toLowerCase(), ses));
    tr.appendChild(mid);
    tr.appendChild(el("span", null, fx(a.values && a.values.last)));
    tr.appendChild(el("span", dirClass(a.values && a.values.change_pct), pct(a.values && a.values.change_pct)));
    const br = el("span", "branch", shortBranch(a.branch, a.scannerId));
    br.title = (a.branch || a.scannerId).replace(/_/g, " ") + " — branch labels the alert, it is not the filter";
    tr.appendChild(br);
    tr.onclick = () => select(a.symbol, cfg.id);
    body.appendChild(tr);
  });
  tile.appendChild(body);
  return tile;
}

/* ── timeline ───────────────────────────────────────────────────────── */
function renderTimeline(idx) {
  const host = $("#timeline"); host.textContent = "";
  const all = alertsUpTo(idx).slice().reverse();
  $("#alertCount").textContent = all.length + " event" + (all.length === 1 ? "" : "s");
  if (!all.length) { host.appendChild(el("div", "empty", "No alerts yet in this replay.")); return; }
  all.slice(0, 60).forEach(a => {
    const row = el("div", "tl-row");
    row.appendChild(el("span", "tl-time", etTime(a.sourceTime)));
    const main = el("div", "tl-main");
    main.appendChild(el("span", "tl-sym", a.symbol));
    const nf = a.news && a.news.flame;
    if (nf) main.appendChild(el("i", "flame " + nf));
    main.appendChild(el("span", "tl-what", ((S.alertMeta[a.scannerId] || {}).title || a.scannerId) + (a.branch ? " · " + a.branch.replace(/_/g, " ") : "")));
    if (a.group && a.group.count > 1) main.appendChild(el("span", "more", "+" + (a.group.count - 1) + " more"));
    row.appendChild(main);
    row.appendChild(el("span", "sev " + a.severity, a.severity));
    row.onclick = () => {
      select(a.symbol, a.scannerId);
      state.openAlert = state.openAlert === a.eventId ? null : a.eventId;
      // Selecting a historical alert seeks the charts to that moment.
      const target = FRAMES.findIndex(f => f.ts === a.sourceTime || f.t * 1000 >= new Date(a.sourceTime).getTime());
      if (target >= 0) { state.frame = target; syncTransport(); }
      render();
    };
    host.appendChild(row);
    if (state.openAlert === a.eventId) host.appendChild(alertDetail(a));
  });
}
function alertDetail(a) {
  const d = el("div", "tl-detail");
  d.appendChild(el("div", "tiny muted", "definition " + a.definitionVersion + " · source " + a.sourceTime + " · observed " + a.observedTime));
  (a.reasons || []).forEach(r => {
    const row = el("div", "reason");
    row.appendChild(el("span", r.passed ? "ok" : "no", r.passed ? "PASS" : "FAIL"));
    row.appendChild(el("span", "reason-name", r.filter || r.field));
    row.appendChild(el("span", null, String(r.value) + (r.threshold != null ? " vs " + r.threshold : "")));
    row.appendChild(el("span", "ev " + (r.evidence || "approximation"), r.evidence || "approximation"));
    d.appendChild(row);
  });
  if (a.group && a.group.count > 1) {
    d.appendChild(el("div", "tiny muted", "consolidated with: " + a.group.also_triggered.join(", ") +
      " — every raw event is kept in history"));
  }
  return d;
}

/* ── context panels ─────────────────────────────────────────────────── */
function kv(host, lab, val, cls) {
  const r = el("div", "kv"); r.appendChild(el("span", "lab", lab));
  r.appendChild(el("span", cls || null, val)); host.appendChild(r);
}
function symbolRow(frame, sym) {
  for (const id of LIST_IDS.concat(["top_gainers", "top_relative_volume", "top_volume_5m", "top_gappers"])) {
    const found = (frame.lists[id] || []).map(rowObj).find(r => r.symbol === sym);
    if (found) return found;
  }
  return null;
}

function renderHeader(frame) {
  const sym = state.selected, meta = SYMS[sym] || {}, nowMs = new Date(frame.ts).getTime();
  const bars = barsUpTo(sym, frame.barIndex);
  const last = bars.length ? bars[bars.length - 1][4] : null;
  const chg = last && meta.prevClose ? (last / meta.prevClose - 1) * 100 : null;
  const hod = bars.length ? Math.max(...bars.map(b => b[2])) : null;
  const row = symbolRow(frame, sym);
  $("#symTicker").textContent = sym || "—";
  $("#symLock").hidden = !state.locked;
  const nf = newsFor(sym, nowMs), flameEl = $("#symFlame");
  flameEl.hidden = !(nf && nf.flame);
  if (nf && nf.flame) { flameEl.className = "flame " + nf.flame; flameEl.title = "news " + Math.round(nf.ageMin) + " min old"; }
  const stats = $("#symStats"); stats.textContent = "";
  const stat = (lab, val, cls) => { const s = el("div", "stat"); s.appendChild(el("span", "lab", lab)); s.appendChild(el("span", cls || null, val)); stats.appendChild(s); };
  stat("Last", fx(last)); stat("Change", pct(chg), dirClass(chg)); stat("HOD", fx(hod));
  stat("RVOL", row ? fx(row.rvolDaily) + "×" : "—");
  stat("5m RVOL", row ? fx(row.rvol5m) + "×" : "—");
  const halted = frame.halts && frame.halts[sym] === "halted";
  stat("Halt", halted ? "HALTED" : "trading", halted ? "down" : null);
  return { last, chg, hod, row, meta, nf, halted, sym };
}

function renderQuote(frame, ctx) {
  const { last, chg, row, meta, nf, halted } = ctx;
  const q = $("#quoteCard"); q.textContent = "";
  const grid = el("div", "qgrid");
  const wide = row && row.spread != null && row.price && row.spread / row.price > 0.01;
  kv(grid, "Last", fx(last));
  kv(grid, "Float", meta.floatShares ? (meta.floatShares / 1e6).toFixed(1) + "M" : "UNKNOWN",
     meta.floatQuality === "verified" ? null : "down");
  kv(grid, "Prev close", fx(meta.prevClose));
  kv(grid, "Float source", (meta.floatQuality || "unknown").replace(/_/g, " ").replace(" proxy", ""),
     meta.floatQuality === "verified" ? null : "down");
  kv(grid, "Change", pct(chg), dirClass(chg));
  kv(grid, "52w high", fx(meta.high52w));
  kv(grid, "Spread", row ? "$" + fx(row.spread, 3) : "—", wide ? "down" : null);
  kv(grid, "Avg volume", vol(meta.avgDailyVolume));
  kv(grid, "Range pos", row && row.rangePos != null ? (row.rangePos * 100).toFixed(0) + "%" : "—");
  kv(grid, "Halt", halted ? "HALTED" : "trading", halted ? "down" : null);
  q.appendChild(grid);
  q.appendChild(el("div", "divider", "catalyst"));
  if (nf) {
    q.appendChild(el("p", "headline", nf.item.headline));
    const g2 = el("div", "qgrid");
    kv(g2, "Published", etClock(nf.item.publishedAt));
    kv(g2, "Observed", etClock(nf.item.firstObservedAt));
    kv(g2, "Age", Math.round(nf.ageMin) + " min");
    kv(g2, "Flame", nf.flame || "none");
    q.appendChild(g2);
  } else {
    q.appendChild(el("div", "placeholder",
      "No qualifying headline observed. No flame does not disqualify a candidate — news is scored, never required."));
  }
  if (meta.floatQuality === "shares_outstanding_proxy")
    q.appendChild(el("div", "note warn",
      "Shares outstanding shown as an explicit proxy — not float. The supply pillar fails until a verified value exists."));
}

/* Level 2 — SIMULATED depth. No licensed depth feed is connected, so the
   ladder is generated deterministically from the replay snapshot (seeded by
   symbol + frame) purely to exercise the widget. Swap _depth() for a licensed
   feed adapter and the rest of the card is unchanged. */
function seeded(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return function () { h ^= h << 13; h >>>= 0; h ^= h >>> 17; h ^= h << 5; h >>>= 0; return h / 4294967296; };
}
function _depth(sym, frameIdx, price, spreadAbs, vol5m) {
  const rnd = seeded(sym + "|" + frameIdx);
  const tick = price >= 1 ? 0.01 : 0.001;
  const half = Math.max(tick, (spreadAbs || tick * 2) / 2);
  const base = Math.max(100, Math.round((vol5m || 20000) / 60));
  const side = dir => Array.from({ length: 8 }, (_, i) => {
    const lvl = price + dir * (half + i * tick);
    let size = Math.round(base * (0.35 + rnd() * 1.3));
    if (rnd() < 0.11) size *= 4 + Math.round(rnd() * 5);      // occasional wall
    return { price: Number(lvl.toFixed(price >= 1 ? 2 : 4)), size: size, mpid: ["ARCA","NSDQ","BATS","EDGX","MIAX"][Math.floor(rnd() * 5)] };
  });
  const bids = side(-1), asks = side(1);
  const median = a => a.map(x => x.size).sort((p, q) => p - q)[Math.floor(a.length / 2)];
  const mb = median(bids), ma = median(asks);
  bids.forEach(l => l.wall = l.size >= mb * 4);
  asks.forEach(l => l.wall = l.size >= ma * 4);
  const prints = Array.from({ length: 10 }, () => {
    const atAsk = rnd() > 0.45;
    return { price: Number((price + (atAsk ? half : -half)).toFixed(price >= 1 ? 2 : 4)),
             size: Math.round(base * (0.05 + rnd() * 0.6)), atAsk: atAsk };
  });
  return { bids: bids, asks: asks, prints: prints };
}
function renderL2(frame, ctx) {
  const host = $("#l2Card"); host.textContent = "";
  const { last, row, halted, sym } = ctx;
  if (last == null) { host.appendChild(el("div", "placeholder", "No quote yet.")); return; }
  if (halted) {
    host.appendChild(el("div", "halt-banner", "HALTED — the book is not a reliable picture during a halt, and a stop does not protect through a reopen."));
  }
  const book = _depth(sym, state.frame, last, row ? row.spread : null, row ? row.volume5m : null);
  const maxSize = Math.max(...book.bids.map(b => b.size), ...book.asks.map(a => a.size));
  const ladder = el("div", "ladder");
  ladder.appendChild(el("div", "ladder-head", "Bid")); ladder.appendChild(el("div", "ladder-head", "Size"));
  ladder.appendChild(el("div", "ladder-head", "Size")); ladder.appendChild(el("div", "ladder-head", "Ask"));
  for (let i = 0; i < 8; i++) {
    const b = book.bids[i], a = book.asks[i];
    const bp = el("div", "lp bid" + (i === 0 ? " inside" : ""), fx(b.price)); ladder.appendChild(bp);
    const bs = el("div", "ls bid" + (b.wall ? " wall" : ""));
    bs.appendChild(el("span", "bar", "")); bs.lastChild.style.width = (b.size / maxSize * 100) + "%";
    bs.appendChild(el("span", "n", String(b.size))); ladder.appendChild(bs);
    const as = el("div", "ls ask" + (a.wall ? " wall" : ""));
    as.appendChild(el("span", "bar", "")); as.lastChild.style.width = (a.size / maxSize * 100) + "%";
    as.appendChild(el("span", "n", String(a.size))); ladder.appendChild(as);
    ladder.appendChild(el("div", "lp ask" + (i === 0 ? " inside" : ""), fx(a.price)));
  }
  host.appendChild(ladder);
  const wall = book.asks.find(a => a.wall);
  if (wall) host.appendChild(el("div", "note warn", "Large offer resting at " + fx(wall.price) +
    " (" + wall.size + "). A seller above the trigger caps the move until it is consumed."));
  host.appendChild(el("div", "divider", "time & sales"));
  const tape = el("div", "tape");
  book.prints.forEach(p => {
    const r = el("div", "print " + (p.atAsk ? "up" : "down"));
    r.appendChild(el("span", null, fx(p.price)));
    r.appendChild(el("span", "n", String(p.size)));
    r.appendChild(el("span", "side", p.atAsk ? "ask" : "bid"));
    tape.appendChild(r);
  });
  host.appendChild(tape);
  host.appendChild(el("div", "note", "Simulated depth generated from the replay snapshot — not licensed market data. Level 2 shows resting orders; the tape shows what actually executed."));
}

/* Setup verdict — mirrors the bundled Pine dashboard rows, then applies the
   playbook GO / WAIT / PASS matrix. Education and planning only. */
function renderVerdict(frame, ctx) {
  const { last, chg, hod, row, meta, nf, halted, sym } = ctx;
  const host = $("#verdictCard"); host.textContent = "";
  const T = S.pillarThresholds;
  const plan = activePlan(sym, frame.t);
  const alerts = alertsUpTo(state.frame).filter(a => a.symbol === sym);
  const recent = alerts.filter(a => frame.t - Math.floor(new Date(a.sourceTime).getTime() / 1000) <= 300);
  const hodActive = recent.some(a => a.scannerId === "hod_momentum");
  const runActive = recent.some(a => a.scannerId.indexOf("running_up") === 0 || a.scannerId.indexOf("squeeze") === 0);

  const priceOk = last != null && last >= T.priceMin && last <= T.priceMax;
  const gainOk = (chg || 0) >= T.gainMinPct;
  const rvolOk = row && (row.rvolDaily || 0) >= T.rvolMin;
  const floatOk = meta.floatQuality === "verified" && meta.floatShares < T.floatMaxShares;
  const newsOk = !!nf;
  const technical = [priceOk, gainOk, rvolOk, floatOk].filter(Boolean).length;
  const momentumOk = row && (row.rvol5m || 0) >= 2;

  // GO / WAIT / PASS — playbook section 6.
  const blockers = [], waits = [];
  if (halted) blockers.push("Halted — no plan survives a reopen at an unknown price.");
  if (technical <= 2) blockers.push("Only " + technical + "/4 technical pillars; 3/5 or fewer is a normal reject.");
  const spreadShare = plan && row && row.spread ? row.spread / plan.riskShare : null;
  if (spreadShare != null && spreadShare > 0.35)
    blockers.push("Spread is " + (spreadShare * 100).toFixed(0) + "% of planned risk — the round trip eats the edge.");
  if (plan && plan.target > (meta.high52w || Infinity) && last < meta.high52w)
    blockers.push("52-week high at " + fx(meta.high52w) + " sits between entry and the 2R target.");
  if (plan && !plan.volumeOk)
    blockers.push("Pullback volume was heavier than the impulse — sellers, not a pause.");
  if (technical === 3) waits.push("3/4 technical pillars — one condition still missing.");
  if (!plan) waits.push("No confirmed first pullback yet; nothing to place a structural stop against.");
  if (plan && last != null && last > plan.entry + plan.riskShare)
    waits.push("Price is already more than 1R beyond the trigger — chasing here inverts the reward/risk.");
  if (!hodActive && !runActive) waits.push("No live momentum event in the last five minutes.");

  const verdict = blockers.length ? "PASS" : waits.length ? "WAIT" : "GO";
  const banner = el("div", "verdict-banner " + verdict.toLowerCase());
  banner.appendChild(el("b", null, verdict));
  banner.appendChild(el("span", null, verdict === "GO" ? "candidate and structure both check out"
    : verdict === "WAIT" ? "watch, do not enter yet" : "reject this candidate"));
  host.appendChild(banner);

  const why = el("div", "why");
  (blockers.length ? blockers : waits.length ? waits : ["Four pillars, a confirmed pullback, usable spread and 2R of room."]).forEach(r => {
    const x = el("div", "why-row");
    x.appendChild(el("span", "why-dot " + verdict.toLowerCase(), ""));
    x.appendChild(el("span", null, r));
    why.appendChild(x);
  });
  host.appendChild(why);

  const table = el("div", "verdict-table");
  const line = (label, value, status, cls) => {
    const r = el("div", "vrow");
    r.appendChild(el("span", "vlab", label));
    r.appendChild(el("span", "vval", value));
    r.appendChild(el("span", "vst " + (cls || (status ? "ok" : "no")), status === null ? "—" : (cls ? status : (status ? "PASS" : "FAIL"))));
    table.appendChild(r);
  };
  line("Price", fx(last), priceOk);
  line("Gain vs close", pct(chg), gainOk);
  line("Daily RVOL", row ? fx(row.rvolDaily) + "×" : "—", !!rvolOk);
  line("Float / supply", meta.floatShares ? (meta.floatShares / 1e6).toFixed(1) + "M" : "unknown", floatOk);
  line("News", newsOk ? "Observed" : "Manual check", newsOk);
  line("Technical score", technical + "/4", technical === 4);
  line("5m RVOL", row ? fx(row.rvol5m) + "×" : "—", !!momentumOk);
  line("HOD / Running", hodActive ? "HOD" : runActive ? "Running Up" : "None",
       hodActive || runActive ? "ACTIVE" : "WAIT", hodActive || runActive ? "ok" : "warn");
  line("Entry", plan ? fx(plan.entry) : "N/A", plan ? "ARMED" : "—", plan ? "ok" : "muted-st");
  line("Stop", plan ? fx(plan.stop) : "N/A", "pullback low", "muted-st");
  line("Target", plan ? fx(plan.target) : "N/A", plan ? plan.rewardMultiple.toFixed(1) + "R" : "—", "muted-st");
  host.appendChild(el("div", "divider", "pine dashboard mirror"));
  host.appendChild(table);

  renderSizing(plan, row);
}

/* Sizing lives outside the re-rendered card so the operator can type into it
   while the replay keeps running. The dollar risk is always theirs. */
function renderSizing(plan, row) {
  const out = $("#sizingOut"); out.textContent = "";
  const risk = Number(state.riskDollars);
  if (plan && risk > 0) {
    const reserve = row && row.spread ? row.spread : 0;
    const prudent = plan.riskShare + reserve;
    const shares = Math.floor(risk / prudent);
    kv(out, "Prudent risk / share", "$" + fx(prudent, 3));
    kv(out, "Shares", String(shares));
    kv(out, "Position value", "$" + (shares * plan.entry).toFixed(0));
    kv(out, "Planned loss", "$" + (shares * prudent).toFixed(2));
    out.appendChild(el("div", "note", "Shares = your risk ÷ (entry − stop + spread reserve), then capped by what the book can actually absorb."));
  } else if (plan) {
    out.appendChild(el("div", "note", "Enter your own dollar risk to size this plan. The app will not assume one for you."));
  } else {
    out.appendChild(el("div", "note", "No armed setup to size yet."));
  }
}

/* ── charts ─────────────────────────────────────────────────────────── */
const PANES = {};
function renderCharts(frame) {
  const sym = state.selected, meta = SYMS[sym] || {};
  const bars1 = barsUpTo(sym, frame.barIndex);
  const hod = bars1.length ? Math.max(...bars1.map(b => b[2])) : null;
  const openTs = OPEN_INDEX >= 0 ? FRAMES[OPEN_INDEX].t : null;
  const plan = activePlan(sym, frame.t);
  PANES.a.render(bars1, { vwap: true, ema9: true, ema20: true, hod: hod, plan: plan, openTs: openTs });
  PANES.b.render(agg(bars1, 5), { vwap: true, ema9: true, ema20: true, hod: hod, plan: plan, openTs: openTs });
  PANES.c.render(meta.dailyBars || [], { ema20: true, ema200: true, h52: meta.high52w });
}

/* ── selection ──────────────────────────────────────────────────────── */
function select(symbol, source, rowIndex) {
  if (!symbol || !SYMS[symbol]) return;
  state.selected = symbol;
  if (source) state.focusTile = source;
  if (rowIndex != null) state.focusRow = rowIndex;
  const url = new URL(location.href); url.searchParams.set("symbol", symbol);
  history.replaceState({}, "", url);
  render();
}
function toggleReasons(listId, symbol) {
  const key = listId + "|" + symbol;
  state.openRow = state.openRow === key ? null : key;
}

/* ── audio ──────────────────────────────────────────────────────────── */
let audioCtx = null;
function beep(severity) {
  if (!state.sound) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const o = audioCtx.createOscillator(), g = audioCtx.createGain();
    const freq = severity === "critical" ? 340 : severity === "high" ? 660 : 520;
    o.frequency.value = freq; o.type = "sine";
    g.gain.setValueAtTime(0.0001, audioCtx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.06, audioCtx.currentTime + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.22);
    o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + 0.24);
  } catch (e) { /* audio is a convenience; the visual alert always fires */ }
}

/* ── render ─────────────────────────────────────────────────────────── */
function render() {
  const frame = FRAMES[state.frame];
  if (!state.selected) state.selected = new URL(location.href).searchParams.get("symbol") || "ABCD";
  $("#clockET").textContent = etClock(frame.ts);
  $("#frameCounter").textContent = "frame " + (state.frame + 1) + "/" + FRAMES.length;
  const badge = $("#sessionBadge");
  badge.textContent = frame.session; badge.className = "badge " + frame.session;
  $("#feedText").textContent = "REPLAY";
  $("#feedAge").textContent = S.generatedFrom;
  const host = $("#tiles"); host.textContent = "";
  DOCK_ORDER.forEach(id => host.appendChild(
    LIST_IDS.indexOf(id) >= 0 ? renderListTile(id, frame) : renderAlertTile(ALERT_TILES[id], state.frame)));
  const ctx = renderHeader(frame);
  renderCharts(frame); renderQuote(frame, ctx); renderL2(frame, ctx);
  renderVerdict(frame, ctx); renderTimeline(state.frame);
}
function syncTransport() { $("#scrub").value = String(state.frame); }

/* ── transport ──────────────────────────────────────────────────────── */
let timer = null;
function tick() {
  if (state.frame >= FRAMES.length - 1) { pause(); return; }
  state.frame++;
  const fresh = FRAMES[state.frame].alerts;
  if (fresh.length) beep(fresh[0].severity);
  syncTransport(); render();
}
function play() {
  state.playing = true; $("#btnPlay").textContent = "❚❚ Pause";
  clearInterval(timer); timer = setInterval(tick, Math.max(60, 1000 / state.speed));
}
function pause() { state.playing = false; $("#btnPlay").textContent = "▶ Play"; clearInterval(timer); }

/* ── wiring ─────────────────────────────────────────────────────────── */
function init() {
  $("#sessionLabel").textContent = S.tradingDate + " · " + S.sessionId + " · deterministic replay";
  $("#disclaimer").textContent = S.disclaimer;
  const scrub = $("#scrub"); scrub.max = String(FRAMES.length - 1);
  scrub.oninput = () => { state.frame = Number(scrub.value); render(); };
  $("#btnPlay").onclick = () => state.playing ? pause() : play();
  $("#speed").onchange = e => { state.speed = Number(e.target.value); if (state.playing) play(); };
  document.querySelectorAll("[data-seek]").forEach(b => b.onclick = () => {
    if (b.dataset.seek === "open" && OPEN_INDEX >= 0) state.frame = OPEN_INDEX;
    if (b.dataset.seek === "alert") {
      const i = FRAMES.findIndex(f => f.alerts.length);
      if (i >= 0) state.frame = i;
    }
    syncTransport(); render();
  });
  const riskInput = $("#riskInput");
  riskInput.value = state.riskDollars;
  riskInput.oninput = e => {
    state.riskDollars = e.target.value;
    const frame = FRAMES[state.frame];
    renderSizing(activePlan(state.selected, frame.t), symbolRow(frame, state.selected));
  };
  $("#btnSound").onclick = () => {
    state.sound = !state.sound;
    $("#btnSound").setAttribute("aria-pressed", String(state.sound));
    $("#btnSound").textContent = (state.sound ? "🔔" : "🔇") + " Alerts";
    if (state.sound) beep("medium");
  };
  document.addEventListener("keydown", e => {
    if (e.target.matches("input,select,textarea")) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const rows = (FRAMES[state.frame].lists[state.focusTile] || []).map(rowObj);
    const k = e.key.toLowerCase();
    if (k === "j" || e.key === "ArrowDown") { state.focusRow = Math.min(rows.length - 1, state.focusRow + 1); if (rows[state.focusRow] && !state.locked) select(rows[state.focusRow].symbol, state.focusTile, state.focusRow); e.preventDefault(); }
    else if (k === "k" || e.key === "ArrowUp") { state.focusRow = Math.max(0, state.focusRow - 1); if (rows[state.focusRow] && !state.locked) select(rows[state.focusRow].symbol, state.focusTile, state.focusRow); e.preventDefault(); }
    else if (e.key === "Enter") { state.locked = !state.locked; render(); }
    else if (e.key === " ") { const id = state.focusTile; if (LIST_IDS.indexOf(id) >= 0) { state.frozen[id] = state.frozen[id] ? null : { order: rows.map(r => r.symbol) }; if (!state.frozen[id]) delete state.frozen[id]; render(); } e.preventDefault(); }
    else if (k === "n") { $("#quoteCard").scrollIntoView({ block: "center" }); }
    else if (k === "a") { $("#btnSound").click(); }
    else if (e.key === "Escape") { state.locked = false; state.openRow = null; state.openAlert = null; render(); }
  });
  PANES.a = makePane("chartA", false);
  PANES.b = makePane("chartB", false);
  PANES.c = makePane("chartC", true);
  const usingTV = PANES.a.engine === "tradingview";
  $("#chartEngine").textContent = usingTV ? "TRADINGVIEW" : "CANVAS";
  $("#chartEngineSub").textContent = usingTV ? "lightweight-charts 4.1.3" : "library unavailable — fallback";
  $("#chartDot").className = "dot " + (usingTV ? "live" : "stale");
  const ro = new ResizeObserver(() => {
    Object.values(PANES).forEach(p => p.resize());
    renderCharts(FRAMES[state.frame]);
  });
  ["chartA", "chartB", "chartC"].forEach(id => ro.observe(document.getElementById(id)));
  window.addEventListener("resize", () => {
    Object.values(PANES).forEach(p => p.resize());
    renderCharts(FRAMES[state.frame]);
  });
  state.frame = Math.max(0, OPEN_INDEX - 8);
  syncTransport(); render();
}
init();
})();
