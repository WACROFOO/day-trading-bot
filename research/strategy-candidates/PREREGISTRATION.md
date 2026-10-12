# Strategy candidates — preregistration

```
ASKED    · the owner, 2026-10-12: "the main objective currently is to test, so you can respo that
           in a specific folder so we track every combination tested ; the objective is to turn
           these candidates and check wether it's profitable and if not analyze why and in which
           way it could be"
WRITTEN  · 2026-10-12, BEFORE any run of S1, S2, L1 or L3 on the five-year record, and committed
           with the runner before the Mac runs it — the git history is the proof of order
CODE     · scripts/candidates/ (the runner) · tests/test_candidates.py
DATA     · universe research/first-pullback-edge/data/candidate_days.csv, 2021-01-01 → 2026-08-21,
           reverse-split rows removed: 15,959 symbol-days, 1,405 sessions
           · bars: Alpaca SIP 1-minute, 04:00-16:00 ET, raw, data/cache/history/ — on the Mac,
           fetched there where missing; this container has no market-data keys
STATUS   · rules fixed, nothing measured. The only run so far is a smoke test on the 20 exported
           days of research/daily/ (outside the five years), to check the plumbing
```

Paper only. The candidates are **hypotheses to test** (CLAUDE.md's evidence labels), none of
them a Ross rule. Results are in R: one R is the planned risk per share times the shares.

---

## 1. The question

For each candidate: is it positive after costs on data it was not chosen on? If not —
**why** (the decomposition in §7) and **what change could make it positive**, stated as a new
hypothesis for a later, separately registered round. Nothing here is tuned after it is read.

## 2. What was already known when this was written

Read before writing, cited so the reader can check each one:

| fact | value | source |
|---|---|---|
| the bot's pullback entry, before costs | −0.006 R gross a trade on train; costs 1.13 R a trade at $20 risk | `research/edge-hunt/REPORT.md` §2, §4 |
| the bot over ten years, live costs | current rules −1.218 / −1.476 R (train 2016-2023 / test 2024-2026); stop ≥ 2 % of price −0.430 / −0.502 | `research/paper-exercise/reports/ablation_live_costs_v2.txt` |
| the best long harm reduction found | stops ≥ 3 %, new-low exit, stop for the day after a +1 R win: −0.345 train, −0.153 validation | `research/edge-hunt/REPORT.md` §2 (track 4) |
| how this population drifts | 8,828 symbol-days, Dec 2022 → Aug 2026: 31 % close green, mean open→close −2.44 %, median −4.88 %, negative mean in 5 of 5 years | `research/momentum-replication/reports/2026-08-known-edges.md` |
| why that drift is hard to harvest | "largely unharvestable by a retail account": hardest-to-borrow names, halts trap the position, unbounded loss | same file, "The honest catch" |
| the day's shape on big runners | high of day median 11:34 ET; HOD → close giveback median 71 %; 89 % of conforming dips followed by a new high | `research/megaday-study/RESULTS.md` §1 — 50 megadays **chosen by hindsight** |
| buying the dip after a new high (NHD) | median MFE 2.04 R vs 1.35 R; holdout +0.69 R on 31 fills, the top 3 trades 128 % of the result, 8 losses in a row; all of it conditional on knowing in advance that the day is a megaday (§6, translated) | `research/megaday-study/RESULTS.md` §2, §5, §6 |
| the #1 gainer's new-high break (F7) | best on train: gross +0.171, net −0.167 R (2,269 trades); validation gross +0.008, net −0.270 (273) | `research/edge-hunt/results/registry.jsonl`, family F7-leader |
| the same where the spread is small (F8) | holdout −0.188 R over 592 trades, every holdout year negative, −0.243 against random entries | `research/edge-hunt/holdout_ledger.jsonl` |
| shorts on the 20 exported days | every variant negative net on the selection days, gross −0.41 to +0.28 R; the 09:30→11:30 fade's worst trade −206.86 % of price | `research/strategy-candidates/prior-20-days/output.txt` |

Ross on crowded gappers, for S2 — a **long-side** caution, which S2 turns into a short
hypothesis of its own: *"It already has 2 million shares of premarket volume. So I already
have a little bit of a negative bias on it before I even pull up the chart."* — `ZfwTJAMLroA`
[13:21], quoted in `knowledge-base/strategies/PARAMETERS.md`.

## 3. The five candidates of the brainstorm, and what happens to each

| id | idea | here |
|---|---|---|
| **S1** | afternoon fade: short once the high of day is old and VWAP is lost | **tested** — 6 configurations |
| **S2** | crowded-gapper fade: short the first red 5-minute bar of a big gap on heavy pre-market volume | **tested** — 8 configurations |
| **L1** | real-time new-high dip: the megaday NHD entry without knowing the day is a megaday | **tested** — 6 configurations |
| **L2** | the #1 gainer's new-high break, wide stop, quick exit | **NOT re-run** — it is F7/F8 (§2): failed validation, and its holdout is already read through F8. Any new L2 variant can only be judged on forward paper |
| **L3** | reference: the bot's live entry + stop ≥ 3 % + new-low exit + done after a loss | **reference only** — 1 configuration, train and validation; never opens the holdout (its levers were read on 2024-2026) |

## 4. Data, split, and the real-time rule

* **Universe.** Every row of `candidate_days.csv` from 2021-01-01 to 2026-08-21, reverse-split
  rows removed (`edge_hunt.data.universe_rows`' rule). It is chosen on the **09:30 open**
  (open $2-20, gap ≥ 10 %, prior 20-day dollar volume ≥ $250k, survivorship-free): known at
  09:30. **So every candidate enters at or after 09:30.** L3's pre-market plans carry the
  hindsight the edge hunt measured (REPORT §3) and are shown apart, labelled.
* **Real-time condition.** At the signal bar's close the name is up ≥ 10 % over the previous
  close, unless a rule below says more.
* **Bars.** Alpaca SIP 1-minute, 04:00-16:00 ET. A symbol-day with fewer than 40 bars is
  skipped. Coverage is printed per year; a missing day is reported, never imputed.

| split | dates | sessions | symbol-days |
|---|---|---:|---:|
| train | 2021-01-01 → 2022-12-31 | 498 | 4,790 |
| validation | 2023 | 245 | 1,811 |
| **holdout** | 2024-01-01 → 2026-08-21 | 662 | 9,358 |
| older (confirmation, §6 criterion 7) | 2016 → 2020 | — | 8,872 |

## 5. The rules

Common to all: one position at a time across names (the bot's `max_positions = 1`; a trade
filled while another is open is not taken); everything decided at a bar's close from bars
stamped at or before it; orders act from the next bar. S1, S2 and L1 take one trade per
symbol-day (the first signal that fills); L3, like the bot, may take several. VWAP is
anchored at 04:00 on the typical price × volume, as `src/momentum_platform/indicators.py`. **SSR:** a symbol-day whose
low has touched −10 % of the previous close before the signal is skipped for shorts (the
short-sale restriction would forbid hitting the bid); a restriction carried from the previous
day cannot be seen here.

Engine conventions, as `scripts/edge_hunt/engine.py`: on every bar, flatten at its open once
the flat minute is reached; the stop in force before the bar is tested first, and a bar that
opens through it fills at its open (a gap or a halt); then the target; then the trail moves.
On the fill bar of a stop-limit entry the stop fills at the stop, and after a cap-return fill
the bar's high earns nothing.

### S1 — afternoon fade (short)

| | rule |
|---|---|
| signal | at the close of bar t, 10:00 ≤ t < 15:00 ET: up ≥ 10 %; the high of day was set ≥ **A** minutes before t; **the close crosses under VWAP** (c(t−1) ≥ VWAP(t−1), c(t) < VWAP(t)) |
| entry | sell short at the open of bar t+1 |
| stop | the high of day + 1 ¢ — taken only if it is 2-20 % above the signal close; otherwise keep scanning. R is measured from the fill; an open at or through the stop cancels the order and the scan goes on |
| exits | **close**: cover at the 15:55 bar's open · **fixed2**: a resting buy limit at 2 R, else 15:55 · **vwap_reclaim**: cover at the next open after a 1-minute close above VWAP, else 15:55 |
| grid | A ∈ {30, 60} × exit ∈ {close, fixed2, vwap_reclaim} = **6** |

### S2 — crowded-gapper fade (short)

| | rule |
|---|---|
| selection, known at 09:30 | gap at the open ≥ **G**; pre-market volume (04:00-09:29) ≥ 2,000,000 shares |
| signal | the first 5-minute bar from 09:30 to 10:30 (09:30-09:34, 09:35-09:39, …) that closes red **while the price is above VWAP** |
| entry | sell short at the open of the next 1-minute bar |
| stop | **hod**: the high of day + 1 ¢ · **bar5**: the red 5-minute bar's high + 1 ¢ — taken only if it is 2-20 % above the 5-minute close; otherwise the next red 5-minute bar. R from the fill; an open at or through the stop cancels, and the scan goes on |
| exits | **vwap**: a resting buy limit at VWAP (the previous bar's), filled at min(open, VWAP) when a bar trades down to it, else 15:55 · **close**: cover at the 15:55 open |
| grid | G ∈ {20 %, 40 %} × stop ∈ {hod, bar5} × exit ∈ {vwap, close} = **8** |

### L1 — real-time new-high dip (long)

| | rule |
|---|---|
| impulse | bar n prints a new high of day and closes ≥ **G** over the previous close; the leg's low = the lowest low of bars n−14 … n |
| pullback | 1-5 bars after n with no new high and at least one red bar; depth D = HOD − the pullback's low, 0 < D ≤ 50 % of HOD − the leg's low; the name still up ≥ 10 % |
| entry | at each valid pullback bar's close, 09:30-11:20: a buy stop-limit at that bar's high + 1 ¢ for the next bar (cap + max(1 ¢, 0.3 %), A10); a new high or a broken pullback waits for the next impulse |
| stop | the trigger − 2 × D (the megaday study's frozen width, `research/megaday-study/data/holdout-protocol.md`) — armed only if 2 × D ≥ 2 % of the trigger |
| exits | **trail1** (1 R trail) · **fixed2** (2 R limit) · **newlow** (out when a bar trades under the previous bar's low − 1 ¢); all flat 11:30 |
| grid | G ∈ {30 %, 50 %} × exit ∈ {trail1, fixed2, newlow} = **6** |

### L3 — reference long (not a candidate)

The desk's detector plans (`backtest_recent.plans_for_day`, VWAP with pre-market volume,
A10 fills), all six gates green, armed 07:00-11:20, up ≥ 10 % at the plan bar, stop ≥ 3 % of
the entry (else skipped), the new-low exit, flat 11:30, one position, **done for the day after
the first losing trade**. One configuration. Train and validation only; pre-market and regular
hours reported apart. It answers "how does the best long we know do on the same five years".

### The random-entry baseline (criterion 5, and the diagnosis)

For every trade: 20 market entries at the open of random bars of the **same symbol-day**, in
the **same window** (S1 10:01-15:00, S2 09:35-10:30, L1 09:31-11:20), on the same side, with
the same stop distance in % of price, the same exit rule and the same costs. Seeded from the
symbol-day and the entry minute, so it is reproducible.

## 6. Choosing, the gate, the holdout, adoption

1. **Train chooses.** Every configuration of a family is evaluated and registered (§8). The
   chosen one has the best one-position mean net R on train among those with ≥ 100 train
   trades. None with 100 → the family fails for lack of trades.
2. **Validation is a gate, not a chooser.** The chosen configuration must be positive net on
   2023 with ≥ 30 trades. Every configuration's validation figures are printed, for the
   diagnosis, and never used to choose.
3. **The holdout opens once per family, ever,** and only behind a passed gate. The runner
   writes the opening to the ledger before it reads a holdout row. A later run may re-read the
   same configuration (same result, deterministic); it may never open another.
4. **Adoption** — all of these, on the holdout, one-position portfolio, net:

| # | criterion |
|---|---|
| 1 | mean net R > 0 |
| 2 | day-clustered bootstrap lower bound > 0 at one-sided α = 0.05 / 2 / 3 = **0.83 %** — Bonferroni over the three families allowed to open (S1, S2, L1) |
| 3 | ≥ 200 trades |
| 4 | mean > 0 in at least 2 of 2024, 2025, 2026 |
| 5 | beats the random-entry baseline: the day-clustered 95 % lower bound of (trade − baseline) > 0 |
| 6 | **shorts:** the break-even borrow cost ≥ 0.5 % of price a round trip (a margin fixed now for locate fees no data here can price — an assumption, not a market rate) |
| 7 | the older period, 2016-2020, read once at the opening: mean net > 0 |

**A pass is not a switch.** It becomes a shadow line in `research/daily/shadow.csv` (logged,
never traded) and goes to the owner as a decision recorded in `docs/preregistration.md` §5. A
short additionally needs a borrow check on the very names the backtest took (IBKR shortable
shares and fees) before any paper trade.

## 7. The diagnosis — why it fails, and what could make it work

Computed for every configuration on train and validation; never on a holdout that stayed shut.

| reading | what it separates |
|---|---|
| gross · costs (commission, spread + 1 ¢, borrow) · net | a bad signal from an expensive one |
| trade − random baseline, and the baseline's own mean | timing from the name-day's drift |
| MFE and MAE in R; "gave back" = MFE ≥ 1 R that ended ≤ 0; exit reasons | an entry problem from an exit problem |
| win rate, average win, average loss; top 5 % of trades' share of the total; mean without the top 1 %; trades beyond −1 R | an edge from a lottery, and gap risk |
| by year · entry time · price tier · stop % · gap · prior 20-day dollar volume (the borrow proxy for shorts) | where it works, if anywhere |

Each configuration gets one rule-based reading line, from these tests in order:

* gross ≤ 0 → **the signal loses before costs**; no cost or exit change fixes it.
* gross > 0 ≥ net → **costs take it**; the levers are cost per R: wider stops, fewer orders,
  regular hours, higher-priced names.
* median MFE ≥ 1 R and mean ≤ 0 → **the price moves the right way first and the exit gives it
  back**; the exit is the lever.
* trade − random ≤ 0 → **random entries on the same names do as well**; the selection carries
  the result, the trigger adds nothing.
* the top 5 % of trades > 100 % of the total → **a lottery**: a few trades make the result.

**Leads** — slices positive net on train (≥ 100 trades) **and** on validation (≥ 30) — are
printed as hypotheses for the next round, never adopted from this one: a lead is tested on its
family's holdout only if that family never opened it, otherwise on forward paper.

## 8. The registry — every combination, counted

* Every configuration evaluated, on any machine, is one line in the run's
  `results/registry.jsonl` (local, git-ignored) and, once the run comes back, in the committed
  `registry.jsonl`. The count per family is the number of distinct configuration hashes in both.
* The committed registry starts with the **prior reads** this line of work has already made
  (§2): F7 (18) and F8 (54), the megaday study's 4 hypotheses, F4's 174 configurations, and
  the 31 short combinations of `research/strategy-candidates/prior-20-days/`.
* A new candidate or a lead's follow-up is added **here, dated, before its first run**, and α
  is re-corrected over every family then allowed to open.

## 9. Contamination, declared

* **S1, S2:** the direction "gappers fade" was read on 2022-2026
  (`research/momentum-replication/reports/2026-08-known-edges.md`).
  The rules themselves never ran on 2021-2026.
* **L1:** the NHD entry was read on the megaday holdout (2025-09-10 → 2026-08-21), on days
  chosen by hindsight. The real-time version never ran.
* **L2:** not run; its holdout is read (F8).
* **L3:** its levers were read on 2024-2026 (`research/edge-hunt/PREREGISTRATION.md` §3);
  reference only.
* A pass by S1, S2 or L1 is still marked **contaminated by the direction**, and the forward
  paper sample (≥ 200 trades) is the judge nobody has read.

## 10. What this cannot test

* **Level 2, borrow availability and fees, locates, halts as such, a short-sale restriction
  carried from the previous day:** no history here. A gap through the stop is in the gross R.
* **The pre-market for S1, S2, L1:** the universe knows the 09:30 open.
* **One-minute bars:** the order inside a bar is unknown; the conventions above decide it.
* **Small train for S2:** crowded gappers are rare; the grid may not reach 100 train trades,
  and then the family fails for lack of trades — said, not hidden.
* **The borrow proxy is weak:** prior 20-day dollar volume is a liquidity measure, not a
  lendable supply.

## 11. Order of events

1. This file, the runner and the tests are committed and pushed — before any five-year run.
2. On the Mac: `bash scripts/update.sh`, then `python3 scripts/candidates/run.py`. It prints
   the report and writes `research/strategy-candidates/results/<run>/` (git-ignored, survives
   `update.sh`).
3. The report comes back (paste or upload) and is committed under `runs/<run>/`; its registry
   and ledger lines are appended to the committed files.
4. The diagnosis drives the next round, written here as a dated amendment before it runs.

```
NOTHING MEASURED YET. No candidate is a trading rule. Not testable here: Level 2, borrow,
locates, halts, the previous day's SSR, ten-second structure. Paper only.
```

---

## Amendment 2026-10-12b — S2's lead as a rule (S2W), written before any run of it

Written after reading run 2026-10-12T1350Z
(`research/strategy-candidates/runs/2026-10-12T1350Z/report.txt`) and before S2W has run
anywhere. Its only source is that report's lead line for S2 G20·hod·close: *stop% 10-20 —
train +0.043 (104) | valid +0.302 (41)*. The other lead (*time 09:30-10 — train +0.002 (210)*)
is too close to zero on train to spend an opening on.

| | rule |
|---|---|
| S2W | S2 G20·hod·close exactly (gap ≥ 20 %, ≥ 2 M pre-market shares, the first red 5-minute bar above VWAP, short at the next open, stop at the high of day + 1 ¢, cover at 15:55), its trade **kept only when the stop is 10-20 % above the 5-minute close**; otherwise that symbol-day is skipped — the slice the lead was read on. One configuration. Borrow not charged |
| gate 1 | the rule itself, one position at a time, positive net on train **and** on validation, ≥ 30 trades in each. It was read there as a slice, so this checks consistency; it is not evidence |
| gate 2 | **2016-2020, never read for any S2 rule:** positive net, ≥ 30 trades. It replaces criterion 7 and is read *before* the holdout, so a failure keeps the holdout shut |
| holdout | only behind gates 1 and 2: **S2's one opening**, criteria 1-6 of §6, α unchanged (0.83 %, three families allowed to open) |

* **Counting.** S2's family becomes 9 configurations. The leads came from many more slices (six
  dimensions × every bucket × 8 configurations); gate 2 and the corrected bound guard against
  that, not the count.
* **What the opening costs.** After it, no S2 idea can be judged on 2024-2026 again — forward
  paper only.
* **Run:** `python3 scripts/candidates/run.py --lead S2W` (the Mac).
