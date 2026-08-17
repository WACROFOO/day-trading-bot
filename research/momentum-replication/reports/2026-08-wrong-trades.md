# The wrong trades — measured, classified, costed

```
LEDGER · research/trade-log/propositions.csv · 10 propositions · 5 acted on
MEASURED 2026-08-17 · walk-forward from yahoo 1-minute bars via tape.py.
Two provenance classes, never mixed:
  (a) re-measured today — IPST, TRUG (today's session, bars still available)
  (b) measured in-session — MSGY, WETO, ONFO, HHS, FGI, WYHG, TDIC; each
      figure was fetched and timestamped in the transcript at the time.
      Yahoo does not serve 1-minute history beyond the recent window, so
      these cannot be re-derived now. They are not re-verifiable here.
! COUNTERFACTUALS FILL AT THE LEVEL. A simulated stop at 7.30 fills when
  the bar's low is 7.30. A real one may not. Read every counterfactual as
  an upper bound on how bad, and a lower bound on how good.
```

## What was considered

10 propositions across 5 sessions (08-11 → 08-17), from 4 sources: my chat
verdicts (5), the `./now` board (3), the Pine strategy (2). **5 were acted
on** — a broker statement would show only those 5, and would omit both of
the week's most instructive rows.

---

## Case 1 — IPST, 2026-08-17: the bailout did not cut the winner

This is the case that prompted the review, and the tape contradicts the
screenshot.

**What the tool did.** Trigger 7.46, stop 7.30, target 7.78 (2R), 1249
shares at $200 risk — reconstructed from the share count, which pins
risk/share at exactly $0.1602. Filled 10:51. BAILOUT fired 10:53 on the
`close < entry within 2 bars` branch (close 7.44 vs entry 7.46), exiting at
roughly **−0.13R (−$25)**.

**What it looked like.** Six minutes later IPST printed 9.66 — a +14R move
from the entry. The obvious reading: the bailout amputated a monster.

**What the tape says.** Walk-forward from 10:51, measured today:

```
10:53  h 7.53  l 7.37  c 7.44   ← BAILOUT (close below entry)
10:54  h 7.50  l 7.35
10:55  h 7.55  l 7.30          ← ✗ STOP 7.30 TOUCHED
10:56  h 7.51  l 7.36
10:57  h 7.75  l 7.44
10:58  h 7.90  l 7.66          ← target 7.78 hit
10:59  h 9.66  l 7.86
```

**The structural stop was touched three minutes BEFORE the target.** Holding
the plan exits at **−1.00R (−$200)**, not +2R. The bailout's −0.13R was the
better of the two available outcomes.

| exit path | result | measured |
|---|---|---|
| BAILOUT (what happened) | **−0.13R** | close 7.44 vs entry 7.46 |
| hold the bracket | **−1.00R** | low 7.30 = stop, 10:55 |
| the fantasy (+14R to 9.66) | never reachable | stop came first |

The bailout **saved ~0.87R** here. `error_class = NONE`.

**The knife-edge, stated rather than hidden:** the 10:55 low is 7.30 and the
stop is 7.30. Whether a resting order fills on an exact touch depends on
size trading at that print — unknowable from OHLC. If it did not fill, the
hold path becomes +2R and the conclusion inverts. **This single case cannot
settle the bailout rule in either direction**, which is precisely why it is
one row in a ledger rather than a reason to change a parameter.

### Verdict on the bailout rule (0.5R MFE in 2 bars / close-below-entry)

`LOCAL_ADDITION`, `evidence_status: UNTESTED`. Measured instances: **1**.
That is one order of magnitude below any threshold decision. **No change.**
The one instance we have argues for keeping it, contrary to the visual
impression it created. Revisit at n ≥ 10; the ledger now accumulates them
automatically.

---

## Case 2 — TRUG, 2026-08-17: the strategy took nothing

Trigger 1.7801, stop 1.7300, 0.4R of room to the 1.82 peak.

```
10:24  h 1.78    10:26  h 1.78
10:25  h 1.76    10:27  h 1.78     ← four bars, never 1.7801
10:28  o 1.74  l 1.56              ← the breakdown
```

**The trigger never filled.** Four consecutive highs printed exactly 1.78;
the order needed 1.7801. Had it filled, the counterfactual is **−1.00R**
(10:28 low 1.56, well through the 1.73 stop).

Two separate rows, two separate errors:

- **`20260817-TRUG-01` — `PRESENTATION`.** The 0.4R room warning existed and
  was rendered in silver next to the share count, under a bright yellow
  `TRIGGER SET` banner. Information present, invisible. **Fixed in V4.8**:
  room < 1R now prefixes the verdict in red and turns the banner orange.
  Verified against these numbers — 0.4R would have fired the warning.
- **`20260817-TRUG-02` — `ANTICIPATION`.** The operator entered near 1.71.
  No proposition existed at that price; the trigger was 7 cents higher.
  Acting before the trigger is a distinct failure from the trigger being
  wrong, and merging the two would have blamed a rule that never fired.
  New taxonomy class, added because this case did not fit the existing ones.

---

## Case 3 — MSGY, 2026-08-11: the only rule misfire in the set

Rejected at 4.39 on gate 5 (reverse split effective today). Every other gate
passed: price, float 0.56M, VWAP, EMA9, MACD positive and above signal,
6.6M volume, 272× RVOL. It printed **5.43** (+24%).

`error_class = SELECTION`. The gate's premise — *"the gap IS the split"* —
requires the reported previous close to be unadjusted. MSGY's 2.3144 was
already 1-for-8 adjusted, so the move was real and the gate fired without
its precondition. FILTERS.md corrected the same day with the two-line test.

**This is the only genuine rule defect among ten propositions.**

---

## Case 4 — WETO, 2026-08-14: variance, and the warning was right

STAR at 09:20, 4/4 technical, float 0.86M. The 09:30 bar traded **29.4M
shares — 34× the entire float — in one minute**, and the stock lost the
10.00 level immediately, ending 36% off its high.

`error_class = VARIANCE`. The board printed *"19.1M shares already traded
pre-market — crowded, the move may be over before the bell"*. The warning
was correct, visible, and specific. A correct warning followed by a bad
outcome is not a defect; it is the strategy's distribution.

---

## Case 5 — ONFO, 2026-08-14: the tool was right, the narration was not

The board ranked ONFO **#1, crowned `◄ STRONGEST`**, and my message named the
condition: *"rien à prendre sauf reprise nette d'ONFO au-dessus de 4.00"*.
It reclaimed 4.00 at 10:56 and printed 5.57 by 11:03 (+39%). The operator
took it and won.

`error_class = NARRATION`. Between 10:31 and 10:43 my messages discussed
WETO — the name that had *already* run — while the ranked #1 was setting up.
The book's guardrail #15 names this exactly: a former runner is a
**distraction** from the obvious name. The tool obeyed the rule; the
commentary did not.

**Consequence, since fixed:** WATCH rows now carry their revival level
(`below EMA9 (flips >5.00)`), so a stale snapshot verdict cannot silently
outlive its own condition.

---

## The pattern across all ten

| error class | n | cases |
|---|---|---|
| `NONE` — correct call, correct outcome | 5 | IPST, HHS, FGI, WYHG, TDIC |
| `SELECTION` — rule misfired | **1** | MSGY |
| `PRESENTATION` — visible ≠ seen | 1 | TRUG-01 |
| `NARRATION` — tool right, summary wrong | 1 | ONFO |
| `ANTICIPATION` — acted before the trigger | 1 | TRUG-02 |
| `VARIANCE` — correct rule, bad draw | 1 | WETO |

**One rule defect in ten propositions. Three failures in the interface
between a correct computation and a human decision.** That is the same
finding the parameter audit produced in a different domain — 21 corrections,
zero arithmetic errors — and it repeats here at a 3:1 ratio.

Cross-cut on the prompt's three questions:

- **selection vs execution:** 1 selection error (MSGY). Zero execution errors
  by the tool; one by the operator (ANTICIPATION).
- **defect vs variance:** 1 defect, 1 variance, and 5 correct calls. The
  remaining 3 are neither — they are transmission failures.
- **invisible vs absent:** every failing case had the information *present*.
  **No `DATA` class instance occurred.** The problem this week was never
  missing data.

---

## What changed, and what did not

| change | origin | evidence | status |
|---|---|---|---|
| Gate 5 requires its arithmetic test | SOURCE | MSGY measured | shipped 08-11 |
| Room < 1R → red verdict, orange banner | MEASURED (TRUG) | n=1 presentation defect | shipped V4.8 |
| WATCH rows carry the flip level | MEASURED (ONFO) | n=1 | shipped 08-14 |
| `ANTICIPATION` added to the taxonomy | the case did not fit | n=1 | shipped |
| **Bailout rule** | — | **n=1, ambiguous** | **UNCHANGED** |
| **`requireRRtoPeak` default** | — | **n=1** | **UNCHANGED, off** |

Two parameters were deliberately left alone despite having a fresh, vivid
case attached to each. One trade is not a measurement, and the ledger exists
so the next revision of this document can say a number instead of a story.

---

## Limitations

- **n=10.** No threshold in this repo may be tuned on it. The report states
  costs; it does not authorise changes.
- **Seven of ten rows are in-session measurements** that cannot be
  re-derived — Yahoo's 1-minute history has expired for them. Future rows
  must be measured on the day (`tradelog.py measure`) or they inherit this
  weakness.
- **Counterfactuals assume fills at the level**, ignore spread, and ignore
  halt reopenings. On this class of stock that is optimistic in both
  directions.
- **No `DATA`-class case appeared.** Absence of evidence: the taxonomy slot
  stays open rather than being deleted.
- Paper account throughout. Nothing here establishes profitability — the
  894-session replication of this strategy class was negative expectancy,
  and ten propositions do not revisit that.
