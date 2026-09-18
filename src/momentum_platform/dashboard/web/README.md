# web/

The browser desk: panes, tiles, cards and the verdict.

| File | What |
|---|---|
| `index.html` | the page skeleton and card layout |
| `app.js` | rendering, including `renderVerdict()` — the setup verdict |
| `live.js` | the live transport: draws stream events in place, swaps the session without a reload |
| `styles.css` | the desk's styling |
| `chartTools.js` | drawing tools and the indicator menu — Lightweight Charts ships neither |
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
