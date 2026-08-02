# What has already been found and corrected

Sixteen defects, recorded so the same ground is not covered twice. Each cites
the document or video timestamp it violated. All are fixed in the current code.

Also recorded: four conclusions that were reported and later withdrawn, because
they were artifacts of the defects below rather than properties of the strategy.

---

## Data preparation

**1. Reverse-split contamination via window stitching.**
Yahoo serves 1-minute data in 7-day windows and adjusts each response
independently. A day's previous close and its open could come from different
adjustment bases, and the ratio between them was recorded as a gap. This
produced FFAI +10,555%, GNPX +2,058%, DFNS +12,555%. The anomalies landed
exactly on window boundaries (Jul 15, 22, 29), which was the tell. Every extreme
"gap" was a reverse split — VIVK 1:15, XPON 1:12, CIIT 1:10, TRIB 1:25.

*Fix:* gaps measured open-vs-previous-close inside a single daily response;
symbol-days within 3 trading days of a split dropped; +200% sanity cap.
`pipeline/fetch_daily.py`.

**2. Impossible fills.** Entry price could exceed the bar's own high.
*Fix:* `entry = min(trigger + slippage, bar high)`.

---

## Entry and exit rules

**3. Target set to `entry + 2R`.**
Five videos state the first target is a retest of the high of day, with 2:1 as a
*filter* on that target — `BUCPPCXOHbs` [47:20], `DP4ayEWhmvM` [1:31],
`iIC62xnblLc` [33:39], `js25lIZMUSY` [42:01], `hLn6LrlXgAE` [20:23].
*Effect:* selling half at exactly 2R then moving the stop to breakeven makes
every winner worth exactly +1.00R by construction.

**4. "First candle to make a new low" fired on any lower-low red bar.**
The corpus qualifies it as a new low *below the flag* — `Xdw5azEqs6o` — i.e.
below the pullback structure, which is the stop.
*Effect:* median hold was 2 minutes; it closed 5 of 14 trades inside 4 minutes.

**5. `stop_min_distance >= spread width` not implemented** (`PARAMETERS.md:161`).
*Effect:* allowed a 2-cent stop on a $15 stock.

**6. 1-bar pullbacks accepted.** `PLAYBOOK.md:99` states 2–3 candles.

**7. A wide stop was treated as a skip.** `PLAYBOOK.md:166` states "cut your
size **or** skip the trade", and the sizing formula already cuts size when the
stop is wider.
*Effect:* rejected every strong mover, leaving the engine trading whichever
watchlist name was moving least.

---

## Structure detection

**8. The leg was measured from one or two "impulse bars"**, so the retracement
rule ran against a meaningless leg.
*Fix:* legs run from a swing low to the highest high since, and chain — when a
pullback resolves upward the next leg starts from the pullback low.

**9. Confluence used `abs(price − level)`**, so a dip that had broken support
and was bouncing underneath counted as being at it. Measured: the pullback low
was below the 9 EMA in 87% of setups, median −1.23%.
*Fix:* a level counts only if the dip reached it and held it.

**10. The trigger was tested after leg extension.**
On a strong mover the trigger bar usually takes out the leg high as well as the
previous bar's high, so it was filed as "leg continues" and the accumulated
pullback discarded.
*Effect:* the faster a stock ran, the fewer signals it produced. VEEE ran $12.20
→ $29.19 on 07-13 and yielded 5 setups all morning, the first at 10:37.
*Fix:* the trigger is tested first. `engine/sim.py::PullbackTracker.update`.

**11. Losing VWAP wiped all swing structure.** This was an invention — VWAP is
an entry gate in the source, enforced separately. These symbols sit below VWAP
57–68% of the session, so structure was destroyed continuously.

**12. Structure tested against the pullback's wick low.**
*Fix:* bodies define structure; the wick is what the stop sits under. Lifted the
retracement rule's pass rate from 24% to 36%.

**13. Confluence tolerance floored at a hardcoded 1 cent.**
`PARAMETERS.md:127` floors it at spread width. Demanding the dip stop within a
penny of two independent levels was gating out ~90% of setups on its own.
*Effect of fixing:* confluence pass rate 9% → 60%. This was the single largest
correction.

Also: "front side" was a flat 2% of the high of day, which excludes anything
that has run hard; now expressed in leg-heights. The 50% retracement rule was
applied to every pullback, but `BUCPPCXOHbs` [50:34] states it about the *first*
pullback after the catalyst; now scoped accordingly.

---

## Exit accounting

**14. The forced close at the trading-window cutoff read the last bar of the
session.** A position still open at `HARD_STOP` (11:30) was flattened at
`sorted(bars)[-1]` — the **15:59** bar — and stamped `11:29`. A four-and-a-half
hour look-ahead on the exit price, in a harness whose whole contract is
forward-only.

It was load-bearing, not marginal. EHGO 2026-07-13 sat flat at the cutoff and
booked −6.38R against the closing price; ADVB 2026-07-22, the largest winner
anywhere in this project, was the same path in the favourable direction. The
17-day total went from +$633.30 to **+$357.54** on the fix, and the
previously reported *"week of 07-20: +8.33%"* is really +5.58%.
*Found by:* `reports/2026-07-july-calibration.md`, while explaining a
−6.38R loss on a position sized to risk 1R.

**15. `calibrate.py` re-derived the entry gate instead of calling it.** The
measurement tool defined "would the engine trade this" as "every
`GATE_CONDITION` holds", silently dropping the 2:1 and spread tests `run_day`
applies on top. It reported 14 tradeable pairs where the engine trades 3. It
now calls `run_day`. Anything that restates the engine drifts from it.

**16. `min_reward_risk` applied as a pre-entry veto.** Not a coding error — a
reading, and the largest single rejection reason in the engine (66). The spec's
own numbers rule it out: `target_typical` $0.15–0.20 against `stop_typical`
$0.08–0.10 is a target 1–2R away, not one at "2× the stop". Measured, setups
passing all 8 gate conditions have a *median* target 1 of 1.14R against 1.79R
for setups that fail — the gate selects names pressed against their high of
day, so the veto was anti-correlated with the gate behind it and killed 74% of
gate-passing setups.
*Fix:* `RR_FILTER` defaults off; 2:1 is measured as a realised ratio over
trades, which is how every citation states it. `reports/2026-08-target-and-entries.md`.

---

## Withdrawn conclusions

Reported in earlier write-ups, then withdrawn. Listed so they are not rediscovered
as if they were real.

**"Every winner makes exactly +1.00R, so the strategy's 2:1 never materialises."**
Artifact of defect 3. The +1.00R was arithmetic forced by using 2R as the target
and then moving the stop to breakeven.

**"The $0.20 stop cap conflicts with the $2–20 price band and excludes every
large winner."** Artifact of defect 7. The source says to cut size, not skip.

**"The entries have no edge — no trade reaches its target under any exit
regime."** Measured before defects 8–13 were fixed, when the detector was
discarding breakouts on the strongest names. It stays withdrawn: across 406
setups, target 1 is reached **56%** of the time. The well-powered replacement
is narrower and survives — 37% of those reach it only after dipping past the
stop, so the documented setup gets to its documented target cleanly on **35%**
of its own signals against a 40% breakeven
(`reports/2026-08-target-and-entries.md`).

**"Raising the trade limit from 2 to 5 costs money."** Measured when the limit
was binding for the wrong reason. It currently never binds.

---

## Reported P&L over time

Every one of these was measured on the same data. The differences are entirely
implementation.

| Stage | Trades | P&L |
|---|---:|---:|
| Initial (defects 1–13 present) | 14 | −$1,037.24 |
| After defects 3, 4, 5, 6 fixed | 4 | −$560.33 |
| After 7–11 fixed | 0 | $0.00 |
| After 12, 13 and scoping fixed | 3 | +$128.70 |
| 17 sessions, halts + §1 confirmation, max 5 | 2 | +$633.30 |
| After defect 14 (the exit look-ahead) | 2 | **+$357.54** |
| After defect 16 — 2:1 veto removed, now the default | 11 | −$601.65 |

The trajectory is the reason no P&L from this harness should be treated as a
result until the frequency discrepancy in `OBSERVATIONS.md` §3 is understood.
As of `reports/2026-07-july-calibration.md` that discrepancy is localised: it
is the scanner and the entry rules, not the universe and not the detector.
