# Prompt: capture today's 10-second data before it expires

**Time-critical.** TradingView retains far less history at seconds intervals
than at minute intervals. Today's 10-second bars will not be available in a
week. `research/momentum-replication/NEXT-STEPS.md` §5 calls sub-minute data
the project's blocker, and 2026-08-05 produced the best specimen the corpus
has: JLHL faded all pre-market, reversed at the open, ran a clean micro-pullback
sequence from 09:41 to 09:47, halted, ran to 16.14, and broke down through VWAP
at 12:01. We already have the 1-minute version of all of it.

Copy everything between the lines into the Claude Chrome extension.

---

I'm on TradingView, logged in, Premium plan. I need to export chart data before
it expires. Work in order and report after each step.

**Rules:** paper trading only — never connect a broker, never place an order,
never open billing. If something isn't available on my plan, say so plainly
rather than substituting something else. Tell me anything you change on my
saved layout so I can put it back.

## Step 1 — JLHL at 10 seconds (the important one)

1. Open a chart, symbol **JLHL**, interval **10 seconds**.
2. Settings → Symbol → tick **Extended trading hours**.
3. Add **VWAP** to the pane. This matters — I want TradingView's VWAP column
   in the file.
4. Press Home / scroll left until it stops loading older bars. **The export
   only contains bars the chart has actually loaded**, so this step decides how
   much data I get.
5. Tell me the **oldest 10-second timestamp** available before you export.
6. Right-click → **Export chart data…** → choose an ISO / date-time format for
   the time column if offered → export.

Report: oldest bar available, roughly how many bars, filename.

## Step 2 — JLHL at 1 minute

Same symbol, same settings, interval **1 minute**, scroll back as far as it
goes, export.

This gives me the same session at two resolutions, which is the whole point.

## Step 3 — INLF at 10 seconds

Repeat step 1 for **INLF**. It halted at the open and swung −43% intraday, so
it's the halt specimen.

## Step 4 — XOS at 10 seconds

Repeat for **XOS**. This one is the control: it did almost nothing (+1.7% from
the open). A pattern that only shows up on movers isn't a pattern.

## Step 5 — Report

| Symbol | Interval | Oldest bar | Bars | Filename |

Then tell me: what is the oldest 10-second bar TradingView will give me on any
symbol? That single number decides whether this is a real data source or a
one-session curiosity.

---

## Then

```bash
python scripts/import_tradingview.py *.csv --dry-run   # check first
python scripts/import_tradingview.py *.csv
```

Sub-minute files land at `data/bars_cache/<SYM>.10s.json` and do not touch the
1-minute cache. Indicator columns go to `data/tv_indicators/`.
