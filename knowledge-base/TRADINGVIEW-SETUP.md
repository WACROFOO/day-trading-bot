# Setting up the screeners in TradingView

Three screens, matching the three jobs his own setup does: find the pre-market
gappers, watch what is running live, and check the after-hours continuation for
tomorrow. Plus the chart layout.

**Read the limitations section first** — one of the five pillars cannot be
screened pre-market in TradingView at all, and knowing that up front changes
how you use screen 1.

---

## Screen 1 — Pre-market gappers (run at 13:00 France)

**Screener → Stock Screener** (or `tradingview.com/screener`). Set the market
to **United States**, then **Filters**:

| Filter | Setting | Pillar |
|---|---|---|
| Price | between **2** and **20** | 1 |
| Pre-market Change % | greater than **10** | 5 |
| Pre-market Volume | greater than **50000** | interest |
| Market Cap | less than **500M** | 2 (proxy — see below) |
| Exchange | NASDAQ, NYSE, AMEX | quality |

Sort by **Pre-market Change %** descending. Save with the **⋮ menu → Save
screen** as `PM Gappers`.

Add these as visible columns so you can judge without opening each chart:
Pre-market Change %, Pre-market Volume, Market Cap, Price, Gap %.

## Screen 2 — Live momentum (run 15:35–17:30)

This is the one that works properly, because relative volume is computed
during regular hours.

| Filter | Setting | Pillar |
|---|---|---|
| Price | between **2** and **20** | 1 |
| Change % | greater than **10** | 5 |
| **Relative Volume** | greater than **5** | 4 |
| Volume | greater than **500000** | 4 |
| Change from Open % | greater than **0** | 5 (still rising) |
| Market Cap | less than **500M** | 2 |

Save as `Live Momo`. This is the closest equivalent to his "high of day
momentum scanner". Sort by Change % or Relative Volume.

## Screen 3 — After-hours continuation (run after 22:00)

Same as screen 1 but swap the pre-market fields for **Post-market Change %**
and **Post-market Volume**. This is the screen that produces tomorrow's watch
list — it is where he starts his Sunday videos, and it is what showed FCUV
running to $18.32 after the bell on 2026-07-31 when the regular close looked
weak.

Save as `AH Continuation`.

---

## Limitations you need to know about

**1. Relative volume does not exist pre-market.** TradingView states it
plainly: *"Relative Volume is not calculated during Extended hours, only
during regular trading sessions."* So pillar 4 cannot be screened at 13:00.
Workarounds:

- Use raw **Pre-market Volume** as the proxy and judge it against the stock's
  normal daily volume by eye (open the chart, look at the volume bars).
- Or use **Relative Volume at Time**, which compares a bar to the same clock
  slot on the previous 10 days — but it only works on 5-minute bars and
  regular hours.
- Or accept that screen 1 finds candidates and screen 2 confirms them after
  the open. This is the honest answer and probably the right one.

**2. Float is the weak point.** TradingView's fundamentals are built around
market cap and shares outstanding, not free float, and float is pillar 2 —
arguably the most important one for squeeze mechanics. `Market Cap < 500M` is
a crude proxy that will let through names with 60M+ floats.

Check float per candidate on a dedicated source before trading it. There are
only ever 3–6 names to check, so this is a 2-minute job, not a screening
problem. FCUV's 702,811 shares would never have shown up as remarkable on
market cap alone.

**3. Extended-hours data is plan-gated.** Pre/post-market columns and
seconds-based charts are not on the free tier. Check what your plan includes
before building screen 1 — if extended-hours data is not available to you,
screen 2 alone is still usable and covers the whole tradeable window.

**4. Seconds charts.** Our research found his actual entries happen on a
**10-second chart** (`research/momentum-replication/reports/2026-08-streams-roundup.md` §1).
TradingView offers second-based intervals on higher plans. If yours has them,
add a 10s chart to the layout — that is the timeframe the entry actually
lives on, and a 1-minute chart cannot show it.

---

## Chart layout

Four charts, one symbol, synced (open a chart → layout selector → **2x2**,
then link all four to the same symbol with the coloured link icon):

| Pane | Timeframe | Purpose |
|---|---|---|
| 1 | **10-second** (or 1m if unavailable) | the entry |
| 2 | **1-minute** | the pattern |
| 3 | **5-minute** | structure and levels |
| 4 | **Daily** | overhead resistance, the 200 MA |

Indicators on the intraday panes:

- **VWAP** (Volume Weighted Average Price)
- **EMA 9** and **EMA 20**
- **MA 200** on the 5-minute and daily
- **MACD** — default 12/26/9, no custom settings
- Volume, with the average-volume line shown

Enable **Settings → Symbol → Extended trading hours** on the intraday panes,
or the pre-market action will be invisible.

Save the layout so it reloads each morning.

---

## Alerts instead of staring

Right-click a screener row → **Add alert**, or set them per-chart. Two worth
having:

- price crossing your planned trigger level, on each watchlist name
- price crossing back below your stop level

Alerts are the mechanism that lets you write the plan at 15:00 and then stop
watching — which is the discipline the daily routine is built around.

---

## What this does not replace

His own scanners are a paid product and are tuned for exactly this strategy.
This TradingView build gets you four of the five pillars reliably and the
fifth (float) by manual check. That is enough to practise on, and the manual
float check is arguably a feature while you are learning: it forces you to
look at each candidate rather than trusting a row in a table.

Sources: TradingView
[filter calculations](https://www.tradingview.com/support/solutions/43000635852-how-are-the-most-popular-filters-calculated/),
[relative volume](https://www.tradingview.com/support/solutions/43000635874-how-do-we-calculate-relative-volume-and-relative-volume-at-time/).
