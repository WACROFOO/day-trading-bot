# Lessons carried over from the Ross Cameron project

Everything here comes from this repo: the code in `src/paper_trading/`, its
tests, the knowledge base, and the commit history. Each lesson is written as
**what happened**, then **the rule for the new system**. The point is to pay
for each mistake only once.

There is a section at the end for lessons that are not in the repo: real
broker rejections, order mistakes, and what went wrong when you were trading.
Those are often the most valuable ones, so please add them.

---

## A. Why the old approach could not be profitable

### A1. Costs were a quarter of the risk on every trade

The platform's own cost model (`src/paper_trading/broker.py`) charges $0.02
slippage + $0.005 commission per share on each fill, which is **$0.05 per share
per round trip**. The strategy caps the stop at $0.20 per share
(`stop_max_distance` in `knowledge-base/strategies/PARAMETERS.md`) and the
typical target is $0.15–0.20.

So every trade started **0.25R in the hole**, and costs took 25–33% of a
typical winner. Very few edges survive that.

**Rule:** round-trip costs must be a small fraction of the expected move. For a
daily-bar trade on a liquid ETF, the spread is a few hundredths of a percent and
the expected move is several percent, so costs land at a few percent of the
move instead of a third. Every backtest also runs at **2× costs**, and a
strategy that only works at 1× is rejected.

### A2. Free data is 15 minutes late, which kills intraday decisions

yfinance data is ~15 minutes delayed (README, scanner, app). Intraday entries,
stops and tape reading on delayed data are simulation, not trading. Real-time
data costs money every month.

**Rule:** decide from end-of-day data, where free data is accurate. The system
runs once a day after the close.

### A3. The edge depended on inputs nobody could compute

- Float is not reliably available for free (`floatShares`, README §Scanner).
- The news catalyst is a manual check.
- Support resolves to discretionary confluence: 424 of 963 actionable support
  mentions in the corpus name no level at all (commit `d6a04ae`).
- Tape reading needs depth of book (commit `0cd6508`).

A backtest of those rules measures the proxy chosen for each input, not the
strategy.

**Rule:** every input to every signal must be computable from data we actually
have, and available point-in-time, meaning it was known on the day the decision
would have been made.

### A4. The advertised numbers did not add up

Worked through, the corpus values imply about **+3.2% per day**
(PARAMETERS.md §9). Nobody compounds that.

**Rule:** before building anything, sanity-check what a strategy's rules imply
per year. Anything that implies more than ~20–25% a year, sustained, is a
red flag to investigate, not a target.

### A5. Marketing is not evidence, and survivors are not a sample

These are the knowledge base's standing rules (`knowledge-base/README.md`),
learned the hard way on this project. They apply unchanged.

---

## B. Order submission and execution

### B1. One funnel for every order

Every order path goes through `broker.py`. The raw ledger write
(`ledger.record_fill`) is unguarded on purpose, and UI code must never call it
directly.

**Rule:** strategies output **target weights only**. They never place orders.
A single execution module turns "target vs. current holdings" into orders, and
nothing else in the codebase talks to the broker.

### B2. Check risk before pricing, and record nothing on a veto

`buy()` calls `gate.assert_can_buy()` before it even fetches a quote. A vetoed
order leaves no trace (`test_broker_buy_vetoed_and_records_nothing`).

**Rule:** keep this. All pre-trade checks (STRATEGY.md §3) run before an order
exists. A rejected order is logged as a rejected proposal, never as a
half-created order.

### B3. Exits are never blocked

The lockout refuses new buys, but sells always go through
(`test_sell_allowed_while_locked`). A kill switch that traps you in a losing
position is worse than none.

**Rule:** the kill switch blocks new risk only. Exits and protective stops keep
working while it is latched.

### B4. The lockout survives restarts and recoveries

The latch is stored in SQLite and stays on even if P&L recovers or the process
restarts (`test_latch_persists_across_instances`,
`test_latch_survives_pnl_recovery`). Only an explicit reset clears it.

**Rule:** same for the new kill switch, which only a human can reset.

### B5. No orphan orders

If a fill fails, the order row is cancelled, so no stale OPEN entry is left
behind (`broker.buy`, `broker.sell`).

**Rule:** this matters more against a real broker. Every order gets a client
order ID and moves through an explicit lifecycle: proposed → submitted →
acknowledged → filled, partially filled, cancelled or rejected. Submission is
**idempotent**: running the daily job twice must not buy twice.

### B6. Stops have to track the position

Selling half shrinks the stop; a manual exit cancels it
(`test_sell_half_shrinks_stop_qty`, `test_manual_exit_cancels_stop`).

**Rule:** after any fill, including a partial one, resize the protective stop.
Reconciliation checks that every open position has exactly one matching stop,
for the right quantity.

### B7. Stops only fired while the app was running

The old platform's biggest execution weakness: bracket stops were checked by a
10-second loop inside the Streamlit app (README §Execution model). Close the
laptop and there were no stops.

**Rule:** no client-side stops, ever. Protective stops are GTC orders held **at
the broker**, so they work when our machine is off.

### B8. Price can gap through a stop

A stop fills at the open when the price gaps below it
(`test_gap_through_fills_at_open_minus_slippage`). Daily-bar systems hold
overnight, so gaps are normal, not rare.

**Rule:** the backtest fills gapped stops at the next open, never at the stop
price.

### B9. Limit orders were rejected instead of resting

The simulator raises `limit not marketable` rather than leaving the order on the
book (`_fill_price`). That was fine for scalping, but it is wrong for a daily
system.

**Rule:** the new simulator rests limit orders. A buy limit fills only if the
next bar trades at or below it, at the limit (or at the open if the open is
already better). Unfilled orders expire explicitly; they never disappear
silently.

### B10. Costs on every fill, and cash checks include them

Commission is charged on every fill and never rounded, and the cash guard
counts it (`test_cash_guard_includes_commission`).

**Rule:** keep this, and add what a euro investor actually pays: FX conversion
EUR→USD and per-order minimums.

### B11. Sizing belongs in code, not in your hands

The platform spec found that Ross's Shift+1 hotkey sizes at 90% of buying
power, which contradicts the risk-based sizing in his own rules (commit
`d300ebc`, PLATFORM.md). The two tools that enforce his written risk rules are
the two he discusses least.

**Rule:** position size is always computed by code from the risk rules, then
capped. There is no manual size field.

### B12. Journal semantics that worked

An overnight exit is attributed to the exit date, and a scale-out counts as one
round trip (`test_overnight_exit_attributes_to_exit_date`,
`test_scale_out_is_one_round_trip`).

**Rule:** reuse these definitions for trade statistics (win rate, expectancy,
average R).

---

## C. Process errors

### C1. A runtime database got committed

`paper_trading.db` was swept into git by a `git add -A` (commit `1117b0f`).
It held no credentials, but the repo is public.

**Rule:** never `git add -A`. `systematic/.gitignore` ignores `private/`,
`data/` and `*.db` from day one, before any key or trade log exists. Personal
data and API keys never get committed. Run a secret scan before pushing
anything that touches configuration.

### C2. Automated extraction silently over-matched

Three regex faults turned up only because output was checked by hand: `ding`
without a word boundary matched holding/trading/adding (**11,883 false hits**);
an unanchored `thin` matched "nothing" and "within"; a bare `a setup` counted
every setup as a quality claim (commits `d300ebc`, `0cd6508`).

**Rule:** every signal gets at least one hand-verified test case with known
dates and known answers before its backtest output is trusted.

### C3. Right number, wrong field

The typed-figure parser took the first number on a line, not the one nearest
the keyword: "Trade 2 Day 6: 500 shares at $4.20, float 2.9 million" filed
**2** as the float (commit `c5bcbcd`).

**Rule:** data errors like this pass every smoke test. Test parsers and data
loaders on adversarial examples, and add range checks (a price that moves 25%
in a day with no split recorded gets flagged, not used).

### C4. Two clocks change on different dates

Europe and the US change their clocks on different dates, so for a few weeks a
year the gap is 5 hours instead of 6 (PLAYBOOK.md).

**Rule:** schedule everything in `America/New_York`, store timestamps in UTC,
and take holidays and half-days from an exchange calendar library, not from a
hand-written list.

### C5. Conflicting parameters invite overfitting

The corpus states float < 20M (18 times) and < 10M (16 times) about equally,
and risk per trade as both 2% and 3–5% (commits `c5bcbcd`, `793b8bf`). The
honest response was to sweep both. But every variant you try raises the odds
that one looks good by luck.

**Rule:** log every backtest variant you run (`research/experiments.csv`:
config, data range, result). Choose parameters on in-sample data only, run the
out-of-sample test once, and prefer parameter plateaus over peaks.

---

## D. Reuse map

| From the old project | In the new one |
|---|---|
| `risk_gate.py` latch: persisted, exits allowed, explicit reset | Kill switch: same pattern, new triggers |
| `ledger.py` orders/fills tables, in-place migration | Ledger: adds order lifecycle states and broker IDs |
| Net-of-cost fill math, cash guard incl. commission | Simulator: adds resting limits, FX, gap fills |
| Journal metrics (win rate, expectancy, avg R) | Weekly review report |
| Offline test suite (93 tests, no network) | Same discipline: all tests run offline on fixtures |
| Intraday scanner, 1-minute charts, hotkey ticket | Not reused: wrong timeframe |
| Real-time quotes from yfinance | Not reused: end-of-day data only |

Patterns get copied and adapted, never imported, so `systematic/` and
`src/paper_trading/` stay independent.

---

## E. Your lessons (please fill in)

Things that are not in the repo but happened to you. A line or two each is
enough:

- Orders the broker rejected, and why:
- Orders that filled somewhere you did not expect:
- Times you broke your own rules, and what triggered it:
- Platform or data problems during a session:
- Anything else you never want to repeat:

These go straight into the rule spec or the kill-switch triggers.
