---
name: trading-report-design
description: Design language for trading analysis reports, scanner output and strategy documents. Use whenever producing a report, card, table or explainer about a trade setup, a candidate stock, a backtest, or a strategy rule — including playbooks, pullback explanations, session reviews and defect write-ups. Encodes provenance-first layout, fail-closed vocabulary, declared-origin rules and the visual devices that make a wrong number visible instead of plausible.
---

# Trading report design

A design system for research output where **being wrong quietly is the
main hazard**. Every rule below exists because a specific failure happened
without it. Keep the incident attached to the rule — it is what stops the
rule being negotiated away later.

## The one principle

**Provenance before numbers.** A figure whose source and freshness are
unstated is worse than a missing figure, because the reader will use it.

The canonical failure: a stock screener served 15-minute delayed data for
months. Between 09:30 and 09:45 every "today" field silently held the
previous session. `FCUV` was reported at `$1.88 / +5% / 18,254 shares` and
rejected on four filters while actually trading `$11.97` on 33M shares.
Nothing looked broken. **Delayed data is plausible data.**

So: the first block of any report states what the data *is*, before it
states what the data *says*.

---

## Document skeleton

Order is not cosmetic — it is a priority claim.

1. **Provenance banner** — source, entitlement, measured lag, session, timestamp
2. **What was considered** — the universe size, before filtering
3. **What survived, and what did not, with reasons** — never a bare survivor list
4. **Per-item detail** — only for survivors, or for anything the reader asked about
5. **What this analysis could not check** — always present, never omitted
6. **Verdict** — last, never first

Rule: a reader who stops after block 1 should be correctly informed rather
than confidently misinformed.

> **Scope note for this repo:** the skeleton above governs *standalone
> documents* — reports, scanner output, playbooks, write-ups. Conversational
> answers keep CLAUDE.md's verdict-first rule: the user asked for the answer
> in the first line, and a chat reply's caveats sit one screen away, not
> buried. The two rules serve the same goal — the reader acts on complete
> information — in two different media.

## The visual devices

### 1. Provenance banner

Leads every report. Colour-code by trust, not by sentiment.

```
FEED · delayed_streaming_900 · 15m behind · clock OPEN / data pre_market · checked 09:44 ET
! SESSION DIVERGENCE — regular-session fields are the PREVIOUS session's.
→ Treat this scan as YESTERDAY's board. Do not act on it.
```

When a limitation is later remediated, say so explicitly rather than
deleting the warning:

```
✓ REMEDIATED — live quotes from yfinance (6 rows). The screener supplied only WHICH NAMES.
```

### 2. The funnel line

State the universe before the filter. A survivor count without a
denominator hides how aggressive the filter is.

```
57 movers on the screen · 2 pass the five pillars · run --wide to see what was rejected and why
```

### 3. Rejects shown, never hidden

Every filtered-out item appears with the reason it died. A `FAILS` column,
not a silent absence.

```
│ # │ TICKER │ Chg%  │ PRICE  │ RVOL  │ FLOAT  │   FAILS    │
│ 1 │ SCKT   │ 446.9 │  2.11  │ 10.0x │  5.4M  │ passes all │
│ 3 │ AUUD   │  53.9 │  1.26✗ │ 11.2x │  4.8M  │ price      │
│ 5 │ VREX   │  48.1 │ 18.39  │  7.4x │ 41.4M✗ │ float      │
```

`✗` marks the offending cell so the eye finds the cause without reading
the reason column. This is the audit trail: **the filter is never silent.**

### 4. Reason lines

One line per item, plain language, the actual cause:

```
WHY
  NO    SCKT   back side of the move — 25% off the high, sitting at 0% of the day's range
  WATCH DKI    float too big
```

The reason must match the logic that fired. A card once displayed
`FLOAT 3.38M` and `float too big` simultaneously — it had actually failed
on *single-source verification*, not size. **A wrong reason is a defect,
not a wording choice.**

### 5. Inline legends

Any derived number carries its interpretation where it is displayed, not
in a footnote:

```
in RANGE: 100% = at the day's high (front side) · 0% = at the low (back side, move is over)
PM RVOL = pre-market volume vs this stock's average FULL day. Over 1.0x is a real event.
```

### 6. Numbered analysis layers

When analysis spans timeframes or stages, number them and state each
one's *job* and what it may not decide:

```
① DAILY   where are the walls? · daily bars, 3-month lookback
② 5-MIN   is the trend intact? · no MACD here (1-min only)
③ 1-MIN   do I take this? · last CLOSED bar 10:10 ET
```

This prevents the most common analytical error: reading a decision off a
context timeframe.

### 7. Gate lamps

Binary checks get a lamp and the sub-conditions that produced it:

```
✓ ① MACD 12/26/9  above signal · above zero · expanding
✗ ② VOLUME  HIGH-VOLUME RED 2.6x avg, 0 bar(s) ago
```

Never collapse several conditions into one lamp without listing them. A
reader must be able to see *which* sub-condition failed.

### 8. Values carry source and units

```
FLOAT  3.38M  YF_ONLY        ← source tag
RVOL   5686.9x  TV           ← and where it came from
       vs 90-day avg: 39.7x — unusual vs 10d, ordinary vs 90d
```

When two sources disagree, **show both and block the conclusion.** Do not
average, do not pick silently.

### 9. The limitations footer

Every report ends by stating what it did not verify:

```
NO TICKET ISSUED. This scanner does not validate spread, executable bid/ask,
fees, halt state, borrow, or manual chart/Level-2 checks.
Journal the observation only; construct any order independently after verification.
```

---

## Vocabulary rules

**Six states, never two.** Anything not positively established fails closed.

`PASS` · `FAIL` · `UNKNOWN` · `STALE` · `NOT_APPLICABLE` · `MANUAL_CONFIRMATION_REQUIRED`

**Never key logic on a display string.** This failed four separate times in
one codebase — renaming a label silently disabled the logic comparing
against it, and no test caught any of them because the tests read the same
labels. Compare against numbers or enumerated constants; if a label must
be compared, assert elsewhere that it is still producible.

**Non-actionable language in research output.** Use `MANUAL REVIEW`,
`WATCH`, `WAIT`, `NO`, `LOG`. Never `BUY`, `TAKE`, `ARMED`, `QUALIFIED`.
Research output that reads like an instruction will be followed like one.

---

## Declaring where a rule came from

Every threshold carries its origin and evidence status:

```
{ "id": "RISK-LOCAL-002", "value": 1.5,
  "origin": "LOCAL_ADDITION",              # or SOURCE
  "evidence_status": "REASONED_NOT_MEASURED",
  "rationale": "...why, including what it costs..." }
```

**`LOCAL_ADDITION` rules must justify themselves in their own text.** One
undeclared local filter — an average-volume floor — excluded the largest
gapper of a session (`+221%` on 25.8M shares against a 6,644-share average
day) *because the stock was normally dormant*, which was the exact case
the strategy hunted. It had been flagged `UNTESTED` and left in.

When a rule is withdrawn, **record the withdrawal in place** rather than
deleting the line. The reasoning is the asset.

---

## Evidence discipline

**Measured, with a timestamp.** Not "the feed seems delayed" but:

```
Measured 2026-08-10 09:40:35 ET:
    SCKT   screener 0.39 / -1.0%     yfinance 2.54 / +557.9%
```

**Before/after tables** for any change to behaviour:

| Rule | Before | Now |
|---|---|---|
| Float cap | 10M hard | 20M (10M = flagged sweet spot) |
| Pre-market volume | floor 25k | **ceiling 1M** — crowding bias |

**Record the mistakes you made while fixing it.** A false alarm raised on
healthy data is worse than no alarm — it trains the reader to ignore the
real one. Write that down when it happens.

---

## Anti-patterns

| Don't | Because |
|---|---|
| Verdict at the top *(documents — see scope note)* | The reader stops there and skips the caveats |
| Survivor list with no denominator | Hides how much was thrown away |
| Silent filtering | The missing name is the one they will ask about |
| A number with no source | It will be trusted exactly as much as a sourced one |
| Averaging disagreeing sources | Manufactures a value neither source supports |
| Green/red by sentiment | Colour must encode *trust*, not *direction* |
| Deleting a warning once fixed | Say `✓ REMEDIATED` instead — the history is the value |
| "Approximately", "should be fine" | State the measurement or state that you did not measure |

---

## Applying this to prose documents

The same discipline in a playbook or explainer:

- **Separate reasoning types into separate documents, cross-linked.** Trading
  reasoning (*is this a good trade?*) and tooling reasoning (*is this number
  real?*) have different standards of proof. Merged, a tooling limitation
  reads as a trading rule.
- **State the scope exclusion up front** — what this document deliberately
  does not cover, and where that lives instead.
- **Tables over paragraphs** for anything with more than two comparable items.
- **Quote the source** when a threshold comes from one, verbatim, with the
  reference.
- **Keep a "what is not a filter" section.** The most expensive errors are
  things that read like rules and are not: a *realised* ratio mistaken for
  an entry threshold, a *dial* mistaken for a floor, a *cold-market setting*
  mistaken for a constant.
