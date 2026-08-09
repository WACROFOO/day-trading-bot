# Order-flow scalping — a second, separate method

**Self-contained. Nothing here relates to anything else in this repository.**
Different instrument, different timeframe, different session, different evidence
base. It is kept in its own directory so nothing in it can be mistaken for, or
silently merged into, other work. It intentionally references no file outside
this folder, and no file outside this folder references it.

| | |
|---|---|
| trader | Fabio Valentino — futures scalper |
| credential | stated top-three, Robbins World Cup futures division, 500%+ / 12 months (**unverified here**) |
| source | one video, `https://youtu.be/tvERE-Beu2U`, Chart Fanatics, 2025-09-21 |
| length | 3h34m · 43,007 words · 5,568 caption lines |
| instrument | Nasdaq **futures** (NQ/MNQ) — never single stocks |
| session | New York only |

## Files

| file | what it is |
|---|---|
| `MODEL.md` | the dissection — the three steps, the vocabulary, and what makes it hard to encode |
| `PLAYBOOK.md` | the executable form: pre-conditions, trigger, stop, targets, management, and a test order |
| `TRANSFER-TO-EQUITIES.md` | **can this run on cash stocks in market hours?** what ports, what degrades, what blocks it |
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

**One document. One session. One trader.**

There is nothing here to cross-check against — no second session, no dated
series, no published trade log, no independent account of the same rules. When a
method is described only once, there is no way to tell a firm rule from an
offhand remark, and no way to catch a number that was misspoken.

Treat every figure in this directory as single-sourced until a second source
exists. That is not a formality: the stop-placement rule, the +20–30% win-rate
claim and the 500% return all rest on the same single testimony.

Two further limits, one stated by the author:

- **Step three is not automatable**, by his own account [00:11:00].
- **Futures are leveraged**, and this directory contains no sizing rules at all.
  Work out contract size and risk yourself before trading anything.

And the standing prior for any trading method: most do not survive honest
out-of-sample testing. Assume this one has not been tested, because it has not.

## To extend this

Adding a second and third source is worth more than any analysis of this one.
Until then `PLAYBOOK.md` closes with a test order whose first three items need
**no order-flow data at all** — the out-of-balance filter, the stop-placement
tweak, and the previous-daily-high target are all testable on ordinary bars.
