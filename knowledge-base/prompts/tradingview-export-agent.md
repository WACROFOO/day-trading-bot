# Prompt: export everything exportable out of TradingView

Copy everything between the lines into the Claude Chrome extension with
TradingView open and logged in.

The point of this run is **chart data**, not the layout. See "What is actually
worth exporting" below for why.

---

I'm on TradingView and logged in with a Premium plan. I want to export data out
of it. Work through the tasks in order and report what each one produced.

**Rules for this whole session:**
- This is PAPER trading only. Never connect a real broker, never place a real
  order, never enter payment details, never open billing or checkout pages.
- Do not change any chart setting except where a task says to. In particular do
  not change symbols, intervals, or indicators on my saved layout without
  telling me — I will need it back the way it was.
- If a feature does not exist on my plan, say so explicitly. Do not improvise a
  substitute silently.
- After each numbered task, tell me in one line whether it succeeded and what
  file it produced.

## Task 1 — Confirm the chart data export exists

1. Open my saved `MOMO` chart layout.
2. Right-click anywhere on the price area of one chart pane.
3. Look for **"Export chart data…"** in the context menu. If it is not there,
   check the top toolbar's `⋮` / "Manage layouts" menu and the camera/share
   icon group.
4. Open the dialog but **do not export yet**. Tell me exactly what options it
   offers — I expect a time-format choice and possibly a choice of which
   indicators to include.

Report: does the option exist, and what does the dialog offer?

## Task 2 — The one that matters: a 10-second chart export

Do this for **one** symbol first so we can check the file before repeating it.

1. Pick the most active small-cap gapper on today's `PM Gappers` or `Live Momo`
   screen. If neither has anything, tell me and use **CUPR** instead.
2. Set one chart pane to that symbol at the **10 second** interval.
3. Turn on **Settings → Symbol → Extended trading hours** so pre-market bars
   are included.
4. Add **VWAP** to that pane if it is not already there. This matters — I want
   TradingView's VWAP values in the export.
5. **Scroll left / press Home to load as much history as the chart will give
   you at 10 seconds.** The export only contains bars that are actually loaded.
   Keep scrolling until it stops loading older bars.
6. Note the **oldest timestamp** the chart will show at 10 seconds. This is the
   single most important number in this whole run — tell me exactly what it is.
7. Export chart data, choosing an ISO or date-time format for the time column
   if offered.

Report: the symbol, the oldest 10-second bar available, roughly how many bars,
and the filename.

## Task 3 — The same symbol at 1 minute

Repeat task 2 at the **1 minute** interval, same symbol, extended hours on,
VWAP on. Scroll back to load as much as it will give.

This gives me the same session at two resolutions, which is the comparison I
want.

Report: oldest 1-minute bar available, and the filename.

## Task 4 — Screener exports

For each of my three saved screens — `PM Gappers`, `Live Momo`,
`AH Continuation`:

1. Open it.
2. Look for an export / download button (often a `⋮` menu or a download icon
   near the top-right of the screener panel).
3. Export it to CSV with all my configured columns visible.

If there is no export button on the screener, say so plainly and instead take a
full screenshot of each screen's results.

Report: three filenames, or an explicit "no export button, screenshots instead".

## Task 5 — Watchlist export

Open the watchlist panel → `MOMO Watch` → the `⋮` menu → look for
**"Export list"**. Export it.

Report: filename, or "not available".

## Task 6 — Layout and alerts (check only, do not fight it)

Answer these as questions, do not spend long trying to force them:

1. Is there **any** way to export a chart *layout* itself — the arrangement,
   the indicator settings — as a file? Check the layout `⋮` menu and Settings.
   I expect the answer is no. Just confirm.
2. Is there any way to export my **alerts** list? Check the Alerts panel's
   `•••` menu.
3. Can any indicator's settings be exported or copied as text? Check the
   settings dialog of the VWAP indicator for a template/preset export.

Report: yes/no for each, and where you looked.

## Task 7 — Final report

Give me:

| Task | File produced | Notes |

Then tell me:
1. **The oldest 10-second bar TradingView will give me.** Restate it.
2. Where the files were saved on disk.
3. Anything you changed on my layout that I need to change back.

---

## What is actually worth exporting

Ranked by what it unblocks, so you know where to push if the agent gets stuck:

| Export | Value | Why |
|---|---|---|
| **10-second chart data** | **the whole reason for this run** | `research/momentum-replication/NEXT-STEPS.md` §5: his entries are on a 10-second chart and 1-minute bars cannot represent them at any parameter setting. This is the project's #1 blocker |
| Chart data with VWAP included | high | Settles whether his VWAP includes pre-market — the open question in `reports/2026-08-vwap-condition.md` — by comparing TradingView's column against ours |
| Screener CSV | medium | Lets the five pillars be scored against a real screen instead of our reconstruction of it |
| Watchlist txt | low | It is a list of tickers; you could retype it |
| **Layout** | **near zero** | There is no supported file export, and a layout is cosmetic — pane arrangement and colours. Nothing in it can be analysed. Do not spend the session chasing it |

**The catch to expect on task 2:** TradingView retains far less history at
seconds intervals than at minute intervals, and the export only covers bars the
chart has actually loaded. A few days of 10-second data is plausible; a month is
not. That is why task 2 asks for the oldest available timestamp as a headline
number — it decides whether this is a real data source or a one-session
curiosity, and it is cheaper to find out than to guess.

## Verified against a real export

`BATS_LNAI, 1.csv` (306 bars, 2026-07-21 to 2026-08-03) exposed three things
the importer now handles, all of which would have corrupted data silently:

- **Duplicate column names.** Two EMAs on the pane both export as `EMA`.
  `csv.DictReader` keeps only the last. Repeats are now suffixed `EMA.2`.
- **The export is sparse.** TradingView emits a bar only where a trade
  happened. That file was missing 92% of its in-session minute slots. The
  importer prints a warning above 2%.
- **Interval inference must use the mode, not the median.** With that many
  holes the median gap was 240s and a 1-minute chart read as `4m`.

And one thing to fix at the source: **extended hours were off**, so the file
starts at 09:30 with no pre-market bars.

## Importing the result

```bash
python scripts/import_tradingview.py "BATS_CUPR, 10S.csv"      # ticker + interval inferred
python scripts/import_tradingview.py *.csv --dry-run           # check before writing
```

Writes `research/momentum-replication/data/bars_cache/<SYM>.<interval>.json` in
the same shape the engine already reads, and any indicator columns to
`data/tv_indicators/`. A 1-minute import lands on `<SYM>.json` and **overwrites
the Yahoo cache the July runs used** — the script warns before it does, so read
the output.
