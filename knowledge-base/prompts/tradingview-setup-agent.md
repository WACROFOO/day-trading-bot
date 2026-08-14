# Prompt: full TradingView workspace build (browser agent)

Copy everything between the horizontal lines into the browser agent with
TradingView open and logged in. Written for an agent, so: explicit sequence,
fallbacks for plan-gated features, and a report after every task. Do not
shorten it — the fallbacks are what stop the agent from silently guessing.

Updated 2026-08-13: full rebuild variant — resets the existing workspace
first, $100k paper account, session shading, the repo's reverse-split Pine
flag, screeners, alert presets and the final audit report.

---

I'm on TradingView and logged in. Rebuild my workspace from scratch for
**paper trading** a small-cap momentum day-trading strategy (Ross
Cameron-style: 1-minute pullbacks on low-float gappers, pre-market included).
I have an existing setup — I want it RESET and rebuilt exactly as below.
Work through the tasks strictly in order; later steps depend on earlier ones.

**Rules for the whole session — read first:**

- This is **PAPER trading only**. Never connect a real broker, never place a
  real order, never enter payment details, never open any billing, checkout
  or upgrade page. If a dialog asks for payment, close it and note it.
- If a feature is unavailable on my plan, do NOT work around it silently —
  write it down, apply the stated fallback, and continue.
- **After each numbered task, give me a one-line report:** `Task N: OK` or
  `Task N: PARTIAL/FAILED — what happened, what you clicked instead`.
- If a UI element isn't where I describe it, look for the nearest equivalent,
  use it, and say what you actually clicked.
- At the very end, produce the **final audit report** described in Task 12.
  Do not skip it.

## Task 0 — Inventory, then reset the existing workspace

1. Before deleting anything, list what currently exists: saved chart layouts
   (layout dropdown, top bar), saved screeners, watchlists, alerts, and
   indicator templates. Write this inventory into your report — it is my
   backup record.
2. Save the current chart layout under the name `OLD-backup-<today's date>`
   so nothing is truly lost.
3. Then reset: create a **new blank chart layout** named `ROSS-MOMO`. Do not
   modify the old layout again after this point.
4. Delete alerts only if the Alerts panel shows more than 20 — otherwise
   pause them all (right-click → Pause) and leave them.

Report: the inventory, the backup layout name, confirmation that `ROSS-MOMO`
is the active layout.

## Task 1 — Paper trading account

1. Open the **Trading Panel** (bottom edge of the chart page).
2. In the broker list choose **Paper Trading** and connect it.
3. Reset the paper account balance to **$100,000**: gear/settings icon inside
   the trading panel → look for "Reset account" or "Balance". If the balance
   is not editable, reset to whatever the default is and tell me the number.
4. In the same settings, if there is a confirmation setting for orders, turn
   **order confirmation ON** (I want the ticket to show before it fills).

Report: paper connected yes/no, balance, order-confirmation state.

## Task 2 — Chart layout: 4 panes, one symbol

1. Layout selector (grid icon, top bar) → **2×2**.
2. Set every pane to symbol **FGI** (yesterday's runner — a good test symbol
   because it has pre-market data, halts and a big range).
3. **Link all four panes** with the coloured link icon in each pane's corner —
   same colour group everywhere, so one symbol change updates all four.
4. Timeframes:
   - top-left: **10 seconds** — fallback if seconds are plan-gated: **1 minute**
   - top-right: **1 minute**
   - bottom-left: **5 minutes**
   - bottom-right: **1 day**
5. On each intraday pane, right-click → Settings → **Symbol** → tick
   **Extended trading hours (ext)**. The DAILY pane keeps extended hours OFF
   — daily candles must be regular-session only.

Report: the four timeframes actually showing, ext-hours state per pane.

## Task 3 — Session shading (pre-market / after-hours)

On each intraday pane: chart Settings → **Appearance** (or Canvas) → find
**Pre-market** and **Post-market** background colours.

- Pre-market background: a light warm yellow (dawn).
- Post-market background: a light cool blue (dusk).
- Keep regular hours default.

The point: the session boundary must be visible at a glance — a surge of
volume at 09:30 and the session ribbon must line up. If the colour pickers
aren't there, look under Settings → Sessions. If truly unavailable, add
"Session breaks" vertical lines instead and note it.

Report: which panes got shading, or the fallback used.

## Task 4 — Indicators, pane by pane

Add from the Indicators dialog (magnifying glass). Defaults unless stated.

**10-second pane (the entry):**
1. **VWAP** (Volume Weighted Average Price — the built-in, session-anchored)
2. **EMA 9** (Moving Average Exponential, length 9)
3. **EMA 20** (length 20)
4. Volume (usually already on; make sure it shows)

**1-minute pane (the pattern):**
1. VWAP
2. EMA 9, EMA 20
3. **MACD** — defaults **12/26/9**, do not customise
4. Volume with **volume MA** enabled (length 20) — the declining-volume tell

**5-minute pane (structure):**
1. VWAP
2. EMA 9, EMA 20
3. **SMA 200** (Moving Average Simple, length 200) — the level Ross plays
   bounces/rejections against intraday
4. MACD 12/26/9
5. Volume with volume MA

**Daily pane (the walls):**
1. **SMA 200** — below it is bearish context
2. Volume
3. No VWAP, no MACD on the daily.

Colour convention on every pane: EMA 9 = green, EMA 20 = orange, SMA 200 =
purple, VWAP = blue (its default). If a colour can't be set, defaults are
fine — say so.

Report: per pane, the list of indicators actually attached.

## Task 5 — The reverse-split flag (custom Pine script)

1. Open the **Pine Editor** (bottom toolbar).
2. Delete the template code and paste the script I give you at the end of
   this prompt (section "PINE SCRIPT").
3. Save as `reverse-split-flag`, then **Add to chart** while the DAILY pane
   is selected.
4. If the editor is unavailable, skip and note it.

Report: compiled yes/no, attached to the daily yes/no.

## Task 6 — Watchlist

1. Create a new watchlist named **`DAY`** (right sidebar, watchlist icon).
2. Add: **FGI, DFSC, LNSR, AIRO** (today's board; I overwrite this daily).
3. Create a second list named **`THEME`** — leave it empty; it will hold the
   running theme names (this week: cheap Chinese/HK tickers, penny runners).

Report: both lists exist, DAY has 4 symbols.

## Task 7 — Screener 1: PM Gappers (pre-market)

Open **tradingview.com/screener**. Market: United States. Build and save as
**`PM Gappers`**:

| filter | value |
|---|---|
| Price | between 2 and 20 |
| Pre-market Change % | greater than 10 |
| Pre-market Volume | greater than 50,000 |
| Market Cap | less than 500M |
| Exchange | NASDAQ, NYSE, AMEX |

Visible columns: Pre-market Change %, Pre-market Volume, Market Cap, Price.
Sort: Pre-market Change % **descending**. If pre-market fields are plan-gated,
build it with regular Change %/Volume, name it `PM Gappers (RTH fallback)`,
and flag this loudly in the report.

Report: saved yes/no, which fields were available.

## Task 8 — Screener 2: Live Momo (regular hours)

Same screener page, new screen, save as **`Live Momo`**:

| filter | value |
|---|---|
| Price | between 2 and 20 |
| Change % | greater than 10 |
| Relative Volume | greater than 5 |
| Volume | greater than 500,000 |
| Change from Open % | greater than 0 |
| Market Cap | less than 500M |

Sort by Relative Volume descending. Columns: Change %, Relative Volume,
Volume, Float (if the column exists — add it; if not, note that float must
be checked externally).

Report: saved yes/no, float column available yes/no.

## Task 9 — Screener 3: AH Continuation (evening)

Copy of screener 1 with **Post-market Change % > 5** and **Post-market
Volume > 50,000** instead of the pre-market fields. Save as
**`AH Continuation`**. Same fallback rule as Task 7.

Report: saved yes/no.

## Task 10 — Alert preset

1. On any chart, hover a price and press **Alt+A** to open the alert dialog.
2. Set: Condition = the symbol's **Price**, **Crossing Up**; Trigger =
   **Once only**; Notifications = **Show toast notification** + **Play
   sound** ON.
3. Open the preset icon (four squares + plus, top-right of the dialog) →
   **Save alert preset** → name it **`level-ping`** → include Condition,
   Trigger, Notifications. **Do NOT include Expiration in the preset** (it
   stores an absolute date and corrupts future alerts).
4. Cancel the dialog without creating the alert itself.

Report: preset saved yes/no.

## Task 11 — Order ticket defaults

1. Open the order ticket on FGI (Trading Panel → Buy/Sell, or right-click
   the chart → Trade). **Do not send any order.**
2. Set the default order type to **Limit**.
3. Time in force: **Day**.
4. Find **"Fill order outside RTH"** — leave it **unchecked** by default, but
   confirm the checkbox exists (I tick it manually on deliberate pre-market
   trades; extended-hours orders must be limit anyway).
5. If there is a default-quantity setting, set it to **100** (I size each
   trade manually: shares = risk ÷ (entry − stop); the Risk-USD field in the
   Exits section is a cross-check, never an input).
6. Close the ticket WITHOUT placing anything.

Report: defaults set, checkbox located, confirmation that nothing was sent.

## Task 12 — FINAL AUDIT REPORT (mandatory)

Produce a single structured report:

```
WORKSPACE AUDIT — <date, time ET>
1  Backup:        OLD layout saved as <name>   inventory: <n layouts, n screeners, n alerts>
2  Paper account: connected <yes/no> · balance $<n> · confirmations <on/off>
3  Layout ROSS-MOMO: 10s <ok/fallback 1m> | 1m | 5m | daily · linked <yes/no>
4  Ext hours:     10s <on> 1m <on> 5m <on> daily <off>
5  Shading:       PM <colour/fallback> · AH <colour/fallback>
6  Indicators:    per pane, as attached (list)
7  Pine flag:     compiled <yes/no> · on daily <yes/no>
8  Watchlists:    DAY (4) · THEME (0)
9  Screeners:     PM Gappers <full/fallback> · Live Momo · AH Continuation
10 Alert preset:  level-ping <saved/no>
11 Order ticket:  limit/Day · outside-RTH box <found/not found> · nothing sent
LIMITATIONS HIT:  <every plan-gated feature, with the fallback used>
```

Anything in LIMITATIONS is not a failure — it's information I need. What I
never want is a silent workaround.

## PINE SCRIPT (for Task 5)

```pine
//@version=5
indicator("reverse-split-flag", overlay=true)
// Flags days where history smells split-adjusted: 52w high >20x current
// close, or a raw daily gap ratio that is a clean integer >=2.
ratio = ta.highest(high, 252) / close
gapR = close[1] / open
cleanInt = math.abs(gapR - math.round(gapR)) < 0.02 and math.round(gapR) >= 2
bgcolor(ratio > 20 ? color.new(color.red, 85) : na)
plotshape(cleanInt, style=shape.labeldown, color=color.red,
     text="SPLIT?", textcolor=color.white, location=location.abovebar)
```

---

End of prompt.
