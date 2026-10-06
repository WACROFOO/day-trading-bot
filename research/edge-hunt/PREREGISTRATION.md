# Edge hunt — preregistration

Written 2026-09-26, **before the first run of any family below**, and
committed before it; the git history is the proof of order. Code:
`scripts/edge_hunt/`. Holdout openings are recorded in
`research/edge-hunt/holdout_ledger.jsonl`, one line per opening, committed.

The question: is there a version of the bot, built from Ross Cameron's rules
or from new hypotheses stated as such, that is positive after costs on data
it was never tuned on? If not, the answer is "no edge", said plainly.

---

## 1. The benchmark — his figures, as the knowledge base records them

All from `knowledge-base/strategies/PARAMETERS.md` §9, which cites the source
of each:

| figure | value | source cited there |
|---|---|---|
| lifetime accuracy | **69 %** over 24,268 day trades; **70 %** over 15,000+ trades since 2017-01-01 | `blog/core-strategy/bull-flag-trading`; `blog/recaps/trade-recap-max-loss` |
| best month of a year (February) | accuracy **68 %**, average winner $1,870, average loser $1,318, win/loss **1.42** | `blog/community-company/behind-trades-get-trading-rut-ep-7` (his TraderVue report) |
| losing month (April) | accuracy **60 %**, win/loss **0.57**, net −$4,229 | same |
| expectancy recomputed on the best month | **+0.65** in units of his average loss | PARAMETERS.md §9 |

Two cautions the same file already states and which bind the comparison:

* His **R is his average loss**, not a planned stop. Every result below is
  also reported as win rate, average win ÷ average loss, and expectancy per
  average loss, so the two can sit side by side.
* His stop is **mental**, ours rests: *"do not compare the result to his
  69% / 1.42 as though they were the same instrument"* (PARAMETERS.md §5,
  citing `-Aj8oowFAFY` [22:47] and `yKV3C2DoaFg` [28:46]).

The broker-statement article (`knowledge-base/warrior-blog/tools-platforms/583-to-1mil.md`)
holds only images in the knowledge base; its figures are not extractable
and are not used.

## 2. Data, and what does not exist

| input | source | limit, stated |
|---|---|---|
| universe | `research/first-pullback-edge/data/candidate_days.csv`: 25,716 gapper-days 2016-02 → 2026-08, survivorship-free; 23,215 with ≥ 40 bars in the store | chosen on the **09:30 gap** — a pre-market name that faded below +10 % by the open is missing (favours pre-market; audited in F2) |
| bars | Alpaca SIP 1-minute, 04:00–16:00 ET, raw, cached `data/cache/history/` | one-minute resolution; intrabar order unknown except on the F3 subset |
| catalysts | Alpaca historical news, `created_at` ≤ decision time | a missing headline is not proof of no news |
| float | SEC `dei:EntityCommonStockSharesOutstanding` (else us-gaap), latest **filed before** the day, ≤ 400 days old — an **upper bound** on float | only tickers in the SEC's *current* map (3,104 of 5,797 names) — delisted names mostly absent: a survivorship bias, reported by year |
| ticks | Alpaca trades on a subset (F3) → 10-second bars | subset only |
| quotes | Alpaca NBBO in the minute of 1,320 sampled fills → the spread proxy | sampled moments, not every trade |
| **Level 2 history** | **does not exist** in any source available here | not simulated, not approximated |
| halts | none historical | a stop gapped through fills at the next bar's open |

## 3. Split and holdout discipline

| split | dates | sessions | symbol-days |
|---|---|---|---|
| train | 2016-01-01 → 2022-12-31 | 1,701 | 12,185 |
| validation | 2023 | 247 | 1,687 |
| **holdout** | 2024-01-01 → 2026-08-21 | 662 | 9,343 |

* Each family chooses on train, confirms on validation, and opens the
  holdout **once**, for **one** configuration. `protocol.open_holdout`
  refuses a second opening of the same family.
* **Validation gate:** if the family's chosen configuration is not positive
  (net, one-position portfolio, ≥ 30 trades) on validation, the family fails
  there and its holdout stays closed.
* **Contamination, declared.** On 2026-09-26, before this document,
  2024-2026 was read as the "test" of `scripts/backtest_history.py` and
  `scripts/ablation_history.py`: the desk's pullback entry under 288 gate ×
  exit × window combinations, 23 filter levers (including stop floors of
  1 %, 2 % and $0.05) and 13 exits. Those numbers are known to me. Any
  family whose chosen configuration re-uses one of those levers on the
  desk's entry (F4 above all) is marked **CONTAMINATED**: it may pass the
  rule, but it goes live only behind a switch that stays OFF until a
  prospective paper sample (≥ 200 trades from 2026-09-28 on) confirms it.
  The future is the only holdout nobody has read.

## 4. The adoption rule

On the holdout, the one-position portfolio (the bot's constraint,
`runner.max_positions = 1`) of the chosen configuration must show, net of
the costs in §5:

1. a positive mean R per trade;
2. a day-clustered bootstrap lower bound above zero, at one-sided
   α = 0.05 / 2 / 6 = **0.42 %** — 95 % two-sided, Bonferroni-corrected over
   the six families this document allows;
3. at least **200** trades;
4. a positive mean in at least **2 of 3** holdout years (2024, 2025, 2026);
5. a mean above the **random-entry baseline on the same names**: per trade,
   K = 20 market entries at the open of random bars in the same window of
   the same symbol-day, the same stop distance in % of price, the same exit,
   the same costs; the day-clustered 95 % lower bound of (trade − baseline)
   must be above zero.

All five, or not adopted. Multiple testing inside a family is handled by the
split itself — one configuration reaches the holdout — and every
configuration evaluated is counted in `results/registry.jsonl` and reported.

## 5. Costs

`scripts/edge_hunt/costs.py`, at the owner's stated $20 risk a trade:
IBKR **fixed** commissions (primary) and **tiered** (sensitivity, with the
exchange, clearing and FINRA fees the fixed plan includes), plus on every
marketable side half the quoted spread from a proxy **calibrated on real
Alpaca NBBO quotes** from train and validation fills only (price tier ×
pre-market/regular × five-minute dollar volume), plus one cent. The proxy
table is frozen in the results folder (spread_proxy.json) before the first
holdout opening; holdout-period quotes are used only to report its error.

## 6. The families and their grids

Base **B0** = the desk today: the live detector's plans
(`scripts/edge_hunt/plans.py`), all six gates green (price, still-rising,
VWAP, 9 EMA, MACD, pullback volume), A10 stop-limit with realistic fills,
trail 1 R, flat 11:30, no stop floor.

Every feature is point-in-time at the plan bar's close (§8).

### F1 — selection: which gappers run

Conditions on B0 (25): gain now ≥ 20 / 30 / 50 / 100 % · pre-market volume
≤ 2 M (the ceiling in PARAMETERS.md, `ZfwTJAMLroA` [13:21]) · pre-market
volume ≥ 250 k (mine — the corpus sets no floor) · relative volume (cumulative ÷ 20-day average daily shares)
≥ 1.5 / 3 / 5 (FILTERS.md Layer 3 gives 1.5 and 3) · session volume ≥ 1 M
(FILTERS.md Layer 3) · SEC shares outstanding ≤ 5 / 10 / 20 M (PARAMETERS.md
`float_max_hot` 20 M, `float_max_cold` 5 M) · a headline since the previous 16:00 · no headline ·
former runner (same name, +50 % in the last 250 sessions) · not a former
runner · first +10 % before 07:00 / 07:00–08:59 / from 09:00 · price $2–5 /
$5–10 / $10–20 · rank 1 / top 3 of the session by dollar volume so far.

Each × stop floor {none, skip under 2 %} = 50; then all pairs of the six best
singles on train (15) and all triples of the best four (4): **69**.
Ranked on train (plan level, ≥ 300 plans); the best validation portfolio of
the top five goes to the holdout.

### F2 — pre-market, 07:00–09:30

Entry {B0's pullback · pre-market-high break: buy stop at the running high
+ 1 ¢ once that high is ≥ 3 bars old and the close is within 3 % of it,
stop under the last five lows, first per symbol-day} × window {07:00–08:00,
08:00–09:30, 07:00–09:30} × stop {none, skip under 2 %, widen to 2 %} ×
exit {trail 1 R, trail 2 R, fixed 2 R} × selection {none, gain ≥ 30 %,
headline, relative volume ≥ 3} = **216**. Same choosing procedure.

Plus an audit that chooses nothing: on sampled sessions, names that were up
≥ 10 % pre-market ($2–20, 20-day dollar volume ≥ $250 k) but are missing
from the 09:30-gap universe, run through the chosen configuration. At the
holdout opening the same audit runs on holdout sessions; if the missing
names' mean, weighted by their share, turns the combined mean non-positive,
criterion 1 fails. Also reported, train only: pre-market against regular
hours on the same symbol-days ("pre-market first", mechanically).

### F3 — ten-second micro-pullbacks

Subset: symbol-days with a filled B0 plan 07:00–10:30, sampled train 150,
validation 60, holdout 250; ticks → 10-second bars. Detector: an impulse of
≥ X % inside six bars with ≥ 3 green, then 1–3 red bars retracing ≤ 50 %,
trigger at the first bar to take out the previous bar's high, stop under the
pullback; Layer 2 (VWAP, 9 EMA, MACD) on completed 1-minute bars. Grid:
X {2 %, 4 %} × stop {none, skip under 1 %, skip under 2 %} × exit {trail 1 R,
fixed 2 R} = **12**. The one-minute B0 plans on the same symbol-days are
reported beside it.

### F4 — exits and sizing (CONTAMINATED, see §3)

Stop rule {none, skip under 1 / 2 / 3 %, widen to 2 / 3 %, skip under 4 ×
the estimated half-spread, skip under $0.05 / $0.10} × exit {trail 0.5 /
1 / 1.5 / 2 R, fixed 2 / 3 R, break-even at 1 R then trail 2 R, ladder
1 R/2 R and 2 R/3 R (PARAMETERS.md §6: half, stop to break-even, a quarter,
a quarter trailed), a five-minute time stop with trail 1 R, the new-low
candle} = **99**; then, on the train-best, daily discipline {none, stop
after the first loss, after two losses, at −2 R on the day, after the first
win ≥ 1 R} (5) and sizing {flat, 1.5 × when a headline AND ≤ 20 M shares /
0.5 × when neither, the inverse as a control} (3) — **107**.

### F5 — new hypotheses, stated as hypotheses

* **H5.1 opening-range breakout on the session's leaders.** Among names
  ranked ≤ k by dollar volume at 09:35 and up ≥ 10 %, with a green first
  five-minute candle: buy stop at that candle's high + 1 ¢ until 10:30, stop
  under its low. k {1, 3} × stop {candle low, widened to ≥ 2 %} × exit
  {trail 1 R, trail 2 R, fixed 2 R, fixed 3 R} × flat {11:30, 16:00} = 32.
* **H5.2 first VWAP test.** 09:35–10:30, up ≥ G %, above VWAP for ten
  minutes, a bar whose low touches VWAP (≤ 0.2 % above) and closes above it:
  buy stop at its high + 1 ¢, stop under its low widened to ≥ 2 %. G {20,
  40} × exit {trail 1 R, fixed 2 R} × stop {as is, widened} = 8.
* **H5.3 hot market.** B0 only when at least k session names are up ≥ 30 %
  at the plan minute, k {2, 4, 6} = 3.
* **H5.4 hold past 11:30.** B0 with flat 16:00, trail 1 R / 2 R = 2.

**45** configurations, one opening.

### F6 — combined

Opened only if two or more families pass: their chosen configurations
together, nothing re-tuned.

**Total grid: 69 + 216 + 12 + 107 + 45 = 449 configurations, at most six
holdout openings.**

## 7. What happens to a pass, and to a failure

A passing configuration is built into the live bot behind a named switch
(default OFF where §3 marks it contaminated), with tests, and recorded in
`docs/preregistration.md` §5 as the owner's decision to take. A failure is
recorded there too, with its numbers. Nothing is tuned on live fills; the
forecast-versus-actuals run (`scripts/backtest_history.py --ledger`) is a
calibration check, never an input.

## 8. Look-ahead controls

* Features read bars stamped ≤ t, headlines created ≤ the close of bar t,
  SEC values filed before the day, and earlier sessions only.
* Entries arm after bar t closes and fill from bar t + 1 under A10.
* Tested in `tests/test_edge_hunt.py`: truncating the bars after t changes
  no feature and no plan up to t; the holdout guard refuses a second
  opening; the random baseline is deterministic and window-bound; costs
  match hand-computed cases.


---

## Addendum 2026-09-28 — F7, the leader breakout (from his own trades)

Written before F7's first run, after `research/ross-trades/` measured his
trades on the tape: at the minute before his entry his name was the #1 gainer
among names then up ≥ 10 % in 57 % of cases (top 3: 88 %), 90 % of his entries
buy a new high of day, and he holds a median 2 minutes. F7 mechanises exactly
that, on the point-in-time runner universe (`scripts/edge_hunt/pit.py`,
269,508 symbol-days 2016-2026 with 1-minute bars 04:00-12:00 ET, split days
removed) — a universe no earlier family used, so its holdout is unread.

* **Leader at minute t:** among names with last price ≥ +10 % over the
  previous close, $1-20, ≥ 50,000 shares since 04:00, all from bars stamped ≤ t
  — the one with the largest gain.
* **Entry:** a buy stop-limit at the leader's high of day + 1 ¢ (A10: cap
  +0.3 %, 3-minute TTL), armed at the close of t; one trade per symbol-day,
  one position at a time.
* **Grid (18):** stop {low of the arming bar − 1 ¢, 3 %} × exit {fixed 1 R,
  trail 1 R, bail after 2 minutes unless +1 R then trail 1 R} × window
  {07:00-09:30, 09:30-11:00, 07:00-11:00}; flat 11:30.
* Same split, same five-part rule, same costs. Seven families are now allowed,
  so the corrected one-sided α is 0.05 / 2 / 7 = 0.36 %. Random baseline: the
  same leaders' symbol-days, random minutes in the window.

---

## Addendum 2026-09-29 — F8, the leader breakout where the spread is small

Written before F8's first run. F7 was +0.171 R gross a trade on train and lost
it to costs (−0.167 net; spreads and commissions 0.2-0.34 R). F8 asks the one
question that result leaves open: **does F7 survive when it only trades where
the round-trip spread is small against the stop?**

* **Base:** F7 exactly (leader, entry, one position, the 18-configuration grid).
* **Filter, known at arming:** the estimated round-trip spread — twice the
  `SpreadProxy` half-spread at the trigger price, from the arming bar's
  pre-market flag and trailing 5-minute dollar volume — must be ≤ X × (trigger −
  stop), X ∈ {0.05, 0.10, 0.20}. 54 configurations.
* **Costs:** the preregistered model at the owner's live sizing: $40 risk a
  trade and at most $2,000 of position value (`docs/preregistration.md` §5,
  2026-09-28). F7 was costed at $20.
* **Choice:** rank on train (2016-2022, n ≥ 300), top 5 read on validation
  (2023), best with n ≥ 30. Holdout (2024-2026) opens once, only if that
  validation mean is positive; five-part rule unchanged. **Eight families are
  now allowed: one-sided α = 0.05 / 2 / 8.**

**Known weaknesses, stated before the run.** (1) The filter and the cost model
use the same spread proxy, so on paper the filter selects exactly the trades
the model charges least; a proxy that under-states real spreads flatters F8
twice. (2) F7's 2023 validation was already read (gross +0.008), so F8's
validation is not blind to the base rule; only the holdout is. (3) The $40 /
$2,000 sizing differs from F7's $20, so part of any F8-vs-F7 difference is the
commission minimum, not the filter; F7 at the new sizing is printed beside it.

---

## Addendum 2026-10-01 — R-audit: the bot's operating rules, one at a time

Written and committed before `scripts/rules_audit.py` first runs. The owner
asked which of the bot's operating rules hide profit and which protect it:
rule 5 (still rising) and every safety, order and exit rule (E, F, G in the
plain-language list of 2026-10-01). This is not a search for an edge — every
configuration measured so far loses after costs — it is a measurement of what
each rule does to net R, drawdown and trade count.

**Data.** The 2,608-session Alpaca SIP 1-minute cache (`data/cache/history`,
04:00-16:00 ET, pre-market volume included) over the candidate-day universe of
`scripts/backtest_history.py` (opened $2-20 with a ≥ 10 % gap; reverse-split
days dropped). Train 2016-2023, test 2024-2026. **The test years are not
pristine:** the 2026-09-26, 09-29 and 09-30 ablations read them for filter
levers. That is why the rule below demands consistency on both periods and a
multiple-comparison correction.

**Baseline B = the live rules on 2026-10-01.** The desk's detector; price
$2-20; still rising (≤ 25 % off the day's high); VWAP, 9 EMA, MACD and pullback
volume green; stop ≥ 2 % of price (A13); stop ≥ 4× the spread, the spread from
the edge hunt's proxy at the arming bar (A6 — never modelled in a backtest
before); plans armed 07:00-11:20; one position, the slot held from the order to
the exit (an unfilled stop-limit holds it until its 3-minute expiry, as
`positions_alive` does live); daily limits as `journal.risk` (−3 R, 3 losses
≤ −0.25 R in a row with scratches skipped, 6 orders, all on gross R as the live
gate reads); entry A10 as `backtest_recent` (re-touch within 3 bars, cap +0.3 %,
1 ¢ minimum, opening above the cap fills only on a return); exit A3 trail 1 R;
flat 11:30; costs `backtest_recent.cost_r` model "live" ($40, $2,000 cap,
spread proxy + 1 ¢). Not modelled: the pillar count (no historical float or
news), halts, the 2-minute signal clock, the 30-second quote clock, the
15-second stop enforcement and the monitored pre-market stop — those are
judged on the live ledger and the incident record, not here.

**Variants, one at a time against B (K = 41):**

| rule | variants |
|---|---|
| 5 still rising | off-the-high limit 15 % · 35 % · 50 % · off |
| E1 window | start 08:00 · 09:30; end 10:30 · 11:00 · 11:30 (no A8 buffer) |
| E2 stop floor | off · 1 % · 1.5 % · 3 % |
| E3 stop vs spread | off · 2× · 3× · 6× |
| E6 positions | 2 at once · no cap (one per symbol) |
| E7 daily limits | all off · loss −2 R · loss −4 R · streak 2 · streak 4 · orders 4 · orders 8 |
| F1 sizing | $20 risk · $80 risk · no $2,000 cap |
| F2 entry order | expiry 1 · 5 bars; cap +0.5 % · +1 % |
| G1 trail | 0.5 R · 1.5 R · 2 R |
| G4 flat time | 11:00 · 12:00 |
| Ross volume (new, tightening) | push volume rising (second-half mean ≥ first-half mean) · push volume elevated (push mean ≥ mean of the 10 bars before it) |
| MACD reading | MACD line above zero AND above its signal |

**Adoption rule.** A variant replaces B only if, in the one-position portfolio
with costs: (1) its mean net R per trade beats B's on train AND on test;
(2) it has ≥ 200 test trades; (3) it beats B in at least 2 of the 3 test years;
(4) the day-paired bootstrap lower bound of (variant − B) mean net R per trade
on test is above zero at one-sided α = 0.05 / 41. For the risk rules (E6, E7,
F1) a change must also not worsen the test-period maximum drawdown in R by more
than 10 %, and a variant that only lowers drawdown is reported, never adopted
on that alone. A rule Ross states in his own words is never relaxed on this
test alone: if it passes, it is flagged to the owner with the data.
**Sensitivities, never deciding:** an intrabar entry model (fill on the
trigger bar itself, the way the live desk arms while the bar forms) and the
"old" cost model (one cent a side).

### Addendum 2026-10-01b — after the adversarial review, before the corrected run

The first run (`research/paper-exercise/reports/rules_audit_output.txt`) put
three single variants through the rule above — no entries before 09:30, stop
≥ 3 %, stop ≥ 6× spread — and, wrongly, $80 risk. A three-lens adversarial
review reproduced every number exactly and found that the backtest's way of
reading a 1-minute bar is the most favourable one for those passes:

* on a fill at the cap after the bar opened above it, the bar's high (which
  came BEFORE the fill) ratcheted the trail;
* a fill-bar low under the stop always stops the trade, though it may have
  come before a fill at the trigger;
* the trail tests each bar's low before its high, where the live trail
  follows the 10-second tape;
* the order expiry counts bars, not minutes.

Under the corrected readings the reviewers measured the singles failing and
a post-hoc combination (no pre-market entries + stop ≥ 3 %) surviving most
but not all corrections. Those numbers are known to me before this run.

**Rules for the corrected run (`scripts/rules_audit.py`, `MODES`).** Mode A
is the preregistered run, unchanged. Mode C corrects the cap-return fill bar
(ratchet with max(fill, close)) and counts the expiry in minutes. **A change
is adopted only if it passes the adoption rule above under BOTH A and C** —
stricter than the original rule, never looser. Reported, never deciding: CA
(C + fill-bar low before a fill at the trigger), H (C + high first on every
later bar), the "old", "light" and gross cost models, and an intrabar entry
gated on the last completed bar (the live desk never sees the trigger bar's
close; the first run's intrabar figures used it and are withdrawn).
**Sizing variants are judged in dollars**, not R. **The two post-hoc
combinations** (09:30 + 3 %; 3 % + 6×) are not among the preregistered
variants and reuse levers read on 2024-2026: by §3 they are CONTAMINATED and
can only go live behind a switch that stays OFF until ≥ 200 prospective paper
trades confirm them. **Two Ross-retracement variants are added (K = 43):**
the pullback may give back at most 50 % of the push (impulse high minus the
first impulse bar's open) — with rule 5, and instead of it. His words:
*"50% is a hard cut ... I prefer to be consolidating in the top 20% 25%"*
(DP4ayEWhmvM 00:30:17); *"I never want to see the price retrace more than 50%
of the move"* (HYoQYCBW4sw 00:34:22). Never run before this addendum.

### Addendum 2026-10-01c — three opening-risk candidates, written before any run

**Origin.** One live paper trade, outside the data: NXL 2026-10-01, a plan
(trigger 8.87, stop 8.58, 3.3 %) built on two pre-market candles that moved
0.28 and 0.27, filled at 09:30:23 and stopped five seconds later at 8.48
(−1.41 R) in an opening minute that ranged 8.26–9.08 (Alpaca SIP). It was
NXL's fifth armed plan of the day. The ten-year plan cache ends 2026-08-21,
so the trade that suggested these rules is not in the sample. None of the
three has been computed on any data before this addendum.

**The three deciding variants (K becomes 46, α = 0.05 / 46 for these three).**

| id | rule | plan field |
|---|---|---|
| O1 | stop distance ≥ 1.0 × the mean high–low range of the 5 completed 1-minute bars before the trigger bar | `range5` |
| O2 | no fill in the first 2 minutes of regular hours (a fill bar of 09:30 or 09:31 is cancelled) | fill-bar time |
| O3 | at most 3 armed plans per name per day; the 4th onwards is refused (count includes plans the filters killed) | `plan_index` |

**Adoption rule:** unchanged and as strict as addendum 2026-10-01b — train
and test better than B, ≥ 200 test trades, better in 2 of 3 test years,
day-paired bootstrap lower bound > 0 at α = 0.05 / 46, under BOTH mode A and
mode C. **Reported, never deciding:** O1 at 0.5× and 1.5×, O2 at 1 and 5
minutes, O3 at 1, 2 and 5 plans, and all three together.

**Contamination, stated in advance.** O2 sits next to E1 "start 09:30"
(read on 2024-2026, fails) and O1 next to E2 "stop floor" (read, fails). They
are different rules (a two-minute window, not the whole pre-market; a stop
relative to recent volatility, not to price), but a pass by O1 or O2 is
flagged as adjacent to a read lever. Any pass goes live only behind a switch,
OFF, until ≥ 200 prospective paper trades confirm it.

### Addendum 2026-10-02 — tick replay, written before its first read-out

`scripts/tick_replay.py` replays the gate-passing plans of 2024-01-01 onward
(2,577 plans, 1,666 symbol-days) on Alpaca SIP prints in time order: the A10
stop-limit entry, the stop, the A3 trail moved every 5 s, the 11:30 flat. It
reads the prevailing NBBO at the fill and at the exit. A ten-plan smoke test
was looked at to check the plumbing; nothing else.

**What it decides.** Only how the existing bar readings rank: the mean per-plan
gap between each bar mode (A, C, CA, H) and the tick replay, and the B
portfolio's net R per trade under ticks with the proxy spread and with the
real spread. **What it may not decide.** No rule is adopted or dropped on
this run. A variant from the rules audit or addendum 2026-10-01c that changes
verdict under ticks is reported as such and goes to a new preregistered run
with the tick reading as the reference, never switched on from here.

### Addendum 2026-10-02b — stage 2, the desk-time replay, before its read-out

`scripts/desk_replay.py` takes every 2024+ plan that passes the live gates
not tied to the trigger candle (7,477) and rebuilds the moment the live desk
arms it: the close of the 10-second candle holding the first print above the
trigger, plus 4 s of rebuild and runner latency; the chart gates and "still
rising" judged on the half-formed minute at that moment; then the order on
the prints as in stage 1. An eight-plan smoke test was looked at for
plumbing. **It decides** only how far the bar-close backtest sits from the
desk as it runs (gate flips, seconds gained, net R of B under each reading).
**It may not decide** any rule; the 10-second-timed entry (stage 3) gets its
own preregistration on this output.

### Addendum 2026-10-02c — stage 3 (10-second entries) and the partial exit, before any run

**Base.** Every plan the live desk would send at desk time (stage 2, gates
judged on the half-formed minute), replayed on SIP prints. Reference **D**:
the A10 stop-limit at the trigger, the plan's 1-minute stop, the A3 trail,
the 11:30 flat. Costs: the REAL spread at each fill (prevailing NBBO), half
of it plus 1 cent per marketable side, IBKR fixed commission per order (a
limit target leg pays no spread, only its commission). $40 risk, $2,000 cap,
one position, the daily limits — `rules_audit.portfolio`.

**Three deciding variants (K = 49, α = 0.05 / 49).** All keep the plan's
1-minute stop and 1 R = trigger − stop.

| id | variant |
|---|---|
| S3-dip | after the desk arms, wait for a 10-second micro pullback (1–3 closed 10-s candles with no new high, lows above the stop) and buy the break of the last one's high + 1¢ (same stop-limit, cap +0.3 %); a 4th candle without a new high resets; 3 minutes from the arm, then cancelled |
| S3-confirm | skip a false break: the order goes in only if the 10-s candle AFTER the crossing candle closes at or above the entry; sent at that candle's close + 4 s |
| P-half2R | the D entry; half the shares sold by limit at +2 R, the rest on the A3 trail; a stop before +2 R takes all |

**Reported, never deciding:** P-half1R (half at +1 R), S3-dip with P-half2R,
and every variant under the proxy spread.

**Adoption rule — stricter than before, because ticks exist for 2024-2026
only, so there is no train period:** ≥ 200 trades; mean net R better than D
in EACH of 2024, 2025 and 2026; day-paired bootstrap lower bound > 0 at
α = 0.05 / 49. A pass goes live only behind a switch that stays OFF until
≥ 200 prospective paper trades confirm it.

### Addendum 2026-10-02d — reaction speed (arming latency and loop period), before any run

**Question (owner, 2026-10-02):** how much would acting faster than the 10-s
candle + 5-s loop improve results, pre-market and regular hours?
**Base:** the stage-3 D trades (desk-time plans passing the live gates, a
measured D fill), on SIP prints, real spreads, $40 / $2,000, `rules_audit.portfolio`.
**Two knobs, a 4 × 5 grid, every cell re-simulated:**
- arming: 10-s candle close + 4 s (live, measured median 3-4 s plan→runner),
  10-s close + 1 s, 5-s candle close + 2.5 s, the crossing print + 1 s;
- loop period (pre-market trigger sampling, the pre-market monitored stop,
  and the A3 trail moves): 1, 2, 5 (live), 10 s, and continuous as a bound.
Pre-market (fill before 09:30) exits are monitored: sampled at the loop
period, filled at the last print at the sample (the cost model adds half the
real spread + 1 cent). Regular-hours stops rest at the broker and trigger on
the first print through them; only the trail moves at the loop period.
Gates stay as the desk judged them at its 10-s moment, so only timing moves.
**It decides** only execution cadence (no selection rule): a faster setting is
worth building if it improves net R per trade in each of 2024, 2025 and 2026
in the session it targets. Reported per session and per year.

### Addendum 2026-10-02e — runner + 10-second micro pullback + 5-minute confirmation, before any run

**Question (owner, 2026-10-02, after AMOD):** enter names the Running Up
scanner flags as climbing, even with no 1-minute pullback, at a 10-second
micro pullback, confirmed by the 5-minute chart. How does it perform before
costs, and what does each cost component take in a real trade?

**Sample, fixed now.** Symbol-days of 2024-01-02 → 2026-08-21 with at least
one `running_up` alert 07:00–11:30 at $2–20 in the replay of the live
scanner classes (`research/paper-exercise/reports/2026-10-02-running-up-study/`,
`alerts.pkl` in the session scratchpad). 300 drawn with `random.Random(20261002)`
from the sorted list. Ticks: Alpaca SIP, first alert's 10-minute chunk to 11:30.

**Setup S (primary), every element point-in-time:**
- *runner*: armed from a `running_up` alert bar's close for 10 minutes;
- *5-minute confirmation*: the last COMPLETED 5-minute bar (from the cached
  1-minute bars, 04:00 on) closes above its 5-minute EMA9, and 5-minute MACD
  (12, 26, 9) line > signal;
- *10-second micro pullback*: the 6 ten-second bars before the pause hold
  ≥ 3 green and span ≥ 1 % (lowest low → highest high); then a pause of 1–3
  bars, none above that high, low not under the leg's midpoint;
- *entry*: buy stop-limit at the last pause bar's high + 1¢ (cap + max(1¢, 0.3 %)),
  live 20 s from that bar's close; *stop*: pause low − 1¢;
- *exit*: the live A3 trail (1 R, moved every 5 s), flat 11:30; one position
  per symbol-day at a time.

**Reported beside it, deciding nothing:** S without the 5-minute confirmation
(N5); S with a fixed exit at +2 R / stop (X2); a random-entry baseline — for
each S trade, 5 entries at random 10-second bar closes inside the same
runner windows, same stop %, same exit.

**Costs, per trade, decomposed:** IBKR Fixed commission at $40 risk / $2,000
cap; half the real NBBO spread at the fill and at the exit; entry slippage
(fill − trigger); exit slippage (level − exit print); the 1¢-a-side model
charge shown separately, because it may double-count slippage. Cost-reduction
cuts (spread ÷ stop, stop %, price, session) are post hoc and labelled so.

**It decides nothing live.** It is an assessment. Anything it suggests needs
its own preregistered run on other days, then the OFF-switch path.

### Addendum 2026-10-03 — the leader (SEL-3) and the green pause, before any run

From the reverse-engineering review of 2026-10-02 (two proposals that survived
adversarial review). Engine: `scripts/rules_audit.py` plans and portfolio,
rule set B (`BASE`), $40 / $2,000, live cost model, bar-order modes A and C,
both required. Train 2016–2022 decides; 2023 must agree in sign; 2024–2026 is
reported only (already read for leaders by F8 and for B by the rules audit).
Day-paired bootstrap, one-sided α = 0.05 / 4 (two tests × two modes).
Script: `scripts/sel3_pause.py`.

**L — the leader.** At each plan's arming bar (bars stamped ≤ the plan bar),
rank the plan's name by % gain over the previous close among the day's
universe names (the 09:30-gap list, known at the open) that are up ≥ 10 %,
$1–20, ≥ 50,000 shares since 04:00. Window 09:30–11:20 only (before 09:30 the
universe itself is hindsight). Variant L2: B restricted to plans ranked ≤ 2;
reference: B in the same window. **Candidate** (built OFF, 200 prospective
paper trades) only if, in both modes: L2 train gross ≥ +0.17 R a trade AND
the train lower bound of (L2 − reference, net) > 0 AND the 2023 difference
> 0. Otherwise the rank becomes a display column and nothing else.

**P — the green pause.** Detector variant: the impulse continues only on a
green bar that makes a new impulse high; any other bar — a green bar with a
lower high included — starts the pullback. Everything else as coded. Plans
rebuilt on every session EXCEPT the 400 days of the 2026-10-02 exploratory
probe (`random.Random(20261002).sample(sorted(universe), 400)`), which were
read. B portfolio, 07:00–11:20. **Candidate** only if, in both modes: train
net better than the coded detector with lower bound > 0 AND 2023 difference
> 0. Otherwise the question "the bot needs a red candle" is closed on the
1-minute chart; the plans only the variant arms are reported (count, gross,
net).

### Addendum 2026-10-05 — green-run continuation, 10-second timing, 1-minute risk, before any run

**Question (owner, 2026-10-05, SAIQ and JAGX):** a name climbing in green
1-minute candles with every live gate green never gets a plan, because the
detector needs a red candle. Can the 10-second chart time an entry there?
**Why this is not a repeat:** addendum 2026-10-02e applied no Layer 2 gate and
no stop floor and stopped at the 10-second low (costs ~1 R a trade); F3 sampled
only days with a filled 1-minute plan. Here every live gate applies and the
1-minute bar sets the stop. Script: `scripts/green_run.py`.

**Setup S.** Context, on the last COMPLETED 1-minute bar (cached SIP bars from
04:00): it and the bar before are green, it makes a new high of day, close
above session VWAP and the 9 EMA, MACD (12,26,9) line > signal, ≤ 25 % off the
high. Timing: the runup_micro 10-second pause (6-bar leg ≥ 3 green, span ≥ 1 %;
1-3 bars without a new high, low above the leg's midpoint). Entry: buy
stop-limit at the pause high + 1¢ (cap A10), live 20 s. **Stop: the low of
that completed 1-minute bar − 1¢.** Refused when the stop is < 2 % of price
(A13) or < 4× the proxy spread (A6), or the price is outside $2–20. Exit: A3
trail 1 R every 5 s, flat 11:30, one position per symbol-day. Sample: the 300
symbol-days of addendum 2026-10-02e (2024-26), already fetched. Real NBBO
spreads at fill and exit, $40 / $2,000.

**Reported beside it:** S10 (stop at the 10-second pause low, same floors);
RND, 5 random entries per S trade at 10-second closes inside the same
green-run windows, same stop %.

**Decision.** Built live on paper (switch, prospective) only if ALL hold: n ≥
100; net mean > 0 with its day-clustered one-sided 95 % lower bound > 0; and
the gross lower bound of (S − RND) > 0. Otherwise the green run is logged on
the desk (no orders) and not traded. This sample's years were read by
2026-10-02e (with a different setup), so a pass is still confirmed
prospectively before any size change.

### Addendum 2026-10-06 — green-run continuation, replication on 600 new symbol-days, before any run

Addendum 2026-10-05 is unchanged in every rule and parameter. It was positive
before costs (+0.103 R, beats random) and negative after (−0.063 net, lower
bound −0.225) on 144 trades. This asks whether that holds on new days.
**Sample:** 600 symbol-days drawn with `random.Random(20261006)` from the
5,679 runner symbol-days of 2024–2026 NOT in the first 300
(`research/paper-exercise/reports/green_run_sample2.json`). Ticks fetched
before the read. **Decision:** the same three conditions as 2026-10-05, read on
the 600 alone; regular hours (09:30–11:20) reported separately and given the
weight, because the 09:30-gap universe flatters pre-market entries. If it
passes, it is traded on paper behind a switch and confirmed on 200 prospective
trades; if it fails, it stays a logged signal on the desk.

### Addendum 2026-10-05b — green-run continuation on 600 new days, before any run

> **Superseded, recorded in place (2026-10-05 18:40 UTC).** This entry was
> written by the same session after a container restart, two minutes after
> addendum 2026-10-06 above had been committed (53d40b3) and its sample drawn.
> It duplicates it and misstates the seed: the sample actually drawn, fetched
> and read is 2026-10-06's, `random.Random(20261006)`
> (`research/paper-exercise/reports/green_run_sample2.json`, unchanged by this
> entry). **2026-10-06 governs**; its decision rule is the one applied. Nothing
> below was used.

Addendum 2026-10-05 found setup S positive before costs (+0.103 R, better than
random, lower bound +0.020) and negative after (−0.063, lower bound −0.225) on
144 trades. **Setup S is frozen exactly as written there** (`scripts/green_run.py`,
commit 20aa85f). New sample: 600 symbol-days drawn with `random.Random(20261005)`
from the same population (2024-01-02 → 2026-08-21 `running_up` alerts at $2–20)
with the first 300 excluded (`green_run.py sample2`); ticks fetched the same way.

**Decision, on the 600 new days alone:** a paper switch (prospective, OFF until
200 live trades confirm) only if n ≥ 200, the net mean's day-clustered one-sided
95 % lower bound > 0, AND the gross lower bound of (S − random) > 0. Reported
beside it, deciding nothing: regular hours only (free of the 09:30-gap
hindsight that flatters pre-market entries), the pooled 900 days, S10.
Otherwise the green run stays a desk log with no orders.

### Addendum 2026-10-06b — E1, the first 5-minute candle to make a new high; B30, the MACD warm-up; before any run

Written and committed before `scripts/five_minute.py` exists or runs. Engine:
`scripts/rules_audit.py` — its 2,608-session cache (24,831 symbol-days,
`data/cache/history`, 1-minute SIP bars 04:00-16:00 with pre-market volume), its
plans for B (`data/cache/rules_audit_plans.pkl`), `fill_retouch`, `run_exit`,
`cost_live`, the day-paired bootstrap; rule set B (`BASE`), $40 / $2,000, cost
model "live"; bar-order modes A and C, both required, as in addendum 2026-10-01b.
Periods: train 2016-02 → 2022-12 (1,701 sessions); gate 2023 (245); holdout
2024-01 → 2026-08 (662), read for other rules many times, never for these two.

**Question (owner, 2026-10-06):** "adapt handling the green uptrending 1 min bars
without a proper pullback in the one minute chart." The desk's detector needs a
red 1-minute candle; on a straight green run it arms nothing. The method's answer
is the 5-minute chart: *"the one minute is fine what's the first five minute candle
to make a new high it'll be over 65 so your entry is 65 your stop is the low at
60"* (`Xdw5azEqs6o` [00:12:38]); *"a five minute pullback ... right at the volume
weighted average price ... right at the nine moving average ... a really good
opportunity for the first five minute candle to make a new high"* (`5X_ZcifasBg`
[00:14:44]); *"it hasn't had a five minute pullback yet we need a five minute
pullback i don't wanna take a premature five minute breakout"* (`qCRNRcU2h7E`
[00:28:14]). And its warning: parabolic names that go *"from you know 7 to 14 on without a five
minute pullback"* and then *"it just Fades back down"* (`t-_T5MTl1FI` [00:34:09]). Not a repeat:
addendum 2026-10-03 P changed the 1-minute pullback's definition and the 10-second
tests (2026-10-02e, 10-05, 10-06) timed entries inside the run; nothing has
measured the 5-minute pullback.

**E1 — setup.** Five-minute candles aligned to the ET clock (:00, :05, …), built
from the cached 1-minute bars (first open, max high, min low, last close, summed
volume; a slot with no prints has no candle). `FirstPullbackDetector`'s rules on
those candles, with its defaults: an impulse of ≥ 2 consecutive green candles
(last 6 kept) spanning ≥ 2 % from the first open; the first candle that closes ≤
its open starts the pullback; up to 4 pullback candles; a pullback whose low
breaks the impulse's low resets. **The order rests during the next candle**, not
after it: at the close of each pullback candle a buy stop-limit is placed at that
candle's high + 1¢ (A10 cap +0.3 %, 1¢ minimum), stop at the pullback's lowest low
− 1¢, live for 5 minutes (the next candle). If it does not fill and that candle
makes no new high, it is re-placed at the new candle's high; a candle that trades
above the previous one's high ends the setup (filled or not — a gap past the cap is
no fill, as in B). Fills, exits and costs are B's: `fill_retouch` from the order
time, A3 trail 1 R on 1-minute bars, flat 11:30, `cost_live`.
**Gates at each placement**, from the 1-minute bars up to the pullback candle's
close, exactly as the live desk computes them (`indicators.chart_gates`): price
$2-20, above VWAP, above the 9 EMA, MACD histogram > 0; pullback volume (mean of
the pullback candles) < impulse volume (mean of the impulse candles); ≤ 25 % off
the high; stop ≥ 2 % of price (A13); stop ≥ 4× the proxy spread (A6); placed
07:00-11:20. **The owner's case, required for E1:** inside the impulse there is a
run of ≥ 4 consecutive green 1-minute bars whose last bar made a new high of day.
One position, the slot held from the order to the exit (an unfilled E1 order holds
it 5 minutes); daily limits as B.

**E1 — decision, sequential, every stage in both modes:**
1. Train: n ≥ 200; net mean R a trade > 0 with its day-clustered one-sided 95 %
   lower bound > 0; the regular-hours subset (orders 09:30-11:20) net mean > 0,
   because the 09:30-gap universe flatters pre-market entries; and the gross lower
   bound of (E1 − random) > 0. Random: per E1 trade, 20 market entries at the open
   of random 1-minute bars in the same window (pre-market · 09:30-10:30 ·
   10:30-11:30) of the same symbol-day, the same stop in % of price, the same
   exit, the same costs; seed 20261006.
2. 2023: net mean > 0.
3. Holdout: §4's five conditions (α = 0.42 %).
A trade's own costs decide, not a fixed line: the 0.40 R mean cost measured on
the 1-minute trades (`research/paper-exercise/reports/2026-10-02-execution-study/cost_decomposition_output.txt`,
`mod.addon`) shrinks in R as the stop widens, and 5-minute stops are wider.
All three stages pass → E1 is built as a paper order source behind a switch, OFF
until 200 prospective paper trades confirm it (the holdout years are not
pristine, §3). Any stage fails → E1 is never an order: the desk shows the state
("EXTENDED — waiting for the first 5-minute candle to make a new high"), nothing
more. Every period is reported whatever the decision; the decision is the first
failing stage. **Reported, deciding nothing:** E1 without the owner's-case
condition; E1 with VWAP as its only chart gate; B ∪ E1 against B (one position,
whichever arms first; day-paired lower bound on the holdout); E1 trades by
pullback count (1st, 2nd, 3rd+).

**B30 — the warm-up blind spot.** The desk's MACD needs 35 one-minute bars from
04:00 (`indicators.MACD_MIN`); before that the gate reads None and B refuses the
plan. The 2026-10-05 rebuild placed 3 of 13 tier-A and 10 of 29 tier-A+B entries of
Ross's June-July trades before a stock's 30th bar
(`research/paper-exercise/reports/2026-10-05-ross-recent-and-execution/README.md`).
On his platform the MACD carries the previous days' bars, so it exists from the
first print; the cache holds no previous-day bars for most names, so that cannot
be replayed. **Variant B30:** B, except that a plan armed with fewer than 35 bars
whose ONLY red gate is MACD is allowed (VWAP, 9 EMA, volume and every other rule
still apply). **Decision:** addendum 2026-10-01's adoption rule against B
(train and holdout better, ≥ 200 holdout trades, 2 of 3 holdout years, day-paired
lower bound on the holdout > 0), at one-sided α = 0.05 / 2 for the two tests of
this addendum, in both modes. A pass relaxes a gate the method states, so it goes
to the owner with the data and is built OFF until 200 prospective trades; a fail
closes the question. Reported: how many B plans are refused by the warm-up alone,
per window and per period.

### Addendum 2026-10-06c — re-anchor a run-past entry instead of dropping it, before any run

**Question (owner, 2026-10-06, IPDN 08:01):** the plan armed at 5.28 / 4.83 and was
dropped because the ask ran past the A10 limit (5.30) between two 5-second checks;
the owner took the move by hand. *"Don't we need to adapt the SL and TP instead of
neglecting the entry?"* Measured so far: widening the cap alone made net R per fill
worse (−0.3808 at +0.3 % → −0.3974 at +2 %) while the fills it added read +0.809 R
gross at +2 % (`research/paper-exercise/reports/2026-10-05-ross-recent-and-execution/execution_audit/cw.txt`) —
there the size and the trail stayed anchored to the trigger. Not tested: keeping the
stop where the chart put it and sizing from the price actually paid.

**Variant RA (re-anchor).** Same plans, same trigger, stop, TTL (3 minutes) and exit as
live. The first print at or above the trigger inside the TTL decides: at or under the
A10 limit (+0.3 %) → the live fill, unchanged; above it but at most **+2 %** over the
trigger → bought at that print, **shares = $40 ÷ (print − stop)**, the A3 trail at
1 × (print − stop), the stop unchanged; above +2 % → nothing, and the next print is
judged the same way until the TTL ends. No profit target (A3). Costs: IBKR Fixed both
sides, half the spread in and (on a stop-type exit) out — the cached spread where the
plan filled live, the median cached spread otherwise; $2,000 notional cap.

**Data and decision.** Primary: the 2,577 B plans with a stage-1 tick outcome, 2024-26
SIP prints (`data/cache/ticks`), plan by plan against live, net dollars ÷ $40. RA is
built (OFF, then 200 prospective paper trades — these years are not pristine) only if
(1) the day-clustered one-sided 95 % lower bound of (RA − live) net per plan is > 0,
AND (2) the re-anchored trades alone have a net mean > 0, AND (3) on 1-minute bars
2016-2023 (`rules_audit` cache, a bar opening above the limit and within +2 % is the
re-anchored fill at its open, reading C) the mean of (RA − live) is > 0. Otherwise the
2¢ band stays and the run-past plan stays a REFUSED row with its reason. Script:
`scripts/reanchor.py`.

### Addendum 2026-10-06d — the detector's blackout, the one-bar impulse, and a 04:00 start, before any run

**Found on IPDN 2026-10-06** (SIP bars replayed through the desk's own detector,
`FirstPullbackDetector`): the 08:01 plan was never sent (A10 ran past), yet the detector
held it TRIGGERED until its 2 R target printed at 08:12, so the 08:09-08:12 push could not
become the impulse of the 08:13 pullback; and the 08:14 push was ONE green bar (6.08 →
6.82), under the two-bar minimum, so the 08:15-08:18 pullback armed nothing. Separately
the owner asks for an earlier start: *"the opening of premarket generaly holds good
uptrends and setups"*. Orders now start at 07:00 (`intent.PREMARKET_START`).

**Variants, each against B (the live rules), one at a time:**
- **D1 no blackout** — once a plan is frozen the machine searches again at once (the
  plan's fate is the executor's); the trigger bar, if green, starts the next impulse.
- **D2 one-bar impulse** — `min_impulse_bars = 1` (the 2 % range minimum unchanged).
- **D12** — both.
- **W4 04:00 start** — B with plans and orders from 04:00 instead of 07:00.

**Engine and decision.** `scripts/rules_audit.py`'s cache, B's gates, fill, exit, costs,
one position and daily limits, plans rebuilt for every variant and for B with the same
code; bar readings A and C. Adopted only under addendum 2026-10-01's rule in BOTH
readings — train (2016-2023) and holdout (2024-2026) net mean per trade better than B,
≥ 200 holdout trades, better in 2 of 3 holdout years, day-paired lower bound on the
holdout > 0 at one-sided α = 0.05 / 4 — AND, added after B30, **total net R not worse
than B's in train and in the holdout** (a mean per trade can rise while the money falls).
A pass is built OFF until 200 prospective paper trades. Script: `scripts/detector_variants.py`.
