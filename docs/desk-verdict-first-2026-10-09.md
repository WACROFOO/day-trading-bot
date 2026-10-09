# The desk, verdict first — 2026-10-09

The owner's 05:30 screenshot, zone by zone: what each highlighted zone says,
what a decision needs instead, how Ross runs his screen and his morning, the
plan, and what was built the same morning. Screenshots:
[`desk-verdict-first-2026-10-09/`](desk-verdict-first-2026-10-09/).

## 1 · Provenance

| what | source | read |
|---|---|---|
| the desk as the owner saw it | `desk-verdict-first-2026-10-09/before_0530_owner.png`: the owner's screenshot, 2026-10-09 05:30:54 ET, pre-market, AIXI selected, four zones circled in green | 2026-10-09 |
| the owner's words | *"all highlighted section contain useless info for me and i feel it misses the verdict part to be clear"* | the same message |
| what each zone draws | `src/momentum_platform/dashboard/web/app.js` (`renderHeader`, `renderDecisionCard`, `renderPillarsBoard`, `renderTape`, `postFocus`), `src/momentum_platform/decision_card.py` (`build_card`), `src/momentum_platform/datasources/ibkr_tape.py` (`TapeFeed.focus`, `_schedule`, `check`) | this session |
| thresholds | `src/momentum_platform/cascade.py`: `PILLARS_MIN = 4` (owner amendment A5), `PRICE_MIN 2.00`, `PRICE_MAX 20.00`, `FADE_MAX_PCT 25.0`; `knowledge-base/strategies/FILTERS.md` gates 1–4 | this session |
| how Ross works his screen | the corpus, read through `scripts/corpus.py`, each quote cited below with its video id and timestamp | this session |
| the course's workstation | `CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/day-trading-basics-preview-mastery.md` §"Minimum layout"; `…/dashboard-scanner-chart-knowledge.md` | this session |

The owner suggested watching one of his recent YouTube videos, because his
screen is visible while he trades. **Nothing here comes from watching video.**
The transcripts in the corpus record what he says about the screen while he
uses it, and that is the evidence used.

## 2 · What was on the screen: the four highlighted zones

| # | zone | what it said at 05:30:54 | what it serves | the finding |
|---|---|---|---|---|
| 1 | **symbol header**, two lines | `1.86 −3.6% · bid×ask 1.81×1.86 · spread 5.0¢ 2.69% · vol 155k · rvol 1.25× · day rvol 0.03× · 5m 0.59×` / `vwap 1.81 (+2.5%) · hod 1.97 · pm high 1.97 (−5.6%) · 52w ×204 split history · float 55.2M SEC shares out · range 50%` | 18 numbers, none of them stating a conclusion | **Each number already had another home.** The pillars (RVOL, float) are on the decision card. VWAP, HOD and PM high are drawn as chart lines. Bid × ask matters only next to an order. Nothing in the header said "NO". |
| 2 | **Decision · order card** | `NO $1.86 is under the $2.00 floor`, then 15 more lines: `2.00 back over`; plan history; `TAPE the tape is on FLYE — select this name`; `WEAK` catalyst with the news-pillar reason; filings / split test; `BOT the bot has no plan…`; two ⚠ warnings; 13 lamp chips on two rows; the risk input; `No order: the cascade killed this name`; `I passed`; `Float you verified` | the answer, then everything that might explain it | **The verdict was there but did not read as one.** One word in 16 px was followed by fifteen lines of equal weight. On a NO, nothing below the first line can be acted on. The order inputs and "I passed" invited action on a name the cascade had killed. |
| 3 | **Five Pillars check**, the AIXI row + its folds | `AIXI 1.86 −3.6% P G R F N 0/5`, `▾ 4 red on the day — not candidates: BIAF INHD FLYE IPW`, `▾ 1 no print yet: SHPH` | the pillars for every name on the desk | **A list of non-candidates.** All six names were out. The board drew five red letters for the one that scored 0/5 and folded the rest, so the useful answer — *nothing here is in play* — had to be inferred. |
| 4 | **Time & Sales** | `FLYE no print yet · STARTING · starting shortly — IBKR allows one tape request per name every 15 s · the tape is on FLYE; it follows the name you select (a viewer reads the owner's) · no prints yet` | the selected name's prints | **A bug and developer text.** AIXI was selected, but the tape was on FLYE and never started. The card explained IBKR's pacing rules rather than saying what to do. |

**Missing from the screen:** a desk-level answer — *is there anything to
trade right now?* Every zone answered a question about one name. Nothing
said that all six names were NO.

### The tape bug, diagnosed

`postFocus` posted the selected name, and `render()` re-posted it every 5 s
whenever the tape was on another name. Two tabs on the desk each did this
for their own selection: a tab left open from an earlier launch, and the one
`day.py` opens on each manual launch. Each post cancelled the other's
request. `TapeFeed._schedule` then held each name for IBKR's 15-s pacing, so
the tape sat in `STARTING` — "starting shortly" — and never ran.

The two-tab state could not be reproduced on the owner's machine from here.
The mechanism is read from the code, and it matches the screenshot's text
exactly.

## 3 · How Ross works the screen (the corpus, read this session)

| what | his words | where |
|---|---|---|
| the scanner set he opens | *"top gainers… pull up a couple other scanners. This one's small cap high of day momentum… my running up scanner… my halt scanner"* | w97KlUrVDk0 @00:48:44–00:49:03 |
| the first look is the alert, not the chart | *"anytime a stock hits a scanner, the first thing I do is I look at the details of the alert… And then I click on the ticker. I check the sector…"* | w97KlUrVDk0 @00:59:47–00:59:59 |
| the verdict is fast | *"if I don't see something right away that I like, then I just move on to the next one."* | ZfwTJAMLroA @00:30:30–00:30:35 |
| at entry his eye is on the tape | *"So, where is my eye? It's mostly on the time and sales right here and on the ask price. And I glance over at the chart"* | ZfwTJAMLroA @01:08:06–01:08:14 |
| Level 2 and the tape go together | *"they really should always just be together because you can't really, at least for my strategy, use one without the other."* | ZfwTJAMLroA @01:45:34–01:45:41 |
| the morning starts at the scan | *"usually by 7:00 a.m. I'm sitting down and I'm looking at the scan"* | wlH8zKZ8vXA @00:44:13–00:44:15 |
| "nothing" is a verdict | *"If I haven't taken a trade by 10:00 a.m., then that's it. I'm going to shut it down. No trade Friday and I'm fine with that. I'd rather have a no trade day than a red day."* | -Aj8oowFAFY @00:33:08–00:33:16 |

The course's minimum workstation lists *"linked 1-minute, 5-minute and daily
charts; Level 2/order book; Time & Sales/tape; … scanners and news/catalyst
panel"*, and adds that L2 and T&S *"Neither should be interpreted alone"*
(`…/day-trading-basics-preview-mastery.md` §"Minimum layout"). The
selected-symbol rule: *"Click one scanner row and both charts, quote header,
news and all symbol-dependent panels switch to the same instrument"*
(`…/dashboard-scanner-chart-knowledge.md`, marked there as clean-room
design).

## 4 · Brainstorm: what a desk for this routine must answer, in order

His morning has a fixed order: scan at 07:00, read the alert details, click,
check the news, read the chart, and at entry watch the tape and the ask.
"Nothing" is a legitimate result. That gives the desk an order of questions,
each with one place on screen:

| # | question | where it is answered now | rule it follows |
|---|---|---|---|
| ① | is the data live? | top bar: feed state, clock, session badge | provenance first |
| ② | **is anything in play?** | **top bar: the desk verdict** — `NOTHING TO TRADE`, or the best word and its names | his no-trade day is an answer, so the desk says it in words |
| ③ | which names, and why not the others? | **Five Pillars · verdicts**: names in play, each with the server's word and one reason; every NO folded into one line that opens to its killing reason | one reason kills a name; rejects one click away, never silent |
| ④ | this name: what is the answer? | **the card's top block**: the word in 30 px, the name, what to do (`skip it` / `keep it on screen` / `hands off until the level` / `read the chart and the tape`), the reason | verdict first |
| ⑤ | what would change it? | the level line: `changes only if back over 2.00`, `level reclaim the 9 EMA 4.90` | one level, not a list |
| ⑥ | which pillars pass? | five value chips: `✓ price $4.88 · ✓ gain +62.7% · ✓ RVOL 7.2× · ✓ float 9.0M · ✓ news STRONG today 09:44` | his first look is the alert's details |
| ⑦ | does the chart agree? | four chips, VWAP · 9 EMA · MACD · pullback volume, **only on a name the cascade let through** | a context gate is not shown where it cannot decide |
| ⑧ | does the tape agree? | the tape line on the card; the Time & Sales card, following the window you look at | his eye is on the T&S at entry |
| ⑨ | the order | trigger, limit, stop, shares at your risk, bid × ask. **Only when an order can exist** | the stop defines the size |

Design rules carried in from the earlier audits, kept:

- **One home per fact.** A number shown in two places drifts in one of them.
- **Colour encodes the word and the gate state**, never price direction.
- **The browser picks what to show, never what to conclude.** Every word,
  reason, level and lamp comes from `decision_card.py`. The desk verdict and
  the list rank the server's words; they never recompute them.
- **Every minute is labelled.** Scrubbed back to an earlier frame, the top
  bar, the header and the list now say which minute the verdicts are from.
  The card always did. In the replay at 09:00, 10:30's WAIT used to show
  with no label.

Ideas weighed and not built today:

| idea | why not now |
|---|---|
| a phase line (e.g. "pre-market — the bot's entries start at 07:00") | the card's own WATCH reason already says this per name; a desk-wide line needs the session boundaries in one place first |
| a "no trade by 10:00" nudge | that is his personal stop rule (-Aj8oowFAFY @00:33:08), not this exercise's window, which is preregistered (`docs/preregistration.md` §5). Changing the window is the owner's decision, asked and not yet answered |
| a verdict column in the maximized pillars table | the maximized table stays the audit view; next pass |
| real Level 2 | owner, 2026-10-09: "not yet" |

## 5 · The plan, and what was applied the same morning

| zone | before | now |
|---|---|---|
| top bar | no desk-level answer | **desk verdict**: `NOTHING TO TRADE · 6 names judged · every one is NO`, or `WAIT DVLT · ABCD · BRXO +1 · 4 of 10 in play`. A click shows the first name. Scrubbed back, it adds `as of 10:30` and dims |
| symbol header | two lines, 18 numbers | **one line**: name, price, change, the server's word and reason; `HALTED` and a stale print only when true |
| decision card | NO + 15 lines of equal weight | **verdict first**: word, name, action, reason; the level; five pillar chips; chart chips, setup, tape, headline, bot line and warnings only on a name in play; the rest under **"Why, in full"**, closed and remembered |
| order area | risk input, "No order", "I passed" and the float box on every card | **hidden on a NO** unless a position is open. Bid × ask moved into the order grid. The float box is folded and says what it changes (the board's chips only — the bot reads its own source) |
| Five Pillars board (column) | a pillar table of every name, red ones folded | **a verdict list**: a funnel line, names in play with word, reason and missing pillars, and `▸ N NO — show why` |
| Time & Sales | another name's tape, developer text | **tape on another name**: one line, `The tape is on FLYE, not on AIXI.`, plus a `show AIXI` button on the live desk. **Starting**: `AIXI starting…`, with IBKR's pacing in the tooltip |
| tape focus | every repaint re-posted the selection, so two tabs fought | a hidden tab never asks. A click, a page opening and a tab coming into view take the tape. A repaint re-asks only when the desk's tape has no name (a restarted desk) |

Screenshots: `after_wait_1030.png` (a WAIT name, replay of 2026-09-01 at
10:30), `after_no_card.png` (a NO name, the NO fold open) and
`after_no_card_why_open.png`. `after_nothing_to_trade_SYNTHETIC.png` is
**synthetic**: every card's word was set to NO in the browser to show the
empty desk. The replay day itself has names in play.

Tests:

- `tests/test_dashboard.py`:
  - new: `test_ui_the_desk_says_whether_anything_is_in_play`, `test_ui_a_no_card_carries_nothing_to_act_on`;
  - rewritten for the new layout: the board, header, verdict, tape and gate-4 tests.
- `tests/test_live_ui.py::test_the_page_asks_for_the_tape_only_when_it_needs_to` covers the tape fix. A repaint leaves another window's name alone; a click takes it back; a hidden tab never asks; a tab coming into view takes it; a restarted desk is asked again.

## 6 · What this could not check

- **The live two-tab state on the owner's Mac.** The diagnosis comes from the
  code and the screenshot's text. If the tape still sticks with one tab open,
  that is a different cause; the next screenshot will show it.
- **YouTube.** No video was watched. Ross's layout comes from his own words
  in the transcripts.
- **The verdicts are the server cascade's, with its amendments.** Under A5 a
  name down on the day can still pass 4 of 5 pillars. If the cascade lets it
  through, the list shows its word, with `✗ gain` beside it, rather than
  hiding it.
- **The maximized pillars table** (E on the board) is unchanged: still the
  13-column audit view, folds included.
- **No Level 2**, by the owner's choice.

## 7 · Verdict

**The verdict was on the screen at 05:30, but four zones of equal weight
buried it, and no zone answered the desk-level question.** The redesign
answers in this order:

1. the top bar — is anything in play;
2. the list — which names, and why not the others;
3. the card — the word, the reason, the level, the pillars;
4. the order — only where an order can exist.

The tape bug was two tabs fighting over IBKR's pacing, fixed by giving the
tape to the window you are looking at.
