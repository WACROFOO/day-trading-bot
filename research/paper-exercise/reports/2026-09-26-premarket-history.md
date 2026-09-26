# Pre-market and the full history — why it was missing, where it is, and what the repo already knows

**Provenance.** Yahoo pre-market volume: measured this session on GRML's
1-minute bars 2026-09-17..25 (every pre-market bar volume 0). Eleven-year
figures: `research/first-pullback-edge/reports/final_report.md`. Seven-session
figures: `scripts/backtest_recent.py` re-run this session with the cost model
added. Paper only.

## 1. Why the backtests had no pre-market

The container that runs these analyses has no IBKR Gateway and no data keys.
Its only free source is Yahoo, and Yahoo's 1-minute API returns **zero volume
for every pre-market bar**. Without volume, pre-market VWAP cannot be
computed and the pullback-volume gate cannot be judged, so those two gates
were skipped before 09:30 and no pre-market conclusion was drawn.

Two sources DO carry pre-market volume, and both are on your Mac:

| source | where | depth | used by |
|---|---|---|---|
| Alpaca SIP feed | the keys already in your `.env` (the headline keys) | 2016 onward | `scripts/backtest_history.py` (new) and the 11-year study |
| IBKR | your Gateway | about a year of 1-minute bars, slow (pacing) | the live desk |

## 2. What the repo already measured over eleven years

`research/first-pullback-edge/reports/final_report.md` ran a Pine port of this
pullback strategy on 25,716 gapper-days 2016-02 .. 2026-08, survivorship-free,
on the Alpaca SIP feed:

| finding | number |
|---|---|
| trades, basic first pullback | 3,627 over 1,453 sessions |
| expectancy, realistic costs | −1.741 R, 95 % CI [−1.79, −1.69] |
| expectancy, no costs at all | −0.404 R |
| years positive | 0 of 11 |
| with VWAP / EMA / MACD gates | −1.644 R |
| random entry minute, same names | −0.940 R (beats every variant) |
| pre-market trades | **zero** — its volume gates rarely passed on 04:00–09:30 tape |

It is a different detector from the desk's (the Pine's impulse filter is
stricter, its stop capped at 3 %), so it does not answer the question for THIS
bot. It does say the burden of proof is heavy.

## 3. The seven sessions, net of costs

Same run as the 09-25 assessment, current rules with A11, regular hours, one
position, now with IBKR commissions and one cent of slippage a side at the
$20 sizing:

| exit | gross R | net R | trades | days positive |
|---|---|---|---|---|
| fixed 2 R | +23.50 | +10.76 | 38 | 4 of 7 |
| A3 trail | +31.22 | **+17.03** | 39 | 4 of 7 |
| BE+2R | +25.23 | +11.87 | 40 | 4 of 7 |

Costs average **0.39 R per trade** at this size. Seven sessions positive after
costs is encouraging and is still seven sessions.

## 4. The new tool — the desk's own rules over ten years, pre-market included

`python3 scripts/backtest_history.py` (runs on the Mac):

- universe: the 25,716 committed gapper-days, plus every day your desk traded (`--ledger`)
- bars: Alpaca SIP, 04:00–16:00, with pre-market volume, one request per session, cached
- rules: the desk's detector and gates exactly, VWAP anchored at 04:00 like the desk, A11, A10 entry with a gap over the limit counted as no fill, stops gapped through filled at the open, costs
- output: per window and per year, gross and net; a **walk-forward optimizer** (every gate combination × exit × window chosen on 2016–2023, scored once on 2024–2026, beside the current rules on the same years); and **forecast vs actuals** — the simulator on each of your live trades against what really happened

The two live trades checked by hand so far: GRML 09-24 simulated −0.02 R,
live −0.02 R; GRML 09-25 simulated −0.83 R, live −1.61 R. The simulator is
exact on a clean fill and optimistic on a thin one.

## 5. The rule that decides pre-market, written before the run

Proposed for the owner to confirm: **pre-market entries continue if, in the
history run, current-rules pre-market trades number at least 200 and their
NET mean on the A3 trail is above zero in the TEST years (2024 onward).
Otherwise pre-market returns to watch-only until a variant passes the same
test.** Regular hours are judged by the same rule on their own cohort.
