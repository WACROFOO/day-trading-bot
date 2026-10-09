# Month study — preregistration

Written 2026-10-09 07:46 ET at git `1de02a4`. No result of this study has
been computed or read: the universe export had not left the owner's Mac at
the time of writing. Every choice below is fixed before the first run. A
change after the first run is written as a dated addendum at the bottom,
with the reason, and never replaces a line here.

## The question

The owner, 2026-10-09:

> *"focus on the last month tickers; all ones that popped out in our
> screeners and make your analysis using our strategy; a flexible one, then
> a more solid, until you reach the optimal combination candidate to
> profitability"*

and, on the purpose:

> *"as we are on paper trading the objective is to have a reliable track
> record to measure the accuracy"*

So: on the names **our** screeners showed between 2026-09-08 and 2026-10-08,
which version of our first-pullback strategy — from every plan the detector
arms, to the strictest gate set — would have made money after costs? And does
it still make money on the last week, which the search does not see?

## Universe

Every symbol-day in the owner's ledger export, from `scripts/day_export.py
--since 2026-09-08 --day 2026-10-08 --board-bars`:

- `research/daily/<day>/screener.csv` (every name the scan returned,
  survivor or reject);
- `board.csv` (every name the desk's board carried);
- `decisions.csv` (every name the bot armed a plan on).

The union per day is the universe. Nothing is added from outside the ledger.
If the export does not arrive, this study does not run on a substitute
universe under this preregistration.

## Data

- **Bars:** Alpaca SIP 1-minute, 04:00–16:00 ET, raw prices. This is the
  feed and convention of `scripts/backtest_history.py`: VWAP anchored at
  04:00 with pre-market volume. Cached in `data/cache/history/`.
- **Previous close and average daily volume:** Alpaca SIP daily bars. Average
  daily volume is the mean of the 30 sessions before the day.
- **Float:** the desk's own `float_shares` from `screener.csv`; else SEC
  shares outstanding (`data/sec_cache/`) as an upper bound; else unknown.
- **News:** Alpaca news headlines naming the symbol, published from 16:00 ET
  of the previous session to the minute a plan arms.
- **The desk's own bars with bid and ask** (`board_bars.csv.gz`) are used
  for two things only:
  - the measured-spread cost model below;
  - a fidelity check of SIP against what the desk saw (median close
    difference per symbol-day, reported).

## Engine

`scripts/backtest_recent.py` `plans_for_day(desk_vwap=True, gap_miss=True)`:

- the desk's `FirstPullbackDetector`;
- A10 fills: a touch within 3 bars; a bar opening above the cap
  trigger + max(1 ¢, 0.3 %) fills only if the tape comes back to the cap;
- stops that the next bar opens through fill at its open.

The engine's code is not changed for this study. Two arming regimes run:

| regime | plans arm | flatten |
|---|---|---|
| **bot window** | 07:00–11:20 ET | 11:30 ET — the bot's rule today |
| **open window** | 04:00–15:50 ET | 15:55 ET — the owner's "don't limit the window" |

## Costs

Every trade is scored gross and net.

| model | what | role |
|---|---|---|
| **live** | the owner's sizing ($40 risk, at most $2,000 of position); IBKR fixed commissions; the edge hunt's NBBO-calibrated spread proxy plus 1 ¢ a side | **primary**: the search is run on this |
| **measured** | as live, but the half-spread is the desk's own bid/ask at the arming minute (`board_bars.csv.gz`), where the desk recorded one | sensitivity, reported |
| **old** | $20 risk, commissions, 1 ¢ a side | sensitivity, reported |

## The levers

Each lever is a filter on plans. Its levels are fixed here.

| id | lever | levels |
|---|---|---|
| G1 | price band | $2–20 at the trigger |
| G4 | still rising | close ≥ 75 % of the high so far |
| VW | above VWAP | 04:00-anchored |
| E9 | above the 9 EMA | — |
| MC | MACD > 0 and above its signal | — |
| PV | pullback volume lighter than the push | — |
| GN | gain vs the previous close at arming | ≥ 10 % · ≥ 20 % · ≥ 30 % · ≥ 50 % |
| RV | volume so far ÷ 30-day average daily volume | ≥ 0.5 · ≥ 1 · ≥ 2 · ≥ 5 |
| FL | float | < 20M known · < 10M known (unknown fails, as on the desk) |
| NW | a headline today, before the arming minute | present |
| SW | stop width as % of price | ≥ 1 % · ≥ 2 % · ≥ 3 % |
| WN | when it arms | pre-market only · regular hours only |
| FP | only the first plan per symbol-day | — |
| EX | exit | fixed 2 R · trail 1 R (the bot's A3) · break-even after 1 R then 2 R |

The bot's current rule set — G1, G4, VW, E9, MC and PV, trail 1 R, bot window
— is scored on the same month as the reference line.

## The ladder, and how the candidate is chosen

**Split.** Chronological:

- **selection:** sessions 2026-09-08 to 2026-10-01;
- **holdout:** sessions 2026-10-02 to 2026-10-08. The search never reads it.

**Steps, run on selection only:**

1. **Flexible (L0).** Every plan, no lever, in each regime and each exit.
   Gross and net, per window.
2. **One lever at a time.** Each lever level added alone to L0, in each
   regime. The change in mean net R a trade and in total net R.
3. **Greedy build to solid.**
   - Start from L0 in the regime and exit with the best mean net.
   - At each step, add the lever level (any id not yet used, or a stricter
     level of one already used) that raises the mean net R a trade the most,
     subject to at least 30 trades remaining.
   - Re-pick the exit at every step.
   - Stop when no addition raises the mean by 0.02 R a trade or more.
   - The last step is **the best found**.
4. **Checks of the best found:**
   - **holdout:** mean and total net R, trades;
   - **random entries:** for each of its selection-period trades, 20 entries
     at random minutes of the same symbol-day inside the same window, with
     the same stop distance in % and the same exit. Gross mean R of the
     strategy minus gross mean R of random;
   - **one position at a time:** the bot's portfolio rule (`portfolio`,
     `max_pos=1`), selection and holdout.

Every configuration evaluated is counted and the count is reported.

## What the result is called

**CANDIDATE**, only if all three hold:

1. selection mean net > 0 on ≥ 30 trades;
2. holdout mean net > 0 on ≥ 10 trades;
3. gross beats random entries on the same names (difference > 0).

Otherwise **BEST FOUND, NOT A CANDIDATE**, with the condition that failed.

Either way it is a hypothesis about one month. The test is the forward paper
record: from the next session, every plan it would take is logged with its
outcome — the owner's "reliable track record".

**Nothing here changes the bot's live rules.** Moving the bot onto the
candidate is the owner's decision, recorded as an amendment in
`docs/preregistration.md` §5, like A2, A5 and A8.

## What this study cannot establish

- **One regime.** A month is about 22 sessions. The 2026-09-26 ten-year run
  found every year negative for the current rules
  (`docs/preregistration.md`).
- **A small holdout.** Five sessions screen out the grossly overfit; they do
  not confirm.
- **The bars are SIP, not the desk's IBKR tape.** The fidelity check reports
  the gap; plans that arm only at the desk's mid-minute reading are not
  modelled (desk replay, addendum 2026-10-02).
- **RV and NW are approximations.** RV is the daily measure, which reads
  low before the open; the desk judges RVOL by time of day where it has a
  profile. NW counts any headline; the desk grades it.

## Addenda

*(none yet)*
