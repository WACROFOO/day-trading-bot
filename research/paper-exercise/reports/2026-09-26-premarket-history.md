# Pre-market and the full history — why it was missing, where it is, and what the repo already knows

**Provenance.** Yahoo pre-market volume: measured this session on GRML's
1-minute bars 2026-09-17..25 (every pre-market bar volume 0). Eleven-year
figures: `research/first-pullback-edge/reports/final_report.md`. Seven-session
figures: `scripts/backtest_recent.py` re-run this session with the cost model
added. Paper only.

## 1. Why the backtests had no pre-market

The container that runs these analyses has no IBKR Gateway and no data keys.
Its only free source is Yahoo, and Yahoo's 1-minute API returns **zero volume
for every pre-market bar**. Without volume, pre-market VWAP cannot be
computed and the pullback-volume gate cannot be judged, so those two gates
were skipped before 09:30 and no pre-market conclusion was drawn.

Two sources DO carry pre-market volume, and both are on your Mac:

| source | where | depth | used by |
|---|---|---|---|
| Alpaca SIP feed | the keys already in your `.env` (the headline keys) | 2016 onward | `scripts/backtest_history.py` (new) and the 11-year study |
| IBKR | your Gateway | about a year of 1-minute bars, slow (pacing) | the live desk |

## 2. What the repo already measured over eleven years

`research/first-pullback-edge/reports/final_report.md` ran a Pine port of this
pullback strategy on 25,716 gapper-days 2016-02 .. 2026-08, survivorship-free,
on the Alpaca SIP feed:

| finding | number |
|---|---|
| trades, basic first pullback | 3,627 over 1,453 sessions |
| expectancy, realistic costs | −1.741 R, 95 % CI [−1.79, −1.69] |
| expectancy, no costs at all | −0.404 R |
| years positive | 0 of 11 |
| with VWAP / EMA / MACD gates | −1.644 R |
| random entry minute, same names | −0.940 R (beats every variant) |
| pre-market trades | **zero** — its volume gates rarely passed on 04:00–09:30 tape |

It is a different detector from the desk's (the Pine's impulse filter is
stricter, its stop capped at 3 %), so it does not answer the question for THIS
bot. It does say the burden of proof is heavy.

## 3. The seven sessions, net of costs

Same run as the 09-25 assessment, current rules with A11, regular hours, one
position, now with IBKR commissions and one cent of slippage a side at the
$20 sizing:

| exit | gross R | net R | trades | days positive |
|---|---|---|---|---|
| fixed 2 R | +23.50 | +10.76 | 38 | 4 of 7 |
| A3 trail | +31.22 | **+17.03** | 39 | 4 of 7 |
| BE+2R | +25.23 | +11.87 | 40 | 4 of 7 |

Costs average **0.39 R per trade** at this size. Seven sessions positive after
costs is encouraging and is still seven sessions.

## 4. The new tool — the desk's own rules over ten years, pre-market included

`python3 scripts/backtest_history.py` (runs on the Mac):

- universe: the 25,716 committed gapper-days, plus every day your desk traded (`--ledger`)
- bars: Alpaca SIP, 04:00–16:00, with pre-market volume, one request per session, cached
- rules: the desk's detector and gates exactly, VWAP anchored at 04:00 like the desk, A11, A10 entry with a gap over the limit counted as no fill, stops gapped through filled at the open, costs
- output: per window and per year, gross and net; a **walk-forward optimizer** (every gate combination × exit × window chosen on 2016–2023, scored once on 2024–2026, beside the current rules on the same years); and **forecast vs actuals** — the simulator on each of your live trades against what really happened

The two live trades checked by hand so far: GRML 09-24 simulated −0.02 R,
live −0.02 R; GRML 09-25 simulated −0.83 R, live −1.61 R. The simulator is
exact on a clean fill and optimistic on a thin one.

## 5. The rule that decides pre-market, written before the run

Proposed for the owner to confirm: **pre-market entries continue if, in the
history run, current-rules pre-market trades number at least 200 and their
NET mean on the A3 trail is above zero in the TEST years (2024 onward).
Otherwise pre-market returns to watch-only until a variant passes the same
test.** Regular hours are judged by the same rule on their own cohort.

## 6. MACD over eleven years (added 2026-09-26)

A11 was decided on seven sessions. The study's trade ledger
(`research/first-pullback-edge/data/trades.parquet`, variant A, common exits,
pessimistic ambiguity) records VWAP, the 9 EMA and MACD at every setup, so the
same question can be asked of 2016–2026. VWAP and 9 EMA read against the
trigger price (the setup bar's close is not stored); MACD green = line and
histogram above zero, as FILTERS.md states it.

| 09:30–11:30, setups with VWAP and 9 EMA green | n | gross R/trade | net R/trade | years positive (net) |
|---|---|---|---|---|
| MACD green (the rule before A11) | 1,237 | −0.490 | −1.608 | 0 of 11 |
| MACD red (what A11 lets through) | 133 | −0.385 | −1.408 | 0 of 11 |
| MACD either (the rule after A11) | 1,370 | −0.479 | −1.589 | 0 of 11 |

Reading: over eleven years MACD as a hard gate **removes setups that did
slightly better, not worse**, than the ones it keeps (gross −0.39 against −0.49,
net −1.41 against −1.61). A11 is supported in direction: dropping the MACD
refusal does not make the strategy worse. It does not make it profitable
either — every cohort, every year, is negative in this study. The study's
detector and exits are the Pine port's, not the desk's (§2), and it recorded
**zero pre-market entries in 11,399 variant-A trades**, so it says nothing
about pre-market. Only `scripts/backtest_history.py` on the Mac, with
pre-market volume and the desk's own detector, can.

## 7. The ten-year run, done (2026-09-26, same day)

Run from the cloud side with the owner's Alpaca paper keys (kept out of the
repository). SIP bars carry real pre-market volume: GRML 2026-09-24 07:00 ET
shows 48,339 shares in one minute where Yahoo shows 0.

**First, a correction to my own tool.** The first version filled every
trigger touch at the trigger. Scored on 300 sampled sessions, that fill model
gives +1.45 R gross a trade in regular hours; a strict "no fill if the bar
opens above the limit" gives +0.05 gross. The difference is fills that cannot
happen: the stock had already jumped past the order. The tool now fills the
way a stop-limit does (at the open inside the cap, at the cap only if the
price returns within 3 minutes, else nothing). The two live fills agree with
it: PFSA 3.73 → 3.74, GRML 14.47 → 14.49. The seven-session result that
justified A11 was made with the wrong model; A11 is reverted
(`docs/preregistration.md` §5).

**The result, 25,716 gapper-days, 2016–2026, current rules, realistic fills:**

| | pre-market | regular |
|---|---|---|
| filled trades | 5,796 | 8,344 |
| gross R/trade, trail | −0.099 | −0.060 |
| net R/trade, trail | −0.605 | −0.487 |
| years positive (one position, net) | 0 of 11 | 0 of 11 |

Pre-market by hour, gross / net trail: 07:00 −0.327 / −0.814 · 08:00 +0.058 /
−0.461 · 09:00 −0.103 / −0.606.

By stop width, both windows, gross / net trail: under 1 % of price −0.238 /
−1.059 (costs 0.82 R a trade) · 1–2 % −0.019 / −0.449 · 2–4 % −0.019 / −0.310 ·
4–8 % −0.048 / −0.242 · 8 % and over −0.024 / −0.166.

Walk-forward optimizer (288 gate × exit × window combinations, chosen on
2016–2023, scored once on 2024–2026): best −0.497 R/trade net on 3,895 test
trades (VWAP + 9 EMA + MACD, trail, regular hours). Current rules on the same
years: −0.615 regular, −0.640 pre-market.

**What it means, simply.** The pullback entry has no edge on its own: before
any cost the average trade is about zero. Costs are then 0.3–0.8 R a trade at
$20 of risk, because the stops are tight, and that is the whole loss. No
combination of the gates changes the sign; the best one loses half a R a
trade out of sample. Pre-market is not where this mechanical version makes
money; it loses slightly more than regular hours. What Ross does in the
pre-market that this cannot see — tape and Level 2 reading, scaling in and
out, 10-second entries, choosing one name out of twenty by feel — is not in
these rules, and this study says nothing about it.

**Limits.** No float, catalyst, pillar count or spread rule; universe chosen
on the 09:30 gap (favours pre-market); one-minute bars; IBKR fixed commission
pricing (tiered is about 30 % cheaper, which does not change any sign).

## 8. Every rule freed one at a time, every Ross guideline added one at a time (2026-09-26)

`python3 scripts/ablation_history.py`. The adoption rule is in its docstring,
written before the first run: positive NET mean on 2024-2026, 95 % lower bound
above zero, at least 200 trades, positive in 2 of 3 test years. Levers ranked
and combined on 2016-2023 only. 63,446 filled plans, realistic fills, costs.

```
1. ONE FILTER LEVER AT A TIME · exit trail 1R (now) · plan level
  lever                               train n  train R  test n   test R
  baseline (current rules)               8347   -0.484    5793   -0.610
  free VWAP                             13325   -0.546    8690   -0.626
  free 9 EMA                             8517   -0.495    5952   -0.629
  free MACD                             12638   -0.565    8617   -0.619
  free pullback volume                  12100   -0.440    8512   -0.528
  free still-rising                      8449   -0.481    5879   -0.608
  free price band                        8539   -0.566    5958   -0.604
  free ALL chart gates                  31444   -0.580   20909   -0.579
  free EVERY rule                       36639   -0.598   26807   -0.577
  + stop <= $0.30                        7711   -0.511    5230   -0.648
  + stop >= $0.05                        6500   -0.297    4388   -0.370
  + stop >= 1% of price                  6415   -0.352    4237   -0.384
  + stop >= 2% of price                  3347   -0.252    2387   -0.346
  + session volume >= 1M                 5248   -0.427    3811   -0.497
  + 1st or 2nd pullback                  3337   -0.539    2363   -0.655
  + 07:00-11:00 only                     7753   -0.476    5389   -0.600
  + 09:35-10:30 only                     3077   -0.352    2092   -0.575
  + pre-market only 08:00-09:30          2430   -0.535    1633   -0.487
  + price $5-20                          4704   -0.421    3327   -0.586
  + price $10-20                         2026   -0.485    1442   -0.558
  + trigger >= pre-market high           2381   -0.362    1709   -0.540
  + trigger >= high of day                591   -0.520     462   -0.831
  + gap >= 30%                           3317   -0.418    2274   -0.616

2. ONE EXIT LEVER AT A TIME · current rules · plan level
  exit                               train gross train net test gross test net
  trail 1R (now)                          -0.033    -0.484     -0.137   -0.610
  fixed 1R                                -0.137    -0.588     -0.255   -0.728
  fixed 1.5R                              -0.155    -0.605     -0.260   -0.733
  fixed 2R                                -0.161    -0.611     -0.235   -0.708
  fixed 3R                                -0.173    -0.624     -0.243   -0.717
  trail 0.5R                              -0.027    -0.478     -0.146   -0.619
  trail 2R                                -0.051    -0.501     -0.171   -0.644
  BE at 1R, target 2R                     -0.129    -0.580     -0.238   -0.711
  Ross ladder 1R/2R                       -0.115    -0.606     -0.228   -0.740
  Ross ladder 2R/3R                       -0.142    -0.622     -0.216   -0.718
  new-low candle exit                     +0.019    -0.432     -0.145   -0.618
  new-low exit + 2R target                -0.085    -0.535     -0.205   -0.678
  breakout or bailout + trail 1R          -0.057    -0.508     -0.140   -0.614

3. GREEDY COMBINATION, chosen on TRAIN only (filters x one exit), then TEST once
  trail 1R (now)                   train -0.122  test -0.249 (n   374)  levers: + stop >= 2% of price, + price $10-20
  fixed 1R                         train -0.087  test -0.084 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  fixed 1.5R                       train -0.180  test -0.209 (n   355)  levers: + stop >= 2% of price, + price $10-20, + 07:00-11:00 only
  fixed 2R                         train -0.099  test -0.059 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  fixed 3R                         train -0.103  test -0.029 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  trail 0.5R                       train -0.099  test -0.174 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  trail 2R                         train +0.047  test -0.099 (n   337)  levers: + stop >= 2% of price, + 1st or 2nd pullback, + price $5-20
  BE at 1R, target 2R              train -0.036  test -0.115 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  Ross ladder 1R/2R                train -0.105  test -0.137 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  Ross ladder 2R/3R                train -0.112  test -0.077 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  new-low candle exit              train +0.045  test -0.147 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback
  new-low exit + 2R target         train -0.049  test -0.183 (n   337)  levers: + stop >= 2% of price, + 1st or 2nd pullback, + price $5-20
  breakout or bailout + trail 1R   train -0.112  test -0.196 (n   337)  levers: + stop >= 2% of price, + price $5-20, + 1st or 2nd pullback

4. THE BEST TRAIN CONFIGURATION, read once on TEST
  exit trail 2R · levers + stop >= 2% of price, + 1st or 2nd pullback, + price $5-20
  train +0.047 R/trade · test -0.099 R/trade over 337 · 95 % lower bound -0.280 · test years 2024 -0.030 (93), 2025 -0.049 (130), 2026 -0.214 (114)
  ADOPTION RULE: NOT MET
```

**Reading, simply.**

- **Freeing a filter never helps**, except the pullback-volume gate, a little
  (−0.61 → −0.53 R on test). Freeing every rule at once gives −0.58: the
  filters are not what is losing the money.
- **The one lever that clearly helps is a minimum stop width.** Refusing stops
  under 2 % of the price (or under $0.05) moves train from −0.48 to −0.25 and
  test from −0.61 to −0.35. Tight stops are where the costs eat the trade:
  a 3-cent stop pays the same commission and slippage as a 30-cent one.
- **No exit changes the sign.** The trailing stop the bot uses is already the
  best of thirteen on test; Ross's scale-out ladder and the new-low exit are
  both slightly worse after costs, because every partial exit pays again.
- **The best combination found on 2016-2023** (stop ≥ 2 %, price $5-20, first
  or second pullback, 2 R trailing stop) was +0.05 R on train and **−0.10 R on
  test**, lower bound −0.28. Fixed 3 R with the same filters reads −0.03 on
  test. Close to break-even; **not positive; the adoption rule is not met.**

**Why Ross is profitable and this is not.** His measured edge sits in what one-
minute bars cannot see: which one name of twenty he chooses and how big he
goes on it, reading the tape and Level 2 before the candle confirms, entering
on 10-second structure, scaling out into strength by feel, and the news. The
mechanical pullback is the frame he trades inside, not the edge itself. Every
study in this repository has reached the same place from a different road.
