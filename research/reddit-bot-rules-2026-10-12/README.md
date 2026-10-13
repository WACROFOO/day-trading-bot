# reddit-bot-rules-2026-10-12/ — would a published Ross-style bot's rules help ours?

| file | what |
|---|---|
| `their_rules.py` | the replay: their rules on our 20 exported days, through the month study's own engine and cost model |
| `results.txt` | its output, every configuration it evaluated (sections A–G) |
| `audit.py` | the checks of the replay: fill-model equivalence, the spike exits, per-day robustness, the old cost model |
| `audit.txt` | its output |

Rerun from the repo root: `python3 research/reddit-bot-rules-2026-10-12/their_rules.py`
and `python3 research/reddit-bot-rules-2026-10-12/audit.py`. Read-only: nothing
here changes the bot.

## 1 · Provenance

```
RULES   · the flow image of "I automated Ross Cameron's small-cap momentum rules into a bot.
          Looking for feedback on the flow" — r/Daytrading, u/Necessary-Gas-1665, 2026-10-11 —
          as read 2026-10-12. Not stored here. Their own record, from the author's comment in
          the thread: ~2 weeks of paper, 13 trades, "slightly negative".
UNIVERSE· research/daily/<day>/ screener + board + decisions: 20 sessions 2026-09-11 → 10-08,
          358 symbol-days; 213 of them have ≥ 40 of the desk's own 1-minute bars (04:00-12:00 ET).
BARS    · the desk's bars (board_bars.csv.gz, bars.csv). The month study used Alpaca SIP and
          found them equal to these (median close difference 0.0); SIP is not reachable here.
ENGINE  · scripts/backtest_recent.py, imported read-only: plans_for_day (FirstPullbackDetector,
          the chart gates, A10 fills, stops a bar opens through fill at its open), simulate,
          entry_cap, cost_r. Bot window 07:00-11:20, flatten 11:30.
COSTS   · "live" (primary): $40 risk, ≤ $2,000 of position, IBKR commissions, the edge hunt's
          spread proxy (research/edge-hunt/results/spread_proxy.json) + 1 ¢ a side.
          "old" (audit.txt §4): $20 risk, 1 ¢ a side.
SPLIT   · the month study's: selection 09-11 → 10-01 (15 sessions), holdout 10-02 → 10-08 (5).
✓ REPLICATION · every plan, selection: fixed 2R −0.820 R a trade (665) here against the month
          study's −0.918 (1,046); trail −1.019 vs −1.124; break-even then 2R −0.895 vs −1.006.
          One-lever deltas on the same signs: VWAP +0.129 vs +0.202, stop ≥ 2 % +0.320 vs +0.293,
          ≥ 3 % +0.354 vs +0.376, first plan only −0.692 vs −0.257 (results.txt §A).
✓ EQUIVALENCE · the replay's own A10 fill (needed to read their 2 % chase beside it) equals the
          engine's on 1,224 of 1,224 plans, gross and net (audit.txt §1).
```

The month study's reference line for "the bot" (G1 G4 VW E9 MC PV, trail) leaves
out A13's 2 % stop floor, which the runner applies (`src/execution/runner.py`,
`SELECTIVE = True`). "Ours as live" below includes it.

## 2 · What was considered

Their rules, box by box, and how each was read here. 53 configurations are
printed in `results.txt`, 8 more under the old costs in `audit.txt`.

| their box | rule | read here as |
|---|---|---|
| FIND | whole market each minute; names up 4 %+ re-priced every 10–30 s | **not testable** — discovery, not plans |
| FILTER | price $2–20 · ≥ 10 % · RVOL ≥ 4.5× (time of day) · float 0.1–20M · news | price = our G1; the others are not re-applied (both bots gate on them) |
| SETUP | 9 patterns | **first pullback only** — the one detector here |
| WAY IN #1 | trigger 1 ¢ over the level, ask polled every 2 s | the A10 fill on 1-minute bars |
| WAY IN #2 | scan 3 s after each candle closes | **not modelled** |
| GATE | front side: ≤ 10 % under the HOD, HOD ≤ 60 min old | `front` |
| | above VWAP | our VW |
| | not a failed breakout | n/a to a pullback entry |
| | chase guard: ask ≤ 2 % over the signal | `chase2` fill: the open up to 2 % over the trigger fills there, above it no trade |
| | fresh signal ≤ 60 s | the trigger trades on the next bar |
| | tight stop ≤ $0.30 | `stop30` |
| | one at a time · done after a loss · −10 % a day (= −2 R at 5 % risk) | portfolio rules, §E |
| ENTER | 2R bracket · 5 % risk · 25 % size until the day is green | `fixed` · R, not $ · `cushion` |
| MANAGE | at +1.5 R the stop locks +0.5 R; sell into a spike: ≥ +1 R after +0.75 R in 60 s | `lock`, `spike`; both together = `theirs` (1-minute bars, the previous close as the price 60 s ago) |
| DAY | entries from 06:00, none after 13:00, flat 15:55 | `wide` regime from 06:00; **12:00-15:55 not read** (the bars stop at 12:00) |

## 3 · What helped, and what did not

Net R a trade, selection / holdout. "On L0" adds the rule to every plan (fixed
2R); "on ours" adds it to our live rules (G1 G4 VW E9 MC PV + 2 % floor, trail
1 R: −0.285 / −0.891, 67 trades). Portfolio: one position, our risk lock (−3 R,
3 losses, 6 entries), total over the month: −21.68 R for ours as live.

| their rule | on L0 | on ours | portfolio | read |
|---|---|---|---|---|
| **2R target** instead of the 1 R trail | fixed −0.778 vs trail −0.988 (all 893) | +0.042 / −0.343 | **−5.32 R** (both periods better) | ✗ **withdrawn**: better on this month (13 of 17 days, both cost models), worse over ten years — §4 |
| **done after a loss** on a name | — | −0.271 / −0.608 (44) | **−15.45 R** (both periods better) | ✓ helps — also under the old costs |
| 2R + done after a loss | — | — | +0.21 R / 31 tr · +0.48 R / 13 tr | ✗ withdrawn with its 2R half; picked after looking |
| front side ≤ 10 % | +0.070 / +0.181 | −0.450 / −0.862 (33) ✗ | — | ✗ helps raw plans, nothing on top of our gates |
| stop ≤ $0.30 | −0.101 / −0.018 ✗ | −0.285 / −0.995 ✗ | — | ✗ hurts — over ten years too (§4); our 2 % floor is the opposite lever, +0.320 / +0.114 |
| fresh signal ≤ 60 s | −0.011 / +0.053 | −0.332 / −0.867 | — | ✗ noise |
| 2 % chase fill | — | +0.152 / −0.984 | — | ? splits between the periods |
| their exit (2R + lock + spike) | −0.939 (all) | −0.304 / −0.540 | −21.10 R | ✗ the spike sold 33 of 34 winners at a median +1.00 R before the 2R target |
| 2R + lock, no spike | −0.835 (all) | −0.101 / −0.420 | −10.19 R | better than our trail, worse than a plain 2R |
| daily stop −2 R | — | — | −16.46 R | ✗ better in selection only, the same per trade in the holdout |
| 25 % size until green | — | — | −4.12 R | ✗ as timing: a constant ¼ size gives −5.85 R and the periods split — it is the smaller size |
| entries from 06:00 | 06:00-07:00 −1.241 / −0.560 (144) | 11 trades | — | ✗ the worst hour on raw plans in selection, better in the holdout |

**Their whole rule set on our names** (G1, VWAP, front side, stop ≤ $0.30,
fresh, the 2 % chase, their exit): −1.080 R a trade over 78 (90 % interval by
day −1.382 … −0.683), against −0.484 for ours (−0.753 … −0.183). One position,
flat size: −45.56 R over 40 trades against our −21.68 over 49. The two
costliest parts: the $0.30 cap with no minimum (our 2 % floor instead:
−1.080 → −0.521) and the spike sell (a plain 2R instead: −1.080 → −0.668).

## 4 · Detail — the two that helped this month, and the ten-year check

- **A plain 2R target — ✗ WITHDRAWN the same day (2026-10-12).** On this month,
  on our live rules, the trail lost 0.48 R a trade and the fixed 2R 0.08 (gross
  −0.100 against +0.234); the 2R was better on 13 of 17 days (audit.txt §3) and
  under the old costs (+0.012 against −0.349, §4); the month study's own L0
  table ranks the exits the same way (`research/month-study/REPORT.md` §3).
  **Ten years say otherwise.** The ablation at live costs already on file —
  61,047 filled plans, train 2016-2023, test 2024-2026
  (`research/paper-exercise/reports/ablation_live_costs_v2.txt`) — has, on the
  current rules, the fixed 2R **worse** than the 1 R trail in both periods:
  −1.331 against −1.218 in train, −1.574 against −1.476 in test (its §2). With
  A13 and the first-or-second-pullback limit (its §3): −0.271 against −0.208 in
  train, −0.190 against −0.325 in test — mixed. A +0.40 R a trade gap on one
  month against −0.11 to +0.14 over ten years (fixed minus trail, the four reads above) is the month, not the exit. The
  recommendation made in the chat that morning is withdrawn.
- **The $0.30 cap — confirmed over ten years.** Same file, §1: "+ stop ≤ $0.30"
  reads −1.291 / −1.590 against the current rules' −1.218 / −1.476 — worse in
  both periods, as here.
- **No second try on a name that stopped you out today — still a lead on
  2026-10-12; ✗ failed over ten years on 2026-10-13 (below).** Plan
  level −0.363 R a trade over 44 against −0.484 over 67; portfolio −15.45 R
  against −21.68, better in both periods; old costs −0.228 against −0.349. The
  month study's stricter "first plan only" made things worse (−0.257 there,
  −0.692 here) — a different rule: it also drops the second try after a win.
  **No ten-year read exists yet**: the ablation never had this lever. It has it
  now (§7).
  **✗ FAILED its ten-year test (2026-10-13, §7):** −0.437 against −0.430 in
  train, −0.488 against −0.502 in test — under the +0.05 it needed in both.
  The month's +0.12 was the month.

## 5 · What this could not check

- **Below one minute:** their 2-second ask poll, the 60-second spike test, the
  order of the stop and the target inside a bar (the stop is taken first).
- **Discovery:** their whole-market minute scan against our 120-s scanner union.
- **Their other eight patterns** and their candle-close entry: no detector here.
- **The pillars** (RVOL by time of day, news, float) — both bots gate on them;
  not re-applied.
- **After 12:00 ET:** their entries to 13:00 and the flatten at 15:55.
- **Spreads as measured:** the exports carry no bid/ask; the proxy prices them.
  Halts and the A6 spread rule are not modelled.
- **Sample:** 20 sessions, 213 symbol-days, 67 trades on our live rules, a
  5-session holdout of 11–22 trades, 61 configurations read. Leads, not results.

## 6 · Verdict

**One of their ideas is still a lead: no second try on a name that stopped you
out** — better on this month in both periods and under both cost models, never
measured over ten years. **✗ Superseded 2026-10-13: the ten-year test (§7)
fails it — no lead is left.** The other, **a plain 2R target in place of the 1 R
trail, is withdrawn**: better on this month, worse over ten years on the
current rules (§4). Their $0.30 stop cap hurts here and over ten years; their
spike sell cut 33 of 34 winners at +1 R; their full rule set loses about twice
what ours does per trade on our names. Nothing here changes the bot.

## 7 · The ten-year test, preregistered 2026-10-12 before any run

`scripts/ablation_history.py` §5 reads both leads on the **live rules** (the
current rules and A13's 2 % stop floor), at the costs the owner passes:

```
python3 scripts/ablation_history.py --costs live      # on the Mac: the history cache lives there
```

| row | what |
|---|---|
| live rules · trail 1R (now) | the reference |
| live rules · fixed 2R · BE at 1R, target 2R | the exit lead, already doubtful (§4) |
| live + done after a loss · trail 1R / fixed 2R | the lead still open |

**A lead HOLDS only if it raises the mean net R per trade over the reference by
at least 0.05 in BOTH the train (2016-2023) and the test (2024-2026) years, with
at least 300 test trades.** Holding makes it a direction for the owner's
amendment (`docs/preregistration.md` §5), like A13 — harm reduction, not the
ablation's own adoption rule, which no configuration has met. The forward
shadow suggested that morning is not set up: one ten-year run settles more than
months of forward sessions, and its 2R half already fails.

### Result — run 2026-10-13, in the cloud on the full history cache

The cache was complete here (2,608 sessions, 24,831 symbol-days, none
missing), so the run did not wait for the Mac. `python3
scripts/ablation_history.py --costs live`, output in
`research/paper-exercise/reports/ablation_live_costs_v3.txt`. Its §1–§4 are
line for line those of `ablation_live_costs_v2.txt`, for example trail −1.218 /
−1.476 and fixed 2R −1.331 / −1.574 on the current rules. Its §5, net R a
trade:

| configuration | train n | train R | test n | test R | verdict |
|---|---:|---:|---:|---:|---|
| live rules · trail 1R (now) | 3,200 | −0.430 | 2,266 | −0.502 | the reference |
| live rules · fixed 2R | 3,200 | −0.515 | 2,266 | −0.515 | ✗ does not hold |
| live rules · BE at 1R, target 2R | 3,200 | −0.474 | 2,266 | −0.510 | ✗ does not hold |
| live + done after a loss · trail 1R | 2,492 | −0.437 | 1,745 | −0.488 | ✗ does not hold |
| live + done after a loss · fixed 2R | 2,591 | −0.524 | 1,812 | −0.465 | ✗ does not hold |

**Neither lead holds.**
- **"Done after a loss"** moves the mean by −0.007 in train and +0.014 in test,
  against the +0.05 it needed in both.
- **The 2R target** is worse than the trail in both periods on the live rules,
  as §4 found on the current ones.

The bot is unchanged.

The live case that made this a question, MNDR 2026-10-12, was the bot's own
five tries on one name (`research/daily/2026-10-12/review.md`):
- the first lost −0.81 R;
- the next four made −0.60, +0.00, +0.08 and −0.35 R on the fills.

Ten years say that day was an anecdote.
