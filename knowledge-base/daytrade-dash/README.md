# Daytrade Dash — the real scanner suite (trial observations)

```
SOURCE · trial access to Ross Cameron's platform, 2026-08-17, relayed via a
ChatGPT browser-extension retrieval. Server-side thresholds are UNDISCLOSED —
everything numeric here is either observed output or approximation, never
the platform's actual formula. Trial data has an expiry date; capture first,
interpret later.
```

## The scanner taxonomy, as retrieved 2026-08-17

| scanner | what it appears to do | our equivalent |
|---|---|---|
| **Five Pillars HOD candidate** | price + gain + RVOL + float, near high of day | `./now` board (P F C R V) |
| **High-of-Day Momentum** | names printing new HODs | none — gap: we check fade, not HOD prints |
| **Running Up** | sustained upward prints | impulse detection in FP V4 |
| **5% in 5 min** | short-burst squeeze | none |
| **10% in 10 min** | slower squeeze | none |
| **52-week breakout** | daily-level break | none (daily walls only in prose) |
| **Former Runner** | ran before, moving again, LOWER volume thresholds | **confirmed** — book ch.10 said exactly this; our day-2 watch is the manual version |
| **Low-float / medium-float branches** | same scans split by float class | our float gate is binary <20M; his is tiered |

Confirmations against the corpus: the Former Runner scanner's existence and
its lower thresholds were claimed in the book (ch.10) — now seen live. The
float TIERING (low vs medium branches) is new information: the 20M cap is a
simplification of a two-tier reality.

## Calibration protocol — the point of the trial

The trial's value is measured divergence, not admiration. Every capture:

1. At a fixed time (07:00 / 08:00 / 09:00 / 09:25 ET), export or screenshot
   the platform's scanner rows (symbol, price, %, volume, float, RVOL as
   shown).
2. Same minute, on the Mac: `./now --scan > captures/YYYY-MM-DD-HHMM-ours.txt`
3. Drop both into `knowledge-base/daytrade-dash/captures/` (create per-day
   files; screenshots as .png next to them).
4. The comparison question is always the same three:
   - names on THEIR board missing from OURS (our discovery hole — the
     TradingView premarket_change floor, the 250k dial, the fund filter?)
   - names on OURS missing from THEIRS (our false positives — or their
     tighter server-side thresholds)
   - rank disagreements in the top 5 (their sort vs our gap-% sort)
5. After ≥3 sessions of captures, write the divergence report to
   `research/momentum-replication/reports/2026-08-dash-calibration.md` and
   only then adjust premarket_stars.py dials — one change per measured gap,
   origin SOURCE (observed), never guessed.

## The ChatGPT Pine replica

A Pine indicator replicating these scanners was generated on the Mac
(`ross_style_momentum_scanner.pine` + setup guide, not yet in this repo, not
yet compiled). Before it joins the toolchain it gets the same treatment as
ROSS FP V3: archived verbatim, divergence-audited against FILTERS.md, then
corrected — push or paste the file to trigger that audit. Until audited it
is a hypothesis with a dashboard, and its Pine Screener mode runs on a
WATCHLIST (max ~1000 names), not the whole market — selection still starts
with a real scan.

## Pine replica audit (2026-08-17)

Audited: `ross_style_momentum_scanner.pine` → corrected copy at
`knowledge-base/tradingview/ross-style-scanner-v2.pine` (original = that
file minus the `// V2:` lines; setup guide archived here).

**Four changes applied:**

| change | origin |
|---|---|
| Daily-RVOL pillar default 5.0 → **2.0** | SOURCE — book GR#1's scanner floors RVOL at 2.0; 5× is the teaching dial, and as a hard gate it re-commits the audit's one error class |
| `allowUnknownFloat` false → **true**, + new plot 11 "Float known" | MEASURED — the week's biggest runners (ONFO, WETO, SXTC) had NO published float; fail-closed silently deleted the hunted population. The provenance column keeps unknowns visible instead of hidden |
| band status "Armed" → "Trigger set" | design pack vocabulary |
| N/A → em dash in dashboard | design pack: absent ≠ zero |

**Flagged, not changed (denominator honesty):**

- **Daily RVOL = cumulative day volume ÷ 20-day full-day average** — at
  07:30 the numerator is a fraction of a day, so morning RVOL is understated
  exactly when it matters. No clean Pine fix; the 2.0 default partially
  compensates. Judge morning RVOL by eye, not by this cell.
- **5-min RVOL average includes overnight bars** on extended-hours charts —
  quiet-bar deflation inflates pre-market RVOL. Same class of bias, opposite
  direction. Both cells are labelled by vendor method, per device 8.
- **Float proxy = shares outstanding** (≥ float by definition) — overstates,
  so the 20M ceiling rejects names whose true float qualifies. Their manual
  input mitigates per-chart; in Screener mode treat FAIL-on-float as
  "verify", not "dead".
- **Entry band = signal-bar high + 1¢, stop = signal-bar low − 1¢** — a
  visualization of the break, not the micro-pullback entry (that lives in
  ROSS FP V4). A 1-min signal bar on a halting name can span $1+: the
  candle-low stop is then fiction (measured medians 0.23–0.83 this week).
  Use the ATR stop method on fast tape.
- **`breakout52` compares against yesterday's completed daily value**
  (lookahead_off) — correct and non-repainting, but a first-ever ATH day
  prints nothing until the next daily close. Known blind spot.

Not compiled here (no TV runtime) — paste into the editor; report errors.

Paper only. Observed scanner behaviour is selection evidence, not edge.
