# Paper-trading exercise — the brief

**A prompt. Hand this to a session as the specification for the work.**
Everything below is either already true in this repo (with the commit that
made it true) or a requirement to build. Nothing here is a claim that the
strategy works.

---

## ① Provenance — what is already true, as of 2026-09-06

| Component | State | Where |
|---|---|---|
| Reject cascade (Layer 1 kills) | built, 37 tests | `src/momentum_platform/cascade.py` `f1bd578` |
| Desk consumes the cascade | built | `src/momentum_platform/dashboard/session_builder.py` `2c683fb` |
| IBKR paper order path | **confirmed live** | `scripts/ibkr_paper_preflight.py` `9e23a2a` |
| Executor, two sessions | built, 32 tests | `src/execution/` `ab34e9d` |
| Bracket placed + cancelled end to end | **confirmed live** | `scripts/paper_trade_smoke.py`, 2026-09-06 |
| Risk gate, 5 rules + latch | built, pre-existing | `src/paper_trading/risk_gate.py` |
| Account | `DUR339781` · PAPER · NetLiq $2,143.70 | preflight output |
| Pre-market stop protection | **UNKNOWN — not yet measured** | `scripts/premarket_probe.py`, unrun |
| Trade ledger | **does not exist** | — |
| Reconciliation / replay | **does not exist** | — |

Baseline for regression: `BASELINE-2026-09-06.md`.
One test fails and did before this work: `test_ibkr_stream.py::test_read_only_connect_skips_the_startup_account_sync_when_ib_async_offers_it`.

---

## ② What is being asked

Build a paper-trading exercise on the IBKR paper account that:

1. Trades the Ross small-cap momentum method, pre-market and opening hours.
2. Records **every** trade taken, every setup seen and passed on, and every
   position wanted but not filled — with the reason.
3. Compares each of those against what the market actually did, so the
   decision can be scored rather than remembered.
4. Never holds a position overnight.
5. May, under stated conditions, follow a stuck position into after-hours.

---

## ③ What the evidence already says — read this before designing anything

These are measurements already in this repo. The exercise must be framed
around them, not run as though they do not exist. Summaries quoted from
`research/momentum-replication/reports/README.md`; each names its report.

| Finding | Report |
|---|---|
| **894 sessions, 8,828 symbol-days: buy-the-open on gappers is negative in every year 2022–2026.** The regime is not persistent (r ≤ 0.09 at any lookback) and a regime filter adds nothing at any threshold | `2026-08-regime-filter.md` |
| **The strategy is a bet on the regime, not an edge in a rule.** 0 of 49 bracket settings positive in March 2024 against 36 of 36 in July 2026 | `2026-08-oos-march-2024.md` |
| Mean MFE +13.76% but **median only +5.09% — the excursion is a tail, not a typical outcome** | `2026-08-regime-filter.md` |
| Of 61 tickers he named: 100% were in the pool, structure found on 97%, 31% pass the five pillars, **3 survive the entry rules.** The scanner and the entry gate are where it is lost | reports index headline |
| **The micro-pullback is often a 10-second pattern a 1-minute detector cannot see** | `2026-08-streams-roundup.md` |
| **Every backtest in this repo buys the 09:30 open** — while he names 07:00 78 times against 36 for 09:30, and "pre-market" 161 times against 9 for "the close" | `2026-07-challenge.md` |
| Equal weight beat the pillar score in **16 of 16** matched pairs; raising the score threshold made it monotonically worse | `2026-08-score-basket.md` |
| Our own 31%-close-green over 894 sessions **is** the documented MAX effect (Bali/Cakici/Whitelaw 2011) — and largely unharvestable | `2026-08-known-edges.md` |

**Two consequences that change the build, not just the framing:**

- **The pre-market path is genuinely unmeasured.** Every existing backtest
  enters at 09:30. Trading 07:00–09:30 is therefore *new evidence*, not a
  replication — which makes the logging requirement the point of the
  exercise rather than a side-effect of it.
- **A 1-minute bot cannot see the documented entry.** If the micro-pullback
  resolves in 10 seconds, a bot on 1-minute bars either misses it or enters
  late, and "late" is a different trade with different expectancy. Bar
  resolution is a first-class design decision, and the ledger must record
  which resolution produced each signal.

---

## ④ Hard requirements

### R1 — Log the universe, not the survivors

Recording only what was noticed measures the noticing. At every decision
point, persist **every candidate the scanner returned**, with its cascade
verdict and the gate that killed it. A "what if I had taken it" analysis
built from remembered names is contaminated before it starts.

`research/momentum-replication/reports/README.md` funnel: 61 named → 100%
in pool → 31% pass pillars → 3 survive entry. Without the denominator at
each stage, none of that is visible.

### R2 — Point-in-time or it is not evidence

Every logged field must be **what was knowable at that instant**, never
what is true now. Float, catalyst, news, session high, RVOL, halt state.

This has already bitten, in this repo, in this workstream: the cascade read
`meta["metrics"]`, which is attached *after* the bar loop, so at plan-arm
time every name looked priceless, failed the price gate closed, and 100% of
plans were suppressed. The test that locks it is
`tests/test_cascade.py::test_cascade_is_evaluated_point_in_time_not_from_end_of_session_metrics`.
The same class of defect is recorded as defect 14 in the replication
`HISTORY.md` — the 11:30 forced exit priced off the 15:59 bar, which
revised one week from +$833.28 to +$557.52 and another to −$199.98.

A backtest that reads a value from the future is not pessimistic or
optimistic. It is void.

### R3 — Both R denominators, always

`planned = (trigger − stop) × shares` · `realised = (fill − stop) × shares`

Report in **realised** R. The replication measured realised risk at a
median **1.52×** planned; read in planned R, expectancy was −1.7408 R
against −1.0818 R realised on the same trades, and "losses worse than 2R"
went from 53.5% to 2.4%. Already implemented in
`src/execution/intent.py::PlacedOrder`. The ledger must persist both.

### R4 — NBBO at the instant of fill, or the fill is unverified

**This is the biggest threat to the exercise's validity and it is not in
the original ask.** IBKR paper *simulates* fills. On low-float momentum
names with thin books, a simulated fill at the limit is frequently
unachievable in the real market. Without the quote at the fill instant,
there is no way to tell a real fill from a gift.

Persist bid, ask, bid size, ask size and the exchange timestamp at fill.
Then score every fill: was the printed size actually available at that
price? A paper P&L that has not been through this test is not a result.

Corollary: **never tune on paper fills.** If the fills are optimistic,
tuning on them amplifies the error rather than measuring it.

### R5 — A control, or the result is unattributable

Every claim of the form "the strategy selected well" needs a matched
baseline run on the same candidates in the same sessions. Minimum: random
entry among cascade-passing names, and equal-weight buy-the-open.

The precedent is direct — `2026-08-score-basket.md`: equal weight beat the
pillar score in 16 of 16 matched pairs. A scoring system that loses to its
own equal-weight baseline looks identical to one that works, until the
baseline is run.

### R6 — Pre-register success before the first trade

Written down, committed, timestamped, **before** any trade: the sample
size, the stopping rule, and what result would count as the strategy
failing. Given the 894-session prior, n=20 trades tells you nothing.

Without this, the exercise is p-hacking with a broker attached.

### R7 — Sessions and the hard stop

| Window | ET | Status |
|---|---|---|
| Pre-market | 07:00–09:30 | tradable, limit only, protection UNKNOWN until probed |
| Regular | 09:30–11:30 | tradable, brackets rest |
| Prime | 09:35–10:30 | where the edge is claimed to be — `PARAMETERS.md` §2 |
| Hard stop, new entries | **11:30** | `PARAMETERS.md` §2 `session_close`, "outer edge, not the centre" (n=16) |
| Midday | 11:30–15:00 | `midday_avoid` — no trades |

Enforced in `src/execution/intent.py::refusals` (`ab34e9d`), because the
cascade does **not** enforce it: an out-of-window name returns
`Verdict.LOG` with `plan_allowed True`, and an executor reading only
`plan_allowed` would open a position at 14:00.

### R8 — Pre-market protection is unknown, and must be settled empirically

`.claude/skills/extended-hours/SKILL.md`:

> Extended hours accept **limit orders only** […] **No stop orders of any
> type** — banned because thin tape makes stop hunting trivial […] Your
> stop is therefore **mental or hotkeyed**, never resting.
> […] GTC limit orders do not participate — they sit off-market and fire at
> 09:30.

That is stated for retail brokers generally (the file names thinkorswim,
Lightspeed, Webull). It does **not** say what IBKR does with a stop
carrying `outsideRth=True`. The first smoke test hit the queuing behaviour
directly — `Warning 399: Your order will not be placed at the exchange
until 2026-09-08 09:30:00 US/Eastern` — and a queued order looks exactly
like an accepted one.

**Run `scripts/premarket_probe.py` between 07:00 and 09:30 ET before
building either path.** If IBKR queues the stop, every pre-market entry is
naked from its fill to the bell and needs a monitored exit instead of a
bracket. Those are different systems. `PlacedOrder.protected` is False
until proven otherwise and the runner must read it.

### R9 — Halts are first-class, not an edge case

`PARAMETERS.md` §8b, 46 claims across the corpus:

- LULD halts exist **only** 09:30–16:00 — a quiet pre-market minute is thin
  tape, never a halt
- **5 minutes is a minimum**, and downside halts run long: one documented
  resume took 20 minutes and reopened $17.36 → $13
- **T1 usually means bad news** and commonly resumes near **50%** of the
  pre-halt price; T12 is untradeable
- Bands double in the opening and closing auctions; the closing window is
  15:35–16:00 exactly, and the opening window's times are **not stated
  anywhere in the corpus**

Required: a stated policy for a halt while in a position, and a logged
record of every halt encountered with its resume price. `PARAMETERS.md` §10
is explicit that **"halt-resume fills are unmodellable from OHLCV"** — so
the live log is the only way this ever gets measured.

### R10 — After-hours: exit-only, and never automatic

The request was "if an order gets stuck we could possibly follow it to
after-hours if setup and volume are convenient." Honouring it requires
saying what it costs, because the corpus is one-sided here.

`.claude/skills/extended-hours/SKILL.md`:

| | after hours |
|---|---|
| his own results | **measured not net profitable** |
| leverage | **NO — margin closes by 16:00 or is auto-liquidated** |
| stops | none |
| options | none |

> "After hours: per his own measured stats, the answer to 'should I trade
> AH?' is **no** — watch, note levels for the 07:00 wave, don't trade."

And it directly contradicts requirement 4 (nothing overnight), since an AH
position must still be closed by 20:00.

**"Stuck" must be defined before it can be handled — it is three different
states:**

| State | What it is | Policy |
|---|---|---|
| Entry limit unfilled | nothing happened | cancel at the hard stop. Never follows to AH — there is no position |
| Partial fill | a real position, smaller | manage and flatten normally |
| Filled entry, exit unfilled at 16:00 | **the only real "stuck"** | the AH clause applies |

For the third state only: AH is permitted as an **exit**, never a new entry
and never adding. It requires explicit human confirmation each time —
`MANUAL_CONFIRMATION_REQUIRED`, not a threshold the bot clears by itself —
because the position is unprotected (no stops), unleveraged, and in a
session the source does not profit in. Every AH continuation is logged as
an exception with its outcome, so the clause can be scored on its own
record rather than defended by argument.

**Margin trap:** if the position was opened on margin it is
auto-liquidated at 16:00 regardless of what the bot intends. Check the
account's margin state before relying on any AH plan.

### R11 — Nightly replay must reproduce the decision

Re-run the cascade against the recorded point-in-time inputs and assert it
produces the **same verdict and the same killed_by**. A divergence means
either the log is lossy or the code changed under it. Both are defects and
neither announces itself.

### R12 — Score my own calls

`CLAUDE.md` rule 8. Every review puts session verdicts next to what
happened, wrong ones named as wrong. A review that only counts P&L will
never find a right call that lost or a wrong call that won.

---

## ⑤ The ledger — the actual deliverable

One append-only record per **decision**, not per trade. Trades are the
small subset that reached an order.

```
decision_id · ts_et · session (premarket|regular) · symbol
scanner:     source · rank · why_surfaced
point_in_time: last · bid · ask · bid_size · ask_size · session_high
               volume · rvol · float · float_source · float_quality
               catalyst · catalyst_source · halted · feed_lag_ms
cascade:     verdict · killed_by · every gate + state + value · warnings
outcome:     TAKEN | REFUSED | NOT_FILLED | SKIPPED
             refusal_reasons[]        <- verbatim from refusals()
order:       trigger · stop · target · shares
             planned_risk · fill_price · realised_risk · slippage_ratio
             nbbo_at_fill{bid,ask,bid_size,ask_size,exchange_ts}
             protected (bool) · stop_status
exit:        reason (stop|target|hard_stop|halt|manual|AH_exception) · price · ts
actuals:     filled in later from the tape — high/low/close over the next
             5, 15, 30, 60 min and to the session close; MFE; MAE
             whether the stop would have been hit; whether the target was
```

The `actuals` block is what makes the exercise a backtest rather than a
diary, and it must be filled for **refused and unfilled candidates too** —
that is the only way "the one I passed on" becomes a measurement.

Storage: SQLite alongside the existing paper ledger
(`src/paper_trading/ledger.py`), so the risk gate's day-keying and the
trade record share one clock. Every timestamp in ET, sourced from the
exchange where one exists — never local. Blotter timestamps in this project
are usually France local = ET + 6h in summer, and that has already caused
confusion.

---

## ⑥ Non-negotiables carried from CLAUDE.md

- **Paper only.** Replication over 894 sessions was negative expectancy.
  Analysis here is selection quality, never a claim of edge.
- **No order path in `momentum_platform`.** Two tests fail if one appears.
  Execution stays in `src/execution/` on its own connection.
- **Provenance rule 1.** No price, volume or indicator without a same-turn
  tool output; tape side from `scripts/tape.py`, never hand-rolled fetch
  code. No knowledge-base claim without reading the file that turn and
  citing it by path. If it is not in the corpus, the answer is "not in the
  corpus."
- **Descend the index**, never grep the corpus blind — `kb.py where` →
  `kb.py open` → `corpus.py`. A hook enforces it.
- **Six-state vocabulary**, fail-closed: `PASS` `FAIL` `UNKNOWN` `STALE`
  `NOT_APPLICABLE` `MANUAL_CONFIRMATION_REQUIRED`. Never `ARMED`,
  `QUALIFIED`, `BUY`.
- **Sizing from stated dollar risk only.** Paper buying power reads
  $14,291 against $2,143 of equity — fiction. The stop defines the size.
- `python3 scripts/factcheck.py --staged` before any `.md` commit.
- Never put a model identifier in commits or pushed files.

---

## ⑦ What this exercise cannot check

Stated up front so no result is read as broader than it is.

- **Real fills.** IBKR paper simulates them. R4 tests plausibility against
  the NBBO; it cannot prove a fill would have happened.
- **Halt-resume behaviour.** `PARAMETERS.md` §10: unmodellable from OHLCV.
  Only the live log will accumulate this.
- **Sub-minute entries.** If the micro-pullback is a 10-second pattern
  (`2026-08-streams-roundup.md`), a 1-minute bot is measuring a different
  entry than the one documented.
- **Level 2 / seller walls.** `PARAMETERS.md` §10: 63% of tape-reading
  mentions unresolved; `large seller/buyer` (104 mentions) needs the book.
- **Borrow, spread quality, fees** beyond IBKR's own commission estimate.
- **Regime.** `2026-08-oos-march-2024.md` — a positive result in one month
  says nothing about another. Any conclusion must state the window it was
  measured in.
- **Foreign private issuers (6-K/20-F)** have no S-3/424B dilution
  tripwire. EDGAR by hand, and say so.

---

## ⑧ Verdict — the order to build in

1. **Run `scripts/premarket_probe.py`** in pre-market. Nothing about the
   pre-market path is decidable until it has run. *(Blocking.)*
2. **Build the ledger (§⑤) and R1/R2 logging.** Log-only, no orders. Run it
   for several sessions and confirm the replay (R11) reproduces every
   decision.
3. **Pre-register success (R6).** Commit it before the first order.
4. **Enable regular-hours trading**, 09:30–11:30, brackets, risk gate live.
5. **Add the pre-market path** in the shape the probe dictates.
6. **Add controls (R5) and the nightly reconciliation.**
7. **AH exception (R10) last**, exit-only, human-confirmed, separately
   scored.

Steps 2 and 3 are not preparation for the exercise. Given a 894-session
negative prior, they **are** the exercise; the orders are how the log gets
its data.

---

*This brief asserts nothing about market data. Every strategy figure is
cited to a file in this repo and was read on 2026-09-06. Platform state is
from test runs and live preflight output on the same date. The pre-market
stop question is open and marked as such throughout.*
