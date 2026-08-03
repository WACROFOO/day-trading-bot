# Prompt: set up TradingView for paper trading (Claude Chrome extension)

Copy everything between the lines into the Claude Chrome extension with
TradingView open and logged in.

Written for a browser agent, so: explicit sequence, fallbacks for plan-gated
features, and a report-back at the end. Do not shorten it — the fallbacks are
what stop the agent from silently guessing.

---

I'm on TradingView and logged in. Set up my workspace for **paper trading** a
small-cap momentum day-trading strategy. Work through the tasks in order.
Don't skip ahead — later steps depend on earlier ones.

**Rules for this whole session:**
- This is PAPER trading only. Never connect a real broker, never place a real
  order, never enter payment details.
- If a feature is unavailable on my plan, don't work around it silently —
  note it and move on to the next task.
- After each numbered task, tell me in one line whether it succeeded.
- If a UI element isn't where I describe, look for the nearest equivalent and
  say what you actually clicked.

## Task 1 — Connect paper trading

1. Open a chart (`tradingview.com/chart`).
2. Open the **Trading Panel** at the bottom of the screen. If it's collapsed,
   there's a tab or an upward chevron along the bottom edge.
3. Find the broker list and select **Paper Trading**.
4. Connect it.
5. Look for a settings/reset option for the paper account and set the starting
   balance to **$600** if that's possible. If the balance isn't editable, leave
   it and tell me what it defaults to.

Report: is paper trading connected, and what is the account balance?

## Task 2 — Chart layout

1. Set the chart layout to **2×2** (four charts). The layout selector is in
   the top toolbar — a grid icon.
2. Set all four charts to symbol **FCUV**.
3. **Link all four charts** so changing the symbol on one changes all of them.
   This is usually a coloured circle/chain icon in each chart's top bar — set
   every pane to the same colour group.
4. Set the timeframes:
   - top-left: **10 seconds**
   - top-right: **1 minute**
   - bottom-left: **5 minutes**
   - bottom-right: **1 day**
5. If 10-second intervals are not available on my plan, set the top-left to
   **1 minute** instead and tell me the 10s interval was unavailable.

Report: which four timeframes are actually showing?

## Task 3 — Extended trading hours

For each of the three intraday panes (10s/1m, 1m, 5m) — **not** the daily:

1. Right-click the chart → **Settings** → **Symbol** tab.
2. Tick **Extended trading hours** (may be called "Extended hours" or "ETH").
3. Apply.

Pre-market data should now appear as a shaded region before 09:30 ET.

Report: is pre-market data visible on the intraday charts?

## Task 4 — Indicators

On the **1-minute** and **5-minute** charts, add:

- **VWAP** (Volume Weighted Average Price) — default settings
- **Moving Average Exponential**, length **9**
- **Moving Average Exponential**, length **20**
- **MACD** — default 12/26/9, do not change the settings
- **Volume** — if not already shown

On the **daily** chart, add:

- **Moving Average Simple**, length **200**
- **Volume**

Use the **Indicators** button in the top toolbar and search by name.

Report: list the indicators on each pane.

## Task 5 — Save the layout

Save the chart layout with the name **`MOMO`** (the save icon / cloud icon in
the top-right of the chart toolbar). Make it the default layout if there's an
option to.

Report: is the layout saved as MOMO?

## Task 6 — Watchlist

1. Open the watchlist panel (right sidebar).
2. Create a new watchlist called **`MOMO Watch`**.
3. Add these symbols: **FCUV**, **SCYX**, **REPL**.
4. Customise the watchlist columns to show, if available: **Last**,
   **Change %**, **Pre-market Change %**, **Pre-market Volume**, **Volume**,
   **Market Cap**.

Report: which columns were you able to add, and which weren't available?

## Task 7 — Screener 1: pre-market gappers

1. Open the **Stock Screener** (bottom panel tab, or `tradingview.com/screener`).
2. Set the market to **United States**.
3. Clear any existing filters, then add exactly these:
   - **Price** between **2** and **20**
   - **Pre-market Change %** greater than **10**
   - **Pre-market Volume** greater than **50000**
   - **Market Cap** less than **500M**
   - **Exchange**: NASDAQ, NYSE, AMEX only
4. Add these columns if available: Pre-market Change %, Pre-market Volume,
   Market Cap, Price, Gap %.
5. Sort by **Pre-market Change %**, descending.
6. Save the screen as **`PM Gappers`**.

If any pre-market filter or column isn't available on my plan, say so
explicitly and set up the rest.

Report: saved? which filters were unavailable?

## Task 8 — Screener 2: live momentum

Create a second saved screen, **`Live Momo`**, with:

- **Price** between **2** and **20**
- **Change %** greater than **10**
- **Relative Volume** greater than **5**
- **Volume** greater than **500000**
- **Change from Open %** greater than **0**
- **Market Cap** less than **500M**
- **Exchange**: NASDAQ, NYSE, AMEX

Sort by **Change %** descending. Save as `Live Momo`.

Report: saved?

## Task 9 — Screener 3: after-hours continuation

Create a third saved screen, **`AH Continuation`**, identical to `PM Gappers`
except swap the pre-market fields for **Post-market Change %** (greater than
10) and **Post-market Volume** (greater than 50000).

Report: saved?

## Task 10 — Final report

Give me a summary table:

| Task | Done? | Notes / what was unavailable |

Then tell me:
1. Anything that needs a paid plan that I don't have.
2. Whether a **Float** or **Shares Float** filter exists anywhere in the
   screener — search the filter list for it and tell me yes or no. This one
   matters to me, so check properly rather than assuming.
3. What the paper trading account balance is set to.

---

## After the agent finishes

Two things it cannot do for you:

- **Float per candidate.** If task 10 confirms there's no float filter, you
  check float manually on each of the 3–6 names that survive the screener.
  Market cap is not a substitute — FCUV's 702,811 shares would look ordinary
  on market cap alone.
- **Alerts.** Set these yourself once you have a plan for a specific name:
  right-click the chart at your trigger price → Add alert. The agent can't
  know your levels before you've written them.
