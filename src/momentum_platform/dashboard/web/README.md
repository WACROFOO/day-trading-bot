# web/

The browser desk: panes, tiles, cards and the verdict.

| File | What |
|---|---|
| `index.html` | the page skeleton and card layout |
| `app.js` | rendering, including `renderVerdict()` — the setup verdict |
| `live.js` | the live transport: draws stream events in place, swaps the session without a reload |
| `styles.css` | the desk's styling |
| `chartTools.js` | drawing tools and the indicator menu — Lightweight Charts ships neither |
| `levels.js` | support/resistance and trend lines ported from this project's `knowledge-base/tradingview/ross-fp-v4.pine`, the volume profile, the prior day's levels and the whole / half dollars — pure arithmetic on bars, checked in node (`tests/test_chart_levels.py`) |
| `vendor/` | third-party chart library, served locally |

## Tools on the desk's own panes

TradingView's Advanced Charting Library has 110+ drawing tools and 100+
indicators, and its licence is company-only and public-project-only, so this
desk cannot use it. `chartTools.js` draws the five that a momentum desk
actually uses — level, trend line, measure, zone, erase — on a canvas over the
pane, anchored to (time, price) so they survive zoom, pan and new candles.

Two rules in it are not cosmetic:

- **the drawing canvas is transparent to the mouse until a tool is picked.**
  Otherwise it eats the crosshair, the zoom and the pan.
- **drawings belong to one symbol and one timeframe.** A level drawn on one
  stock reappearing on another is worse than no level at all.

The measure tool reports the move in **R** as well as in $ and %, because R is
the unit every decision here is made in and no charting package can compute it:
it needs the plan's risk per share, which only this desk knows.

The `ƒ` button on each pane toggles volume, VWAP, the 9/20/200 EMAs, MACD,
the high of day and the plan levels, stored per pane.

## Older candles, levels and the TradingView look (2026-10-13)

- **Older candles.** The intraday panes hold the sessions before today: the previous one as
  soon as a name is shown, one more each time the chart is dragged past its oldest bar — from
  IBKR through `../chart_history.py`, on its own client. The daily pane loads older years the
  same way. Every indicator is computed per session from 04:00 ET, as the gates compute today's,
  so today's lines are the gates' own and no gate ever sees an older bar.
- **Levels** (ƒ → *Support / resistance (ross-fp-v4) · prior day · $ levels*, on by default on
  the 1- and 5-minute): the S/R fan of our own TradingView strategy, ported line for line —
  R1 R2 above, S1 S2 below the live price from each pane's own swings, the nearest each side a
  band — each labelled with its swings and `vol N×`, the volume traded there against the
  average; the prior day's high, low and close; the whole and half dollars either side.
  **Places to watch, never signals**: whether price turns at them is not measured.
- **Trend lines** (ƒ → *Trend lines · breakouts (ross-fp-v4)*, on by default on the 1- and
  5-minute): the Pine's V9.10 tangents under today's higher lows and over its lower highs. They
  never cut a confirmed bar, so only live price crosses them, and the label says so at once:
  `downtrend BROKEN ▲`, `uptrend LOST ▼`.
- **Volume profile** (ƒ → *Volume profile · visible range*, on by default on the 5-minute):
  volume by price over the bars in view, with the settings of the corpus's volume-profile class
  (24 rows, value area 70 %, up versus down, point of control in red), built from one-minute
  bars.
- **The look.** TradingView's dark background with a visible grid; MACD in its own pane with
  its own scale, one time axis under both; the date on the axis where a session starts; the
  extended hours tinted for every session. The values legend stays off (owner, 2026-10-02) —
  ƒ → *Values* brings it back.
- **Handling.** The wheel over the price axis (or ⌥ / Alt + wheel on the chart) zooms the
  price; a double-click on the axis restores it. The bare wheel zooms time around the newest
  bar. **»** returns a pane to its newest bar, and a pane is never left showing mostly empty
  future. Only the pane under the pointer drives the shared time axis of the price and MACD
  panes; a live tick redraws one point a series, and nothing redraws when no bar changed.

A Pine script cannot run here: Pine runs inside TradingView's own charts, and this desk draws
with Lightweight Charts. The levels and lines above are a port of ours; a test reads the Pine
file's own numbers and fails if the two drift apart.

## Which chart is which

Two different kinds of chart live on this page, and only one of them is the
desk's:

- **`chart-1m`, `chart-5m`, `chart-10s`, `chart-daily`** — drawn here, from the
  IBKR stream the runner trades on (market data type 1, real time), with
  TradingView's Lightweight Charts vendored under `vendor/`. These are the
  default panes: 1-minute large on top, 5-minute and 10-second beneath.
- **`tv-widget`, `tv-widget-5m`** — TradingView's own page in an iframe, on the
  viewer's tradingview.com entitlement. Useful for their drawing tools; **its
  data is not the desk's** and may be delayed. They wait in the tray.

They held the two big slots until 2026-09-18, when the owner found them
showing candles fifteen minutes behind the tape the runner was deciding on.
A card carrying a different price from the desk's is worse than no card.

Nothing provider-side reaches this code: secrets stay server-side.
