# External review pack — 18 September 2026

Self-contained. Written to be pasted into another assistant for an
independent review. **The reader has no access to this repository**, so
every fact needed is stated here, with the source file named in brackets
for the owner's benefit. Code that matters is quoted inline.

This pack supersedes `docs/REVIEW-PACK-2026-09-08.md`. It covers what
happened in the ten days since: a defect that silenced the entire strategy,
what the recovered data actually says, and a change of direction that is
about to spend real effort. **The direction change is the thing to attack.**

---

## 0. TL;DR for the reviewer

1. Five live sessions produced **389 decisions and 389 rejections**. Zero
   trades. Cause: the news feed had no API keys, and a gate that fails
   closed read "no data" as "no news". My defect, now fixed.
2. Reconstructing what would have happened: **19 takeable trades, 63%
   win rate, +$229** net of spread. That number **fails two of its own
   three tests** and I do not believe it (§4).
3. The repo's own eleven-year study says this strategy has **no edge**.
4. But the corpus says the pattern is often a **10-second** pattern, and
   every test so far, including the eleven-year one, used **1-minute**
   bars. That is the pivot (§5).
5. I have built the measurement that can kill the new direction in two
   days (§7). **Tell me if it is the wrong measurement.**

**The single question I most want challenged:** is §5 a real insight, or
am I rationalising a negative result into "we tested the wrong thing"?

---

## 1. What this project is

A paper-trading exercise that replicates Ross Cameron's small-cap momentum
method mechanically on Interactive Brokers and grades its own selection
quality. Paper only; the code refuses any account id not starting with
`DU`, IBKR's paper prefix, and there is no switch to disable that.

The owner is neither a developer nor a trader. He is doing this to learn the
method and to find out, honestly, whether it works.

Two historical studies in the same repository already found the method
negative. The exercise exists to measure what it selects under live
conditions, not to prove it profitable.

## 2. Architecture

```
gap scan (finviz) ──► desk watches those names on IBKR real-time data
                              │
                    Layer 1 reject cascade  (price, float, catalyst,
                              │              still-rising, split,
                              │              instrument, tick, buyout)
                    pullback detector (Layer 2, 1-minute bars)
                              │
          every armed plan written to a SQLite LEDGER at that instant
                              │
          runner, separate process, reads the ledger every 5 s
          ├─ REFUSED  (reason recorded)
          ├─ LOG_ONLY (phase A — where the exercise is)
          └─ TAKEN    (phase B+: entry + stop as one bracket)
                              │
          grader adds what happened next from the desk's own bars;
          a replay check re-runs every decision from its stored inputs
```

Key property: **every decision is stored with the exact inputs that
produced it**, so it can be replayed. Replay currently reproduces 389 of
389. This is what made §3 and §4 possible after the fact.

## 3. The defect — five sessions, zero trades

### What happened

| | |
|---|---|
| Sessions | 11, 14, 15, 16, 17 September 2026 |
| Decisions recorded | 389 |
| Verdicts | **389 REJECT**, 0 plans allowed, 0 orders |
| Kill reasons | catalyst **254** · price 88 · float 47 |
| `decisions.catalyst` | **0 on all 389 rows** — never once true |

Nothing ever passed gate 3.

### Root cause

The desk's only headline source is Alpaca's news endpoint, read with keys in
a local `.env`. The owner's laptop was reset on 11 September. I wrote him a
replacement `.env` and **omitted the Alpaca keys**. Every news pull returned
`no headline source` for the whole week.

Gate 3 fails closed. With no feed it read the absence of data as the absence
of news and killed everything that survived price and float.

A second defect, found while verifying the fix against the live endpoint:
the "market roundup" filter keyed on a `category` field that every live
record fills with the **provider name** (`benzinga`). It had never fired
once. VEEA read `catalyst=True` on four headlines, all of which were lists
of other companies.

### What I changed

**Amendment A2** (owner-approved, recorded in `docs/preregistration.md` §5):
gate 3 is now a **flag, not a kill**, for this exercise. It is still
evaluated and recorded; it no longer stops the cascade. The rule as taught
is one constant away.

```python
# src/momentum_platform/cascade.py
CATALYST_GATE_KILLS = False   # A2, owner, 2026-09-17

if killed_by:
    gates.append(skipped("catalyst", "Catalyst"))
elif i.catalyst_today or i.live_theme:
    add(Gate("catalyst", "Catalyst", GateState.PASS, ...))
elif not i.catalyst_source_ok:
    # "no headline source" is UNKNOWN, not "none": the desk cannot say
    # there was no news when it never looked.
    add(Gate("catalyst", "Catalyst", GateState.UNKNOWN, "no headline source",
             ..., kills=CATALYST_GATE_KILLS))
else:
    add(Gate("catalyst", "Catalyst", GateState.FAIL, "none",
             ..., kills=CATALYST_GATE_KILLS))
```

Also: the desk now emits a `news_source` record when it has no feed, so the
cascade can distinguish "no news" from "never looked"; the rules fingerprint
carries the flag so the hash moves and the 389 old decisions keep theirs; and
the roundup filter scans the headline using the word list the browser and CLI
already shared.

**Reviewer question 1.** Is "flag, not kill" the right response, or should a
missing feed have **halted the session** instead? The argument for halting: a
desk that cannot evaluate a mandatory gate is not running the strategy. The
argument against: it is log-only research and the killed cohort is graded
anyway.

## 4. What the suppressed trades would have done — and why I distrust it

Every one of the 389 stored decision inputs was re-run through the amended
cascade. This is the same mechanism as the replay check, not a simulation.

```
389 decisions recorded
├─ 191 still killed   price 88 · float 47 · rising 56
│                     (56 of the 254 catalyst kills would have died at the
│                      next gate anyway — the catalyst gate was masking it)
└─ 198 plan allowed
   └─  53 prospective (live bars; history-armed rows excluded)
       └─  51 trigger touched
           └─  19 takeable under the one-position-at-a-time rule
```

Four readings, each stricter than the last:

| reading | n | target first | mean R | total |
|---|---:|---:|---:|---:|
| every allowed decision | 198 | 50% | +0.51 | +75.7 R |
| prospective only | 53 | 59% | +0.80 | +40.7 R |
| one position at a time, gross | 19 | 63% | +0.83 | +15.7 R |
| net of one spread round trip | 19 | **63%** | **+0.60** | **+11.5 R = $229** |

Grading detail: when one bar touched both stop and target, the **stop** is
credited. 32 of the 51 triggered decisions were blocked by an open position.

### Three tests, and it fails two

**(a) The interval includes zero.**
```
n = 19 · mean +0.604 R · stdev 1.48 · se 0.34
95% CI: −0.06 to +1.27 R          ← includes zero
bootstrap 20,000 resamples: −0.04 to +1.24 · P(mean ≤ 0) = 3.5%
```

**(b) Hold-to-close beats it on the same entries.**

| same 19 entries, same costs | mean R | total |
|---|---:|---:|
| strategy (2R target, stop at dip low) | +0.604 | +11.5 |
| hold to the close | **+1.036** | **+19.7** |
| paired difference | **−0.432** | |

This is **failure condition #2** of the pre-registration, written on
6 September before any of it was known: *"the strategy series does not beat
`hold_close` on the same rows."*

**(c) It is one day.**

| session | trades | net R |
|---|---:|---:|
| 11 Sep | 13 | **+11.0** |
| 15 Sep | 6 | +0.5 |
| 14, 16, 17 Sep | 0 | — |

Without 11 September: n = 6, mean +0.085 R. Six symbols total, TNON alone 6
of the 19 trades.

**Reviewer question 2.** Is there any defensible reading of these 19 trades
other than "noise"? I say no. I want that checked, because the owner very
much wants it to be a yes and I am the one who has to hold the line.

## 5. The pivot — a resolution error, or a rationalisation?

### The evidence

The repository's own parameter file has said this since August
(`knowledge-base/strategies/PARAMETERS.md`):

> Of the "micro pullback" mentions carrying an explicit timeframe, 19 are
> 10-second against 59 one-minute. On a 1-minute chart a 10-second pullback
> is not a candle — it is the wick of one.
>
> **This is not a parameter error, it is a resolution error.** No setting of
> `MIN_DIP_BARS` on 1-minute data can represent it, and it is the mechanical
> explanation for why replicated entries sit in front of a median −1.56 R
> excursion.

Spoken sources, live, deciding in real time:

> *"this is a 10 second micro pullback so let it pull back and then we'll get
> that curl up through 20"* — video `6xIr761eZj8` [41:38]
>
> *"This is a 10-second micro pullback. Looking for the break of 14 and 15."*
> — video `XIQUoLyUWuw` [33:32]

### The state of the code

The desk already receives IBKR **5-second** real-time bars, aggregates them
into **10-second** candles, and publishes them to the browser. The detector
that arms plans is fed **1-minute bars**. Until this week the 10-second
candles were **discarded**: the read that drains them emits each exactly once.

So the eleven-year study (§6) tested a 1-minute version of a pattern the
corpus says is often traded at 10 seconds.

### The counter-argument I cannot dismiss

A finer resolution means **smaller stops**, and the spread is already a
quarter of the stop at 1-minute (§7). It is entirely possible that the
10-second pattern is real, visible, and **not executable by a retail
account**, which would mean the professional trades it profitably and the
replication cannot.

**Reviewer question 3.** This is the crux. Is "we tested the wrong
resolution" a genuine insight, or is it the classic move of a failed
backtest looking for a reason it does not count? What would distinguish the
two, empirically, before spending weeks?

## 6. What the historical studies say

Both are in the repository, both adversarial, both against this strategy.

**`research/first-pullback-edge/`** — ablation of this exact setup.
3,627 trades, 1,453 sessions, 5,797 names, eleven years (2016–2026).
Survivorship-free: 12,613 tickers, 6,701 of them delisted. Costs modelled.

> **Verdict: NO EDGE.** Every variant's 95% CI lies entirely below zero, in
> every one of the eleven years, and in a 478-session untouched holdout.

Detail worth having (variant A, realistic costs, 9,149 trades):

| | |
|---|---|
| win rate | 20.6% |
| average winner | +0.67 R |
| average loser | **−2.06 R** (planned stop is −1.00 R) |
| exits | STOP 67.0% · STOP_GAP 12.6% · target 17.7% |
| reached 1 R at any point | 36.1% |
| **never reached 0.5 R** | **53.0%** |

**An exit study is pointless and I checked.** Crediting every trade that ever
reached a target with the full target, ignoring whether the stop came first,
which no real exit could beat:

| target | would have reached | resulting mean |
|---:|---:|---:|
| 1.0 R | 36.1% | −1.17 R |
| 2.0 R | 19.3% | −1.23 R |
| 3.0 R | 5.8% | −1.36 R |

Every choice deeply negative. The exit is not the problem.

**A correction I had to make mid-review.** The published headline is that a
random entry minute beats the strategy by 0.80 R. The study's **own code**
documents that this comparison is unfair three ways, chiefly the risk
denominator: the strategy uses a buy-stop, so the fill lands above the
trigger and realised risk is a median 1.52× the planned risk that R is
denominated in.

> *"the strategy reads -1.741 R on planned risk and -1.082 R on the risk
> actually taken, so the headline 0.80 R gap to this baseline collapses to
> about 0.14 R"*

I had quoted the 0.80 R figure to the owner as evidence the entry was "worse
than a coin flip on both sides". That was wrong and I corrected it. The
honest statement: the pullback entry is **roughly level with a random entry**,
and both lose about 1 R per trade.

**Reviewer question 4.** Given all of §6, is any further work on this
strategy family justified, or is the correct advice "stop, the universe and
the cost structure are the problem"?

## 7. What has been built, and the measurement that can kill it

### The number that decides everything

Measured on the owner's own 11–17 September tape, 39 prospective setups
carrying a stored quote:

| | |
|---|---|
| median spread | $0.020 |
| median planned risk per share | $0.128 |
| **median spread ÷ risk** | **0.25** |
| setups where the spread exceeded the **entire** stop | 5 of 39 |

A round trip pays roughly one full spread, so the spread costs `1/k` of R
where `k` is how many times the stop exceeds the spread. The strategy's own
best theoretical case is **+0.25 R per trade** (50% wins on the half-at-1R
ladder):

| k | spread at most | costs | left of the +0.25 R | setups surviving |
|---:|---:|---:|---:|---|
| 4 | 25% of risk | 0.250 R | **0.000 R** | 19 of 39 |
| 6 | 17% | 0.167 R | +0.083 R | 17 of 39 |
| **8** | **12%** | **0.125 R** | **+0.125 R** | 16 of 39 |
| 10 | 10% | 0.100 R | +0.150 R | 12 of 39 |

I had proposed `k = 4` in the first draft of the plan. It costs exactly the
entire theoretical edge. Corrected to **8**. Commissions take a further
0.05–0.07 R, so `k = 8` keeps roughly +0.06 R in the best case.

### The module structure

`src/momentum_platform/microflow/`, one module per responsibility:

| module | owns | status |
|---|---|---|
| `config.py` | every parameter once, each with `origin` and `evidence_status` | built |
| `bars.py` | fold 10s to minutes, coverage, sync assertion, forming minute | built |
| `spread.py` | the `k` gate, three states, fails closed on a missing quote | built |
| `measure.py` | dip shapes, survival-by-k, GO/NO-GO | built |
| `context.py` | Layer A, the 1-minute context | phase 1 |
| `timing.py` | Layer B, the 10-second timing | phase 1 |
| `risk.py` | position caps | phase 2 |

Three config values are declared **UNKNOWN** because the corpus gives no
number: the dip retrace cap, the bailout timer, and one other. A test fails
if any parameter has no provenance at all.

The gate, in full:

```python
def gate(trigger, stop, bid, ask, cfg) -> Verdict:
    if trigger is None or stop is None:
        return Verdict(State.UNKNOWN, "No trigger or stop ...")
    rps = trigger - stop
    if rps <= 0:
        return Verdict(State.FAIL, ...)
    if bid is None or ask is None:
        return Verdict(State.UNKNOWN,
            "No quote — the spread could not be established, so the gate "
            "fails closed rather than assuming zero.")
    if ask < bid:
        return Verdict(State.UNKNOWN, "Crossed quote ...")
    spread = ask - bid
    ratio = spread / rps
    if rps >= cfg.spread_k * spread:
        return Verdict(State.PASS, ..., kills=False)
    return Verdict(State.FAIL, ...)
```

### The design, in the owner's own words

**1-minute is the base. 10-second confirms inside a forming momentum
candle.** Not a 10-second strategy.

- **Layer A, 1-minute, closed bars.** Impulse over 1–6 candles at or near
  the day's high; volume above its recent average; above VWAP; above the
  9 EMA; MACD positive and above signal. Arms HUNTING. Never enters.
- **Layer B, 10-second, closed candles inside the forming minute.** We are
  in a 1-minute candle trading above its open; 1–3 ten-second candles fail
  to make a new high; volume falls during that dip; price holds VWAP and the
  9 EMA through it; the dip is shallow; a candle then takes out the previous
  candle's high. That is the entry. Stop = the dip low, minus a tick. Then
  the spread gate.

Excluded from v1: the 5-minute trend confirmation. Register split measured
this week: **21 mentions in teaching material, 0 in 290 live-stream
transcripts, 0 in 69 daily recaps.** Taught, never spoken while deciding.

### A bug a test caught, disclosed because it matters

My first dip detector treated a candle exceeding its neighbour as a "push".
Sideways chop under an old high then produced a string of one-candle
"pullbacks" a few ticks deep. Those fake dips would have dragged the measured
stop distribution downward and risked a **false NO-GO** — killing the project
for the wrong reason. The push must now set a new high of the run.

### The kill rule, written before the data

Phase 2 is abandoned if any of these holds at read-out:

1. the 10-second cohort does not beat a **symmetric** random control on the
   same instants, on **realised** risk, with a CI excluding zero;
2. median realised risk exceeds 1.5× planned risk (the stop does not hold);
3. fewer than 30 takeable setups in the sample;
4. the replay check fails on any session.

**Reviewer question 5.** Is the Phase-0 measurement the right one? It
measures dip depth against the spread on shape alone, without the Layer A
context gates, which I argue is an optimistic upper bound and therefore
conservative for a NO-GO. Is that reasoning sound, or does omitting the
context gates bias it in a way I have not seen?

## 8. Decisions the owner has made

| decision | value |
|---|---|
| spread gate `k` | 8 |
| phase 2 shape | paper orders from day one; week 1 read as **execution quality only**, not profit |
| order sender | the 10-second detector only; the 1-minute detector stays log-only as the paired control |
| concurrent positions | allowed, capped at **3 positions and 3 R** of open risk, no margin borrowing in v1 |
| a NO-GO at phase 0 | accepted as a legitimate outcome |

On concurrent positions: the PDT rule is **not** the constraint. It was
eliminated in spring 2026 and margin accounts now need $2,000; the account
holds $2,143. The real constraints are that cash binds before risk does
($20 of risk on a 3-cent stop is 666 shares, $2,331 of stock at $3.50) and
that every name on this desk is a low-float momentum runner in the same
session, so three positions is three times one bet.

## 9. Known weaknesses, stated up front

1. **Sample.** Five sessions. Nineteen reconstructed trades. Nothing here is
   statistically meaningful and the pack says so throughout.
2. **Paper.** No real fill has ever occurred. Paper fills are optimistic.
3. **The halts table has been empty for five sessions.** Either none
   occurred or the live path is not recording them. Unexplained, and at
   10-second resolution a halt is the difference between a stop and a gap.
4. **One universe, one regime**, mid-September 2026.
5. **The owner wants this to work.** He has said so directly. That is the
   main bias risk in the project and I am the only counterweight.
6. **I introduced the defect in §3** and then produced the analysis that
   evaluates it. An independent check of §4's arithmetic is welcome.
7. The 5-minute check and the third-pullback rule are **inconsistent between
   two files** in the repo (`MICRO-PULLBACK-SPEC.md` says skip the third
   pullback; `PARAMETERS.md` shows him taking it at reduced size). Not yet
   resolved.

## 10. Questions for the reviewer, consolidated

1. Is "flag, not kill" right for a mandatory gate whose data source is
   missing, or should the session halt?
2. Is there any defensible reading of the 19 reconstructed trades other than
   noise?
3. **Is the 10-second pivot a real insight or a rationalisation?** What
   would distinguish the two before weeks are spent?
4. Given the eleven-year result, is any further work on this strategy family
   justified at all?
5. Is the Phase-0 spread measurement the right gate, and is measuring shape
   without the context gates genuinely conservative?
6. Is `k = 8` defensible, or does the +0.25 R baseline it rests on already
   assume too much (it assumes a 50% win rate this strategy has never shown;
   the eleven-year figure is 20.6%)?
7. What are we not measuring that would change the answer?

---

*Paper only. No order has ever been placed by this system. The strategy
being tested was measured negative over 894 sessions and again over eleven
years by studies in this same repository; nothing in this pack claims
otherwise.*
