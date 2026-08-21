# V12 — disposition of the Codex manager audit

| Artifact | SHA-256 |
|---|---|
| V11 baseline as audited | `70c4db21e14aff9092889eff59e8d1aa25e28555ebe7e2133db01a6d3d0bba31` |
| Codex candidate (V11.1) | `fc7d3e78fc0618cb1972d23b5c74d6b243a1dbfa9d306e3074e22bed0ec1419a` |
| V12 (compiled by operator) | `7e89210aec0b5ee00c7267ae337bfc40f9eab87e5ee94170d9c995b3ab19cfba` |
| **V12.1 (this file)** | `a2fffe5db395a482662f1dfa95c47834213b089673893ee727f2c8897266eb1a` |

The audited baseline hash resolves to my commit `beaaa02` **with the trailing
newline stripped** — verified by reproducing the hash. So Codex audited the
post-CE10156 V11, and its line references map to my file.

## Release status

`LIFECYCLE TESTS FAILED`

**C1 is now partially satisfied: V12 compiled and ran.** Operator screenshot
shows `ROSS FP V12` live on USDE, 1-minute, dashboard rendering, verdict
`REJECTED / NO`, plan and ladder populated. That clears `COMPILE FAILED`.

It cannot advance further: A01–A38 have not been run and section 8 has no
data. `LIFECYCLE TESTS FAILED` is the honest status — the lifecycle tests
have not passed because they have not been run.

Still not claimed anywhere: `accurate`, `validated`, `production-ready`,
`profitable`.

### V12.1 display revision (operator report on the running build)

Six defects, all display-layer, all reported from the live V12 chart:

| # | Reported | Change |
|---|---|---|
| 1 | grid eats the chart | `dashSize` defaults `tiny`; new `dashCompact` retires the standing LIMITS caveat row, which reappears whenever the ambiguity count is non-zero |
| 2 | verdict far too long | one verb + short reason; live/playbook/room provenance clauses demoted behind `dashFull` |
| 3 | markers unusable at zoom, far above/below candles | `location.abovebar/belowbar` offset by a fraction of the **visible price range**, so the gap grows as you zoom out. All twelve now `location.absolute` pinned to a price, with an ATR-fraction clearance — ATR is in price units, so it holds at any zoom |
| 4 | want dollar P&L on the chart | live label on the last bar of an open position: net $, %, share count, green/red. One label moved per bar, not one per bar — `max_labels_count` is finite |
| 5 | SIZE "63% of $2000" meaningless | SIZE is now shares + dollars only; modeled risk, budget and binding constraint moved to `dashFull` |
| 6 | PLAN rungs unnamed | `T1 7.20 (88) · T2 7.26 (44) · T3 7.31 (44)` |

Item 3 is the second time this bug was fixed. The V12 fix corrected the
`BOUGHT`/`SOLD` **labels** (`yloc`) but left the twelve `plotshape` **markers**
on bar-relative locations. Same defect class, different API, and I did not
sweep for the second one — the same failure that produced C2.

## Method

The audit says *"Do not merge the Codex candidate blindly."* I reproduced its
two load-bearing structural claims against V11 first, then adopted the
candidate as the base once it was clear it was the more advanced artifact —
the same call made earlier for V9.12 over V10.

**C2 reproduced.** V11 line 2149:

```
bool fastOK = fastCoreOK and sessionGate and venueGate and entryTimeOK
```

No `confluenceGate`, no `pullbackIndexGate`, **no `v11RiskGovernorOK`** — with
`fastLane` and `uptrendLane` both `input.bool(true, …)`. A §8-locked account
could still place a lane order. This is my defect, and the same failure mode as
the §8 walkaway I fixed last turn: a rule added in one place without auditing
every path that can reach an order.

**C10 reproduced.** V11 line 1489 `pushDollarVolume := close * volume`, and
line 1054 `candidateAvgVolume * math.max(close, candidateStartClose)` — the
larger endpoint, biased upward on rising bars exactly as described.

I initially doubted the candidate's own C2 fix, because `fastOK` looked
unchanged. That was wrong: it gates inside `fastCoreOK` and at three sites
(2262, 2336, 2652) plus the dashboard.

## Critical findings

| ID | Disposition | Evidence |
|---|---|---|
| C1 no compile evidence | **DEFERRED** | No TradingView here. Status stays `COMPILE FAILED`; header says so. Handoff below. |
| C2 lanes bypass gates | **ACCEPTED** | Reproduced in V11. Candidate: lanes default `false`, `[EXPERIMENTAL]`; `confluenceGate and pullbackIndexGate and v11RiskGovernorOK` enforced at 2262 / 2336 / 2652 and mirrored in the verdict text (2160-2162). |
| C3 governor ignored open loss | **ACCEPTED** | Candidate evaluates drawdown and daily limits continuously incl. open P&L and routes a live lock through the single flatten request. Untested — see A27-A30. |
| C4 var/varip transaction split | **ACCEPTED** | Candidate makes cursor-committed facts intrabar-persistent and guards the new-day reset with `barstate.isnew`. Untested — needs tick replay (A31/A32). |
| C5 UNKNOWN float scored | **ACCEPTED** | Candidate requires verified provenance + ticker binding; unknown adds no point. |
| C6 "third trade" ≠ "third pullback" | **ACCEPTED** | Proxy removed; the ordinal gate decides. Coherent with `maxPullbackIndex`. |
| C7 sizing omitted fixed costs | **ACCEPTED** | Candidate reserves planned order costs before dividing by per-share risk and caps cash at `min(maxPositionValue, equityBase)`. Per-quantity proof table is A17 and needs a chart. |
| C8 unlimited stop-market chase | **ACCEPTED** | Capped stop-limit is the default with an explicit order-model input. |
| C9 same-bar double count / result leak | **ACCEPTED** | Candidate dedupes ambiguity by entry identity and reconstructs unseen same-bar round trips. |
| C10 dollar volume not notional | **ACCEPTED** | Candidate uses `volume * hlc3` per bar throughout. A36 hand-reconciliation still needs a chart. |

## High-priority findings

| ID | Disposition | Evidence |
|---|---|---|
| H1 RVOL is a chart proxy | **ACCEPTED** | Renamed `TV pace EWMA`; warm-up requires N observations; display-only until a matched dataset exists. I have no MSS data here, so no calibration is attempted or claimed. |
| H2 confluence measured at close | **ACCEPTED** | Candidate measures at the dip low and requires recovery on/above the level. |
| H3 ordinal reset on marginal HOD | **ACCEPTED** | Marginal HOD updates the high without resetting the ordinal. Still a heuristic — the labelled-replay test is not run. |
| H4 halt band false precision | **ACCEPTED** | Heuristic veto defaults OFF and is labelled. |
| H5 session default vs own evidence | **ACCEPTED** | Evidence default ON. |
| H6 narrative exits on by default | **ACCEPTED** | Both default OFF. These were mine, added in V11 with mention-counts as justification, which is not evidence of incremental performance. |
| H7 "CONFIRMED data" while reading the live bar | **ACCEPTED** | Label made truthful. |
| H8 dashboard hid the real ladder | **ACCEPTED** | Exact whole-share rungs, binding size constraint and cost-inclusive risk shown. |

## Added by V12, beyond the audit

**Position markers did not track price.** Operator-reported and not in the
Codex candidate. `BOUGHT`/`SOLD` used `yloc.belowbar` / `yloc.abovebar`, which
ignore the y value and hang the label off the candle by a fixed screen offset,
while the dotted result line beside them is anchored to the real fill prices.
Zooming the price scale slid the markers off the line, so the two disagreed
about where the trade happened. Both are now `yloc=yloc.price` at
`tradeEntryPrice` / `resExitPx`.

## What is blocked, and why

| Required | Blocker |
|---|---|
| C1 compile proof, Properties, input defaults | No TradingView in this environment |
| A01-A38 acceptance matrix | Every case needs a running chart |
| §7 telemetry export | Produced by a run |
| §8 development + holdout reports | **No market-data access at all** — every feed host is blocked by egress policy |
| §9 scoring | Gated on compilation |

Any number I produced for those would be fabricated. They are handoffs.

## Handoff — what to run

1. Paste this exact file. If the editor alters it, the compiled hash is the
   release hash, not `7e89210aec0b5ee00c7267ae337bfc40f9eab87e5ee94170d9c995b3ab19cfba`.
2. Report compile errors verbatim with line numbers. Each one becomes a
   `scripts/pine_check.py` rule, as CE10156 did.
3. Then A01-A38, then the development/holdout split.

## Disagreement with the Codex candidate

None material. Where the candidate and V11 differ, the candidate is right on
every point I checked. I have **not** independently verified C3, C4, C7 or C9
behaviourally — they need a running chart — so those are adopted on the
candidate's reasoning, not on my own reproduction, and are marked accordingly
above rather than being called fixed.
