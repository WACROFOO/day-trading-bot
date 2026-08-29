# The assistant — plan for the third instrument

```
SCOPE · design plan for ross-assist-v1.pine, a Pine v6 INDICATOR (never a
        strategy) that coaches a HUMAN through the Ross decision sequence
        on a live chart. It places no orders, holds no position, simulates
        nothing. Requested 2026-08-29: "an aid, not a trading bot."
SOURCES · everything below was read this session from:
        knowledge-base/strategies/FILTERS.md · PARAMETERS.md · SCANNERS.md
        knowledge-base/tradingview/STRATEGY-COVERAGE.md · SCANNER-V2-PLAYBOOK.md
        .claude/skills/ross-tradingview-mastery/references/master-context.md
        · tradingview-setup.md
        No market data was fetched and none is cited.
STATUS · paper only. The repo's 894-session replication of this strategy
        was NEGATIVE expectancy
        (research/momentum-replication/reports/2026-08-regime-filter.md).
        This tool's job is discipline and visibility, not prediction.
```

Evidence vocabulary, used on every row (from the mastery skill):
`CONFIRMED` he states it · `QUALITATIVE` defined without a number ·
`OBSERVED` measured once, not a rule · `APPROXIMATION` our number, declared ·
`UNKNOWN` not established — rendered as `?`, never guessed.

---

## 1 · What exists, and the gap this fills

The repo already carries two Pine instruments
(`knowledge-base/tradingview/README.md`):

| instrument | answers | what it is |
|---|---|---|
| `ross-style-scanner-v2.pine` | **WHICH NAME** | Layer 0–1 selection: pillar scoring, Pine Screener columns, HOD/squeeze events |
| `ross-fp-v4.pine` | **WHEN** | a *strategy* script: simulates its own entries, stops, targets — a bot's-eye view |

Neither follows the **human** through a trade. The scanner stops at "worth
charting"; fp-v4 trades its own simulated position and its dashboard serves
that simulation. Nothing on screen answers the questions the operator
actually asks in sequence while trading by hand:

```
am I allowed to trade right now?          (session clock, daily limits)
is this stock still the right stock?      (pillars, fade, crowding)
is the tape behind an entry?              (the §3 gate, and only §3)
what is my exact plan if I click?         (trigger, stop, shares, target)
I'm in — when do I get out?               (hard-exit signals, scaling)
should I be done for the day?             (§8, the rules-as-the-fix layer)
```

That last column is the one the corpus itself says matters most and costs
nothing to encode: emotional control resolves not to feelings but to
*"rules as the fix"* (214) and *"walk away"* (107) — §8 enforced by
something other than the trader (`PARAMETERS.md` §10). An indicator that
holds no position can still hold the rules.

---

## 2 · Design decisions — the rejected alternatives, visible

| decision | rejected alternative | why it died |
|---|---|---|
| indicator, chart-only | strategy script with simulated fills | exists (fp-v4); user asked for an aid; and backtest fills on this class are not portable — 25% of fills hit same-bar trigger+stop ambiguity (`STRATEGY-COVERAGE.md` limit 9) |
| third instrument | merge into scanner v2 | the repo's own rule: one tool answers WHICH, one answers WHEN (`SCANNER-V2-PLAYBOOK.md` header). This one answers AM-I-ALLOWED / WHAT'S-MY-PLAN — a third job |
| entry gate = §3, exactly and only §3 | "improve" the gate with pattern rules | a full implementation produced ~18 defects, none a wrong number; adding extras cut the pass rate 6.7%→3.5% (`PARAMETERS.md` §13) |
| R:R shown as information | R:R ≥ 2 as an entry veto | the 2:1 is a *realised* ratio; as a veto it was the single largest rejection reason (66) and he has posted 0.57–1.42 (`PARAMETERS.md` §13, §9) |
| dials and gates rendered as different objects | one threshold set | *"a scanner setting is not a trade gate"* — the six-defect pattern of the 2026-08 audit (`PARAMETERS.md` §15) |
| 3rd pullback → `REDUCE SIZE` lamp | 3rd pullback → skip | he takes the third at reduced size: *"this is the third pullback... bought the dip at 68"* (`0uunIYE_wVY` [19:22], via `PARAMETERS.md` §13) |
| wide stop → `CUT SIZE` lamp | wide stop → reject | *"cut your size or skip"* — the sizing formula already shrinks shares (`PARAMETERS.md` §13) |
| float + catalyst = manual inputs, fail closed | auto-detect | Pine exposes no float field and no news; an untyped value must show `?` and fail the pillar, which is honesty, not a bug (`STRATEGY-COVERAGE.md` limits 2, 6) |
| non-actionable vocabulary | BUY/ARMED labels | research output that reads like an instruction is followed like one (`trading-report-design`; SETUP→REVIEW rename 2026-08-14) |
| alerts fire to the operator's phone | webhook automation | a webhook receiver is a bot with extra steps — out of scope by request |

---

## 3 · The instrument, module by module

Decision order on the dashboard mirrors fp-v4's audited order — verdict
object first, selection last — but the verdict set is coaching vocabulary:
`STAND DOWN` · `NO` · `WAIT` · `WATCH` · `REVIEW` · `MANAGE` · `DONE FOR THE DAY`.
Never BUY, never TAKE.

### A · CLOCK — am I allowed to trade?

| rule | value | status | source |
|---|---|---|---|
| pre-market window opens | 07:00 ET | CONFIRMED — era-checked: 78 vs 36 mentions in the 2026 challenge | `PARAMETERS.md` §2 |
| entry blackout | 09:30–09:35 | CONFIRMED (n=44) | `PARAMETERS.md` §2 |
| prime window | 09:35–10:30 | CONFIRMED (n=44) | `PARAMETERS.md` §2 |
| wind-down warning | 10:30–11:00, *"right around that 90 minute mark"* | CONFIRMED | `blog/recaps/starting-off-september-grateful-334` via `PARAMETERS.md` §2 |
| hard stop | 11:30 — outer edge, not the centre | CONFIRMED (n=16) | `PARAMETERS.md` §2 |
| midday | 11:30–15:00 → `STAND DOWN` | CONFIRMED | `PARAMETERS.md` §2 |
| after hours | no trades 16:00–20:00 — *"doesn't look like I'm net profitable trading after hours"* | CONFIRMED, measured by him | `FILTERS.md` Layer 3 |

Render as a phase chip plus countdown to the next boundary (the `./now`
pattern). The clock **only ever downgrades** a verdict; it never upgrades.

### B · STOCK FIT — is this still the right stock?

The five pillars as a lamp card, each lamp with its sub-condition. Pillar
values, not scanner dials — with the dial shown greyed beside the gate so
the two objects stay visibly different (`PARAMETERS.md` §15).

| pillar | gate value | dial (grey, informational) | status | source |
|---|---|---|---|---|
| price | $2–20, *"between 5 and 10 is even better"* | — | CONFIRMED | `oKlhUSSHe2Q` [00:30:35] via `SCANNERS.md` B5 |
| change on day | ≥ 10% | scan dial 5% | CONFIRMED | `oKlhUSSHe2Q` [00:30:16]; dial `FILTERS.md` Layer 0 |
| relative volume | trade floor **1.5×**, best ≥ 3× | scan dial 5× | CONFIRMED — measured from his broker split | `blog/risk-psychology/rollercoaster-trader-behind-trades-ep-6` via `PARAMETERS.md` §1 |
| float | < 10M pillar; < 5M bright | dial 20M | CONFIRMED — three layers, all correct (C3) | `oKlhUSSHe2Q` [00:30:38]; `w97KlUrVDk0` [00:54:55]; `SCANNERS.md` C3 |
| catalyst | manual checkbox, fail closed; a live theme substitutes | — | CONFIRMED incl. the theme correction | `FILTERS.md` gates 1&3 note, 2026-08-12 |

Plus the three fit checks a chart *can* compute:

| check | fires when | status | source |
|---|---|---|---|
| fade from high | > 25% off the pre-market/day high → `NO — back side` | CONFIRMED — *"stair stepping down… I'm not a buyer"* | `FILTERS.md` gate 4 |
| pre-market volume ceiling | > ~1M shares pre-market → warning, *"I'm not the first one to see it"* | CONFIRMED — a ceiling with **no floor** (NCTY on 8,000) | `FILTERS.md` Layer 1; `PARAMETERS.md` §1 |
| session volume floor | cumulative < 1M shares → warning — *"less than a million... I actually lost $8,000"* | CONFIRMED, measured | `PARAMETERS.md` §1 |

RVOL cells carry the ᵗ tag and the denominator legend: daily RVOL is
biased **low** all morning, 5-min RVOL biased **high** pre-market on an
extended-hours chart (`SCANNER-V2-PLAYBOOK.md`, denominator problem).
The two cells never share a lamp.

### C · TREND GATES — is the tape behind an entry?

Exactly the §3 entry gate. Six evaluable lamps, two honest `UNKNOWN` chips.

| lamp | condition | status | source |
|---|---|---|---|
| ① MACD | 12/26/9, hist > 0 **and** above signal — this IS "front side of the move", not a separate test | CONFIRMED (n=66) | `PARAMETERS.md` §3, §13; `iIC62xnblLc` [26:20] |
| ② VWAP | price > vwap | CONFIRMED (n=45) | `PARAMETERS.md` §3 |
| ③ 9 EMA | price > ema9 — a dip that *recovers* is bullish; only sustained below is bearish | CONFIRMED (n=30) | `FILTERS.md` Layer 2 |
| ④ volume shape | pullback volume < impulse volume | CONFIRMED (n=168) | `PARAMETERS.md` §3 |
| ⑤ pullback count | index ≤ 2 green · index 3 → `REDUCE SIZE`, never skip. A 1-candle pause does **not** consume the count | CONFIRMED | `PARAMETERS.md` §3, §13 |
| ⑥ support confluence | ≥ 2 of {whole/half dollar, ema9, ema20, ma200, vwap, flipped level} within `tol` | CONFIRMED structure; `tol` **UNSOURCED — sweep input** | `PARAMETERS.md` §3 |
| ⑦ tape | buyers hitting the ask | `UNKNOWN` chip — no tape in Pine | `PARAMETERS.md` §3, §10 |
| ⑧ Level 2 | no seller wall | `UNKNOWN` chip — no book in Pine | `PARAMETERS.md` §3, §10 |

⑦ and ⑧ are rendered, not omitted: the card must show the operator that
two of eight gates are theirs to check by eye. Collapsing them away is the
silent-filter anti-pattern.

### D · THE PLAN — what exactly happens if I click?

Levels drawn only while gates A–C allow it; otherwise greyed "hypothetical".

| element | rule | status | source |
|---|---|---|---|
| trigger line | one tick above **the previous red candle's** high — not the move high, not HOD; intrabar | CONFIRMED (n=80) | `blog/core-strategy/bull-flag-trading` via `PARAMETERS.md` §4 |
| anticipation note | for a *level* (whole dollar, PM high, HOD): position 10–25¢ below, add through — candle=confirm, level=anticipate | CONFIRMED (29 streams vs 1) | `PARAMETERS.md` §4; `KQU4HPH4S_4` [14:34] |
| stop line | pullback candle low; never widen, never average down | CONFIRMED (n=50) | `PARAMETERS.md` §5 |
| stop too wide | distance > $0.30 → `CUT SIZE` lamp (emotional limit, not chart-derived) | CONFIRMED | `blog/recaps/starting-off-september-grateful-334` via `PARAMETERS.md` §5 |
| stop too tight | distance < spread → `NO` — a stop inside the spread cannot survive noise (5 of 16 losses in one study) | CONFIRMED defect record | `PARAMETERS.md` §13 |
| shares | `risk_budget ÷ (entry − stop)`, risk 2% of account (input) or $50 flat beginner path | CONFIRMED (n=125) | `PARAMETERS.md` §7 |
| open throttle | first trades at **¼ size** until day P&L ≥ +$1,000 (manual P&L input) | CONFIRMED | `blog/other/how-being-a-great-loser-can-lead-to-day-trading-success` via `PARAMETERS.md` §7 |
| ceiling | 20,000 shares | CONFIRMED | `blog/other/3-lessons-making-60k` via `PARAMETERS.md` §7 |
| target 1 | the **nearest** objective — HOD retest or measured move; typical 15–20¢ | CONFIRMED | `PARAMETERS.md` §6, §13 |
| R:R chip | displayed with legend *"realised ratio, not an entry veto — his best month posted 1.42"* | CONFIRMED reading | `PARAMETERS.md` §9, §13 |

### E · MANAGE — I'm in; when do I get out?

The indicator cannot know a fill. One manual input — `my entry price`
(0 = flat) — switches the card from PLAN to MANAGE. Then:

| signal | action shown | status | source |
|---|---|---|---|
| +1R reached | `SCALE 50%` · stop→breakeven prompt (breakeven trigger ≥ +$0.10) | CONFIRMED | `PARAMETERS.md` §5, §6 (50/25/25) |
| first candle to make a new low **below the flag** | `EXIT` lamp — bar-local lower lows are noise | CONFIRMED reading | `Xdw5azEqs6o` via `PARAMETERS.md` §13 |
| MACD crosses negative | `EXIT` lamp | CONFIRMED (n=66) | `PARAMETERS.md` §6 |
| VWAP break | `EXIT` lamp — hard invalidation | CONFIRMED (n=45) | `PARAMETERS.md` §5 |
| high-volume red candle | `EXIT` lamp with multiple (e.g. 2.6× avg) | CONFIRMED (n=168) | `PARAMETERS.md` §6 |
| large topping tail | `EXIT` lamp | CONFIRMED (n=8) | `PARAMETERS.md` §6 |
| green candles shrinking | `WARN` | CONFIRMED (n=168) | `PARAMETERS.md` §6 |

### F · DISCIPLINE — should I be done for the day?

Three manual inputs (day P&L, day peak P&L, consecutive losses) drive the
§8 lamps. This is the module with the highest claimed leverage and zero
chart dependency:

| lamp | rule | status | source |
|---|---|---|---|
| green-to-red | day was green, now negative → `DONE FOR THE DAY` | CONFIRMED (n=68) | `PARAMETERS.md` §8 |
| giveback | ≥ 50% of day's peak gain surrendered → `DONE` | CONFIRMED (n=68) | `PARAMETERS.md` §8 |
| loss streak | 3 consecutive losses → `DONE` | CONFIRMED (n=68) | `PARAMETERS.md` §8 |
| max daily loss | = daily goal magnitude; ≤ 6% of account | CONFIRMED (n=68) | `PARAMETERS.md` §8 |
| trade count | > 4 names → `WARN` | CONFIRMED (2–4, n=22) | `PARAMETERS.md` §7 |

`DONE FOR THE DAY` outranks every other verdict on the board.

### G · HALT AWARENESS

| element | rule | status | source |
|---|---|---|---|
| band estimate | from **prior close** tier: >$3 → 10% · $0.75–3 → 20% · <$0.75 → lesser of 15¢/75% | CONFIRMED — tier 3 verbatim *"lessor of 15 cents or 75%"*; do not reconcile toward the wrong 15% article | `PARAMETERS.md` §8b |
| band doubling | opening and closing auctions; closing window 15:35–16:00 exactly; opening times unstated | CONFIRMED / UNKNOWN | `StpXbe3Ga3Y` [08:37]; `blog/rules-regulation/circuit-breaker-halts` via §8b |
| enforceability lamp | stop distance wider than the live band → `STOP UNENFORCEABLE` — a stop cannot be honoured through a halt | repo rule, carried from fp-v4 | `FILTERS.md` rule via `STRATEGY-COVERAGE.md` |
| dwell note | price must sit at the band 15 seconds | CONFIRMED | `PARAMETERS.md` §8b |
| honesty line | Pine sees a halt only as a gap in bars; resumption fills are unmodellable | CONFIRMED limit | `PARAMETERS.md` §8b; `STRATEGY-COVERAGE.md` limit 4 |

---

## 4 · The honesty register — free parameters and manual inputs

Everything the operator must supply or sweep, in one place, because these
are where the tool can lie:

| input | default | origin | note |
|---|---|---|---|
| float (M shares) | 0 → `?`, pillar fails closed | manual | `scripts/chart_card.py` bridges a Top Gainers export |
| catalyst confirmed | off | manual | reading the headline is the operator's job |
| my entry price | 0 = flat | manual | switches PLAN→MANAGE |
| day P&L / peak / loss streak | 0 | manual | drives module F |
| account size, risk % | — / 2.0 | `PARAMETERS.md` §7 | |
| support `tol` | 0.25% | **UNSOURCED** | sweep 0.10–0.50, never tune (`PARAMETERS.md` §3) |
| RVOL thresholds by phase | playbook profiles | APPROXIMATION | denominator workarounds, `SCANNER-V2-PLAYBOOK.md` |

Pine constraints to hold (from `tradingview-setup.md` and the tradingview
README): Pine v6; `scripts/pine_check.py` before any push (CE10272 /
CE10123 are the two classes that have shipped broken); no repaint — state
from confirmed bars, anything intrabar labelled as such; chart-only tool,
so the Pine Screener 10-plot budget does not bind it; 1-minute chart,
extended hours ON.

---

## 5 · Build order and validation

1. **v0.1 — CLOCK + STOCK FIT** (A, B). Verify against `./now SYM` on live
   names: same phase, same pillar verdicts, divergences logged.
2. **v0.2 — TREND GATES + PLAN** (C, D). At a fixed minute, compare every
   lamp against `python3 scripts/tape.py SYM` — VWAP, EMA9, MACD, stop
   honesty. A disagreement blocks the release, not the note.
3. **v0.3 — MANAGE + DISCIPLINE + HALTS** (E, F, G).
4. **Parallel run, 5 sessions.** Chart card vs `./now` vs Day Trade Dash at
   the same timestamp; store triples in `knowledge-base/daytrade-dash/captures/`
   per that folder's protocol. After ~20 samples the RVOL offset becomes a
   measured number instead of a mystery (`SCANNER-V2-PLAYBOOK.md`).
5. **Sweep the two free parameters** (`tol`, RVOL phase thresholds) and
   report the spread. If a verdict flips inside the swept range, the lamp
   is downgraded to `WATCH`, not tuned until it agrees.
6. Every release: `pine_check.py`, then compile in TradingView — the lint
   is not a compiler and TradingView is the only authority.

---

## 6 · What this tool cannot check

Carried forward from `STRATEGY-COVERAGE.md` and `PARAMETERS.md` §10, none
of it solvable from Pine:

- the **10-second micro-pullback** — often sub-minute; a 1-minute chart
  shows it as a wick (250 mentions across 117 streams)
- **true float** and **news quality** — manual, fail-closed
- **Warrior's RVOL** — same direction, different denominator; never compare
  as equals
- **halt state and resumption fills** — a gap in bars is all Pine sees
- **tape and Level 2** — gates ⑦⑧ stay on the operator
- **spread and executable size** — no quote data in an indicator
- **dilution, splits, buyouts, EDGAR** — Layer 0/1 lives in `./now --scan`
  and `catalyst_score.py`, before this tool is ever opened

NO TICKET ISSUED. This is a checklist renderer. It validates no order, and
a board of green lamps is a prompt to read the chart, never an instruction.

---

## 7 · Verdict

The perfect aid is not a better signal — the corpus and 894 replayed
sessions agree the signal is not where the money was lost. It is the
**third instrument**: scanner v2 says WHICH, fp-v4 demonstrates WHEN, and
this one holds the operator to AM-I-ALLOWED, WHAT-IS-MY-PLAN, and
WHEN-AM-I-DONE — the §8 layer he himself frames as rules doing the job of
discipline. Build it as a coach with fail-closed chips, dials visibly
separate from gates, and the two free parameters swept in the open.

Paper only. A green dashboard is not an edge.
