# V12 — disposition of the Codex manager audit

| Artifact | SHA-256 |
|---|---|
| V11 baseline as audited | `70c4db21e14aff9092889eff59e8d1aa25e28555ebe7e2133db01a6d3d0bba31` |
| Codex candidate (V11.1) | `fc7d3e78fc0618cb1972d23b5c74d6b243a1dbfa9d306e3074e22bed0ec1419a` |
| V12 (compiled by operator) | `7e89210aec0b5ee00c7267ae337bfc40f9eab87e5ee94170d9c995b3ab19cfba` |
| **V12.1 (this file)** | `a2fffe5db395a482662f1dfa95c47834213b089673893ee727f2c8897266eb1a` |

The audited baseline hash resolves to my commit `beaaa02` **with the trailing
newline stripped** — verified by reproducing the hash. So Codex audited the
post-CE10156 V11, and its line references map to my file.

## Release status

`LIFECYCLE TESTS FAILED`

**C1 is now partially satisfied: V12 compiled and ran.** Operator screenshot
shows `ROSS FP V12` live on USDE, 1-minute, dashboard rendering, verdict
`REJECTED / NO`, plan and ladder populated. That clears `COMPILE FAILED`.

It cannot advance further: A01–A38 have not been run and section 8 has no
data. `LIFECYCLE TESTS FAILED` is the honest status — the lifecycle tests
have not passed because they have not been run.

Still not claimed anywhere: `accurate`, `validated`, `production-ready`,
`profitable`.

### V12.1 display revision (operator report on the running build)

Six defects, all display-layer, all reported from the live V12 chart:

| # | Reported | Change |
|---|---|---|
| 1 | grid eats the chart | `dashSize` defaults `tiny`; new `dashCompact` retires the standing LIMITS caveat row, which reappears whenever the ambiguity count is non-zero |
| 2 | verdict far too long | one verb + short reason; live/playbook/room provenance clauses demoted behind `dashFull` |
| 3 | markers unusable at zoom, far above/below candles | `location.abovebar/belowbar` offset by a fraction of the **visible price range**, so the gap grows as you zoom out. All twelve now `location.absolute` pinned to a price, with an ATR-fraction clearance — ATR is in price units, so it holds at any zoom |
| 4 | want dollar P&L on the chart | live label on the last bar of an open position: net $, %, share count, green/red. One label moved per bar, not one per bar — `max_labels_count` is finite |
| 5 | SIZE "63% of $2000" meaningless | SIZE is now shares + dollars only; modeled risk, budget and binding constraint moved to `dashFull` |
| 7 | source text leaking across the chart layout | every `input.*` carries `display = display.none` and every `plot()` `display = display.pane` — see below |
| 6 | PLAN rungs unnamed | `T1 7.20 (88) · T2 7.26 (44) · T3 7.31 (44)` |

**Item 7 — the status-line leak.** The strip across the top of the chart —
`ROS... 5 1 2 6 0.6 20 2 100,000 1 4 50 0.7 30 40 0700-1130 … % of account
(source: 2…` — was TradingView printing all 109 input values, and some input
*label text*, into the status line, plus the value of every `plot()`. With 109
inputs that strip is wider than the chart.

I told the operator last turn this was only a chart setting. That was wrong:
Pine inputs and plots both take a `display` parameter. All 108 inputs are now
`display = display.none` and all 18 plots `display = display.pane` — they still
draw on the chart, they just stop printing their values into the header. Zero
calls remain unscoped, verified by paren-matching the file rather than by
grep, because ten plots were named `displayEntry`, `displayStop` … and a
substring test skipped them.

### V12.2 — levels, and the panel items that gate nothing

**Levels were drawn edge-to-edge with no anchor.** `allPiv` stored pivot
*prices only* — the bar was thrown away — so an S/R line had nothing to
attach to and was drawn `extend=extend.both`: a rule across the entire chart,
through history the level did not exist in. That is why every level read as
constant and unrelated to price. Pivot bars are now kept beside the prices
(`pivHighBars` / `pivLowBars` / `allPivBars`), `f_near` was replaced by
`f_nearIdx` which returns *which* pivot it picked, and each level now starts
at the swing that created it and extends **right only**.

**The nearest-R / nearest-S boxes are gone.** They drew the same level a
second time — R1 and S1 already are the nearest levels — as a shaded band,
also `extend.both`. Two renderings of one price, one of them spanning all
history. Zero `extend.both` remain in the file.

**Labels moved clear of the right edge** (`bar_index + 8`), which is where
they were colliding with the trend-line labels and producing the garbled
overlap.

**What the highlighted panel items meant, and why they are off now.** The
operator was right that they gate nothing:

| Item | Meaning | Now |
|---|---|---|
| `Risk ·` `DipLen ·` `Fit ·` | gate chips; the trailing `·` is the panel's "not judgeable yet" marker, shown when no candidate setup exists | kept — they do gate |
| `Conf 3 ·` | §3 confluence count | kept — gates via `confluenceGate` |
| `§8` | daily risk governor, green = not locked | kept — gates via `v11RiskGovernorOK` |
| `3 hits`, `-.2% · TV-EWMA 4.1x (8.75M/1.99M exp) · float ?` | STOCK FIT: day change, the TV pace proxy, unknown float | **off by default** |

STOCK FIT is display-only — `scanGates` defaults off, so none of it can block
or permit a trade — and its detail string is the widest text in the panel. It
was setting the width of column 6, which is why `Conf` and `§8` rendered as
bars stretched across half the table rather than as chips.

Verified this pass changed **display only**: `hardGatesOK`, `fastCoreOK`,
`fastOK`, `confluenceGate`, `pullbackIndexGate`, `v11RiskGovernorOK`,
`riskGate`, `rrGate`, `scanGate`, `momentumGate` and `pushGate` are all
byte-identical to the Codex base.

### V12.3 — the lines

Two geometry bugs, both mine, both visible as lines floating in empty space.

**Trend lines were projected forever.** They were drawn between two past
pivots and then `extend = extend.right`. On a chart whose right margin has
not traded yet, that projection is the *only* part on screen: two lines
crossing blank space, touching no candle, describing nothing. A trend line
states the leg that exists — it is not a forecast. Both now terminate at the
last bar, at the line's own value there (`upNow` / `dnNow`, already computed
for the lost/broken test).

**S/R projected to the chart edge.** A level *should* look forward, unlike a
trend line, but not across an untraded margin. Bounded to 12 bars past the
last one, just beyond the labels.

The file now contains **zero** `extend.right` and **zero** `extend.both`.
Every drawn object has both endpoints on, or just past, real bars.

Trend labels are nudged ±0.25 ATR off the line end so the two cannot land on
the same pixel when the lines converge — that was the garbled
`downtrend`/`uptrend` overlap.

Display-only again, verified: all ten gate booleans byte-identical to the
Codex base.

### V12.6 - the structure map, rebuilt

Five attempts each fixed a real defect and the levels were still reported
wrong. This is a rebuild on a different architecture, taken from Codex's
V12.6.2 spec (the file itself never arrived - three pastes carried its header
comments only - so the design is implemented from that spec, not merged).

**The load-bearing change.** Codex: *"Plot-based MAIN/trend series provide a
historical rendering backstop; last-bar drawing objects remain responsible for
labels and projection."* Every level is now a **plotted series**. A `plot()` is
bound to its value by TradingView itself - it cannot sit at a price other than
the number it carries, at any zoom, on any bar. Every earlier version drew
levels only as `line.new` objects created on the last bar, and that is where
the drift and the label/position disagreements lived.

**Anti-fabrication.** A trend line is not drawn until **two confirmed pivots**
form a genuine higher-low or lower-high pair. The old tangent/touch-count
fitting manufactures a line out of any price series - which is how a $13.70
stock got a line at $12.97. Slope comes from the pair, projection is finite
(`tlProjectBars`, default 20), and the break state is close-confirmed and
persistent rather than re-decided by a wick.

**Provenance.** MAIN R and MAIN S are the closest eligible level and they name
their source - `pivot`, `HOD`, `PM high`, `prev close`. Anything beyond
`srReachATR` (default 6 ATR) is not structure the next few minutes will meet,
and is not drawn at all.

Zero live `extend.right` and zero live `extend.both` remain - the two textual
occurrences left are a comment and a tooltip string. Every drawing object's
coordinates are explicit bar_index/price pairs.

`showChartMap` is back to `true`: it was turned off in V12.5 as a stopgap
because the map was wrong, and the map has now been rebuilt.

Gate booleans: all ten still byte-identical to the Codex V11 base.

**Not compiled here.** There is no TradingView compiler in this environment.
`scripts/pine_check.py` is clean and paren/bracket balance is zero, but by the
audit's own rule that is not a compile proof. V12.6 is a candidate until it is
pasted into TradingView and the result reported.

### V12.6.1 - CE10272, and the checker gap that let it ship

TradingView: `Undeclared identifier "sm"` at line 3058, 13 problems.

**Cause.** V12.6 rebuilt the structure map by replacing a line range. That
range ran 2849-3128, and old lines 3127-3128 were:

```
sm = showMarkers and not bigMarkers
lg = showMarkers and bigMarkers
```

They had nothing to do with the structure map. They sat at the tail of the
range and were deleted as collateral, leaving twelve plotshape calls reading
two names that no longer existed.

**Swept, not spot-fixed.** Every top-level binding in the replaced range was
diffed against the new file. Four are missing and all four are intentional
(`dnTL`, `upTL`, `dnTLlab`, `upTLlab` - the old trend-line objects the
rebuild replaced). Then every identifier in the whole file was checked
against every binding in the whole file: `sm` and `lg` are the only two names
used and never declared. One defect, confirmed as one.

**The checker gap.** `pine_check.py` was clean on this file. `forward_refs()`
compares line numbers only for names it already found a declaration for:

```
if name in SKIP or name in params or name not in declared:
    continue
```

A name with NO declaration hits `name not in declared` and is skipped - the
one case the CE10272 rule could not see. Added `undeclared()`, which flags
any identifier bound nowhere in the file. Getting it quiet required handling
three real false-positive classes first: dotted paths of arbitrary depth
(`strategy.closedtrades.entry_price`), tuple destructuring
(`[macdValue, macdSignal, macdHist] = ta.macd(...)`), and named-argument keys.

Verified by regression, not by a clean pass: run against V12.6 as shipped it
reports `sm` at line 3058 - the same identifier at the same line TradingView
reported. Run against V12.5 it is clean, confirming V12.6 introduced this.

The declarations are now immediately above the plotshape block that consumes
them, so a future block edit cannot orphan them without also deleting the
uses.

### V12.9 - the structure map, on finite lines. My V12.6 was the bug.

The operator's chart showed four jagged lines wandering across it, shadowing
price, touching nothing. That is not a rendering glitch. It is exactly what
V12.6 asked TradingView to draw.

**Cause.** `mainR` is defined as "the nearest confirmed level ABOVE THE
CURRENT CLOSE". Its value therefore changes on almost every bar. V12.6 fed it
to `plot()`, and `plot()` joins per-bar values into one continuous line. Two
of those (resistance, support) plus two more for the trend lines are the four
squiggles. Four series; zero levels.

`plot()` is right for something that genuinely has a value on every bar - an
EMA, VWAP. A support level is ONE price and needs ONE horizontal line.

**My reasoning was wrong too, and that is the more useful admission.** I moved
to plots claiming line objects "drift" under zoom. They do not. A line whose
two y-coordinates are prices is pinned to those prices at every zoom level.
What drifted in V12.0 was `location.abovebar` / `yloc.abovebar` on *shapes and
labels* - a different API on a different object, already fixed separately. I
generalised one bug into a rule that did not apply to lines and deleted code
that worked. V11 had it right: `line.new(b1, v, b2, v)`. Codex reached the
same conclusion independently in its V12.8 header - *"finite line objects
only: no historical stair-step plots"*.

**Now.** Four objects, which is the entire ask: main resistance, main support,
uptrend, downtrend. Each is a finite `line.new` with explicit bar_index/price
coordinates, rebuilt on the last bar, showing current structure only. A
horizontal level passes the same price as both y-coordinates, so it is
horizontal by construction rather than by intent.

Added: a **role buffer** (max of 2 ticks, 5% ATR) so a level price is sitting
exactly on is classified as neither support nor resistance and is not drawn -
previously it would be named as a target price had already reached. Levels
are anchored at the bar where they formed, so the line starts at its origin.
Trend lines still require two confirmed pivots forming a real higher-low or
lower-high pair.

Removed from the default chart: the impulse-peak, high-of-day and
pre-market-high series. MAIN resistance now names its source ("R 3.84 . HOD"),
so those three said nothing the structure map does not. Behind
`showContextPlots`, default off.

`dayLow` did not exist in this file; the block keeps its own `srDayLow`.
That was caught by the `undeclared()` rule added in V12.6.1, on its first
run against new code.

Display-only: all ten gate booleans still byte-identical to the V11 base.
Still not compiled here - TradingView remains the only real compiler.

### V12.10 - stale structure: why DAIC showed a useless line and no support

The V12.9 geometry held (R 2.4500 sat on 2.45, S 1.8050 on 1.805), but the
levels it chose were the wrong ones. Three causes, each reproduced before
being fixed.

**1. The pivot arrays are never reset per session.** `pivHighs` / `pivLows`
keep the last 40 confirmed pivots whenever they happened. On DAIC, +449% on
the day, that array still carried pivots from when the stock traded near
$0.40. A level from a different price regime is not structure. Fixed with a
day-scoped copy for the structure map only - the shared arrays also feed the
confluence gate, so they are untouched and every gate boolean still behaves
identically.

**2. No support existed because a strict pivot needs clearance on both
sides.** In a tight range none confirm, so the map reported nothing while
price was visibly bouncing off a shelf. DAIC's obvious floor was ~2.15; the
nearest confirmed pivot below was 1.805, half a dollar away and useless. The
extreme of a recent window is a real level whether or not a pivot confirmed
on it, so the swing high/low over `swingLookback` (20) bars now competes as a
candidate and names itself "20-bar low".

**3. The rising line was expired, not wrong.** My first explanation - that
the pair-finder picked a bad anchor - was incorrect, and porting both the old
and new function to Python disproved it: on that pivot pattern they choose
the same anchor. The actual cause is staleness. The newest pivot low was 80
bars old; its slope was measured across 15 bars and extrapolated 95 more, so
a line built from 1.62 -> 1.80 was still being drawn at 2.76 against a price
of 2.34, sweeping up through the entire consolidation. Nothing was wrong with
the pair; the line had run out and no rule said so.

Two guards, verified on the reproduction: FRESHNESS - expire a line whose
newest anchor is older than `tlMaxAgeBars` (60). REACH - project at most one
anchor-span past the newest pivot (measure 15, project 15, not 95), and if
that reach is already behind the current bar, draw nothing. DAIC's line fails
both independently; a current line (pivots 5 bars back) passes both.

Also: structure reach tightened from 6 ATR to 3 ATR, and trend pairs are now
validated so no intermediate pivot violates the line - an uptrend line must
sit under the lows it connects.

Display and level-selection only. All ten gate booleans remain byte-identical
to the V11 base, and the arrays the gates read are unmodified.

### V12.11 - the V9 structure block, restored verbatim

The operator: *"go back to V8 or V9; figure out how you did manage these
indicators in the chart."* Correct instruction. There is no V8/V9 file in the
repo, but V11 IS V9.12 (I built it by merging the latest V9 revision with the
V10 fixes), so its structure block is the V9 code. Lines 2513-2762 of
`ross_fp_v11.pine` are now in V12, verified byte-identical.

**Three regressions, all mine, each the same mistake.**

1. `extend=extend.both`. V9 draws a level as a horizontal rule across the
   WHOLE chart, past and future. In V12.4 I called that a bug - "a line
   extending into empty margin" - and replaced it with finite segments
   spanning origin-bar to a few bars right of now. It was not a bug. A level
   is a price that matters everywhere, so it must be visible wherever the
   operator has scrolled. This is the single biggest reason levels kept
   reading as detached from the candles.

2. Two levels each side, not one. V9 prints R1/R2 and S1/S2, deduplicated
   within half an ATR so a cluster shows once, plus the prior-day close
   dashed. I had narrowed it to one level per side behind an ATR reach cap
   that could suppress everything - which on DAIC it did, producing "no
   support neither resistance".

3. Tangent trend lines, not pivot pairs. V9 takes, from each candidate
   anchor, the MINIMUM slope to any later low - the line that by construction
   cannot cut through the lows - then keeps it only if two or more lows touch
   within tolerance. V12.10 demanded two confirmed `ta.pivotlow` pivots,
   which in a tight range never confirm, so no trend line was drawn at all.

Every one of these came from me taking a single real defect, generalising it
into a rule, and discarding working code that the rule happened to cover.
V12.6 (plot-based levels) was the same error. The lesson is narrower fixes,
and checking the previous version before replacing its approach.

Removed the six inputs that only existed to serve the discarded design
(`showChartMap`, `srReachATR`, `tlProjectBars`, `maxTLdistATR`,
`swingLookback`, `tlMaxAgeBars`) so the settings dialog stops offering
controls that do nothing.

Kept from V12: the marker-location fix, the `sm`/`lg` declaration, the
`undeclared()` checker rule, and `showContextPlots` (default off) for the
impulse-peak / HOD / PM-high series the operator called clutter.

All ten gate booleans remain byte-identical to the V11 base.

### V12.12 - the misalignment is a CHART SETTING, not the code

The operator: *"by dragging the graph upper or lower we lose analysis
capabilities of the chart indicators; as they get unaligned with the
candles."* Eleven revisions had not fixed this. The reason is that it is not
in the Pine file.

**The proof.** Every S/R label is created as

```
label.new(bar_index + 2, v, "R" + str.tostring(v, format.mintick))
```

The y-coordinate and the text are THE SAME VARIABLE `v`, and with no `yloc`
argument the default is `yloc.price`. It is not possible for that label to
render at a price other than the one printed in its own text. Yet the DAIC
screenshot shows:

| label text | drawn at | ratio |
|---|---|---|
| prev_close 3.91 | ~3.30 | 0.844 |
| R 4.66 | ~4.05 | 0.869 |
| S2 4.10 | ~3.60 | 0.878 |
| R 5.04 | ~4.30 | 0.853 |

A roughly CONSTANT ratio across four independent levels is a single linear
price-to-pixel transform applied to the drawings and a different one applied
to the axis. No Pine code can produce that; the script hands TradingView a
price and has no say in how it is mapped to a pixel.

What produces it is the price-scale option **"Scale price chart only"**. With
it on, a vertical drag rescales the main series alone and leaves overlaid
drawings on their previous mapping - which is the reported symptom stated
almost word for word. A script pinned to a second scale does the same thing.

This is worth recording as a method failure: from V12.0 onward I treated
"lines do not align" as a geometry bug and rewrote the drawing layer five
times over it - bar-relative locations, then line objects, then plot series,
then finite lines, then back to V9. Each rewrite fixed something real, and
none of them could have fixed this, because the transform was never mine to
control. The arithmetic above took two minutes and should have been the first
thing I did.

**The one real code defect in the same screenshot.** The teal uptrend line was
anchored on the session low at 2.05 while price was 3.66 - 1.6 dollars of
empty space under the candles. V9 scores a line as `touches*2 - distance`
with distance capped at 20, so distance is a soft term. It was not outvoted
here: no nearby line reached the two-touch minimum, so the far line was the
only candidate and was drawn by default. Because TradingView auto-scales the
pane to fit every drawing, it also pulled the axis down to 1.20 and squashed
the candles into the top half - destroying exactly the "analysis capability"
the operator is describing.

Fixed with a hard ceiling rather than a score term: `maxTLdistATR` (3.0). At
ATR 0.18 the session-low line sits 8.94 ATR away and is now rejected outright,
so the outcome is no line instead of a useless one. A live pullback line at
1.44 ATR still draws.

Gate booleans unchanged.

### V12.13 - what V8 actually did, recovered from git

The operator asked me to stop working from revision history and instead
recover how V8 traced lines correctly. The whole history is in git -
`knowledge-base/tradingview/ross-fp-v4.pine` kept its filename while the
version advanced through V7.x, V8.x and V9.x - so this is recoverable fact,
not memory.

**V8 had no diagonal trend lines.** Its `showTrendLines` input is a toggle for
the EMA9 / EMA20 / VWAP plots:

```
showTrendLines = input.bool(false, "Show EMA9 / EMA20 / VWAP", group=gVisual)
```

Drawn diagonals were introduced in V9.6 ("automatic trend lines with
break/loss flags") and reworked in V9.7, V9.8, V9.9 and V9.10 - five attempts
in the original line too. Every complaint in this thread - "lines make no
sense", "cuts through the candles", "detached from price", "useless lines" -
has been about a diagonal. Not once about a horizontal level. V8 looked clean
because there was nothing diagonal in it. Diagonals are now default OFF.

**V8's S/R geometry is already what ships.** `line.new(bar_index - 1, v,
bar_index, v, extend=extend.both)` plus `label.new(bar_index + 2, v, ...)`,
unchanged. The one substantive difference is polarity: V8 sourced resistance
from `pivHighs` and support from `pivLows`. V9.5 pointed both at `allPiv` so
any pivot could be either role, which doubles the candidate pool and allows a
pivot LOW to be drawn as resistance above price. Default is now V8;
`srBothPolarities` restores V9.5.

**Overlapping labels.** Every label printed at `bar_index + 2`, so two levels
a few cents apart collided on the same pixel row. Each label now gets its own
x column (`srLabelStagger`, 4 bars).

### Why "adapt to zoom and drag" cannot be delivered by any Pine script

Stated plainly because it has been asked for repeatedly. **Pine has no access
to the chart viewport.** There is no API for the visible bar range or the
visible price range, and a script is not re-executed when the chart is panned
or zoomed. Drawing objects are built on `barstate.islast` and hold their
coordinates until a new bar arrives. Nothing in Pine - not this file, not V8,
not the Codex candidates - can recompute levels for wherever the chart has
been scrolled to.

This is exactly why V8 read as correct at every zoom: a HORIZONTAL line with
`extend.both` spans the full width at one price, so there is no anchor to
drift away from and no viewport dependence to fail. A diagonal is anchored to
two specific bars; pan away from them and it floats in space with nothing
visible to relate it to. The V8 look is not a better algorithm, it is a shape
that is immune to the problem.

Combined with the scale finding in V12.12 - "Scale price chart only" applying
a different price-to-pixel transform to drawings than to the axis - the two
non-code causes account for the whole complaint.

Gate booleans unchanged.

### V12.14 - trend lines back on, and the level that was drawn twice

Two operator reports, both correct.

**"No trend lines."** V12.13 turned them off because V8 had none. That was my
inference, not the ask - the request was never "remove them", it was "make
them work". Default restored.

They would also have been suppressed with the toggle on: V12.12 set the
distance ceiling at 3.0 ATR, which is too tight. On VNRX (ATR ~0.01) a
downtrend line projecting 0.02-0.04 above a 0.68 price is 2-4 ATR away, and
that is exactly the line a breakout has to break, so it must be drawn.
Ceiling raised to 6.0 ATR, which still rejects DAIC's session-low tangent at
8.94 ATR. Verified both cases.

**"Levels are still overlapped."** Real, and a different mechanism from the
label collision fixed in V12.13. The band boxes print their own
`R <price>` from `nearestRes`, which is computed from `allPiv` in a separate
block at line 1176 and never deduplicated against the R1/R2 lines. On VNRX
that produced `R1 0.7146` and `R 0.7097` - 0.0049 apart, inside the half-ATR
dedup tolerance. One level, two drawings, two labels on top of each other.

The first level drawn on each side is now remembered (`srR1` / `srS1`) and a
band box is skipped when it would only restate it. Tolerance is 0.75 ATR,
deliberately wider than the 0.5 ATR line dedup: at exactly 0.5 the VNRX pair
was suppressed by one ten-thousandth, which is true but not worth depending
on. Anything the line dedup passes is more than 0.5 ATR from its neighbour,
so the wider box tolerance cannot hide a distinct level.

Gate booleans unchanged.

### V12.16 - a range for every trend, not a single rail

Operator: *"for each pattern uptrend or downtrend, the resistance and support
-- I need a range for every trend forming."*

A single tangent only ever gives the side the trend leans on. An uptrend line
is the floor price keeps bouncing off; a downtrend line is the ceiling it
keeps failing at. Neither says where the move runs out, which is the half you
need to size a target.

Each trend now draws both rails:

| trend | fitted rail | opposite rail |
|---|---|---|
| uptrend | floor, tangent under the lows | ceiling, parallel |
| downtrend | ceiling, tangent over the highs | floor, parallel |

The opposite rail is offset by the **largest excursion the other extreme made
from the fitted line over the same span** - the standard parallel channel. So
an uptrend's ceiling is the furthest the highs ever got above its floor, which
by construction contains every high in the leg.

Parallel rather than a second independent fit, deliberately. Two free fits can
diverge, converge or cross, and at that point they no longer describe one
move. A parallel pair always does.

Labels now carry the range rather than one number:

```
uptrend  2.60  -  3.06
downtrend broken  3.70  -  3.94
```

Both rails extend right, the opposite rail is dashed and lighter so the fitted
one still reads as primary, and the band between them is shaded at 94%
transparency (`fillTrendChannel`, on). `showTrendChannel` turns the whole
addition off.

Verified by porting the maths to Python against a synthetic rising leg: zero
highs finish above the computed ceiling, confirming the offset is a true
containing envelope. One low sits below the floor - that is pre-existing V9
behaviour, whose tangent search starts at `a + 2` and therefore skips the bar
immediately after the anchor. Not introduced here and left alone.

Object budget checked: worst case about 15 lines against `max_lines_count=50`,
and 13 labels against `max_labels_count=100`.

Gate booleans unchanged - display only.

### V12.17 - the mastery bundle, applied to the existing strategy

Additive only. Nothing was replaced; the four enhancements below were chosen
because each closes a gap between the confirmed Preview material and what this
script actually measured.

**1. The daily 200 EMA - a real defect, not an enhancement.** The line read:

```
ma200v = ta.sma(close, 200)
```

A 200-period SIMPLE average on the CHART timeframe. On a 1-minute chart that
is a ~3.3-hour intraday line. The playbook's confirmed reference is the DAILY
200 EMA - "privilégier un titre au-dessus du daily 200 EMA", with one sitting
$0.50-1.00 overhead treated as problematic resistance. Wrong timeframe AND
wrong average type, and it fed `ma200Support`, one of the six §3 confluence
components - so the confluence gate was counting a level the strategy does not
mean. Now `request.security(..., "1D", ta.ema(close, 200))` with
`lookahead_off`. `use200Daily` restores the old behaviour for comparison.

**2. The fifth pillar.** The script scored four (price, RVOL, gap, float); the
playbook names five. Catalyst is now operator-supplied and fail-closed exactly
like the float - confirmed, bound to this ticker, and given a provenance that
is not "Unknown" or "Chat/rumour". Switching symbols fails closed rather than
carrying yesterday's news to a new chart.

Confirmed and respected: breaking news is *preferred but not mandatory*, and
Warrior's own Five Pillars scanner does not require news. So the catalyst
raises the score and the grade and never vetoes on its own. The flame is
reproduced as a news-age clock only (red 0-2h, orange 2-12h, yellow 12-24h),
explicitly not a compliance score.

`pillarScore5` and an A/B/C grade sit beside the existing four-pillar
`pillarScore`, which is byte-identical - the scanner gate is untouched.

**3. Scenario D: does 2R fit before the wall?** The playbook requires "un
objectif d'au moins 2R avant la première résistance probable", and Scenario D
fails a trade on precisely this. Nothing measured it: the script sized the
trade, drew T1/T2/T3, and let the operator find the wall afterwards. The
nearest overhead obstacle among HOD, daily 200 EMA, pre-market high and
nearest confirmed pivot is now named, the room is expressed in R, and the HIGH
OF DAY row turns red when it is under target.

Verified against both worked scenarios in the playbook:

| case | wall | room | expected | got |
|---|---|---|---|---|
| Scenario D (5.20 / stop 5.00 / 200EMA 5.50) | daily 200 EMA | 1.5R | PASS | flagged under 2R |
| Scenario B (6.75 / stop 6.65 / HOD 7.00) | HOD | 2.5R | 2.5R | 2.5R |

**4. Price sweet spot.** $2-20 qualifies, $5-10 is the band the course calls
ideal. Display only.

**The one behavioural change, stated plainly.** Every gate boolean is still
byte-identical in source to the V11 base, and the four-pillar scanner score is
untouched. But item 1 changes the VALUE `ma200Support` returns, which feeds
`supportCount` and therefore `confluenceGate`. That is a deliberate correction
- the gate was counting the wrong line - and it is the only place this release
can change which trades arm.

`request.security` count is 2, well inside the limit of 40.

### V12.18 - multi-time-frame alignment, and an audit of what is still missing

The operator asked four questions. Answers came from the code, not memory.

**Catalyst is score-only, as required.** `pillarCatalyst` appears in exactly
four places, all scoring or display. It is in no gate and no veto, matching
"preferred but not mandatory".

**Gaps: correct. Windows: absent.** `scanGap` measures the RTH open against
`prevCloseD`, which is a genuine `1D` request - so the gap is computed on the
daily reference the playbook defines. The price WINDOW is not implemented at
all: the only "window" in the file is the 07:00-11:30 session-time window.
The §11 rule - a low-structure zone worth about twice a normal daily candle
or twice the daily ATR - has no code, and the script has no daily ATR either
(`ta.atr(14)` is chart-timeframe).

**Alignment was completely absent - now built.** The script had NO 5-minute
data. It read one timeframe and called that the setup, while §10 devotes a
section to the interaction. One tupled `request.security` (call budget now 3)
supplies 5-minute close, EMA9, EMA20, high and low, and the four states are
named as the playbook names them:

| 5m constructive | 1m constructive | state | playbook |
|---|---|---|---|
| yes | yes | `aligned` | best case |
| yes | no | `1m weak` | refuse normally |
| no | yes | `1m leads` | exceptional leader only |
| no | no | `neither` | no |

Plus the oversized-bar warning: a 5-minute bar wider than `bigBar5ATR` (4)
times the 1-minute ATR gets flagged, because its low is not a stop you can
take at normal size.

**Advisory, not a gate**, deliberately. The playbook says "refuser
NORMALEMENT" - normally, not always - and it lists personal thresholds as
things to fix after backtesting. It reports on the verdict line; gating comes
after the operator has watched it.

Intrabar behaviour documented in-line: the 5-minute values update while that
bar forms, which is what an operator reads. They never trigger an order.

**Chart patterns: none exist.** Zero hits for ABCD, flat top, cup and handle,
double top, head and shoulders, gravestone, doji or hammer. The four
`KIND_*` constants are entry mechanics, not chart patterns. Two candlestick
shapes DO exist under other names: `bottomingTail` and `toppingTailWarning`.

Worth recording for scope discipline: the bundle §9 confirms exactly four
patterns - ABCD, flat top breakout, cup and handle, double top. Inverted
head-and-shoulders and inverted gravestone are NOT in the confirmed set, so
building them would import unconfirmed material. §9 also states plainly that
these shapes "ne remplacent ni les Five Pillars ni le plan de risque", which
argues for labels rather than gates.

**Not implementable in Pine at all:** spread (no bid/ask exposed to a
strategy - `syminfo.bid`/`ask` count is zero), Level 2, tape, dilution and
SEC filings. Those stay operator-side by nature, not by omission.

### V12.19 - gaps and windows, corrected against the lesson

The operator: *"windows are made of big candles in the previous days, where
there would be no resistance -- check twice the gap and windows lesson."*
Correct on both counts, and V12.17 had the consequence backwards.

Re-read from `references/day-trading-basics-preview-mastery.md`, Chapter 5
"Gaps & Windows on Daily Charts":

- Gap: the regular-session open is materially above or below the prior close.
- Window: "a large area with little visible support/resistance, created by a
  true gap **or a large long-body candle**."
- Size: roughly 2x a typical daily candle or 2x daily ATR.
- "Recent price action overrides older levels; scan from the current right
  edge to the left and upward."
- "**Do not skip across a newer gap/window to use an older minor level as if
  the newer structure did not exist.**"
- Gap fill: the move back through the empty zone to the boundary of the candle
  before the gap.
- Strong-daily-chart checklist, item 1: "**large gaps/windows create room**".

**What I had wrong.** My earlier summary called a window a zone to treat as an
obstacle. It is the opposite: a window is empty space, and empty space is
ROOM. V12.17's wall search took the nearest overhead level unconditionally, so
a stale price sitting inside a window -- one the market has already run
through -- could be reported as the ceiling and understate the room. That is
precisely the error the lesson warns against.

**Now.** Windows are detected on the daily timeframe from two sources: the
most recent oversized daily BODY (>= `winMinATR` x daily ATR, default 2.0, per
the lesson) and the most recent genuine untraded gap between consecutive daily
bars. A level falling inside either is skipped as resistance. Window and gap
EDGES remain real levels -- the checklist names "gap-edge or window-edge
resistance" -- and the current HOD is exempt, because today's own high is live
structure whatever older window contains it. Overhead empty space is reported
as "window overhead = room", and the gap-fill boundary is named.

Detection runs INSIDE the daily context deliberately. On a 1-minute chart a
requested daily series indexed `[1]` means "the previous CHART bar's value of
the daily high", not the previous day -- so evaluating the loop inside
`request.security` is what makes `open[i]`/`close[i]` genuine prior days.

Verified on the lesson's own shape: a 4.00-7.00 daily body against ATR 1.20
(3.00 >= 2 x 1.20 qualifies), entry 5.20, risk 0.20, a stale pivot at 5.60
inside the window and today's HOD at 5.80.

| version | wall chosen | room | reading |
|---|---|---|---|
| V12.17 | stale pivot 5.60 | 2.0R | borderline, wrong |
| V12.19 | HOD 5.80 | 3.0R | correct |

`request.security` count is 4, inside the limit of 40.

## Method

The audit says *"Do not merge the Codex candidate blindly."* I reproduced its
two load-bearing structural claims against V11 first, then adopted the
candidate as the base once it was clear it was the more advanced artifact —
the same call made earlier for V9.12 over V10.

**C2 reproduced.** V11 line 2149:

```
bool fastOK = fastCoreOK and sessionGate and venueGate and entryTimeOK
```

No `confluenceGate`, no `pullbackIndexGate`, **no `v11RiskGovernorOK`** — with
`fastLane` and `uptrendLane` both `input.bool(true, …)`. A §8-locked account
could still place a lane order. This is my defect, and the same failure mode as
the §8 walkaway I fixed last turn: a rule added in one place without auditing
every path that can reach an order.

**C10 reproduced.** V11 line 1489 `pushDollarVolume := close * volume`, and
line 1054 `candidateAvgVolume * math.max(close, candidateStartClose)` — the
larger endpoint, biased upward on rising bars exactly as described.

I initially doubted the candidate's own C2 fix, because `fastOK` looked
unchanged. That was wrong: it gates inside `fastCoreOK` and at three sites
(2262, 2336, 2652) plus the dashboard.

## Critical findings

| ID | Disposition | Evidence |
|---|---|---|
| C1 no compile evidence | **DEFERRED** | No TradingView here. Status stays `COMPILE FAILED`; header says so. Handoff below. |
| C2 lanes bypass gates | **ACCEPTED** | Reproduced in V11. Candidate: lanes default `false`, `[EXPERIMENTAL]`; `confluenceGate and pullbackIndexGate and v11RiskGovernorOK` enforced at 2262 / 2336 / 2652 and mirrored in the verdict text (2160-2162). |
| C3 governor ignored open loss | **ACCEPTED** | Candidate evaluates drawdown and daily limits continuously incl. open P&L and routes a live lock through the single flatten request. Untested — see A27-A30. |
| C4 var/varip transaction split | **ACCEPTED** | Candidate makes cursor-committed facts intrabar-persistent and guards the new-day reset with `barstate.isnew`. Untested — needs tick replay (A31/A32). |
| C5 UNKNOWN float scored | **ACCEPTED** | Candidate requires verified provenance + ticker binding; unknown adds no point. |
| C6 "third trade" ≠ "third pullback" | **ACCEPTED** | Proxy removed; the ordinal gate decides. Coherent with `maxPullbackIndex`. |
| C7 sizing omitted fixed costs | **ACCEPTED** | Candidate reserves planned order costs before dividing by per-share risk and caps cash at `min(maxPositionValue, equityBase)`. Per-quantity proof table is A17 and needs a chart. |
| C8 unlimited stop-market chase | **ACCEPTED** | Capped stop-limit is the default with an explicit order-model input. |
| C9 same-bar double count / result leak | **ACCEPTED** | Candidate dedupes ambiguity by entry identity and reconstructs unseen same-bar round trips. |
| C10 dollar volume not notional | **ACCEPTED** | Candidate uses `volume * hlc3` per bar throughout. A36 hand-reconciliation still needs a chart. |

## High-priority findings

| ID | Disposition | Evidence |
|---|---|---|
| H1 RVOL is a chart proxy | **ACCEPTED** | Renamed `TV pace EWMA`; warm-up requires N observations; display-only until a matched dataset exists. I have no MSS data here, so no calibration is attempted or claimed. |
| H2 confluence measured at close | **ACCEPTED** | Candidate measures at the dip low and requires recovery on/above the level. |
| H3 ordinal reset on marginal HOD | **ACCEPTED** | Marginal HOD updates the high without resetting the ordinal. Still a heuristic — the labelled-replay test is not run. |
| H4 halt band false precision | **ACCEPTED** | Heuristic veto defaults OFF and is labelled. |
| H5 session default vs own evidence | **ACCEPTED** | Evidence default ON. |
| H6 narrative exits on by default | **ACCEPTED** | Both default OFF. These were mine, added in V11 with mention-counts as justification, which is not evidence of incremental performance. |
| H7 "CONFIRMED data" while reading the live bar | **ACCEPTED** | Label made truthful. |
| H8 dashboard hid the real ladder | **ACCEPTED** | Exact whole-share rungs, binding size constraint and cost-inclusive risk shown. |

## Added by V12, beyond the audit

**Position markers did not track price.** Operator-reported and not in the
Codex candidate. `BOUGHT`/`SOLD` used `yloc.belowbar` / `yloc.abovebar`, which
ignore the y value and hang the label off the candle by a fixed screen offset,
while the dotted result line beside them is anchored to the real fill prices.
Zooming the price scale slid the markers off the line, so the two disagreed
about where the trade happened. Both are now `yloc=yloc.price` at
`tradeEntryPrice` / `resExitPx`.

## What is blocked, and why

| Required | Blocker |
|---|---|
| C1 compile proof, Properties, input defaults | No TradingView in this environment |
| A01-A38 acceptance matrix | Every case needs a running chart |
| §7 telemetry export | Produced by a run |
| §8 development + holdout reports | **No market-data access at all** — every feed host is blocked by egress policy |
| §9 scoring | Gated on compilation |

Any number I produced for those would be fabricated. They are handoffs.

## Handoff — what to run

1. Paste this exact file. If the editor alters it, the compiled hash is the
   release hash, not `7e89210aec0b5ee00c7267ae337bfc40f9eab87e5ee94170d9c995b3ab19cfba`.
2. Report compile errors verbatim with line numbers. Each one becomes a
   `scripts/pine_check.py` rule, as CE10156 did.
3. Then A01-A38, then the development/holdout split.

## Disagreement with the Codex candidate

None material. Where the candidate and V11 differ, the candidate is right on
every point I checked. I have **not** independently verified C3, C4, C7 or C9
behaviourally — they need a running chart — so those are adopted on the
candidate's reasoning, not on my own reproduction, and are marked accordingly
above rather than being called fixed.
