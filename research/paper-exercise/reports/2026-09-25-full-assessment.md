# Full assessment, 2026-09-25 — the bot, the platform, the rules, and a seven-session backtest

**Provenance.** Trades and refusals come from the owner's pasted `review`,
`missed` and desk logs of 2026-09-18 to 09-25. The backtest is
`python3 scripts/backtest_recent.py` (committed with this report): Yahoo
1-minute bars for 2026-09-17 .. 09-25, 31 names the desk carried, 65
symbol-days, 422 pullback plans. Prior evidence is cited by path from
`research/momentum-replication/reports/`. Paper only; nothing here is a
claim of edge.

## 1. The answer in five lines

1. **The machinery now works.** Entries fill at the plan price, stops execute, exits are printed, days settle themselves, the desk survives an outage. None of that was true on 2026-09-22.
2. **The bot is not profitable yet.** Seven live trades, net about −3.8 R planned. Two losses explain almost all of it: a defect exit on 09-22 (−5.41 R) and a stop that slipped on 09-25 (−1.61 R).
3. **One rule was costing money and is now relaxed.** In regular hours a red MACD no longer blocks an entry (amendment A11). It met a test written before the backtest ran.
4. **Every other rule was kept on the evidence.** The price band, the trailing exit and the one-position rule all proved themselves in the backtest. Two gates are promising but not proven.
5. **Your internet is the biggest platform risk.** Every "connectivity lost" line in the logs is the laptop losing its network. The bot now keeps the Mac awake and restarts itself, but a wired connection is the real fix.

## 2. The plan that was followed

| step | what | result |
|---|---|---|
| 1 | list every defect and weakness seen in the logs since 09-18 | §3 and §4 |
| 2 | fix the defects in code, with a test each | §5 |
| 3 | write the rule for relaxing a gate BEFORE running the backtest | docstring of `scripts/backtest_recent.py` |
| 4 | backtest the rules as they are, and with each rule removed in turn | §6 |
| 5 | change only what passed step 3's rule, record it as your decision | A11, `docs/preregistration.md` §5 |
| 6 | this report | |

## 3. The platform, point by point

| # | point | state | what was done |
|---|---|---|---|
| P1 | laptop loses internet → IBKR link drops (error 1100) | **your side**, the main risk | the day now keeps the Mac awake (`caffeinate`), waits for the Gateway, restarts the desk up to 5 times, pauses history requests when IBKR stops answering |
| P2 | a second login on your username (phone, browser) takes the market data (10197) | your side | the desk names it in plain words; close IBKR Mobile and the Client Portal while it runs |
| P3 | NYSE American names (APUS) have no real-time data on this account | account setting | the desk drops them and, since tonight, never re-requests them. Buy "NYSE American" real-time only if you want those names |
| P4 | IBKR history farm stops answering; every request blocked the desk 20 s | fixed tonight | three timeouts in a row pause history for 5 minutes; live bars carry the session |
| P5 | Ctrl-C was read as an outage and the desk restarted | my defect of 09-24, fixed | Ctrl-C now ends the day; the next start settles it |
| P6 | the day ended if the Gateway was not up yet | fixed tonight | waits up to 20 minutes |
| P7 | 1-minute chart showed no candles after switching symbol | fixed tonight | the price axis kept the previous symbol's range after a manual drag; a symbol change now resets it |
| P8 | slow rebuilds (up to 31 s) | fixed 09-24 | news fetch moved off the rebuild; engine queries made cheap |
| P9 | a day the desk did not finish was never graded | fixed 09-24 | settled automatically at the next start |
| P10 | no IBKR float data on this account | limitation | finviz, then SEC shares outstanding labelled as an upper bound |
| P11 | Level 2 panel is simulated | limitation | labelled SIMULATED; buy depth only if a measured rule needs it |
| P12 | `tape.py` used Yahoo while the desk used IBKR | fixed 09-24 | IBKR whenever the Gateway answers |

## 4. The bot, point by point

| # | point | evidence | state |
|---|---|---|---|
| B1 | entry filled far below the plan | WHLR 09-23: plan 8.31, fill 7.87 | fixed by A10; PFSA and GRML since filled within 2 cents |
| B2 | a resting stop did not execute for 50 minutes | WHLR 09-23 | fixed by the stop of last resort; every stop since executed |
| B3 | stop filled far beyond its level on a thin name | GRML 09-25: stop 16.22, fill 15.99, 0.82 R extra | measured on every stop exit (`slip`, `rng30` in TRADES); a refusal rule is dated (A12 candidate) |
| B4 | exits printed nothing | PFSA 09-24 | fixed: EXIT lines |
| B5 | breakeven exits counted as losses toward the daily lock | 09-24 | fixed: ±0.25 R is a scratch |
| B6 | two-cent stops still reach the planner | VEEE 12.53/12.51, JAGX 2.94/2.92 in the backtest | measured (A9); the spread rule A6 refuses most of them live |
| B7 | pre-market entries unproven | 0 pre-market trades so far | nothing to change; the count continues |

## 5. What changed in code tonight

| change | why | test |
|---|---|---|
| **A11**: a red MACD does not refuse a regular-hours entry | met the pre-written rule, §6 | `tests/test_a11_and_assessment.py` |
| price axis autoscale on symbol change | P7 | same file |
| keep the Mac awake during the day | P1 | same file |
| banned no-data names, history backoff, Ctrl-C, Gateway wait, stop-slippage columns | P3–P6, B3 | `tests/test_session_fixes_0925.py` |
| `scripts/backtest_recent.py` | reproducible backtest of any rule set | same file |

## 6. The backtest

Upper bound: fill at the trigger, no commissions, no halts, the pillar gate
and the spread rule not modelled. Stops that the next bar opens through fill
at that bar's open.

**Regular hours, plan by plan** (each plan scored as if taken):

| plans where… | triggered | fixed 2 R | trailing stop | win rate | days positive |
|---|---|---|---|---|---|
| every rule green | 24 | +18.00 | +23.94 | 58 % | 4 of 7 |
| only MACD red | 17 | +11.50 | +7.62 | 59 % | 4 of 6 |
| only volume red | 15 | +3.00 | +12.32 | 40 % | 2 of 5 |
| only VWAP red | 11 | +4.00 | +3.48 | 45 % | 3 of 5 |
| only price red | 7 | −1.24 | −2.96 | 29 % | 1 of 4 |
| two or more rules red | 101 | +22.89 | +25.13 | 45 % | 5 of 7 |
| no rules at all | 181 | +58.15 | +76.25 | 46 % | 7 of 7 |

**Regular hours, as the bot would really trade** (one position at a time):

| rule set | fixed 2 R | trailing stop | break-even then 2 R | trades |
|---|---|---|---|---|
| rules until tonight | +12.00 | **+23.60** | +14.73 | 22 |
| **with A11 (MACD as a flag)** | +23.50 | **+31.22** | +25.23 | 39 |
| without the volume gate too | +29.50 | +44.68 | +31.78 | 53 |
| two positions allowed | +18.00 | +23.94 | +14.73 | 24 |

**How to read it, simply:**

- The rules make each trade better. Plans with every rule green average about +1 R on the trailing stop; plans with no filter average about +0.4 R.
- MACD was removing good trades in regular hours. Seventeen of them, positive on both exits, on most days. It passed every test, so it now flags instead of blocking.
- The volume gate looks costly too, but its result depends on two days out of five. That fails the consistency test, so it stays and keeps being counted.
- The price band is working: the plans it alone refuses lose money.
- The trailing stop is the right exit on this sample. It beat the fixed 2 R target and the break-even variant.
- A second position adds almost nothing. The one-position rule stays.

**Cross-check against real fills.** GRML 09-24 10:07: backtest trail −0.02 R,
live −0.02 R. GRML 09-25 10:28: backtest −0.83 R, live −1.61 R — the live
loss includes a fill at the entry cap and more stop slippage than the
open-price model assumes. The backtest is close on clean fills and
optimistic on thin ones.

**Why this is not proof of profit.** Seven sessions, in sample, no costs.
The 894-session replication found buying gappers negative in every year
2022–2026 (`research/momentum-replication/reports/2026-08-regime-filter.md`)
and found the strategy fails on entry accuracy, not on reward to risk
(`research/momentum-replication/reports/2026-08-target-and-entries.md`).
A positive week is consistent with a favourable regime, which that work says
does not persist.

## 7. Pre-market

Plans with every evaluable rule green scored +18.00 fixed and +38.73 trail
over 54 triggered, but Yahoo carries no pre-market volume, so the VWAP and
volume gates could not be judged there. The live ledger's graded pre-market
cohort read −4 R over 13 on 09-24. Nothing was changed pre-market.

## 8. My own calls, scored

| call | when | outcome |
|---|---|---|
| "the trailing stop gives winners back" | 09-24 | **wrong over seven days**: the trail beat the fixed target |
| GLND "killed on float" | 09-24 tape review | **wrong**: under A5 float flags; corrected in that report |
| "one-position rule costs little" | 09-24 | right: two positions add +0.3 R over seven days |
| restart logic for the desk | 09-24 | **defect I introduced** (Ctrl-C restarted it); fixed 09-25 |
| "the MACD gate refuses money in regular hours" | 09-24, on 9 rows | confirmed on 17 rows under a pre-written rule |

## 9. What you do

Tonight, once, with nothing running, then the normal morning:

```
cd ~/day-trading-bot && git reset --hard origin/claude/playbook-pullback-explanation-tg5c33 && git pull
```

Before each session: laptop on power and, if possible, on a cable; IBKR
Mobile and the Client Portal closed. After 11:30 ET the usual `stuck`,
`review`, `missed`. After 20 trades taken with a red MACD, A11's kill rule is
read the same way as A3's.

## 10. Limitations

Yahoo bars, not IBKR; RTH-anchored VWAP in the backtest against a 04:00
anchor live. Seven sessions. Fill at the trigger, no fees, no halts, pillar
gate and spread rule not modelled. One-position portfolio is time-ordered by
entry, not by the desk's real publication delays.
