# The real-quote cost check — 2026-10-12

```
RUN      · 2026-10-12T1512Z-quotes on the owner's Mac, git 8512a1e, 2,211 s; the report is filed
           verbatim: research/strategy-candidates/runs/2026-10-12T1512Z-quotes/report.txt
RULES    · research/strategy-candidates/PREREGISTRATION.md, amendment 2026-10-12c: the execution
           model and the decision rule were committed (8512a1e) before any quote was fetched
DATA     · Alpaca SIP prints and NBBO quotes · the Mac's bar cache · train 2021-2022 and 2023 only
           — data the five-year run had already read; 2024-2026 untouched
SAMPLE   · S2's four close-exit configurations and S2W: 1,610 trades, 803 distinct; 26 distinct
           trades had no quote at the entry (unresolved — counted, never guessed)
```

Paper only. R a trade; "Q" is the trade executed on the real tape, "proxy" the five-year run's
cost model, "Q0" the real tape with no slippage cent — the best a market order can do.

## 1 · The decision

| | |
|---|---|
| trades (S2 G20·hod·close, train + 2023, trade level) | 454 of 475 re-priced — 4 % unresolved, none cancelled |
| proxy net · Q net · Q0 net | −0.145 · −0.119 · −0.064 |
| Δ = Q − proxy | **+0.026 R**, 95 % day-clustered interval +0.002 … +0.043 |
| the rule fixed in advance | \|Δ̄\| ≤ 0.05 R → **the proxy holds** |

Real execution is a little cheaper than the proxy charged — 0.026 R a trade — and well inside
the band written down before the run.

## 2 · What the quotes say

* **Spreads are tighter than the proxy most of the time and wider in the tail:** at entry the
  real median is 1.0 ¢ against the proxy's 2.2 ¢, the real mean 3.8 ¢ against 3.3 ¢. At the exits
  the median is 1.0 ¢, at the stops and at 15:55.
* **Entry:** the bid minus a cent sits a median 1.5 ¢ (mean 2.9 ¢) under the bar's open.
* **Stops:** the one-minute bars stopped 250 trades; the prints confirm all 250, none later.
  The bar logic is right for these trades.
* **Where the proxy errs most:** names over $10, +0.077 R on 84 trades; under $10, +0.010 to
  +0.016.
* **Even at the touch with no slippage (Q0) the chosen configuration loses −0.064 R a trade.**
  No market order executes better than the touch, so "costs take it" is real, not an artefact
  of the model.

## 3 · S2 under real quotes — every configuration, one position at a time

| configuration | train: proxy → Q | 2023: proxy → Q |
|---|---|---|
| G20·hod·close (the train choice) | −0.047 → −0.012 | −0.089 → −0.072 |
| G20·bar5·close | −0.145 → −0.098 | +0.214 → +0.135 |
| G40·hod·close | −0.135 → −0.086 | +0.360 → +0.399 |
| G40·bar5·close | −0.169 → −0.115 | +0.864 → +0.725 |
| S2W (G20·hod·close, stop 10-20 %) | −0.040 → −0.019 | +0.221 → +0.214 |

Every configuration still loses on 2021-2022. The split between 2021-2022 and 2023 is a year
effect that costs do not touch.

## 4 · What follows, by the rules

* **S2W fails its gate 1.** As a rule, one position at a time, it loses on train: −0.040 R on
  127 trades under the proxy (−0.019 under Q), and gate 1 needs train and 2023 both positive.
  These numbers come from the same trade-building and one-position code that
  `run.py --lead S2W` runs, on the same bar cache, so that command would print the same failure
  and stop before 2016-2020.
* **S2 is closed.** Had the check said "too pessimistic", the re-choice on train under Q would
  have picked the same configuration (G20·hod·close, −0.012, the best of the five) and failed
  2023 the same way (−0.072). The outcome does not depend on which branch the check took.
* **S2's 2024-2026 stays unread** — the one untouched holdout left for short rules on this
  universe. A new idea would need its own preregistration, counted against the 9 S2
  configurations already in `registry.jsonl`.

## 5 · One line of the report is void

"Our shares above the displayed bid size: 425" compared our share count with sizes Alpaca
reported in **round lots** for those years. Its changelog says CTA/UTP quote sizes represented
"the number of round lots available at the quoted price" until **2025-11-03**, and are shown in
shares from then on
([Alpaca changelog](https://docs.alpaca.markets/us/changelog/marketdata-bid-and-ask-size-display-change)).
A displayed 3 was 300 shares. The code now converts lots to shares before comparing; the line
decided nothing.

## 6 · My calls, scored

| my call | what happened | score |
|---|---|---|
| the proxy might misprice these trades enough to spend S2's holdout on the wrong rule | Δ +0.026 R, inside the band; same choice under either cost model | the check was worth its run; the suspicion was **wrong** |
| S2W's likeliest outcome: it fails a gate | it fails gate 1 on train | right |
| "costs take it" (the five-year read-out) | confirmed on the real tape: it loses even at the touch | right |
| reading the size line at face value | I flagged the unit as uncertain in the code, and it was round lots | caught before it misled |

## 7 · What this could not check

* **Borrow and locates:** no number here charges either; real shorts only do worse.
* Depth beyond the displayed touch, queue position, and a short-sale restriction carried over
  from the day before.
* 26 distinct trades had no quote in the 60 s before the entry.
* Q's 4-second latency is the desk's measured median; a faster or slower order moves fills
  slightly.

## 8 · Verdict

**The cost estimate holds, and S2 is closed by its own rules.** Real quotes make S2 0.026 R a
trade cheaper — not enough: every configuration still loses on 2021-2022, even filled at the
touch with no slippage. S2W fails its first gate and S2's 2024-2026 stays unread. With S1 and L1
already closed, **none of the brainstormed candidates is profitable.** Paper only.
