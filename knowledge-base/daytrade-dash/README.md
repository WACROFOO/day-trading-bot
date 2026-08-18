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

## VENDOR-DOCUMENTED — the support portal, retrieved from the local corpus

```
SOURCE · knowledge-base/warrior-support/stock-scanners-day-trade-dash/
         19000117763-scanners-how-to-load-use-them-in-the-chat-room-wt.md
         Warrior Trading's own help-desk page, "Modified Thu, Jan 8, 2026".
         This is the VENDOR describing its own product - a primary source for
         platform behaviour, and a stronger one than a transcript for anything
         mechanical. It is still not a threshold disclosure: no numeric filter
         values appear anywhere in it.
```

### The news flame, settled

The portal publishes the table directly, under the column header
**"Age of Headline"**:

| indicator | age of headline |
|---|---|
| red flame | 0 to 2 hours old |
| orange flame | 2 to 12 hours old |
| yellow flame | 12 to 24 hours old |
| **no indicator** | **over 24 hours old** |

This matches the two transcripts (`oxob0x0Xz7s` @00:57:52, `oKlhUSSHe2Q`
@00:18:43) exactly, and closes the one part that was inference rather than
quotation: that the colour encodes **recency and nothing else**. The vendor's
own column header is "Age of Headline". No quality, source or magnitude
dimension exists.

Two mechanical facts the transcripts do not give:

- **The flame can lag its own alert by up to 5 minutes.** "For the alert
  scanners, the news indicators can update up to 5 minutes after the alert has
  already been made" - so a fresh alert showing no flame may still be a news
  move. Judging catalyst by the first paint is a mistake.
- **The 5 Pillar scanners do not filter news at all.** "we do not currently
  filter out whether a stock has news or not... you will want to ensure that
  the stock also features a flame indicator." The fifth pillar is manual even
  on the scanner named after the five pillars.

### The complete scanner inventory

**List scanners** (update every 30 s): Top Gappers (top 100; **stop updating
at 09:30**), Ross's 5 Pillar Scan List, Penny-Top Gappers (<$5), Ross's Top
Gappers, Large Cap, Large Cap Earnings with Gap, Top Gainers / Top Losers
(continue all day), Low Float Top Gainers, Penny Top Gainers / Losers, After
Hours Top Gainers (16:00-20:00), Recent IPO Top Moving (uplisted, held above
open, last 90 days), **Recent Reverse Split** (last 30 days, **more than
10:1**; the column value is the ratio), Change Since Open, Top of Trend
(built for Power Hour 15:00-16:00), Continuation, Top RSI Trend, Top Relative
Volume, Top Volume 5 Minutes, Large Cap Highest Volume.

**Alert scanners** (update every second, optional chime): Ross's 5 Pillar
Alert; **Small-Cap HOD Momo** with sub-strategies Low Float Med/High Rel Vol,
Low Float High Rel Vol $20+, Low Float Volatility Hunter (HOD breakout),
Former Momo, Medium Float Med Rel Vol $20+, Medium Float High Rel Vol $20+,
Medium Float High Rel Vol under $20, Squeeze 10%/10min, Squeeze 5%/5min,
Squeeze 52wk Breakout; **Penny HOD Momo** (all **under $2.00**) with Penny
52-week High, Penny Volatility Hunter, Penny Squeeze; Running Up; Running
Down; Reversal; Large Cap HOD Momo; **Halt Scanner**.

This confirms the six branches in the 08-18 export are sub-strategies of one
scanner (Small-Cap HOD Momo), which is why `event` was `New High` on every
row - the parent scanner is defined as "Scans for New HOD price alerts on
above-average momentum".

### Columns the export has and we did not know were standard

Symbol/News, Price, Volume Today, Relative Volume (Daily), Relative Volume
(5 min), Gap %, **ATR**, Change From Close %, Short Interest, **Short Ratio**.
Volume, Float and Gap% are gradient-coloured by value; the HOD scanner adds a
**Strategy column colour-coded per sub-strategy**.

**Float can read zero** for IPOs and new listings, and real float data can be
absent for 24-48 hours; the platform then shows a **"Check Filings"**
indicator. That is the vendor conceding the same unknown-float hole that made
`allowUnknownFloat` necessary in scanner v2 - it does not fail closed either.

### A divergence worth keeping, not resolving

On video (`yg5E_mqGFGg` @00:19:36) he says audio is on for **two** strategies:
*"low float and squeezing up 10 in 10 minutes"*. The portal instead documents
his setting as **all strategies except the Medium Float ones**:
*"Want to set the same alerts that Ross has on the Small Cap - High of Day
Momentum scanner? Select all strategies except the Medium Float scanners."*

Both are sources; neither is obviously stale. Recorded as a divergence rather
than silently picking one. What both agree on: **Medium Float is the tier he
does not want interrupting him.**

---

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
   research/momentum-replication/reports/2026-08-dash-calibration.md
   (NOT YET WRITTEN — planned output, not a citation) and
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

## First live snapshot — observed bounds (2026-08-17, 40 HOD alerts)

From `WARRIOR_SCANNER_SOURCE_ANALYSIS.md` (clean-room, no credentials
touched). OBSERVED, single-snapshot — bounds, not thresholds:

- **The float tiers get their first bounds:** "Low Float – High RVOL"
  showed floats up to **5.38M**; "Medium Float – High RVOL – under $20"
  showed **33.39M**. So low-float ceiling ≥5.4M, and 33M classifies as
  medium — our binary 20M cap sits between the two real tiers.
  **Tightened 2026-08-18** by the Momo CSV export: low-float ceiling
  **≥8.40M** (XOS), medium **includes 41.92M** (WFF, which fires the medium
  branch and no low-float one). Boundary bracketed to (8.40M, 41.92M].
- **The platform alerts below $2** (Volatility Hunter at $1.07, Squeeze 5/5
  at $1.73–1.99) — consistent with the penny-theme finding of 08-12: the $2
  floor is OUR selection rule, not the scanner's.
- **Former Momo floats were tiny**: 0.319M–1.60M in this snapshot.
- Displayed RVOL values were flagged implausibly large by the analyst — do
  not copy Warrior RVOL numbers into any tool without the denominator
  question answered (see calibration).
- API surface confirmed server-side (`/v1/scanner/config`, `/const`,
  `/strategies` — bearer-protected). Thresholds are unrecoverable from the
  client; calibration is the only honest path.

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

---

## Momo alert export, 2026-08-18 — first filter reverse-engineering

**MEASURED.** Operator exported 295 high-day-momentum alert rows (04:02–05:36
ET, 7 symbols, 6 branches) to `captures/2026-08-18-momo-alerts.csv`. Full
analysis: `research/momentum-replication/reports/2026-08-18-momo-scanner-reverse-engineering.md`.

Three results worth carrying:

1. **`event` is `New High` on 295/295 rows.** Cross-checked against continuous
   1-min bars: the alert bar sets a new high of day in **293/293** measurable
   cases, against a **5.0%** base rate over all 626 bars of those names. The
   six branches are qualification rules sharing one trigger — and it is a
   trigger `./now` does not implement.
2. **Low Float / High Rel Vol caps price near $10.** PFSA passes every other
   observable condition of that branch and never fires it; bracket
   [9.83, 10.1951). The medium-float branch caps at $20 by its own name, so
   the low-float branch is the *tighter* one on price.
3. **Former Momo carries the lowest RVOL floor — IPST fired at 2.13**, the
   minimum in the file. Confirms ch.10's "lower thresholds" claim from output,
   and lands just above the 2.0 the scanner v2 correction already adopted.

The export contains **no news/flame field** — `Symbol / News` is only a quote
URL. The flame is UI-only and does not survive CSV export.

---

## Incident log — TRUG, 2026-08-17

**MEASURED.** `tape.py TRUG` 10:33 ET: HOD 1.82 @10:23 on 1.62M shares;
10:26 and 10:27 both topped at exactly 1.78; 10:28 opened 1.74, low 1.56.

The strategy armed a trigger at **1.7801** with stop 1.7300 — i.e. **4 cents
under the impulse peak with a 5-cent stop, 0.4R of room**. The trigger was
never cleanly taken out (highs printed 1.78, not 1.7801) and the next bar
broke down 18 cents.

Three defects, all mine, all in presentation rather than arithmetic:

1. **The 0.4R room warning was rendered in silver, next to the share count.**
   A red flag nobody can see is not a red flag. → V4.8 puts it in the verdict
   line, in red, as `⚠ ONLY 0.4R TO PRIOR HIGH`.
2. **A bright yellow `TRIGGER SET` banner reads as an instruction** — the exact
   failure mode the design pack's vocabulary rule names. Renaming ARMED to
   TRIGGER SET did not fix the colour. → V4.8 turns the banner orange when the
   room is thin.
3. **`requireRRtoPeak` shipped default OFF**, justified in the V3 audit by the
   "2:1 R:R is a realised ratio, not a pre-entry veto" finding. That conflated
   two different objects: the *trade plan's* R:R (correctly not a veto) and
   *room to the prior high* (a genuine extension check the source does make).
   The gate stays optional — flipping a default on one trade would be inferring
   a threshold from one day — but it is now recommended in the input group and
   the warning fires regardless.

Not a defect, and worth recording plainly: the script's trigger was 1.7801.
An entry taken at 1.71 is **below** the trigger — anticipating the setup, not
taking it. The tool never printed a signal at that price.
