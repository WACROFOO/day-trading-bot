# Audit: why the week of 2026-07-27 produced almost nothing

Result under audit: 5 sessions, 3 trades, 1 winner, +$49.97 (+0.50%).

The question is not "why was P&L bad" — it was roughly flat. It is **why only
3 trades in 5 days when the source describes ~2 per day**, and why the two
busiest days produced none.

---

## Measurement 1 — the watchlist names were already broken

`PARAMETERS.md:31` lists an explicit **reject**: *faded from pre-market high*.
It was never implemented.

Of the 19 watchlist name-days that week, **13 had already faded more than 10%
off their pre-market high before the opening bell**:

| Day | Names, open vs pre-market high |
|---|---|
| Mon 07-27 | EDBL −21%, LGHL −48%, DFNS −20%, BIYA −13% — **all four** |
| Tue 07-28 | INLF −12%, PMN −14%, EHGO −11% |
| Wed 07-29 | NCRA −24%, AMIX −18%, VIVK −13%, GMM −14%, STFS −25% — **all five** |
| Thu 07-30 | NUWE −13% |
| Fri 07-31 | — (CUPR 0%, TCX −1%) |

## Measurement 2 — and they stayed broken

Median share of the 09:30–11:30 window spent **above VWAP**:

| Day | Above VWAP | Median run | Median net | Trades |
|---|---:|---:|---:|---:|
| Mon 07-27 | **2%** | +8.5% | −15.4% | 2 |
| Tue 07-28 | 41% | +18.0% | +2.3% | 1 |
| Wed 07-29 | **9%** | +24.2% | −15.9% | **0** |
| Thu 07-30 | **8%** | +6.6% | −17.4% | **0** |
| Fri 07-31 | 62% | +55.4% | +13.3% | **0** |
| **Week** | **16%** | +14.4% | −6.4% | 3 |

Fade rate 63% against a 58% seventeen-day baseline.

The entry gate requires `price > VWAP`. If names sit below VWAP 84% of the
window, almost nothing can pass — and `price > VWAP` was indeed the largest
single rejection (69 of the week's rejections).

**Wednesday is the clearest case: 46 setups, every one of the five names faded
off its pre-market high, 9% of bars above VWAP, zero trades.** The gate refused
to trade a day on which every candidate was already dead. That is the rule
working. The defect is upstream — those names should never have been on the
list.

---

## Root cause

**Selection, not execution.** The watchlist was built on gap size and relative
volume alone, with no check that the stock was still *going up* when trading
started. The gate then filtered out the wreckage one setup at a time, which
looks like an over-strict gate but is really a contaminated input.

This also explains the low trade count: feed the engine faders, and it
correctly declines them.

---

## Fixes applied — both documented, neither invented

**1. `rate_of_change_min > 0`** — "% gain per minute, rising"
(`PARAMETERS.md` §1). The corpus gives the sign but no magnitude, so it is
expressed without a threshold: at 09:35, is the stock above its open? A name
that has broken from its pre-market high is falling by then. Uses only
09:30–09:34 bars.

Searched for a numeric fade threshold to implement `faded from pre-market high`
directly; the corpus does not state one, so none was invented — the
rate-of-change sign is the number-free expression of the same idea.

**2. `volume_min >= 500,000` cumulative** (`PARAMETERS.md` §1, n=102) — a hard
documented number that was missing.

First applied to the first five minutes, which was wrong: the spec says
"cum.", meaning accumulated over the session. The 5-minute reading excluded TCX
on Friday — the name that then ran +36%. Corrected to a rolling cumulative
check evaluated at each setup, making it a seventh gate condition.

**3. Watchlist persistence ordering** — `watchlists20.json` was written before
the rate-of-change filter ran, so `audit20.py` was replaying a watchlist the
run never traded. The audit reported 6 trades while the run reported 2. Fixed:
persisted after all selection rules.

---

## Effect

| | Before | After |
|---|---:|---:|
| Week trades | 3 | 3 |
| Week P&L | +$49.97 | +$49.97 |
| 17-day trades | 6 | 2 |
| 17-day P&L | +$817.95 | +$633.30 |

The week is unchanged — the three names actually traded (AGPU, BIYA, EHGO) pass
the new rules, so the fixes removed candidates without removing trades. Over 17
days the cumulative-volume gate is more binding, cutting 6 trades to 2.

Look-ahead audit passes at every cut-off, now against the same watchlist the
run uses.

---

## What this does and does not establish

**Does:** the low trade count that week was substantially a selection defect,
and two documented rules were missing. `price > VWAP` doing most of the
rejecting was a symptom of feeding it dead stocks, not evidence of an
over-tight gate.

**Does not:** the fixes are not validated by these numbers. Trade count fell to
2 over 17 days, which is the wrong direction for the frequency problem, and
n=2 says nothing. The justification is that both rules are in `PARAMETERS.md`
and were simply absent — not that P&L improved.

The market context matters too: the source describes no-trade days as real but
rare (`glDujVuXiiI` — *"the second no trade day of 2025... I looked at the
scans, I didn't see anything I liked"*). Three of five sessions producing
nothing is far more than that, so selection is unlikely to be the whole story.
