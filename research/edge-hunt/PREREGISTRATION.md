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
