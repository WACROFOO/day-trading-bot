# Design handoff — Momentum Workstation desk

For a designer, or for Claude Design, working on the browser desk at
`src/momentum_platform/dashboard/web/`. Written 2026-09-04 against commit
`96863db`. Everything below is measured from the current files, not remembered.

---

## 1. What this screen is

A single-viewport trading workstation for Ross Cameron / Warrior-style
small-cap momentum trading. It runs locally at `127.0.0.1:8787`, streams live
Interactive Brokers data read-only, and is looked at — not read — in glances of
under a second while the market moves. It never places an order.

**The user.** One person, one screen, six and a half hours a day, under time
pressure, deciding whether a stock that just moved is worth a plan. They are
not browsing. They are scanning for a change of state.

**The job of the screen, in one sentence.** Show which names just qualified,
why, what the setup looks like on the chart, and what the plan would be — with
every number labelled by how much it can be trusted.

**The reading path,** left to right, top to bottom:

```
Top gainers (who passed)  ->  Running Up (who is accelerating)  ->  High of Day
   ->  Quote / catalyst (what is the story)  ->  Charts (what does it look like)
   ->  Five Pillars board (all names, scored)  ->  Screener (the whole band)
   ->  Setup verdict (GO / WAIT / PASS, and the plan)
```

---

## 2. Non-negotiable constraints

Break any of these and the redesign cannot ship.

| Constraint | Why |
|---|---|
| **Every number keeps its honesty label.** Evidence chips (Confirmed / Observed / Approximation / Unknown), `SO` on a shares-outstanding proxy, `SIMULATED` on the Level 2 card, "not licensed market data", "not this desk's feed" on the TradingView panes, and the no-orders disclaimer. | The desk's whole value is that it never dresses a guess as a fact. Shorter wording is welcome; removing a label is not. |
| **UNKNOWN is a third state, never a fail and never a pass.** It must be visually distinct from both. | A missing float is not a failing float. |
| **Information density stays.** Roughly 40 to 60 rows of data are visible at once on a 1760x1020 viewport, and the page must never scroll. Only row lists scroll, inside their own cards. | Scrolling costs a glance. A redesign that adds whitespace by removing rows is a downgrade. |
| **No new dependencies.** No CDN, no build step, no framework, no icon font, no webfont beyond the two already loaded. Plain DOM and CSS, served from this machine. | A content blocker eating a CDN request must never silently change the desk mid-session. |
| **Single dark theme, painted explicitly.** No host-theme inheritance, no light mode. | It is looked at for hours in a dim room next to TWS. |
| **Layout is user-arranged.** Cards live in named slots, can be dragged between slots, resized by gutters, parked in a tray, and the arrangement persists per browser. | Do not hard-code positions. |

---

## 3. The current system, as measured

### Colour tokens (`styles.css` `:root`)

```
Ground      --bg #080b10   --panel #0f151d   --panel-2 #131b25
Lines       --line #1d2836  --line-soft #182231
Ink         --ink #dde6f1   --ink-dim #9db0c6   --ink-faint #7d8fa5
Direction   --up #2ad17f    --down #ff5f6e      --flat #8fa3b8
Plan        --entry #22c7e8 --stop #ff5f6e      --target #3ddb95
UI accent   --focus #4aa8ff
Attention   --hi #ffc247    --critical #ff8a3d
State       --ok-* (green)  --no-* (red)        --unk-* (amber)   ink/bg/line each
News flame  --flame-red #ff4a3d  --flame-orange #ff9a2e  --flame-yellow #ffd54a
```

Semantic rule already in force: `--entry` / `--stop` / `--target` belong to the
plan drawn on a chart and to nothing else; `--focus` is the UI's own accent.
Keep that separation.

### Type

Three families, all loaded: IBM Plex Sans (UI), IBM Plex Mono (every number),
IBM Plex Sans Condensed (the wordmark only).

**Sizes actually in use — 13 distinct values with no ramp:**

| px | uses | px | uses |
|---|---|---|---|
| 10 | 15 | 9.5 | 6 |
| 9 | 12 | 8 | 4 |
| 11 | 12 | 12 | 3 |
| 10.5 | 11 | 14 | 2 |
| 8.5 | 7 | 11.5 | 2 |
| | | 19 / 18 / 15 | 1 each |

`.tsym b` is 11.5px inside an 11px row, so the ticker beats its own row by half
a pixel — an accident, not a decision.

### Shape

Seven border-radius values in use: 2, 3, 4, 5, 6, 8px, 999px, plus `50%`. The
`--r: 7px` token exists and is honoured three times.

### Spacing

No scale. Padding values are written inline per rule, commonly `3px 8px`,
`4px 8px`, `6px 8px`.

---

## 4. Card inventory

15 cards. Each is `.card` with a `.card-head` (grip, title, state pill, extras,
expand button) and a body.

| Card | Body | Notes |
|---|---|---|
| `scan-pillars` | Ranked list: symbol+flame, price, change, RVOL, float | The funnel's first gate |
| `scan-running` | **Timeline**: time, age, symbol+flame+session pill, price, change, branch | Rail with a node per event; newest node lit |
| `scan-hod` | Same timeline shape | |
| `quote` | Two-column key/value grid, then the catalyst block | Flame chip, grade chip, headline, 24h age bar, read-out |
| `chart-1m` `chart-5m` `chart-10s` `chart-daily` | Lightweight Charts panes | Candles, volume, VWAP/EMA lines, entry/stop/target price lines, session shading |
| `tv-widget` `tv-widget-5m` | TradingView's embedded chart | Their data, their chrome; carries a delayed badge |
| `pillars-board` | 13-column table, one row per desk name | Currently 1100px min-width in the shortest slot |
| `screener` | Ranked table: symbol, price, change, source, age | The whole price band |
| `level2` | Simulated ladder + tape | Labelled SIMULATED |
| `timeline` | Alert log with expandable detail | In the tray by default |
| `verdict` | Banner (GO/WAIT/PASS), why-list, pillar mirror table, risk inputs, sizing | The decision card |

---

## 5. Known problems worth solving

From an adversarially-verified audit. The high-severity ones are already fixed;
these are the ones still open, and they are the brief.

**Hierarchy**
1. **Every card carries identical chrome**, so the Setup verdict — the card that
   makes the decision — looks exactly like a reference pane. Nothing on the
   screen leads. This is the single biggest opportunity.
2. **The same ticker is set at two weights and two sizes** depending on which
   card it is in.

**Type and shape**
3. Thirteen font sizes, no ramp, one of them half a pixel above its own row.
   Propose an integer-only scale and map every current use onto it.
4. Seven border-radius values; `--r` is mostly ignored. Pick two or three.
5. No spacing scale at all.

**Colour**
6. **The session pill is a filled amber chip on every premarket alert row.** In
   a premarket session that is every row, and it out-shouts the news flame,
   which is the rarer and more important signal.
7. **Two chart legend keys are the identical purple**, so VWAP and the 52-week
   line cannot be told apart on the Daily card.
8. **Time & Sales paints ten full-width tinted blocks.** The tape reads as a
   colour bar rather than as individual prints.
9. The severity chip is the only chip in the app rendered in lowercase.

**Layout**
10. **The Five Pillars board is 13 columns and 1100px wide inside the shortest
    slot on the desk**, so it scrolls on both axes. Either the column set or the
    slot has to change. Which columns earn their width is a real question:
    Last, Vol today, Avg vol, Spread, HOD, vs VWAP, then five pillar cells and a
    score.
11. The expanded-card overlay and the tray hard-code the top bar's height in
    three places.

**Motion**
12. A 1.5s amber card-wide pulse fires on a new arrival and is not covered by
    the reduced-motion guard.

---

## 6. What a good outcome looks like

- A trader glancing for 300ms lands on the thing that changed, not on the
  brightest thing.
- The decision card reads as the decision card without being loud.
- Colour carries meaning only: direction, state, plan, recency. Nothing is
  coloured for decoration.
- One type ramp, one spacing scale, two or three radii, and every existing
  element mapped onto them.
- Same or higher information density than today.
- Both themes is not a requirement; this desk is deliberately single-look. Paint
  every colour explicitly.

## 7. What is out of scope

Copy rewriting (just done: every tile note is one line with the full sentence in
the tooltip), the funnel order, which cards exist, the data model, and anything
that would need a build step.

---

## 8. Practical

**Files.** `styles.css` (471 lines, all of it), `index.html` (251 lines, card
markup), `app.js` (2189 lines — only the class names it emits matter; the logic
does not need touching for a visual pass).

**See it without market data**, on any machine, in 30 seconds:

```
bash scripts/start.sh --replay
```

or on Windows:

```
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Replay
```

Then open `http://127.0.0.1:8787` and press Play. The recorded session drives
every card with real shapes: full lists, firing alerts, arming plans, a red-flame
catalyst, an UNKNOWN float, a WAIT verdict.

**A single self-contained HTML file** of the whole desk, for pasting into a
design tool:

```
python3 scripts/build_dashboard_artifact.py desk.html
```

**Check the work.** `python3 -m pytest -q` — 364 tests. Several assert on class
names and layout geometry (`test_ui_chart_stack_...`, `test_ui_five_pillars_board_...`,
`test_ui_tiles_report_state`), so they will catch a rename that breaks the page.
