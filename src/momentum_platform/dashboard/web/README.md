# web/

The browser desk: panes, tiles, cards and the verdict.

| File | What |
|---|---|
| `index.html` | the page skeleton and card layout |
| `app.js` | rendering, including `renderVerdict()` — the setup verdict |
| `live.js` | the live transport: draws stream events in place, swaps the session without a reload |
| `styles.css` | the desk's styling |
| `vendor/` | third-party chart library, served locally |

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
