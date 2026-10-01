# The bot's operating rules, one at a time — audit (2026-10-01)

```
DATA   · Alpaca SIP 1-minute bars, 04:00-16:00 ET, pre-market volume included
         (data/cache/history, 2,608 sessions 2016-02 .. 2026-08) · candidate-day
         universe of scripts/backtest_history.py (opened $2-20 on a >= 10 % gap,
         reverse splits dropped) · 88,823 plans armed 07:00-11:30
SPLIT  · train 2016-2023 · test 2024-2026 — NOT pristine: the 09-26/29/30
         ablations had read it for stop floors and windows
COSTS  · backtest_recent.cost_r "live": $40 risk, $2,000 cap, IBKR fixed
         commissions, spread proxy (edge hunt) + 1 cent a marketable side
PLAN   · research/edge-hunt/PREREGISTRATION.md, addenda 2026-10-01 and
         2026-10-01b, each committed before its run
CODE   · scripts/rules_audit.py · scripts/indicator_audit.py
OUTPUT · rules_audit_output.txt (first run) · rules_audit_output_v2.txt (corrected)
         · rules_audit_results.json · indicator_audit_output.txt (this folder)
PAPER  · the live ledger (data/journal.sqlite) lives on the owner's Mac and was
         NOT read here; live-only rules are judged on the incident record
```

Paper only. Every configuration in this report loses money after costs; the
question is which rules make it lose less, not which make it win.

## 1. What was considered

* **Rule 5** (still rising, ≤ 25 % off the day's high) and every safety (E),
  order (F) and exit (G) rule of the plain-language list of 2026-10-01.
* **41 preregistered variants**, one at a time against the live rule set B,
  plus two of Ross's own retracement rule (K = 43) and two post-hoc pairs.
* **Each variant in a one-position portfolio** with the live gates: the
  position slot held from order to exit, the daily limits of `journal.risk`,
  the A6 spread rule, flatten at 11:30.
* **Before any rule was judged, the inputs were audited** (section 2).

## 2. Are VWAP, the 9 EMA, MACD and the volume check computed right?

Independent recompute (numpy/pandas) at every plan the detector armed, 300
sampled sessions (`indicator_audit_output.txt`).

| check | desk | backtest | independent recompute | match |
|---|---|---|---|---|
| VWAP, anchored 04:00, (H+L+C)/3 × volume | `indicators.vwap` | same function | agrees on every plan | ✓ |
| 9 EMA on 1-minute closes | seeded with the first close | same | agrees; TradingView's SMA seed flips 15 of 9,832 gates, 13 of them on plans with < 20 bars | ✓ |
| MACD 12/26/9 warm-up | none until 35 bars → WATCH, refused | same | 18 % of pre-market plans have < 35 bars since 04:00 | ✓ (by design) |
| MACD "positive" | histogram > 0 (line above signal) | same | the zero line is never tested — and Ross means exactly "above the signal line" (w97KlUrVDk0 01:32:55; iIC62xnblLc 00:08:49) | ✓ |
| pullback volume < push volume | mean of the pullback bars < mean of the push bars | same detector | agrees | ✓ |
| push volume rising | **not checked** — the docstring said it was | not checked | docstring corrected | ✗ → fixed text |
| the minute being judged | the desk judges the trigger bar **while it forms** | judged at the bar's **close** | of 2,146 plans the backtest allows, 189 are refused at the break; 201 refused plans are allowed there | ✗ (see §5) |
| entry timing | live order on the break, can fill on the trigger bar | **re-touch** within the next 3 bars | 25.4 % of plans broke through on the trigger bar and never came back within 3 bars: the backtest skips them | ✗ (see §5) |
| volume units IBKR vs Alpaca | share volume (ib_async 2.1.0, no scaling) | Alpaca shares | **not measured here** — needs the ledger: `--alpaca-compare` on the Mac | ? |

**Defects found and fixed in the live code** (commit bcfc867 and 57ab97e):

| defect | effect | fix |
|---|---|---|
| a risk-gate veto left an `intent` order row | the one-position rule then refused **every** entry until a human cleared it (reproduced) | the row ends `NotFilled`; test |
| an order the trader refused was marked `Refused`, a status the one-position rule counts as alive | same blocking | `NotFilled`; test |
| the 6-entry daily cap counted the order being asked about | it was a 5-entry cap | counts orders sent; test |
| IBKR warning 2161 capped a buy limit **below** the trigger (BIYA 09-30: 3.00 → 2.97) | fills only on a failed break | cancelled; test |
| a minute partly covered by 10-second candles replaced IBKR's complete minute | volume undercounted for VWAP and the volume gate | IBKR minute kept unless the stream has all six; test |
| the review tallied refusals by raw text | A8 filed under "11", every A6 pair its own key | one shared `refusal_key`; test |
| a decision's gates could not be reproduced from the ledger's bars | audits mixed timing with formula | `decisions.chart_json` stores the values judged on |

## 3. The ten-year measurement — every rule, every variant

Net R per trade (train 2016-2023 / test 2024-2026), one position, live costs.
**A** = the preregistered bar reading. **C** = corrected: on a fill that came
back down to the cap, the fill bar's earlier high no longer raises the trail,
and the 3-minute expiry counts minutes, not bars. A change is adopted only if
it passes the preregistered rule under **both** (addendum 2026-10-01b). `lb` =
the day-paired lower bound of the gain over B at one-sided α = 0.05 / 43.

| | A train / test | C train / test | test trades / month |
|---|---|---|---|
| **B — the live rules** | −0.411 / −0.477 | −0.436 / −0.475 | 46 |
| B, pre-market entries only (C) | −0.472 / −0.544 | | |
| B, 09:30-10:30 (C) | −0.399 / −0.403 | | |
| B, 10:30-11:30 (C) | −0.470 / −0.437 | | |

| rule | variant | A test (lb) | C test (lb) | verdict |
|---|---|---|---|---|
| **5 still rising** | ≤ 15 % · 35 % · 50 % · off | −0.480 (−0.040) · −0.472 (−0.005) · −0.473 · −0.473 (−0.008) | −0.483 · −0.470 · −0.472 · −0.472 (−0.012) | **KEEP 25 %** — no setting matters ✗ |
| | Ross's own rule: pullback ≤ 50 % of the push, with / instead of rule 5 | −0.503 (−0.152) / −0.496 (−0.150) | −0.500 (−0.162) / −0.494 (−0.161) | **do not add** — loses more ✗ |
| **E1 window** | start 08:00 | −0.436 (−0.003) | −0.424 (+0.001) | passes C only ✗ |
| | start 09:30 (no pre-market entries) | −0.383 (+0.003) | −0.396 (−0.027) | passes A only ✗ |
| | end 10:30 · 11:00 · 11:30 (no A8 buffer) | −0.490 · −0.479 · −0.473 (−0.007) | −0.479 · −0.476 · −0.470 (−0.007) | **KEEP 07:00-11:20** ✗ |
| **E2 stop floor** | off / 1 % / 1.5 % (identical: A6 already binds) | −0.488 (−0.031) | −0.485 (−0.032) | **KEEP 2 %** — removing it costs |
| | 3 % | −0.387 (+0.010) | −0.391 (−0.009) | passes A only ✗ |
| **E3 stop vs spread** | off · 2× · 3× | −0.498 · −0.489 · −0.474 | −0.485 · −0.481 · −0.471 | **KEEP 4×** — looser loses |
| | 6× | −0.398 (+0.001) | −0.410 (−0.022) | passes A only ✗ |
| **E6 positions** | 2 at once · no cap | −0.481 · −0.481 | −0.481 · −0.480 | **KEEP one** ✗ |
| **E7 daily limits** | all off | −0.466 (−0.019), drawdown 795 R vs 712, worst day −13.4 | −0.462, drawdown 782 vs 702, worst day −14.2 | **KEEP** — the limits cap the bad days ✗ |
| | loss −2 R · −4 R · streak 2 · 4 · orders 4 · 8 | none better on both | none better on both | **KEEP −3 R / 3 / 6** |
| **F1 sizing** | $20 · $80 · no $2,000 cap | R: −0.508 · −0.471 · −0.477 | R: −0.505 · −0.468 · −0.475 | **OWNER** — a capital decision (§6) |
| **F2 entry order** | expiry 1 · 5 bars | −0.473 (−0.053) · −0.488 | −0.464 (−0.051) · −0.489 | **KEEP 3 minutes** ✗ |
| | cap +0.5 % · +1 % (closer to Ross's 10-20 ¢ offsets) | −0.487 · −0.500 | −0.483 · −0.496 | **KEEP +0.3 %** — wider caps lose more |
| **G1 trail** | 0.5 R | −0.450 (−0.042) | −0.452 (−0.054) | better mean, not significant; KEEP 1 R |
| | 1.5 R · 2 R | −0.513 · −0.579 | −0.502 · −0.570 | **KEEP 1 R** |
| **G4 flat time** | 11:00 · 12:00 | −0.473 · −0.477 | −0.468 · −0.474 | **KEEP 11:30** — no difference |
| **Ross volume (new)** | push volume rising | −0.524 (−0.107) | −0.530 (−0.126) | **do not add** — loses more |
| | push volume elevated | −0.447 (−0.016) | −0.433 (−0.010) | better mean, not significant ✗ |
| **MACD reading** | line above zero and signal | −0.464 (−0.021) | −0.459 (−0.021) | not Ross's rule; not significant ✗ |

**No preregistered single variant passes under both readings.**

### The one candidate — post-hoc, contaminated

| | A | C | CA | H | old costs (A / C) | gross (C) | intrabar entry, gated at the break |
|---|---|---|---|---|---|---|---|
| B test | −0.477 | −0.475 | −0.432 | −0.568 | −0.329 / −0.326 | −0.107 | −0.461 |
| **no entries before 09:30 + stop ≥ 3 %** | −0.293 (+0.055) | −0.304 (+0.030) | −0.310 (−0.017) | −0.430 (+0.028) | −0.179 (+0.021) / −0.189 (−0.003) | −0.022 (−0.057) | −0.327 (+0.023) |

CA = C plus a fill-bar low taken to come before a fill at the trigger. H = C plus
the high first on every later bar. The pair passes A and C and most
robustness readings, not all. It makes about 18 trades a month against 46. It
was chosen after seeing the test years, and both of its levers had been read
on them before; the adversarial review measured that neither leg adds
significantly to the other on test. By §3 of the edge-hunt preregistration it
is **CONTAMINATED**: it is built (`runner.A15_CANDIDATE`, **OFF**) and goes on
only after ≥ 200 prospective paper trades confirm it. Scoring it on the
ledger as sessions accumulate: `exercise.py whatif --start 09:30 --stop-pct 3`.

## 4. Rules a 1-minute backtest cannot judge — from the incident record

| rule | what it prevents | record | verdict |
|---|---|---|---|
| signal younger than 2 min | an order on a plan whose bar is no longer current | 67 "bar clock" refusals in 12 sessions, mostly history loaded at start; one defective morning (09-21, stale plans 142-400 s) | KEEP |
| quote younger than 30 s | an order or a spread check on a price the desk no longer has | no recorded firing | KEEP; it measures when the desk wrote the quote, not the quote's own time — open item |
| one position at a time | — measured in §3 too | 28 refusals; ~15 were a ghost-order defect, since fixed | KEEP |
| no trading on history loaded at start | orders on inputs that were not point-in-time | 132 refusals, zero cost by design | KEEP |
| A8: no entry in the last 10 min | an entry the 11:30 flatten closes | 1 refusal (DCOY 09-23, a winner), 1 incident (GRML 09-22, mostly a flatten defect) | KEEP — §3 shows no gain from 11:30 |
| market sell after 15 s under the stop | a stop the broker never executes (WHLR 09-23: ~50 min dead) | 1 firing (BIYA 09-30) | KEEP; log the ask, the last print and the leg's status at each firing — open item |
| monitored pre-market stop (A1) | IBKR queues pre-market stops to 09:30 | no monitored position ever existed | KEEP while pre-market entries are on |

## 5. What this analysis could not check

* **Entry timing.** The live bot buys on the break, inside the trigger
  minute. The backtest waits for a re-touch over the next three minutes: in
  25.4 % of plans the break never came back (`indicator_audit_output.txt`, (e)). An intrabar model gated on the last completed
  bar reads B at −0.461 and the candidate at −0.327; the true live number sits
  between the models, and 1-minute bars cannot tell where.
* **The minute being judged.** The desk judges the gates on a forming minute,
  the backtest on a closed one. Both swapped groups lose money, so this is a
  calibration gap, not a hidden edge.
* **Spreads.** The cost model is a proxy calibrated on 2016-2022 quotes. The
  stop-width results are mostly cost: before costs, the 3 % floor improves
  B by about 0.01 R.
* **Universe.** Names are chosen on the 09:30 gap, which flatters pre-market
  trades by an estimated 0.02-0.05 R. That bias works against the candidate,
  not for it.
* **Not modelled:** float, news and the pillar count (no historical source),
  halts, the signal and quote clocks, the 15-second stop rule.
* **The live ledger** (`data/journal.sqlite`) is on the owner's Mac. Run
  there: `python3 scripts/indicator_audit.py --ledger data/journal.sqlite`
  and `--alpaca-compare` (IBKR vs Alpaca volume units).

## 6. Verdict

**No rule changes.** None of the 43 preregistered variants passes the
adoption rule under both bar readings. Looser rules lose more: a smaller
stop floor, a looser spread multiple, more positions, wider entry caps,
longer expiries and wider trails. Tighter versions of rule 5, the window and
the daily limits gain nothing that survives the correction. Ross's own
retracement and push-volume rules lose more than the bot's current ones.

**One candidate is built, switched OFF:** no entries before 09:30 plus a 3 %
stop floor (A15). It is about +0.17 R a trade better than B in the corrected
reading, about $6.80 a trade at $40. It stays a candidate because it was
chosen on already-read years.

**Seven live-code defects are fixed.** Two of them could each have frozen
the bot for the rest of a session.

**Sizing is the owner's decision.** At $80 risk the R loss is slightly
smaller (fewer $1 commission minimums per R), but every dollar figure
doubles. At $20 it is the reverse.

Every configuration here loses after costs. This audit sets how the bot
loses least while it is measured; it does not make it profitable.
