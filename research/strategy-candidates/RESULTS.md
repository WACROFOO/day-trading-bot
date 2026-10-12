# Strategy candidates — the five-year run of 2026-10-12

```
RUN      · 2026-10-12T1350Z on the owner's Mac, git 7163c35, 803 s; the report was pasted back and
           is filed verbatim: research/strategy-candidates/runs/2026-10-12T1350Z/report.txt
RULES    · research/strategy-candidates/PREREGISTRATION.md, committed before the run. The 21
           configuration hashes the Mac printed equal the committed code's (checked when filed)
DATA     · Alpaca SIP 1-minute bars (the Mac's data/cache/history) · candidate_days.csv 2021-2023
           · bars found for train 4,155 of 4,790 and validation 1,609 of 1,811 symbol-days
           · 2024-2026 NOT read: no family passed its gate, so none opened its holdout
COSTS    · live: $40 risk, ≤ $2,000 a position, IBKR fixed both orders, half the proxy spread + 1 ¢
           a marketable side · borrow NOT charged
```

Paper only. R a trade, one position at a time, net of costs unless "gross" is written.

## 1 · What was considered

21 configurations — S1 6, S2 8, L1 6, and L3 as the reference — chosen on train
(2021-2022), checked on validation (2023). Signals before the one-position rule
(train / validation): S1 1,587-1,774 / 605-702 · S2 170-374 / 53-113 · L1 279-491 / 107-211 ·
L3 498 / 216.

## 2 · What survived — nothing

| family | chosen on train (n ≥ 100) | train net (gross) | 2023 net (gross) | fails on |
|---|---|---|---|---|
| S1 afternoon fade | A60·close | −0.180 (+0.035) · 493 | **−0.294** (−0.063) · 237 | the 2023 gate |
| S2 crowded-gapper fade | G20·hod·close | −0.047 (+0.125) · 272 | **−0.089** (+0.075) · 106 | the 2023 gate |
| L1 new-high dip | G50·newlow | −0.087 (+0.048) · 277 | **−0.135** (+0.003) · 107 | the 2023 gate |
| L3 reference | — | −0.371 (−0.036) · 281 | −0.091 (+0.217) · 143 | reference only |

No holdout opened: 2024-2026 is still unread for S1, S2 and L1.

## 3 · Why each failed, and in which way it could work

### S1 — by the time the setup appears, the fade is over

* Gross across all six configurations: −0.022 to +0.035 on train, −0.063 to +0.004 in 2023.
* 73 % of trades end at the 15:55 cover, 27 % on the stop, 5 beyond −1 R. Squeezes are not
  what kills it: after the setup the price barely moves.
* The trigger beats random timing on the same names (+0.077 R, 95 % lower bound +0.005), but
  random shorts on those names lose −0.258 R. +0.08 on a −0.26 base is still −0.18.
* **How it could work: no supported way.** The report's generic levers (wider stops and so on)
  do not apply: with three trades in four ending at the close, the stop rarely binds, so a wider
  one only rescales R around a drift that is zero. No slice was positive in both periods.
  **Closed.**

### S2 — the closest: the fade is there, costs and the year take it

* **Holding to the close beats covering at VWAP in all four pairs, in both periods** (gross):

  | | train close / vwap | 2023 close / vwap |
  |---|---|---|
  | G20·hod | +0.125 / −0.038 | +0.075 / −0.038 |
  | G20·bar5 | +0.096 / −0.075 | +0.457 / +0.074 |
  | G40·hod | +0.022 / −0.049 | +0.509 / +0.084 |
  | G40·bar5 | +0.030 / −0.089 | +1.063 / +0.221 |

  The fade runs past VWAP; covering there cuts the winners while the stop still takes whole
  losers.
* The chosen G20·hod·close:
  * Gross +0.125 against 0.172 of costs (commission 0.052, spread + 1 ¢ 0.120).
  * 47 % reach +1 R (median MFE 0.95 R), and 26 % of those give it all back. 53 % stopped.
  * Win rate 36 %; average win +1.688 against an average loss of −1.040.
  * The trigger beats random timing by +0.101 (lower bound −0.035, not significant).
* **The sign flips with the year.** 2021 +0.026 · 2022 −0.165 · 2023 −0.089. The three
  close-exit configurations that lost on train won 2023 (+0.214, +0.360, +0.864 on 51-102
  trades), and the train choice lost it.
* Borrow: negative before any; at 0.5 % of price a round trip, −0.114.
* **How it could work.** Costs (0.172 R) exceed the gross (+0.125 R). A wider stop lowers the
  cost per R and the share of early stop-outs. The run's lead says the same thing:
  * stops 10-20 % above — train +0.043 (104) | 2023 +0.302 (41).
  * That is **S2W**, preregistered as amendment 2026-10-12b: 2016-2020 first (never read for any
    S2 rule), then S2's one holdout opening only if it holds there.
  * Even a pass leaves borrow untested. These are crowded small caps, and nothing here says they
    could have been borrowed.

### L1 — without hindsight, the entry is a random entry

* All six configurations negative net; gross −0.058 to +0.056 on train.
* The chosen G50·newlow:
  * Trade − random −0.004 (lower bound −0.079): the dip after a new high does what a random
    minute does on the same names.
  * Median MFE 0.21 R, in L1's R of twice the dip depth; 12 % reach +1 R.
* The megaday study's NHD figures were measured on days chosen because they turned out huge:
  median MFE 2.04 R, 81 % reaching 1 R (`research/megaday-study/RESULTS.md` §2). In real time
  that knowledge is gone, and so is the effect. It was the selection, not the entry.
* **How it could work: only by knowing earlier which names will run.** That is the problem the
  megaday study left open; it needs the days where the same signals fired and nothing
  happened. Nothing here can test it. **Closed.**

### L3 — the reference

* −0.371 train (281), −0.091 in 2023 (143); gross −0.036 / +0.217; costs 0.335 R; trade −
  random −0.088.
* Regular hours −0.308 on train (150) but +0.155 in 2023 (74); pre-market −0.444 / −0.355
  (flattered, the universe knows the open). One period each way: noise, not a lead.

## 4 · What the five years say across all four

* **Nothing pays its costs on 2021-2022.** The best gross on train is +0.125 R (S2); costs run
  0.12-0.34 R a trade.
* **The triggers barely beat random timing on the same names:** +0.077 (S1), +0.101 (S2),
  −0.004 (L1), −0.088 (L3).
* **Random entries on these names lose on both sides:** shorts −0.258 (S1's window) and −0.148
  (S2's); longs −0.083 (L1's) and −0.283 (L3's).
* The spread decides more than the side. These names cost more to cross than they move in an
  intraday hold, short or long.

## 5 · My calls, scored

| my call (the brainstorm, 2026-10-12) | what happened | score |
|---|---|---|
| S1 was my first bet | the worst of the three: gross ≈ 0 in both periods | **wrong** |
| S1's risk: "squeezes and halts upward" | not what killed it: 27 % stopped, 5 beyond −1 R; the drift is not there | **wrong** |
| S2 second | the closest: gross positive held to the close in all 8 cells; still negative net, failed the gate | partly right |
| L1: "once the hindsight is removed, the result may vanish" | it vanished: no better than a random entry | right |
| L2 proposed as a candidate | already tested and failed (F7/F8); I found that only when writing the rules | **wrong** — a miss |
| L3 "probably still negative" | −0.371 train, −0.091 in 2023 | right |

## 6 · What this run could not check

* Borrow, locates, a short-sale restriction carried from the day before, halts as such. S2's
  numbers are before all of them.
* Bars were missing for 13.3 % of train and 11.2 % of validation symbol-days. They are not
  imputed, and which way they bias the result is unknown.
* One-minute bars; the order inside a bar is unknown. The spread is a proxy fitted on sampled
  quotes.
* The leads come from many slices (six dimensions × every bucket × 8 configurations). They are
  hypotheses, which is why S2W must pass 2016-2020 before it may open anything.

## 7 · Verdict

**No candidate is profitable after costs on the five years.** All three fail the 2023 gate,
and their 2024-2026 data stays unread. S1 and L1 are closed; L3 confirms that the reference
long loses. S2 is the only one whose fade exists before costs. Its wide-stop lead is
preregistered as S2W and waits for one Mac run, gated on 2016-2020 before it may open S2's
holdout. Paper only.
