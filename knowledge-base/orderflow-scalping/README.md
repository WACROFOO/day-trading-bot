# Order-flow scalping — a second, separate method

**This is not the Ross Cameron corpus.** Different instrument, different
timeframe, different session, different evidence base. It is kept in its own
directory so nothing here can be mistaken for, or silently merged into,
`../strategies/`.

| | |
|---|---|
| trader | Fabio Valentino — futures scalper |
| credential | stated top-three, Robbins World Cup futures division, 500%+ / 12 months (**unverified here**) |
| source | one video, `https://youtu.be/tvERE-Beu2U`, Chart Fanatics, 2025-09-21 |
| length | 3h34m · 43,007 words · 5,568 caption lines |
| instrument | Nasdaq futures |
| session | New York only |

## Files

| file | what it is |
|---|---|
| `MODEL.md` | the dissection — the three steps, the vocabulary, and how it differs from the Ross corpus |
| `PLAYBOOK.md` | the executable form: pre-conditions, trigger, stop, targets, management, and a test order |
| `transcripts/tvERE-Beu2U.txt` | deduplicated timestamped captions, with a provenance header |

## The method in six lines

1. Trade only when the market is **out of balance** — he claims this filter
   alone is worth 20–30% of win rate.
2. Validate a level using a **volume profile drawn across the swing that broke**;
   low volume nodes are the reaction levels.
3. The trigger is **aggression** on the footprint, not a candle.
4. Enter on **break *and* test**. Never the break alone.
5. Stop goes beyond the **aggression cluster**, and **1–2 ticks inside** the
   obvious high, to be filled before the stop-run accelerates.
6. First target is the **previous daily high**; move to break-even when CVD
   confirms; scale when the tape turns.

> *"When there is direction, location and aggression, your ability to predict is
> zero but your ability to read is 100."* — [00:11:29]

## Evidence weight — read this before trusting any of it

The whole method of this repo is that a claim's register and sample size decide
how much it is worth. On that scale, this directory is **thin**:

| | Ross corpus | here |
|---|---|---|
| documents | 2,680 across four registers | **1** |
| registers | teaching / recaps / streams / blog | one live session |
| cross-checks possible | register splits, date stamps, P&L statements | **none** |

There is no lopsided register split to find here, because there is only one
register. The `../../research/momentum-replication/reports/2026-08-parameter-audit.md`
method — read the same rule across four registers and find the type errors —
**cannot be run on this material.** Treat every number below as single-sourced
until a second source exists.

Two further limits, both stated by the author or by this repo:

- **Step three is not automatable**, by his own account [00:11:00].
- **Futures are leveraged.** No sizing tool in this repo transfers; `scripts/size.py`
  assumes cash equities and a €500 account.

And the standing prior: this repo's replication of a far better-documented
strategy came out **negative over 894 sessions**
(`../../research/momentum-replication/reports/2026-08-regime-filter.md`).

## To extend this

Adding a second and third source is worth more than any analysis of this one.
Until then `PLAYBOOK.md` closes with a test order whose first three items need
**no order-flow data at all** — the out-of-balance filter, the stop-placement
tweak, and the previous-daily-high target are all testable on ordinary bars.
