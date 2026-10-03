# Reverse-engineering Ross against the bot's pillars — 2026-10-03

```
INPUTS · research/ross-trades/ (1,512 of his trades, 702 rebuilt on Alpaca SIP 1-min bars, 2026-09-28)
       · research/edge-hunt/ (F1-F8), the rules audit, the 2026-10-02 tick, cost and Running Up studies
       · the corpus via scripts/corpus.py (teaching / recaps / streams), quotes cited by id and timestamp
METHOD · a 10-agent review on 2026-10-02: evidence map, corpus, code and data; three designers
         (selection / entry / exit-size-execution), adversarial review of each proposal, synthesis
FOLLOW-UP · the two survivors that run on local data, preregistered (addendum 2026-10-03, d880624)
         and run 2026-10-03 with scripts/sel3_pause.py on ten years of 1-minute bars
! The Ross trade ledger and the point-in-time universe cache are not in this checkout; the review used
  their committed summaries. Probes marked "session scratch" were exploratory and decide nothing.
! AMOD 2026-10-02 trade facts come from the owner's blotter in chat, not from a committed file.
```

Paper only. No claim of edge.

## Follow-up tests, 2026-10-03 (addendum 2026-10-03)

Rule set B, $40 / $2,000, live costs, bar-order modes A and C both required; train 2016-22 decides,
2023 must agree, 2024-26 reported only. Outputs: `research/paper-exercise/reports/sel3_leader_output.txt`,
`research/paper-exercise/reports/sel3_pause_output.txt`.

| test | train 2016-22, mode A / C (net R a trade) | 2023 | decision |
|---|---|---|---|
| **L — only the minute's #1-2 gainer** (09:30-11:20) | leaders −0.395 / −0.422 against all −0.407 / −0.428; gross −0.035 / −0.062 against −0.033 / −0.054; lower bound −0.034 / −0.042 | +0.034 / +0.017 | ✗ not a candidate: gross far under the +0.17 bar, bound < 0 |
| **P — green pause starts a pullback** (07:00-11:20, 400 probe days excluded) | pause −0.483 / −0.504 against coded −0.438 / −0.461; lower bound −0.085 / −0.084 | −0.093 / −0.089 | ✗ worse; the 13,564 plans only the pause arms are −0.079 / −0.090 gross |

The leader rank does not help the bot's pullback entry: among B's own trades, rank 1 is −0.027 / −0.036 gross on
train. Letting a green lower-high candle start a pullback finds more plans and they are worse. **The question "the bot
needs a red candle" is closed on the 1-minute chart.** The 5-minute new-high entry (E1 below) is the one open test.


## 2. What Ross actually does: measured against what he says

| Behaviour | Measured on his rebuilt trades | What he says (id [time], register) | Label |
|---|---|---|---|
| Where he enters | 90% at or above the high of day; median +3.1% above the prior high; stock already up a median +50%, 9.7% above VWAP (`analysis.txt:20-26`) | His order of entries: "first candle to make a new high ... next best ... micro pullback ... bull flag" (`aqTXoV923OE` [01:08:07]-[01:08:51], teaching) | Confirmed |
| Which stock | #1 gainer 57%, top 3 88% (n 315); #1 by dollar volume only 20% (`analysis.txt:29-30`) | "I really like trading a stock that is the leading gainer" (`W6AErTREKHw` [00:03:54]-[00:04:08], recap) | Confirmed |
| How fresh the move is | Median 25.5 min after the first +10% (`analysis.txt:24`); the bot's plans arm a median 202 min after it (SEL-2 count, scratch) | "your first pullbacks are usually the strongest" (`m5zu_X-_51I` [00:46:47], teaching) | Observed |
| Session | 43% pre-market, 50% 09:30-10:30 (`analysis.txt:26`) | "beginning at 7:00 a.m." (`BZwJFPk3cBM` [00:00:38], recap) | Confirmed |
| Climb with no pullback | — | Max loss at the low of the previous wave, "way down" on all-green candles (`_fsRWw0VbS4` [00:17:24], teaching). If the first new-high candle goes by: "if you miss it, you miss it" (`aqTXoV923OE` [01:08:07]) | Confirmed |
| How he gets in live | Named setups: dip buy 30, micro pullback 19, first 5-min candle to make a new high 27 (17+10), halt resumption 15 (`analysis.txt:51`) | "bought the dip": 301 hits in 120 streams, 8 in teaching (corpus.py). Starter on the dip, add on the 5-min break (`Ho9qjJ80EEc` [00:28:51], stream) | Observed |
| 5-minute trigger | "first five minute" appears in 71 of 290 streams (corpus.py, E1 verdict) | "eight green candles in a row i would definitely be waiting for a pullback the first five minute candle to make a new high" (`Ho9qjJ80EEc` [00:08:18], stream) | Observed |
| Timeframe | Micro pullbacks with a stated timeframe: 1-min 59, 10-s 19 (`2026-08-streams-roundup.md` §1) | "this is a 10 second micro pullback" (`6xIr761eZj8` [00:48:43], stream) | Observed |
| Extended stock | — | "four or five green candles in a row" (`K06k5iKStkU` [00:30:24]). His answer is smaller size, not a skip (`0zXUMrYyTx0` [00:49:22], streams) | Confirmed |
| Stops | Stated on only 30 of 702 trades, median 6.1% of price; a stop under the 1-min bar would be a median 9.8% (`analysis.txt:35-37`) | Mental stops, not resting orders (`PARAMETERS.md` §5, `-Aj8oowFAFY` [22:47]) | Confirmed |
| Exit | Hold median 2 min (IQR 1-6, n 349); move median +1.95%, positive 76%; 60 min after his exit the low sits a median 14.5% below it (`analysis.txt:41-43`) | "breakout or bailout ... pretty ruthless" (`t-_T5MTl1FI` [00:27:44], stream). No time limit is stated anywhere in the corpus | Confirmed |
| Where his money comes from | Top 10% of trades = 182% of his net; live-stream register: win/loss 0.29, -$94,280 (n 40) (`analysis.txt:15-17`) | A starter, then adds, with the stop raised to break-even (`KzVbXzkoZkA` [00:20:27]-[00:21:28], stream) | Confirmed |
| Tape at the moment of entry | Level 2 or tape cited on 7% of trades (`analysis.txt:50`); tape words near 17% of entry utterances against 7% at random (streams-roundup §9) | "moving off of the charts ... looking at the level two" (`c814DtTOGDg` [00:05:35], recap) | Confirmed |
| Shorts | None in any recap or stream | "I don't short stocks" (`EXvwTI4krTI` [00:19:10], stream) | Confirmed |
| The bot on his stocks | A desk plan sat within 5 min of his entry 63% of the time, but only 9% had every gate green and filled. Gates red near his entry: MACD 226, volume 203 (`analysis.txt:54-55`) | — | Confirmed |


## 3. Pillars and verdicts review

| Pillar / verdict | As coded | Evidence | Recommendation | Label |
|---|---|---|---|---|
| A verdict exists only when the 1-min detector arms | `session_builder.py:370-385` | The detector finds structure near 63% of his entries; it is the gates that refuse them (`analysis.txt:54-55`) | KEEP. Add a MISSED log line (new high printed, no plan armed), display only | Confirmed |
| A pullback starts only on a bar with close ≤ open | `pullback.py:149-158` (read this turn) | Exploratory "pause" variant: net -0.424 vs -0.435. The owner's green lower-high bar occurs 0.04 times per symbol-day (scratch freq.py (session scratch, not committed)) | KEEP. Close the question with a descriptive check (Plan step 1) | Observed |
| Trigger = previous bar high +1¢; stop = pullback low | `pullback.py:165-172, 209-231` | Forcing the trigger to be a high-of-day break: -1.478 / -1.934 vs -1.218 / -1.476 (`ablation_live_costs_v2.txt`) | KEEP | Observed |
| Price $2-20 (kill) | `cascade.py:183-185, 239-252` | Freeing it: -1.307 / -1.481 vs baseline (ablation L5-11) | KEEP. The `penny_theme` input is never passed: a defect, so wire it or delete it | Confirmed |
| Float < 20M (A5: flag only) | `cascade.py:113-123` | `float_m` is empty on every historical row, so it cannot be tested | FLAG ONLY | Unknown |
| Catalyst (A2: flag only) | `cascade.py:283-307` | Headline -0.474 vs none -0.538 (`v3_F1.txt`). `live_theme` is never passed (`session_builder.py:592-640`) | FLAG ONLY. Wiring `live_theme` is a defect fix | Observed |
| **Pillar count ≥ 4 of 5 (kill)** | `cascade.py:309-330` (read this turn: an UNKNOWN pillar counts as a fail) | Not in FILTERS.md, which calls 5× RVOL a dial and sets the trade floor at 1.5× (`FILTERS.md` L20, L162, L218). Never backtested (`scripts/rules_audit.py:20-22`). Rejects 95.7% of replayed scanner alerts | **OWNER DECISION, on fidelity to FILTERS.md.** Turning it off makes the desk equal to the backtested rule set B: -0.436 / -0.475 net (`rules_audit_open_output.txt:21`). No R gain | Confirmed |
| Still rising ≤ 25% off the high | `cascade.py:332-344` | "no setting matters" (rules audit L82) | KEEP | Confirmed |
| Split / ETF / tick size / buyout | `cascade.py:346-392` | Their inputs are never passed on the live desk | KEEP. Wire them as defects | Confirmed |
| VWAP, 9 EMA, MACD (refuse) | `cascade.py:397-446` | Freeing any one loses more (ablation L5-11, L18-21) | KEEP | Confirmed |
| Pullback volume lighter than push (refuse) | `pullback.py:215-216`; `runner.py:65-79` | Roughly neutral at stops ≥ 2%: -0.424 / -0.489 vs -0.430 / -0.502. Teaching register only (`DP4ayEWhmvM` [00:17:28]) | KEEP. This is your fidelity choice; A14 stays reverted | Observed |
| Layer 3 (session volume, RVOL 1.5×): warnings | `cascade.py:419-432` | Session volume ≥ 1M is mid-pack once the 2% stop floor applies (-0.509, `v3_F1.txt`) | KEEP as warnings. Wire `premarket_volume` | Observed |
| A13 stop ≥ 2% of price; A6 stop ≥ 4× spread | `runner.py:58-63, 205-224` | Stop ≥ 2%: -0.430 / -0.502 vs -1.218 / -1.476 (ablation L15). The only lever that ever moved R | KEEP | Confirmed |
| A10 entry: +0.3% cap, 3-min life | `intent.py:74-85` | Caps of +0.5% / +1%: -0.487 / -0.500 vs -0.477 | KEEP | Confirmed |
| Trail 1R, 11:20 / 11:30 cutoffs, 3-loss lock | `intent.py:66-73`; `risk.py:44-50` | Trail is the best of 13 exits tested. With limits off, drawdown is 795 vs 712 R | KEEP | Confirmed |
| Leader rank (#1 by % gain) | Not coded anywhere | His entries: rank 1 by gain 57%. F1 ranked by dollar volume instead (-0.534) | TEST (SEL-3) | Hypothesis |
| REVIEW is a yes/no over 8 gates | `cascade.py:435-460` | Ross cuts size rather than skipping (`0zXUMrYyTx0` [00:49:22]) | No change until a size dial is measured | Approximation |
| Microflow 10-second layer | Paused | Phase 0 NO-GO: only 2 of 37 quoted dips clear k=8 | KEEP PAUSED | Observed |


## 4. Surviving hypotheses, ranked by (value × probability) ÷ cost

Two proposals survived the adversarial review: SEL-3 and E1.

**1. SEL-3: leader by % gain on the bot's own plans** (cheapest decisive test)
- **Mechanics:** rank each plan's stock by % gain among names up ≥ 10% at the arming minute. Compare B plans ranked ≤ 2 with the rest, regular hours 09:30-11:20.
- **Why not already refuted:** F1 ranked by dollar volume (`features.py:147-153`), which matches his entries only 20% of the time, against 57% by gain (`analysis.txt:29-30`). F7 and F8 used a high-of-day break with wide stops, not the bot's pullback entry.
- **Cost arithmetic:** costs are about 0.40 R a trade at the bot's spread-to-stop ratio of 0.154 (full report L204). Even a +0.25 R split leaves the leaders near +0.045 gross and about -0.35 net, against B's -0.436. That is about +0.09 R a trade better, and still negative.
- **Test:** preregister first. Train 2016-22 (1,327 of 2,091 regular-hours plans rank ≤ 2), mode C, day-clustered bootstrap, a random-minute baseline that only looks forward, and a sign check on 2023 (174 plans). 2024-26 is report-only. **Kill line:** train gross below +0.17 means the leader stays display-only. That is the expected outcome.
- **Data and hours:** all local (`data/cache/rules_audit_plans.pkl`, `data/cache/history`, ranks already in scratch sel/feats.pkl (session scratch, not committed)). About 1-2 h, plus about 1 h for the baseline. Probability of passing: low, because the cut keeps 63% of plans.

**2. E1: first 5-minute candle to make a new high, once the 1-minute is extended**
- **Mechanics:**
  - When there are ≥ 4 consecutive green 1-min bars at a new high of day within 10 min, stop taking 1-min entries.
  - P = a completed 5-min bar with no new high.
  - Buy stop-limit at P's high +1¢ (cap +0.3%). Stop at P's low -1¢; refuse stops under 2%.
  - Exit: F7's bail (out after 2 min unless +1R, then trail 1R), plus one variant that also exits on a red 5-min close.
- **Why not already refuted:**
  - Never tested as a continuation trigger. F5's H5.1 was the session's first 5-min candle (gross -0.018), and runup_micro used the 5-min chart only as a filter.
  - It is Ross's own named answer to an extended stock (`Ho9qjJ80EEc` [00:08:18], stream). His support is mixed, though: "would have been a risky setup" ([00:08:25]), and he times this entry on the 1-min (`txPT1JwFUJQ` [00:21:21]).
- **Cost arithmetic:**
  - Stops: median 3.32%, interquartile 2.11-4.86% (scratch freq2.py (session scratch, not committed)).
  - Real-tape cost at $40 risk: 0.478, 0.374 and 0.233 R for stops of 2-3%, 3-5% and ≥ 5% (`cost_decomposition_output.txt:41-43`). That puts the cost at about 0.38-0.40 R and break-even gross at about +0.40.
  - Passing the holdout needs about +0.50 gross, roughly 3× F7's +0.171.
- **Test:** preregistered addendum (alpha 0.05/2/9). Regular hours 09:35-11:00. Train 2016-22, then a 2023 gate (net > 0, n ≥ 30), then the 2024-26 holdout read once under the five-part rule. 20 random entries per symbol-day that only look forward, bar-order modes A and C, and cap misses reported.
- **Data and hours:** local. About 1 day of code and 0.5-1 h of CPU. A tick audit would need network. Probability: low.

**Cheap closures.** These were killed as proposed, but a local descriptive check settles the question:
- **Green pullback (from E3):** report gross R for `red_pullback_bars=0` against `>0` by joining `trades.parquet` to `rejected_setups` (minutes). Then re-score train plans with a leg-low stop, paired against the F4 3%-widened stop (half a day).
- **10-second timing (from E2):** re-score runup_micro's signal and random entries at identical 1-minute stops on the cached 300 symbol-days (2-3 h). A lower bound ≤ 0 retires 10-second entries on runner days.

**Killed, with the one reason each died:**
- **SEL-1 (pillar count becomes a grade):** history can only measure the RVOL half, and that is already measured. Turning the count off just makes the desk equal to B at -0.436 / -0.475 net.
- **SEL-2 (ignition clock):** as written it needs the deleted point-in-time universe and network. And his own fresh leader entries are -0.141 gross under the bot's exits (`analysis.txt:61`).
- **SEL-4 (prior-session heat):** the terciles collapse into eras. "Hot" covers 95-98% of days in 2024-26, and the gain over random de-sizing is about +0.013 R.
- **SEL-5 (exhaustion veto, short mirror):** only 49 train and 4 validation cases, capped at about +0.02 R. No borrow data and no short path.
- **E2 (10-s timing with a 1-min stop):** the 10-s signal lost to random at the same stop (-0.193 vs -0.109, `runup_micro_output.txt:4,7`). S3-dip, the decoupled version, also failed (lower bound -0.004).
- **E3 (green pause, leg-low stop):** his own entries with a 9.8% bar stop are -0.141 gross. F4's 3% widening was +0.0001 gross (`registry.jsonl:1590`).
- **E4 (anticipate the level with a limit below it):** a limit at L-0.10 sits at or above the last print, so it fills immediately at the ask and is not a passive order. The cost hurdle was understated about 3×.
- **E5 (LULD band as gate and target):** there is no base entry to put it on and no halt archive. The closest analogue, the room-to-high gate, was harmful (-0.532, first-pullback-edge `final_report.md` §6).
- **S1 (short the V8 reversal):** a baseline that only looks forward cuts its margin to +0.02 to +0.07 gross. The best net before borrow is -0.111, and 2022 is negative (scratch, exploratory).
- **X1 (borrow go/no-go):** it cannot change any decision while S1 is negative before borrow.
- **R1 (his exit on his entries):** the data is gone, and costs cap the result at ≤ +0.08 R even if it captured his full stated move.
- **EXIT-1 (10-s stall bail plus scalp):** at most +0.01 to +0.03 R, and M3 is already refuted under strict fills.


## 6. What cannot be copied, and what your discretion adds

**Cannot be copied with this data.** Plainly, the parts of Ross that carry the money are the parts the bot cannot see:
- **Level 2 and depth:** no history exists in any source here (`research/edge-hunt/REPORT.md` header).
- **Fills inside the spread:** the bot pays 0.387 R a trade.
- **Size on the runner:** his top 10% of trades make 182% of his net. Adding at +1R on the bot's fills loses (net -0.547 / -0.335, exploratory).
- **A discretionary 2-minute exit:** no time number exists in the corpus, and the mechanised version (F7) faded.
- **Halt resumptions:** no archive and no indicative price.
- **His point-in-time universe:** 69% of his stocks were outside the bot's 09:30-gap universe (`analysis.txt:28`), and that cache is gone.
- **Float and news history:** empty on every row.

**What your discretion adds** (chat facts, not in the repo):
- **Blotter since 2026-08-31:** 20 trades, 14 wins, +$8,306, average win $634 against average loss $95.
  - 7 shorts made $5,881 (71%), BENF alone $3,900. The longs therefore made about $2,425 (arithmetic).
  - The bot is long-only, and Ross gives nothing for the short side.
  - The short rule tested (S1) is net negative before borrow. If your short edge is real, it is your discretion, not that rule.
- **AMOD:** +$260, +$150, +$180, +$520.
  - Entries 2-4 sat at new highs of day, the same place as 90% of Ross's entries. Your exits came within 1-2 minutes, matching his 2-minute median hold.
  - No stops were recorded, so these trades cannot be expressed in R. Writing the stop down at entry fixes that.
- **The bot's AMOD calls against what happened** (rule 8; one day, generalises nothing):
  - The 4 trades taken sum to -0.25 R (+2.40 -0.60 -0.72 -1.33).
  - The volume gate refused 08:35, which went on to net -1.11 R: right. It refused 08:51, which went on to net +1.50 R: wrong.
  - The loss lock blocked 08:57, which went on to net +0.66 R: wrong.


## 7. Limitations

- **Chat-only facts:** the AMOD trade facts and the 20-trade blotter are not in the repo (`2026-10-02-full-report.md` L8-9).
- **Plan count not reconciled:** the session's facts say 11 AMOD plans; look.py (session scratch, not committed) counts 19 between 04:13 and 09:47 (13 from 07:04). Not reconciled here [Unknown].
- **Exploratory probes:** the pause, short, scalp, frequency and count probes live in scratch only, were not preregistered, and decide nothing.
- **The Ross trade study cannot be re-run here:** the ledger CSVs and the point-in-time cache are gone, and only 22 of 61 extraction batches were run. Recaps over-represent winners. Streams date from 2021-23, recaps from 2026.
- **Consumed test years:** the 2024-26 holdout is already used for leaders (F8) and for gappers (rules audit). Any adoption needs prospective paper trades.
- **Ticks:** they cover 2024-26 only, just 9% of symbol-days cover all of 09:30-11:30, and there are no quotes between the cached moments.
- **Corpus tools:** `claims.db` is missing, so `corpus.py --claims` fails.
- **Evidence-map correction:** the "first five-minute candle is blog-only" line is wrong. It comes from caption line breaks; the streams carry it in 71 of 290 files.
- **Index defect, noted but not fixed (read-only):** `research/first-pullback-edge/data/README.md` says 8,152 ticker-days. The file holds 25,716.
- **Cost figures assume $40 risk.** Cost per R changes at any other size.

Main files: `research/ross-trades/results/analysis.txt`, `src/momentum_platform/pullback.py`, `src/momentum_platform/cascade.py`, `research/paper-exercise/reports/2026-10-02-full-report.md`
## The plan (step 1 now done: both tests fail)

1. **This week, local, about one day: SEL-3 plus the green-pullback closure.** Preregister before reading any outcome.
   - Decision rules: SEL-3 train gross below +0.17 → the leader stays display-only. At or above +0.17, with lower bound > 0 and the same sign in 2023 → 200 prospective paper trades with the switch OFF.
   - Green pullback: if the leg-low stop gains less than +0.10 R gross over the 3% widening → close the "no 1-min pullback" question for good.
2. **E1, the 5-minute new high.** Preregister the addendum, then train → 2023 gate → holdout once.
   - Decision rules: train gross below +0.40 → close the 5-minute family. A holdout pass → switch OFF until 200 prospective paper trades.
3. **Your fidelity decisions, which claim no edge:**
   - The A5 pillar count, which FILTERS.md treats as a dial, not a kill.
   - Wiring `penny_theme`, `live_theme`, `premarket_volume` and gates 5-8, as defect fixes.
   - Decision rule: adopt only as rule fidelity, with an expected R change of about 0 (SEL-1 verdict). If the count goes off, the desk logs an "A5 would kill" flag on every plan.
4. **Prospective data that backtests cannot make.**
   - You tag each manual entry (5m-NH, level break, 10-s dip, short) and write its stop at entry into `research/trade-journal/journal.csv` (3 rows today).
   - The desk logs MISSED, each pillar's state, and halt transitions (`session_builder.py:162-163`).
   - Decision rule: after 200 filled paper trades, compare the plans A5 would have killed with those it kept, in net R at $40 risk, as one comparison with a day-clustered bootstrap. Your own trades go through `scripts/trade_audit.py`.


## Verdict (written 2026-10-02, before the follow-up tests)

**Reverse-engineering Ross only makes sense now as a narrow follow-up, and the missing 1-minute pullback is not what holds the bot back.**

- **It has already been done.** On 2026-09-28 the repo extracted 1,512 of his trades and rebuilt 702 of them on the tape (`research/ross-trades/REPORT.md`). Findings [Confirmed]:
  - 90% of his entries buy at or above the high of day so far.
  - He was on the #1 gainer 57% of the time and held a median 2 minutes (`research/ross-trades/results/analysis.txt:26, :29, :41`).
  - His exact entries, managed the way the bot manages trades, lose: gross -0.141 R, net -0.441 R (`analysis.txt:61`).
- **The mechanical copy of that profile faded.** F7, the leader breakout, is the only rule with a positive gross ever found on a point-in-time universe. It went from +0.171 on train to +0.008 in 2023 and -0.071 on the 2024-26 holdout (`REPORT.md` §4, §7) [Confirmed].
- **Ross does not buy a climb that has no pullback either:** "I usually set my max loss at the low of the previous wave. So, if we're looking at a chart and it's just a bunch of really big green candles, then we know that our max loss is somewhere way down" (`_fsRWw0VbS4` [00:17:24]-[00:17:34], teaching).
- **The real bottleneck is cost against an entry worth about zero.** Every 1-minute or 10-second pullback entry measured sits between -0.40 and +0.08 R gross. Costs are 0.387 R a trade and grow as the stop gets tighter relative to the spread (`research/paper-exercise/reports/2026-10-02-full-report.md` §4.1) [Confirmed].
- **What the 2026-09-28 work could not see** was his own exit applied to his entries, a fair random baseline, the 39 of 61 batches never extracted, Level 2, and his size on the runner. Most of that cannot be rebuilt here without the deleted ledger and network access.

**AMOD 2026-10-02 (one name; the trade facts are from chat and are not in the repo):**
- AMOD was not short of 1-minute pullbacks. Between 07:00 and 09:44 it printed 83 green, 72 red and 7 doji 1-minute bars, with a longest green run of 6 (scratch amod_mech.py (session scratch, not committed), SIP bars) [Observed].
- The bot was held back by three rules: the 3-loss lock, the pullback-volume gate and the +0.3% entry cap. Relaxing each of them has already been measured over 10 years as no better:
  - Wider entry cap: -0.487 / -0.500 R against -0.477 (`2026-10-01-rules-audit.md` §3).
  - Freeing the volume gate: -0.424 / -0.489 against -0.430 / -0.502 (`ablation_live_costs_v2.txt`).
  - Changing the lock streak to 2 or 4: not better on both measures (rules audit).
- Loosening the red-candle rule itself moved net R by +0.011 (-0.424 against -0.435; scratch inv/pause_probe.py (session scratch, not committed); exploratory, decides nothing).

