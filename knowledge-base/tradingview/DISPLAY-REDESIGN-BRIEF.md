# V9 display + sizing redesign brief

A self-contained prompt. Paste it, together with `ross-fp-v4.pine` (V8.2),
to the model doing the work. It encodes four operator-reported defects from
live charts (CDTG + JZ, 2026-08-20), the mechanism behind each, and the
acceptance criteria. Nothing here is optional colour — every requirement
traces to a defect that actually happened.

---

## The prompt

You are redesigning the display and sizing layer of a 2,200-line Pine v6
strategy (`ross-fp-v4.pine`, revision V8.2) that implements Ross Cameron's
first-pullback pattern. Paper trading only. The execution core (state
machine, orders, exits, audit fixes V6–V8.2) is correct and OFF LIMITS
except where a requirement below names it. Your job is what the operator
SEES.

Start from the operator's own question, which is the design brief in one
line: **"What is the relevant information I need to focus on for a trade
decision? Make spotting it immediate. Professional and accurate, and at
the same time simple to use."**

A trade decision on this pattern needs exactly five things, in this order:

1. **Verdict** — trade / almost (what's missing) / no (why) / in a trade
   (what to do now). One line, current, never stale, never overwritten by
   a banner.
2. **Entry** — the trigger price, visibly anchored on the chart.
3. **Stop** — the structural stop, visibly anchored, with its $ risk.
4. **Target(s)** — T1 (half off, +1R) and T2 (2R), visible.
5. **Size** — shares to buy, from a rule the operator can recite.

Everything else — gates detail, scanner pillars, halt band, VWAP, S/R,
quality scores, ambiguity counters — is diagnostics: it must exist, but it
must never compete visually with those five.

### Defect 1 — the Clock lamp confuses two different clocks

Live JZ chart, 13:30 ET (market OPEN): `Clock✗`. The operator read this as
an error — "we are in an open market." The lamp actually reports the
STRATEGY's arming window (07:00–11:30 ET session gate + venue + last-bar
rule), not whether the exchange is open. Both meanings are real; the
display conflates them.

Also: the live CDTG chart traded at 13:30 with `Clock✓` because that
chart's inputs carry a STALE PER-CHART OVERRIDE — TradingView preserves
customized input values across script updates, so a months-old "ignore the
trading window" experiment (the V4.4-era directive, reversed in V7)
silently survives every new version pasted onto that chart.

Required:
- Split the display into two named facts: market phase (pre-market / OPEN
  / after-hours) and strategy window (07:00–11:30, on/off state of the
  hard gate). Wording must make "market is open but the playbook window is
  over" readable in one glance.
- When `useSessionWindow` is OFF, say so loudly on the dashboard (it is a
  non-default risk state), so a stale chart override can never masquerade
  as a signal.

### Defect 2 — share count follows no rule the operator recognizes

Live CDTG: "63 shares · $7 at risk (.37% of account)". The arithmetic is
internally consistent — `shares = min(floor(riskBudget / (risk_per_share +
slip_reserve)), floor(maxPositionValue / entry))` with a $20 budget and a
2×10-tick slip reserve — but it is unreadable ("why $7 when my budget is
$20?" — because the slip reserve consumed the rest, invisibly) and its
basis (1% of $2,000) is not the source's rule.

The source's rule, measured (`knowledge-base/strategies/PARAMETERS.md`
§7, cite it in-code):

```
risk_per_share = entry - stop
shares         = risk_budget / risk_per_share
risk_pct_per_trade = 2.0% of account   (n=125; 3–5% also stated)
risk_flat_beginner = $50               (n=125)
size ladder: 100 shares flat, +100/week (beginner path)
size_open_fraction = 0.25 of normal at the open, earned back
                     after +$1,000 on the day
max_trades_per_day = 2–4
```

Required:
- Default risk budget = 2% of `strategy.initial_capital` (input still
  overridable; keep the $-flat option for the beginner path).
- The SIZE row must show the DERIVATION, not just the result:
  `risk/share $X → N shares for $Y budget (slip reserve $Z) = P% of acct`.
  No number may appear whose origin the row itself does not state.
- Keep the slippage reserve in the sizing (audit finding 14 — removing it
  regresses a fix), but SHOW it.
- The existing third-fill-half-size rule stays; label it when active.

### Defect 3 — the chart is messy where it should be clean

Live CDTG shows, stacked in one screen area: an orange AMBIGUOUS SEQ
label, order-comment text ("Quick buy on break", "+75", "−75", "Exiting —
closed below entry"), SET/BUY/EXIT/SEEN markers, six S/R lines with
labels, halt bands, dotted HOD, entry/stop/target lines, and yellow
partial remnants. The operator cannot find the setup in the noise.

Required — a strict two-layer chart:
- **Decision layer (always on):** entry / stop / target lines for the
  LIVE plan only, the HOD, and at most one compact marker per event class
  (entry, exit, rejection). Order comments must be short codes, not
  sentences — the sentence belongs in the dashboard STATUS row.
- **Diagnostic layer (one input toggle, default OFF):** AMBIGUOUS SEQ
  labels, SEEN ghosts, S/R fan, halt bands, VWAP/EMA ribbons, debug
  levels. AMBIGUOUS SEQ must remain COUNTED on the LIMITS row even when
  its labels are hidden — the count is an audit artifact (finding 3) and
  may not be silently lost.
- Delete nothing that feeds the dashboard; this is about which layer
  renders where.

### Defect 4 — the setup itself must be legible in one look

"The setup is not clear." The dashboard has the data but the hierarchy is
flat — 13 rows of equal visual weight. Required:
- Rows 1–3 (VERDICT / PLAN / SIZE) get the visual emphasis; everything
  below reads as reference. Colour must encode trust and state, never
  decoration (repo rule: `trading-report-design`).
- The verdict vocabulary stays fail-closed and non-actionable in research
  surfaces, but THIS is the execution surface: BUY >x.xx / WAIT — reason /
  NO — reason / MANAGE are the four verbs. One of them is always present.
- A criterion that cannot be judged yet renders `·`, never `✗` (V5.2
  rule — a false cross teaches the eye to ignore crosses).

### Constraints (violating any of these is a failed delivery)

- Pine v6. `plotshape` size/text need const strings. `var` rolls back
  between realtime ticks; `varip` latches survive — do not add varip
  without naming why. No `security()` changes.
- The execution core is off limits: state machine, order placement,
  exits, cancels, the varip latches, the ambiguity counter, the
  session/venue gates' LOGIC (their display is yours).
- Every threshold or rule you cite must name its source file; anything
  not in the knowledge base is labelled `[UNTESTED local]`. No invented
  numbers — this repo's most expensive failure mode.
- Paper only. The 894-session replication was negative expectancy; an
  accurate display is not an edge and must not imply one.
- Run `python3 scripts/pine_check.py` before delivering. TradingView is
  the only real compiler; say so in the header, and bump `REV`.

### Acceptance test (do this before answering)

Recreate the two live scenes mentally and state what the new display
shows: (a) JZ squeezing, clock 13:30 ET, default inputs — market OPEN, window
over, pattern forming; (b) CDTG at 14:00 ET, stale override, trade done
40 minutes ago, thin current tape. If either scene produces a stale
banner, an unexplained share count, a Clock lamp readable as "market
closed", or a chart where the plan lines are not the most visible thing —
the redesign is not done.

---

**DELIVERED — V9.0, 2026-08-20.** All four defects implemented; the two
string-keyed-logic and hidden-ambiguity-count traps the acceptance test
would have caught were fixed before delivery. `pine_check` clean;
TradingView compile still the operator's step.

Paper only. Display work; no edge claimed.
