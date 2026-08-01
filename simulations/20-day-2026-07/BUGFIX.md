# Four deviations from the strategy, found and fixed

The 21% win rate was a symptom, not a result. Challenged on it, I audited my
implementation against the corpus rather than the P&L. Four rules were wrong.
All four are verifiable against source material, not judgement calls.

The tell was trade duration: **median hold 2 minutes, maximum 5.** No trade
ever had room to work.

---

## Bug 1 — the target was 2R instead of the high-of-day retest

I set `T1 = entry + 2 x risk`. The corpus says the target is a **retest of the
high of day**, and 2:1 is a *filter* applied to that target:

- *"profit target is a move back to the high of day"* — [BUCPPCXOHbs 47:20](https://www.youtube.com/watch?v=BUCPPCXOHbs&t=2840s)
- *"First profit target: retest of high of day"* — [DP4ayEWhmvM 1:31](https://www.youtube.com/watch?v=DP4ayEWhmvM&t=91s)
- *"Profit target: retest of the high of day"* — [iIC62xnblLc 33:39](https://www.youtube.com/watch?v=iIC62xnblLc&t=2019s)
- *"Stop loss at the low of the pullback; profit target at previous high of day"* — [js25lIZMUSY 42:01](https://www.youtube.com/watch?v=js25lIZMUSY&t=2521s)
- *"Retest of the high of day using 2:1 profit-to-loss ratio (if risk is 20 cents, target is 40 cents up)"* — [hLn6LrlXgAE 20:23](https://www.youtube.com/watch?v=hLn6LrlXgAE&t=1223s)

**Why it mattered:** selling half at exactly +2R and moving the stop to
breakeven makes every winner worth exactly +1.00R and nothing else. That is
what produced the earlier "all three winners made +1.00R" finding — it was my
arithmetic, not the market's.

## Bug 2 — "first candle to make a new low" fired on ordinary noise

I exited on any bar whose low was below the previous bar's low with a red
close. The corpus qualifies it: *"first candle to make new low **below flag**"*
— [Xdw5azEqs6o](https://www.youtube.com/watch?v=Xdw5azEqs6o). Below the
pullback structure, which is the stop already.

**Why it mattered:** in a 1-minute uptrend a lower low happens within 1–3 bars
almost always. It closed 5 of 14 trades inside 4 minutes. Replaced with the
bar-local Exit-3 signal that *is* documented: a big red candle on heavy volume.

## Bug 3 — `stop_min_distance` was never implemented

`PARAMETERS.md:161` specifies `stop_min_distance >= spread width`. I had only
the `<= $0.20` cap.

**Why it mattered:** it let through a PLRZ trade with a **2-cent stop on a $15
stock** (0.13% of price, 12 shares after the liquidity cap). No stop that tight
survives the spread. Now floored at an estimated spread — the 25th-percentile
1-minute bar range, since quote data is not available here.

## Bug 4 — 1-bar pullbacks were accepted

`PLAYBOOK.md:99` says the pullback is **2–3 candles**; the bull-flag document
says 2–4. I allowed 1. A single red print is not a retracement.

---

## What the fixes did

| | before | after all four |
|---|---:|---:|
| Trades (17 days, max 5) | 14 | 4 |
| Total P&L | −$1,037.24 | −$560.33 |
| Winners at exactly +1.00R | 3 of 3 | n/a — cap removed |
| Median hold | 2 min | 3.5 min |

**It is still negative, and I have not fully solved it.**

---

## Sweep: this is not a tuning problem

`level_tolerance` is documented as unstated (`PARAMETERS.md:127`, "sweep
0.1–0.5%"). The pullback-index reset rule is also undetermined. Both swept:

| reset | tol% | setups | trades | wins | P&L | exp R |
|---|---:|---:|---:|---:|---:|---:|
| vwap | 0.10 | 476 | 4 | 1 | −560.33 | −0.700 |
| vwap | 0.25 | 476 | 4 | 1 | −560.33 | −0.700 |
| vwap | 0.50 | 475 | 6 | 1 | −952.89 | −0.800 |
| vwap | 1.00 | 469 | 8 | 1 | −1153.17 | −0.728 |
| vwap | 2.00 | 463 | 11 | 1 | −1646.06 | −0.754 |
| newhod | 0.10 | 476 | 4 | 1 | −560.33 | −0.700 |
| newhod | 0.25 | 476 | 5 | 1 | −564.33 | −0.760 |
| newhod | 0.50 | 475 | 7 | 1 | −956.89 | −0.829 |
| newhod | 1.00 | 469 | 10 | 1 | −1175.42 | −0.704 |
| newhod | 2.00 | 456 | 14 | 1 | −1868.23 | −0.751 |

**Exactly one winner in every cell.** Loosening only adds losers. The sign
never flips, so no parameter choice rescues it.

## Diagnostic: the exits are exonerated, the entries are not

Identical entry signals, three exit regimes:

| exit regime | trades | wins | reached T1 | P&L | exp R |
|---|---:|---:|---:|---:|---:|
| as documented (all exits) | 4 | 1 | **0** | −560.33 | −0.700 |
| stop + target only | 4 | 0 | **0** | −799.93 | −1.000 |
| stop + target, no MACD | 4 | 0 | **0** | −799.93 | −1.000 |

**No trade reached its first target under any regime.** With the break signals
removed, every trade goes to the stop at −1.00R. The MACD and VWAP exits were
*reducing* the average loss, not causing it.

So the residual defect is in **entry detection**, and I have not fixed it.

## What is still wrong, honestly

The tracker finds **476 setups across 17 days on ~47 symbols — about 28 a day.**
A human trading this sees perhaps 2–5. My pullback detector is firing roughly
ten times too often, which means most of what it calls a pullback is noise, and
the filters then select four of them on grounds that have nothing to do with
whether the structure was real.

That is the next thing to fix, and it is not a parameter. It needs the impulse
to be qualified — a real push of meaningful size relative to the stock's own
range, not merely two bars of higher highs — before anything after it counts as
a pullback.

**n=4. The P&L number here means nothing.** What means something is the
diagnostic: entries, not exits, and a detector firing an order of magnitude too
often.
