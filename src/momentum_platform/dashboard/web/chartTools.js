/* Drawing tools and an indicator menu for a Lightweight Charts pane.
   ---------------------------------------------------------------------------
   Lightweight Charts is a renderer, not a charting application: it ships no
   drawing tools and no indicator menu. TradingView's Advanced Charting Library
   has both, but its licence is company-only and public-project-only, so it is
   not available to this desk. These are the five tools that actually get used
   on a momentum desk, drawn on a canvas over the pane:

     level     a horizontal price line — HOD, pre-market high, a whole dollar
     trend     a two-point line
     measure   drag a box: move in $, in %, in bars, and in R
     zone      a rectangle over a consolidation
     erase     click a drawing to remove it

   The measure tool reports R because that is the unit every decision on this
   desk is made in, and no charting package computes it: it needs the plan's
   risk per share, which only this desk knows.

   Drawings are stored per symbol and timeframe in localStorage, so a level
   marked on the 1-minute chart is still there after a reload — and does NOT
   follow you to another symbol, which is the mistake that makes a drawn level
   dangerous.

   COORDINATES. A drawing is anchored to (time, price), never to pixels, so it
   stays on the bar it was drawn against through zoom, pan and new candles.
   The conversion is the chart's own: timeScale().timeToCoordinate and
   series.priceToCoordinate. A point scrolled out of view returns null and is
   simply not painted that frame. */

(function (global) {
  "use strict";

  const TOOLS = [
    { id: "cursor", glyph: "⌖", title: "Cursor — pan and zoom (Esc)" },
    { id: "level", glyph: "─", title: "Horizontal level — one click" },
    { id: "trend", glyph: "╱", title: "Trend line — click, then click" },
    { id: "measure", glyph: "▭", title: "Measure — drag: $, %, bars, R" },
    { id: "zone", glyph: "▨", title: "Zone — drag a rectangle" },
    { id: "erase", glyph: "⌫", title: "Erase — click a drawing" },
  ];
  const COLORS = { level: "#ffc247", trend: "#7fd1ff", zone: "rgba(41,98,255,.13)",
                   zoneEdge: "#2962ff", up: "#2ad17f", down: "#ff5f6e", ink: "#cfe0ff" };
  const HIT = 6;               // px: how close a click must be to erase a drawing

  function storeKey(paneKey, symbol, tf) {
    return "momentum-workstation.draw.v1." + paneKey + "." + (symbol || "?") + "." + (tf || "?");
  }
  function load(paneKey, symbol, tf) {
    try { return JSON.parse(localStorage.getItem(storeKey(paneKey, symbol, tf)) || "[]"); }
    catch (e) { return []; }   // private window, cleared storage: draw nothing, never throw
  }
  function save(paneKey, symbol, tf, items) {
    try { localStorage.setItem(storeKey(paneKey, symbol, tf), JSON.stringify(items)); }
    catch (e) { /* storage full or blocked: the drawing still works this session */ }
  }

  /* Attach tools to one pane. `chart` and `series` are the Lightweight Charts
     objects; `host` is the .chart-host element; `paneKey` distinguishes the
     1m / 5m / 10s / daily panes so their drawings do not collide. */
  function attach(chart, series, host, paneKey) {
    const canvas = document.createElement("canvas");
    canvas.className = "draw-layer";
    host.appendChild(canvas);
    const bar = document.createElement("div");
    bar.className = "draw-bar";
    host.appendChild(bar);

    let tool = "cursor", items = [], pending = null, hover = null;
    let symbol = null, tf = null, riskShare = null;

    TOOLS.forEach(t => {
      const b = document.createElement("button");
      b.className = "draw-btn" + (t.id === "cursor" ? " on" : "");
      b.textContent = t.glyph; b.title = t.title; b.dataset.tool = t.id;
      b.addEventListener("click", e => { e.stopPropagation(); setTool(t.id); });
      bar.appendChild(b);
    });
    const clearBtn = document.createElement("button");
    clearBtn.className = "draw-btn wipe"; clearBtn.textContent = "✕";
    clearBtn.title = "Remove every drawing on this symbol and timeframe";
    clearBtn.addEventListener("click", e => {
      e.stopPropagation();
      items = []; save(paneKey, symbol, tf, items); paint();
    });
    bar.appendChild(clearBtn);

    function setTool(id) {
      tool = id; pending = null;
      bar.querySelectorAll(".draw-btn").forEach(b =>
        b.classList.toggle("on", b.dataset.tool === id));
      // In cursor mode the canvas must not exist as far as the mouse is
      // concerned, or zoom and pan stop working.
      canvas.style.pointerEvents = id === "cursor" ? "none" : "auto";
      canvas.style.cursor = id === "erase" ? "not-allowed" : id === "cursor" ? "default" : "crosshair";
      paint();
    }
    document.addEventListener("keydown", e => { if (e.key === "Escape") setTool("cursor"); });

    /* -- coordinates ------------------------------------------------------ */
    const x = t => { try { return chart.timeScale().timeToCoordinate(t); } catch (e) { return null; } };
    const y = p => { try { return series.priceToCoordinate(p); } catch (e) { return null; } };
    const toTime = px => { try { return chart.timeScale().coordinateToTime(px); } catch (e) { return null; } };
    const toPrice = py => { try { return series.coordinateToPrice(py); } catch (e) { return null; } };
    function at(e) {
      const r = canvas.getBoundingClientRect();
      const px = e.clientX - r.left, py = e.clientY - r.top;
      return { px, py, t: toTime(px), price: toPrice(py) };
    }

    /* -- painting --------------------------------------------------------- */
    function paint() {
      const w = host.clientWidth, h = host.clientHeight;
      const dpr = global.devicePixelRatio || 1;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
        canvas.style.width = w + "px"; canvas.style.height = h + "px";
      }
      const g = canvas.getContext("2d");
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, w, h);
      g.font = '10px "IBM Plex Mono", ui-monospace, monospace';
      items.forEach((d, i) => drawOne(g, d, w, h, i === hover));
      if (pending && pending.b) drawOne(g, pending, w, h, false);
    }

    function drawOne(g, d, w, h, hot) {
      g.save();
      g.lineWidth = hot ? 2.5 : 1.5;
      if (d.kind === "level") {
        const py = y(d.a.price);
        if (py == null) { g.restore(); return; }
        g.strokeStyle = COLORS.level;
        g.setLineDash([5, 3]);
        g.beginPath(); g.moveTo(0, py); g.lineTo(w, py); g.stroke();
        label(g, d.a.price.toFixed(2), 4, py - 3, COLORS.level);
      } else if (d.kind === "trend" && d.b) {
        const x1 = x(d.a.t), y1 = y(d.a.price), x2 = x(d.b.t), y2 = y(d.b.price);
        if (x1 == null || x2 == null || y1 == null || y2 == null) { g.restore(); return; }
        g.strokeStyle = COLORS.trend;
        g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
      } else if (d.kind === "zone" && d.b) {
        const box = rect(d);
        if (!box) { g.restore(); return; }
        g.fillStyle = COLORS.zone; g.strokeStyle = COLORS.zoneEdge;
        g.fillRect(box.x, box.y, box.w, box.h);
        g.strokeRect(box.x, box.y, box.w, box.h);
      } else if (d.kind === "measure" && d.b) {
        const box = rect(d);
        if (!box) { g.restore(); return; }
        const up = d.b.price >= d.a.price;
        const col = up ? COLORS.up : COLORS.down;
        g.fillStyle = (up ? "rgba(42,209,127,.10)" : "rgba(255,95,110,.10)");
        g.strokeStyle = col;
        g.fillRect(box.x, box.y, box.w, box.h);
        g.strokeRect(box.x, box.y, box.w, box.h);
        measureLabel(g, d, box, col);
      }
      g.restore();
    }
    function rect(d) {
      const x1 = x(d.a.t), y1 = y(d.a.price), x2 = x(d.b.t), y2 = y(d.b.price);
      if (x1 == null || x2 == null || y1 == null || y2 == null) return null;
      return { x: Math.min(x1, x2), y: Math.min(y1, y2),
               w: Math.abs(x2 - x1), h: Math.abs(y2 - y1) };
    }
    function label(g, text, px, py, colour) {
      const wd = g.measureText(text).width + 6;
      g.fillStyle = "rgba(11,17,25,.85)";
      g.fillRect(px, py - 10, wd, 12);
      g.fillStyle = colour; g.fillText(text, px + 3, py);
    }
    /* The measure read-out. R is the point of it: a 12-cent move means nothing
       until you know the stop is 6 cents away. When no plan is live the R line
       is omitted rather than computed against a guess. */
    function measureLabel(g, d, box, col) {
      const move = d.b.price - d.a.price;
      const pctMove = d.a.price ? move / d.a.price * 100 : 0;
      const lines = [
        (move >= 0 ? "+" : "") + move.toFixed(3) + "  " + (pctMove >= 0 ? "+" : "") + pctMove.toFixed(2) + "%",
      ];
      if (riskShare && riskShare > 0) lines.push((move / riskShare).toFixed(2) + " R");
      const wd = Math.max.apply(null, lines.map(s => g.measureText(s).width)) + 10;
      const bx = box.x + box.w + 4, by = box.y + Math.max(0, box.h / 2 - 8);
      g.fillStyle = "rgba(11,17,25,.92)";
      g.fillRect(bx, by, wd, 12 * lines.length + 4);
      g.fillStyle = col;
      lines.forEach((s, i) => g.fillText(s, bx + 5, by + 11 + i * 12));
    }

    /* -- hit testing, for the eraser -------------------------------------- */
    function hitIndex(p) {
      for (let i = items.length - 1; i >= 0; i--) {
        const d = items[i];
        if (d.kind === "level") {
          const py = y(d.a.price);
          if (py != null && Math.abs(py - p.py) <= HIT) return i;
        } else if (d.b) {
          const box = rect(d);
          if (!box) continue;
          if (d.kind === "trend") {
            const x1 = x(d.a.t), y1 = y(d.a.price), x2 = x(d.b.t), y2 = y(d.b.price);
            if (x1 != null && pointToSegment(p.px, p.py, x1, y1, x2, y2) <= HIT) return i;
          } else if (p.px >= box.x - HIT && p.px <= box.x + box.w + HIT &&
                     p.py >= box.y - HIT && p.py <= box.y + box.h + HIT) return i;
        }
      }
      return -1;
    }
    function pointToSegment(px, py, x1, y1, x2, y2) {
      const dx = x2 - x1, dy = y2 - y1;
      const len2 = dx * dx + dy * dy;
      const t = len2 ? Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / len2)) : 0;
      return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
    }

    /* -- input ------------------------------------------------------------ */
    canvas.addEventListener("mousedown", e => {
      if (tool === "cursor") return;
      const p = at(e);
      if (tool === "erase") {
        const i = hitIndex(p);
        if (i >= 0) { items.splice(i, 1); save(paneKey, symbol, tf, items); paint(); }
        return;
      }
      if (p.price == null) return;
      if (tool === "level") {
        items.push({ kind: "level", a: { t: p.t, price: p.price } });
        save(paneKey, symbol, tf, items); setTool("cursor"); paint(); return;
      }
      pending = { kind: tool, a: { t: p.t, price: p.price }, b: null };
    });
    canvas.addEventListener("mousemove", e => {
      if (tool === "cursor") return;
      const p = at(e);
      if (pending) {
        if (p.t == null || p.price == null) return;
        pending.b = { t: p.t, price: p.price };
        paint();
      } else if (tool === "erase") {
        const i = hitIndex(p);
        if (i !== hover) { hover = i; paint(); }
      }
    });
    canvas.addEventListener("mouseup", () => {
      if (!pending) return;
      // A click with no drag is not a drawing; it is a misfire.
      if (pending.b) { items.push(pending); save(paneKey, symbol, tf, items); }
      pending = null;
      setTool("cursor");
    });
    canvas.addEventListener("mouseleave", () => { hover = null; paint(); });

    chart.timeScale().subscribeVisibleLogicalRangeChange(paint);

    return {
      /* The pane calls this on every render. A symbol change swaps the stored
         drawings: a level drawn on one stock must never appear on another. */
      sync(nextSymbol, nextTf, plan) {
        riskShare = plan && plan.riskShare ? plan.riskShare : null;
        if (nextSymbol !== symbol || nextTf !== tf) {
          symbol = nextSymbol; tf = nextTf;
          items = load(paneKey, symbol, tf);
          pending = null;
        }
        paint();
      },
      repaint: paint,
      hasDrawings() { return items.length > 0; },
    };
  }

  global.ChartTools = { attach, TOOLS };
})(window);
