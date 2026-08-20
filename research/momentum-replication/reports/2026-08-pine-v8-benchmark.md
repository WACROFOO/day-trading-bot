# V7.5 vs V8.0 on real tape — what the re-audit fixes actually change

```
Reproduce: python3 research/momentum-replication/pine_bench.py --fetch
DATA · Yahoo v8 chart API, 1-minute, pre/post included — the same endpoint
       scripts/tape.py uses. Fetched 2026-08-19. 30 symbols · 100,506 bars ·
       11 trading days (2026-08-05 → 2026-08-19). Yahoo keeps 1m for ~30
       days; this window is the maximum the universe allowed.
UNIVERSE · 7 names from the 2026-08-18 Day Trade Dash alert export (the only
       MEASURED scanner rows this repo has: SGLY PFSA WFF XOS HCWB WETO IPST)
       + 23 names worked up in sessions 08-05..08-19 (MSGY JWEL SCKT WXM WYHG
       GENK ELPW STIM TDIC DKI INLF NXTC XHLD ZJYL CLRO ASTC AZI BYAH, EHGO
       YJ TNON BTCT CDTG). Selection is therefore HINDSIGHT-BIASED toward
       names that moved — fine for comparing two engines on the same tape,
       useless as an expectancy estimate.
ENGINE · a Python port of the SHARED decision core of
       knowledge-base/tradingview/ross-fp-v4.pine (V7.5, commit 33bfaab) and
       the operator's V8.0 candidate. It is NOT the Pine: TradingView is the
       only Pine compiler. Both configs run the identical setup detector, so
       porting error cancels in the comparison; absolute numbers inherit it.
```

## What was compared

The V8.0 re-audit candidate differs from V7.5 in four ways a bar-level
simulation can exercise. Everything else it changes (varip rollback zombies,
display/plan chain, alert dedup) alters what the screen *says*, not what
fills, and is out of scope here.

| id | divergence | V7.5 | V8.0 |
|---|---|---|---|
| D1 | same-bar trigger+stop | bracket lands next bar → the position survives an entry bar that also touched the stop | exits pre-staged → stopped the same bar, counted as ambiguous |
| D2 | last-window-bar arming | arms until 11:30 | no arming on the ≥11:29 bar |
| D3 | sizing basis | $100k acct · $200 risk · $25k max position | $2k acct · $20 risk · $2k max position |
| D5 | HOD-retest undercut | any touch keeps the episode | deep undercut kills it |

## Funnel

330 ticker-days considered → 59–62 armed setups → **20 fills in both
engines** (identical entries; only exits and sizes diverge) → 2 session-edge
flattens each. No setup was rejected by the shares≥1 gate under either
sizing, and no arm was placed on a last-window bar.

## Results

| config | fills | W–L | ΣR | cash (own basis) | ambiguous bars |
|---|---:|---:|---:|---:|---:|
| V7.5 | 20 | 2–18 | **−7.66R** | −$1,572.64 | 0 counted (5 occurred) |
| V8.0 | 20 | 1–19 | **−10.55R** | −$249.01 | 5 counted |
| V8 exec + V7.5 sizing | 20 | 1–19 | −10.61R | −$2,161.41 | 5 |
| V7.5 exec + V8 sizing | 20 | 2–18 | −7.60R | −$191.41 | 0 counted (5 occurred) |

The hybrids isolate the cause: **the entire behavioural gap (−2.9R) is D1.**
D2 and D5 fired zero times in 330 ticker-days. Sizing (D3) moved R only
through share rounding (±0.06R) — its effect is cash scale and the
commission finding below.

### D1 in detail — 5 of 20 fills (25%) hit trigger AND stop in one minute

Of the five ambiguous entry bars, three were stopped shortly afterwards
anyway (same −R either way: STIM 08-11, STIM 08-18, CLRO 08-07). Two
changed the outcome:

| trade | V7.5 books | V8.0 books | swing |
|---|---:|---:|---:|
| XHLD 2026-08-17 | +1.50R (T2) | −0.75R (same-bar stop) | 2.25R |
| CLRO 2026-08-10 | −0.15R (later stop) | −0.85R (same-bar stop) | 0.70R |

The XHLD bar, from the fetched tape: 09:34 ET, o 6.160 h 6.190 l 6.055
c 6.142. Trigger 6.17 (prior red-bar high + tick), stop 6.07. The bar
touched both. Whether the low printed before or after the trigger is
unknowable from OHLC — the next bar ran 6.14 → 6.525 and V7.5's surviving
position laddered out at +1.5R, while V8's pre-staged stop books −0.75R.
Neither number is the truth; the truth is tick-order the data does not
carry. **V8's contribution is not that its number is right — it is that it
counts these bars (5) and flags the expectancy as non-portable, where the
V7.5 tester books +1.5R silently.** At 25% of fills, that flag is doing
real work on exactly this tape.

### D3 finding — commission drag at the $2,000 basis

Cash P&L vs nominal R×risk:

| config | nominal ΣR × risk | actual cash | drag |
|---|---:|---:|---:|
| V7.5 ($200 risk) | −$1,532 | −$1,572.64 | ~2.7% |
| V8.0 ($20 risk) | −$211 | −$249.01 | **~18%** |

Same $1/order commission, ten times the relative weight: a stop-out is 2
orders = $2 = 10% of a $20 risk budget before slippage; a full T1+runner
ladder is 3 orders = 15%. This is structural to the $2k rebase, not an
engine defect — but it means the $2k account pays a fixed toll per trade
that the $100k paper basis made invisible. The V8 file's own header does
not mention it.

### Consistency check

Both configs are negative on this tape (2 winners in 20, both engines).
n=20 proves nothing by itself, but it is CONSISTENT with the 894-session
replication (`2026-08-regime-filter.md`): an accurate implementation is
still not an edge. Nothing here contradicts the repo's standing verdict.

## V8.1 rerun — execution parity, and the ghost layer measured

```
RERUN · 2026-08-19 15:08 ET, bars refreshed to that minute (100,823 bars).
        08-19 is PARTIAL: power hour and after-hours missing on the last day.
```

V8.1's execution core is byte-identical to V8.0 (its changes are
display-layer), and the rerun confirms it: **20 fills, −10.55R, 5 ambiguous
— unchanged.** What V8.1 adds is the ghost layer: the same pattern engine
shown outside the clock window with SEEN markers and a plan, order withheld.
The GHOST config measures what that layer would have displayed by opening
the window to 04:00–20:00 and hypothetically trading the extra signals by
the same rules — which the real script never does.

| clock bucket | signals | W–L | ΣR (hypothetical) |
|---|---:|---:|---:|
| PRE 04:00–07:00 | 0 | — | — |
| WINDOW 07:00–11:30 (the real trades) | 20 | 1–19 | −11.15R* |
| LATE 11:30–16:00 (**ghost-only**) | **31** | 5–26 | **−9.47R** |
| AH 16:00–20:00 | 0 | — | — |

\* differs from the real −10.55R because in the GHOST run nothing flattens
at 11:30 — the two SESSFLAT trades ran on and lost more; afternoon positions
also occupy state. The 20 entries are the same.

Three readings:

1. **The clock earns its keep, measured.** The 31 afternoon signals the
   ghost layer shows but refuses to trade sum to −9.47R hypothetical over
   11 days (5 winners, 26 stops). The discipline the ghosts make visible-
   but-untraded avoided roughly 9.5R of losses on this tape.
2. **The operator's CDTG instinct was real — and so is the base rate.**
   CDTG 2026-08-18 fires two afternoon ghosts, 11:45 and 14:08, both
   reaching the 2R target — the exact session the operator traded manually
   while the script showed nothing (the complaint that produced the ghost
   layer). V8.1 would have shown both. The same afternoon tape also
   produced 26 stop-outs elsewhere: the layer's value is showing the
   pattern while the window rule keeps the aggregate from being paid for it.
3. **Zero pre-market ghosts is weak evidence, not proof.** The volume
   gates (2× a 20-bar baseline, $100k/min) rarely pass on thin 04:00–07:00
   tape in this sample. JWEL-class pre-market runs may still produce
   ghosts on their day; this window contained none that qualified.

## V8.2 addendum — the late-join path, measured

Three live defects (CDTG + JZ screenshots, 2026-08-20) produced V8.2: a
LATE JOIN path (the impulse scanner could only see a push on a bar that was
itself the green peak — a machine busy with a trade while the peak printed
came back to IDLE inside the dip and never assessed it), a liquidity
measure that takes the best of 5-bar burst / 20-bar / day average $-per-min
(the 20-bar-only figure called CDTG "too thin, $17.6k/min" 40 minutes after
it traded millions), and the universe banner demoted so it can no longer
replace a live state's verdict.

Late-join, added to this harness and rerun: **+1 fill inside the
07:00–11:30 window over the full 11 days** (XHLD 08-17 09:40, −0.18R);
ΣR −10.55 → −10.73, nothing else moved. On this tape the path is
near-neutral on P&L — its effect is coverage: dips that printed while the
machine digested a previous trade are now assessed (and ghost-flagged when
the clock refuses, which is where the CDTG 13:30 miss actually lived).

## What this benchmark could not check

- **Tick order** — the entire D1 question. Only broker-grade tick data or
  live forward-running settles it; 1m OHLC cannot.
- **The Pine itself** — this is a Python port of the shared core. State
  machine parity with the actual scripts is asserted, not proven; neither
  V7.5 nor V8.0 has been compiled since V5.x.
- **Intrabar/display divergences** — varip rollback, zombie states, ghost
  signals, plan chain: invisible to bar data by construction.
- **Halts** — Yahoo omits empty minutes; LULD halts on these names (MSGY
  08-14) appear as gaps the fill model steps over optimistically.
- **Scanner gates** — float, daily RVOL, news: off-chart in both engines,
  not simulated.
- **D2/D5** — zero occurrences here is weak evidence of rarity, not proof.
- **The last day** — the V8.1 rerun's 08-19 data ends 15:08 ET; that day's
  late/AH buckets are incomplete by construction.

## Verdict

MANUAL REVIEW of two findings before merging V8:

1. **D1 is the whole behavioural difference and it is common** (25% of
   fills). V8's conservative floor plus the ambiguity counter is the more
   honest backtest; keep it. Anyone comparing V8 backtests to earlier V7.x
   numbers must expect ΣR to drop for accounting reasons alone — on this
   tape, −2.9R of the gap is bookkeeping policy, not strategy change.
2. **The $2k rebase imports ~10–15% fixed commission drag per trade** that
   the header does not disclose. Worth a header line — at $20 risk the
   round-trip toll is a tenth of the budget before the market moves.

Paper only. 20 fills; a comparison of accounting policies, not an
expectancy measurement.
