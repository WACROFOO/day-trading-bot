# web/

The browser desk: panes, tiles, cards and the verdict.

| File | What |
|---|---|
| `index.html` | the page skeleton and card layout |
| `app.js` | rendering, including `renderVerdict()` — the setup verdict |
| `live.js` | the live transport: draws stream events in place, swaps the session without a reload |
| `styles.css` | the desk's styling |
| `vendor/` | third-party chart library, served locally |

Nothing provider-side reaches this code: secrets stay server-side.
