# Month study — report

Run 2026-10-09 ~08:10 ET as preregistered (`PREREGISTRATION.md`, addendum A
written before the run). The output is in `output.txt` and `results.json`;
views read after the verdict, which chose nothing, are in `exploratory.json`.

## 1 · Provenance

| what | value |
|---|---|
| universe | the owner's ledger export, `research/daily/<day>/`: screener, board and decision names, **20 sessions, 2026-09-11 to 2026-10-08, 358 symbol-days** (screener 284, board 214, decision 177; a name can be in several) |
| bars | Alpaca SIP 1-minute, 04:00–16:00 ET, raw. **Checked against the desk's own bars: 59,383 minutes compared, median difference 0.0** |
| engine | `scripts/backtest_recent.py` `plans_for_day(desk_vwap=True, gap_miss=True)`, unchanged: the desk's detector, A10 fills, gap-through stops |
| costs | **live** (primary): $40 risk, at most $2,000 of position, IBKR commissions, spread proxy plus 1 ¢. **old**: $20 risk, 1 ¢ a side |
| split | selection 15 sessions (09-11 to 10-01) · holdout 5 sessions (10-02 to 10-08), never read by the search |

**✗ The measured-spread sensitivity could not run.** The desk's `bars` table
carries no bid or ask: 81,714 exported minutes, 0 with a bid. The desk's
quotes live in other ledger tables (`quotes`, `quote_ticks`) that the export
does not carry.

## 2 · What was considered

| regime | plans armed | filled |
|---|---:|---:|
| bot window: arms 07:00–11:20, flat 11:30 | 1,939 | 1,347 |
| open window: arms 04:00–15:50, flat 15:55 | 4,004 | 2,782 |

**450 configurations evaluated.** That count is the measure of how much
searching was done; a month this short will reward some combination by luck.

## 3 · The ladder

**Flexible (L0) — every plan, selection sessions, net R per trade (gross in
brackets):**

| | fixed 2R | trail 1R | BE then 2R |
|---|---|---|---|
| bot window | −0.918 (−0.037) · 1,046 | −1.124 (−0.062) | −1.006 (−0.079) |
| open window | −1.023 (−0.060) · 2,095 | −1.226 (−0.064) | −1.087 (−0.083) |

Before costs the entries are about zero. Costs take about 0.9 R a trade. The
open window loses more than the bot's window; inside it, pre-market loses
less than regular hours (fixed: −0.919 against −1.104).

**The bot's rules today** (G1 G4 VW E9 MC PV, trail 1 R, bot window):

- selection: **−0.879 R a trade** over 119 trades;
- holdout: **−1.694** over 31 trades.

**One lever at a time** (bot window, fixed exit; change in net R a trade
against L0):

- **largest gains:**
  - stop width ≥ 3 % **+0.376**;
  - gain ≥ 50 % **+0.344**;
  - stop width ≥ 2 % **+0.293**;
  - above VWAP **+0.202**;
  - RVOL ≥ 5 **+0.148**.
- **made it worse alone:**
  - first plan only **−0.257**;
  - pullback volume **−0.042**;
  - MACD **−0.040**.

The open window ranks them the same way, led by stop width ≥ 3 % (+0.438).

**Greedy build, selection only** (≥ 30 trades, stop under +0.02 R):

| step | rule set | exit | selection n | net R/trade | total |
|---|---|---|---:|---:|---:|
| 0 | L0 | fixed | 1,046 | −0.918 | −960.7 |
| 1 | stop ≥ 3 % | fixed | 391 | −0.542 | −212.0 |
| 2 | + price $2–20 | BE | 155 | −0.310 | −48.1 |
| 3 | + regular hours | BE | 85 | −0.164 | −13.9 |
| 4 | + above VWAP | BE | 57 | +0.034 | +1.9 |
| 5 | + lighter pullback volume | BE | 33 | +0.333 | +11.0 |
| 6 | + still rising | BE | **31** | **+0.406** | **+12.6** |

## 4 · Checks of the best found (step 6)

| check | result | |
|---|---|---|
| selection mean net > 0 on ≥ 30 | +0.406 on 31 trades | ✓ |
| **holdout mean net > 0 on ≥ 10** | **−0.728 on 7 trades (−5.1 R)** | **✗** |
| beats random entries, same names (gross) | +0.591 against +0.131 (620 random entries) | ✓ |
| one position at a time, net | selection +10.8 R over 30 trades (7 of 11 days up) · holdout −5.1 R over 7 | |
| old costs | selection +0.432 · holdout −0.652 | |

**VERDICT for step 6: BEST FOUND, NOT A CANDIDATE.** It fails the holdout.

## 5 · Read after the verdict (chose nothing)

**Every step on the held-out week:**

| step | selection | holdout |
|---|---|---|
| 0 L0 | −0.918 · 1,046 | −0.823 · 301 |
| 1 stop ≥ 3 % | −0.542 · 391 | −0.661 · 146 |
| 2 + price | −0.310 · 155 | −0.251 · 69 |
| 3 + regular hours | −0.164 · 85 | **−0.250 · 32** |
| 4 + VWAP | +0.034 · 57 | −0.668 · 14 |
| 5 + pullback volume | +0.333 · 33 | −0.728 · 7 |
| 6 + still rising | +0.406 · 31 | −0.728 · 7 |

The first three steps cut the loss in **both** periods. Steps 4–6 turned the
selection positive and made the holdout worse — the signature of fitting
the noise of 15 sessions.

Step 6's selection profit is not one lucky trade: +12.58 R in total, +10.65
without its best trade, +8.76 without its best two. Across all 38 of its trades,
selection and holdout, the gains come from 7 names (MEDS, GRML, VEEA,
RETO, IMCC, MSS, FTFT); 15 others lost.

The ten-year run agrees on the first lever: *"The largest improvement in both
periods is a stop-width floor (≥ 2 % of price: train −0.48 → −0.25, test
−0.61 → −0.35)"* (`docs/preregistration.md`, 2026-09-26).

## 6 · What this could not check

- **Measured spreads:** the export's bars carry no bid/ask (section 1).
- **Sample size:** 15 + 5 sessions, one month, one regime. Seven holdout
  trades cannot confirm anything; they can only refute.
- **SIP, not the desk's tape:** the closes agree minute for minute. Arming
  at the desk's mid-minute reading is not modelled.
- **Approximations:** RV is the daily measure; NW counts any headline.

## 7 · Verdict

**No combination of our strategy's levers made money on both the 15
selection sessions and the held-out week.** The best found, +0.41 R a trade
over 31 trades, lost 0.73 R a trade on its 7 holdout trades.

**What held in both periods is a direction, not a profit:**

- stops at least 3 % of price;
- the $2–20 band;
- regular hours;
- break-even after 1 R, then 2 R.

That set lost 0.16 R a trade in selection and 0.25 in the holdout. The bot's
current rules lost 0.88 and 1.69.

For the owner's forward paper record — both are owner decisions, and nothing
here changes the bot:

1. log step 6 and step 3 on the desk as shadow strategies, which costs
   nothing;
2. consider the stop-width floor as the harm-reducing amendment that both
   this month and the ten-year run point to.
