# Edge hunt — report

```
DATA   · Alpaca SIP 1-minute bars 04:00-16:00 ET, raw prices, real pre-market volume
         (cache data/cache/history, fetched 2026-09-26) · 22,419 symbol-days, 2,601 sessions,
         2016-02 → 2026-08-21, survivorship-free universe minus its 885 reverse-split rows
       · Alpaca news, created_at <= decision time · SEC shares outstanding (3,104 of 5,797
         names — current ticker map only) · 1,288 real NBBO moments at desk fills
       · ticks → 10-second bars on 460 symbol-days · 80 sessions audited for pre-market
         runners the 09:30 universe cannot see (1,404 names)
       · LEVEL 2 HISTORY: none exists in any source here — not simulated
COSTS  · at the owner's $20 risk a trade: IBKR fixed commissions, plus on every marketable
         side half the quoted spread (proxy fitted on real quotes) plus 1 cent
         (preregistered, primary) · sensitivities: max(spread/2, 1c) "light" · 1c "old"
         · IBKR tiered
SPLIT  · train 2016-2022 · validation 2023 · holdout 2024-2026, one opening per family
RULE   · research/edge-hunt/PREREGISTRATION.md, committed (2dfd229) before any run
```

Paper only. Nothing here is a claim of edge. Everything is measured in R: one R is the
planned risk (trigger − stop) times the shares, about $20.

---

## 1. What was considered

| | count |
|---|---:|
| preregistered families | 5 (+ a combined one, opened only if two pass) |
| configurations per run | 516: selection 69 · pre-market 216 · 10-second 12 · exits/sizing 174 · new 45 |
| runs | 3: v1 · v2 after the framework review's fixes · v3 without reverse-split days |
| configuration evaluations on train | 1,548 — every one in `results/registry.jsonl` |
| read on validation | the train top five of each stage |
| holdout openings | **1 of 6 allowed** (`holdout_ledger.jsonl`) |
| adopted | **0** |

Two deviations from the preregistration, both before any opening: the exits/sizing family
crossed discipline × sizing on its train top five (174 configurations, not the declared
107), and the 10-second family ranked with a 100-plan train minimum, not 300, because its
tick subset is small.

## 2. What survived and what did not

Net R per trade, one position at a time (the bot's rule), final run (v3). Gross is before
any cost; cost is what the model charges.

| track | chosen on train | train | validation | holdout | fails on |
|---|---|---|---|---|---|
| **the bot today** (all six gates, trail 1 R) | — | **−1.135** (5,867) · gross −0.006 · cost 1.129 | **−1.138** (891) | not re-read | — |
| 1 · selection | up ≥ 50 % **and** pre-market volume ≤ 2 M, stops ≥ 2 % of price | −0.389 (383) · gross +0.014 | −0.239 (39) | ✗ closed | validation |
| 2 · pre-market | pre-market-high break 08:00-09:30, stop widened to 2 %, 2 R trail | +0.137 (1,734) · gross +0.657 | +0.149 (274) | **+0.106** (942) | ✗ criteria 1, 2, 5 |
| 3 · 10-second micro-pullback | impulse ≥ 4 %, stops ≥ 1 %, fixed 2 R | −0.607 (136) · gross −0.033 | −0.401 (62) | ✗ closed | validation |
| 4 · exits and sizing | stops ≥ 3 %, new-low candle exit, stop for the day after a +1 R win | −0.345 (1,098) · gross +0.015 | −0.153 (204) | ✗ closed | validation |
| 5 · new hypotheses | opening-range breakout on the session's top 3 by dollar volume, stop ≥ 2 %, trail 1 R | −0.254 (968) · gross −0.018 | −0.213 (165) | ✗ closed | validation |

**F2's holdout, criterion by criterion** (opened at 12:40 UTC, git c5ee317, before the read):

| # | criterion | result | |
|---|---|---|---|
| 1 | positive mean | +0.106 R raw · **−0.060** after the preregistered audit (48 % of such trades are on names the universe misses; those average −0.243) | ✗ |
| 2 | corrected lower bound > 0 (α 0.42 %) | −0.064 | ✗ |
| 3 | ≥ 200 trades | 942 | ✓ |
| 4 | positive in 2 of 3 years | 2024 +0.266 · 2025 +0.022 · 2026 +0.000 | ✓ |
| 5 | beats random entry on the same names | −0.027 (lower bound −0.122) | ✗ |

Cost sensitivity, same holdout: tiered +0.132 · light +0.203 · old +0.427. Criterion 5
fails under every cost model (−0.017 to −0.027). Removing the reverse-split days afterwards
changes nothing: +0.108, bound −0.062, −0.033 against random, audit-adjusted −0.059.

## 3. Why the one survivor was an illusion

The universe is every name that **opened** at least 10 % up. A pre-market entry at 08:30
on such a name already knows it will be up 10 % at 09:30. Split F2's entries by where the
stock stood at the moment the order was armed (train, v3):

| armed when the stock was… | plans | gross | net | vs random, same names |
|---|---:|---:|---:|---:|
| **already up ≥ 10 %** (what a real scanner sees) | 2,776 | +0.160 | **−0.364** | −0.224 |
| up less than 10 % (only the future open put it in the list) | 1,150 | +1.666 | +0.988 | +0.767 |

Validation says the same (−0.361 against +0.920). The whole "edge" was hindsight. With the
real-time condition the pre-market-high break loses like everything else. The protocol
caught it three ways: the random baseline, the audit, and the corrected bound.

## 4. What the tracks say, plainly

* **The entry has no edge before costs.** The bot's pullback averages −0.006 R gross on
  train and +0.024 on validation. Nothing downstream can turn zero into a profit.
* **Costs are larger than we thought.** Real quotes at the desk's own fills: median spread
  3 cents, and the half-spread is over a cent on 70 % of fills. At $20 of risk the bot pays
  **1.13 R a trade**. Stops under 1 % of price pay 2.7 R a trade on a +0.15 R gross.
  (The 2026-09-26 reports said 0.3-0.8 R; that model charged one cent a side.)
* **Selection (track 1).** No feature makes it positive: float bound, fresh headline,
  relative volume, gain, pre-market volume ceiling, former runner, time of the first move,
  price tier, rank of the day. A headline helps a little (−0.99 vs −1.14 with no floor, v1).
* **Pre-market (track 2).** The desk's pullback loses **more** pre-market than in regular
  hours: −1.38 against −0.96 R on train. "Pre-market first" does not hold mechanically.
* **10-second entries (track 3)** beat the one-minute entry on the same names (−0.61
  against −0.99 R) and are still well negative.
* **Exits and sizing (track 4).** The biggest single lever is refusing tight stops: taking
  only stops ≥ 3 % of price, with the new-low exit, moves the loss from −1.13 to about −0.33 R. That is harm reduction, not an edge.
  Ladders, break-even moves, time stops, daily stops and pillar-based sizing change little.
* **New hypotheses (track 5).** Opening-range breakouts on the leaders, first VWAP test,
  hot-market gate, holding past 11:30: all negative.

## 5. The benchmark — how close to Ross

His figures from `knowledge-base/strategies/PARAMETERS.md` §9. His R is his average loss,
so the comparable columns are win rate, average win ÷ average loss, and expectancy per
average loss. His stop is mental, ours rests (same file, §5): not the same instrument.

| | win rate | win ÷ loss | expectancy per average loss |
|---|---:|---:|---:|
| Ross, lifetime | 69 % | — | — |
| Ross, best month (February) | 68 % | 1.42 | +0.65 |
| Ross, losing month (April) | 60 % | 0.57 | — |
| the bot today (train) | 19 % | 0.85 | −0.65 |
| best exits/sizing (train) | 22 % | 1.51 | negative |
| F2 on the holdout (hindsight-inflated) | 41 % | 1.68 | +0.09 |

Nowhere near. The gap is the win rate: 19 % against 60-69 %. One-minute bars cannot see
what he trades on (tape, Level 2, which one name of twenty, scaling), and this study cannot
test those.

## 6. What went into the bot, and what failed

**Nothing went into the bot.** No configuration passed, so there is no switch. Recorded as
failures in `docs/preregistration.md` §5. One fix to an existing tool:
`scripts/backtest_history.py` now drops reverse-split days (its ten-year numbers of
2026-09-26 included 885 of them).

Open for the owner, not adopted: refusing entries whose stop is under 3 % of price (or
2 %). It cuts the loss by about two thirds and is still negative, and the 2024-2026 data
had already been read for stop floors. If the paper exercise continues, it is the one
evidence-backed way to lose less.

## 7. My previous calls, scored

| date | my call | what happened | score |
|---|---|---|---|
| 09-25 | A11: MACD should only flag, not block, in regular hours (seven sessions) | the fill model was impossible; with realistic fills and eleven years, reverted 09-26 | **wrong** |
| 09-25 | the seven-session backtest was positive (+10.76 / +17.03 R) | realistic fills: −2.23 / −13.08 R | **wrong** |
| 09-25 | the price band, the trail and one position "proved themselves" | the trail is close to the best exit here; none of them is a source of edge | partly |
| 09-24 | "the trail gives winners back" | not true over seven days | **wrong** |
| 09-24 | GLND was killed on float | it was not, under A5 | **wrong** |
| 09-25 | the PFSA stop may have failed | it executed | **wrong** |
| 09-26 | a proposed pre-market rule | −0.64 R on the test years; not met | **wrong** |
| 09-26 | a stop-width floor is the strongest harm reducer | confirmed: best lever in tracks 1, 2 and 4, still negative | right |
| 09-26 | pre-market loses more than regular hours for this entry | confirmed: −1.38 against −0.96 | right |
| 09-26 | costs are 0.3-0.8 R a trade | real spreads: 1.13 R a trade | **understated** |
| today | the pre-market-high break was the first positive family | hindsight in the universe; failed its holdout | **wrong** — caught by the protocol, not by me |

## 8. What this analysis could not check

* **Level 2, tape, halts, borrow, short side:** none exist historically here; not simulated.
* **The universe is chosen on the 09:30 gap.** It is audited for F2 only. Every other
  family's pre-market trades carry the same hindsight, which **flatters** them; they
  failed anyway.
* **Float** is an SEC upper bound, known only for names still in the SEC's current map
  (43-69 % of trades by year): a survivorship bias. **No headline in Alpaca is not proof of
  no news.**
* **One-minute bars:** the order inside a bar is unknown; the fill bar's low is assumed to
  come after the fill (pessimistic). Ticks were used on a 460-day subset only.
* **Spreads** come from 1,288 sampled moments, averaged per cell (price tier ×
  pre-market/regular × recent dollar volume). The primary model can charge an entry above
  the stop-limit's own cap (pessimistic); the "light" row bounds that.
* **One position** frees its slot at the fill, not at the order; resting orders are
  ignored.
* **Contamination:** 2024-2026 had been read for the desk's gates, exits and stop floors on
  2026-09-26, before this study. It did not matter: only F2 reached the holdout.
* The framework was reviewed by an adversarial multi-agent pass before the opening
  (13 findings confirmed out of 36). The findings that could move a verdict were fixed
  first, and every family was re-run. The reverse-split finding was fixed after the
  opening; §2 shows it changes nothing.

## 9. Verdict

**No edge.** No version of the bot tested here is positive after costs on data it was not
tuned on. Four of five tracks fail on validation, before the holdout. The fifth, pre-market
high breaks, looked positive only because the universe knew which names would still be up
at the open. On the holdout it does no better than random entries on the same names. With
a real-time scanner condition it loses −0.36 R a trade.

The mechanical pullback has no edge before costs, and costs at $20 of risk are about one R
a trade. What makes Ross profitable is not in one-minute bars.

```
NO SWITCH ADDED. Paper only. Not validated: executable bid/ask beyond sampled quotes,
Level 2, halts, borrow, float beyond the SEC bound, catalyst quality, the Pine's behaviour.
Reproduce: scripts/edge_hunt/ (README there), tests/test_edge_hunt.py.
```
