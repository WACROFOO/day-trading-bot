---
name: extended-hours
description: Ross Cameron's pre-market and after-hours trading mechanics — sessions, why extended-hours orders reject, limit-plus-offset order construction, hotkeys, leverage and options restrictions, and where the edge lives (07:00–09:30 ET). Use for any question about trading outside regular hours, orders not filling pre-market, after-hours moves, or extended-session setup.
---

# Extended-hours trading — the mechanics

Source: Ross Cameron's pre-market/after-hours guide (2026-08 episode,
transcript in session log). His measured numbers, not folklore.

## Sessions (all ET; France = ET + 6h in summer)

| session | ET | France | notes |
|---|---|---|---|
| pre-market | 04:00–09:30 | 10:00–15:30 | most retail brokers only allow from **07:00** |
| active PM | **07:00–09:30** | **13:00–15:30** | volume surges at 07:00 — the real window |
| regular | 09:30–16:00 | 15:30–22:00 | LULD halts active ONLY here |
| after hours | 16:00–20:00 | 22:00–02:00 | he is **measured not net profitable here** |

His P&L split: 2016–2019, ~$111k of $1.6M came pre-market. From March 2020
the distribution moved — the day now starts at 07:00 and peaks 09:00–10:00.
The cause: stocks stopped waiting for the bell. News → instant move.

## Order mechanics — why your order rejects, and what works

Extended hours accept **limit orders only**:

- **No market orders** (reject or sit until 09:30)
- **No stop orders of any type** — banned because thin tape makes stop
  hunting trivial; a light-volume wick would cascade them. Your stop is
  therefore **mental or hotkeyed**, never resting
- **GTC limit orders do not participate** — they sit off-market and fire at
  09:30. This is also why gappers dump at the bell: every resting GTC sell
  placed above yesterday's range executes at once
- **Time-in-force must be the extended one** (thinkorswim: `EXT`;
  Lightspeed: plain `DAY` already works extended; Webull: tick "extended
  hours"). Wrong TIF = the silent no-fill everyone hits first

**The fill trick: limit with an offset.** Buying "at the ask" fills only the
displayed ask size. To actually get in, place the limit **10–15¢ above the
ask** (selling: below the bid) — it sweeps the levels up to your cap and
fills immediately. That's the whole secret: `buy = ask + offset`,
`sell = bid − offset`, extended TIF.

Hotkeys, his layout: buy-ask+offset · sell-bid−offset · sell-ask (to sit on
the offer) · profit-target at +N¢ · scale-out by % where the platform allows.

## Leverage and instruments

| | pre-market | after hours |
|---|---|---|
| leverage | **allowed** | **NO** — margin closes by 16:00 or is auto-liquidated |
| options | none | none |
| stops | none | none |

The 16:00 forced-liquidation is why short squeezes often ignite 15:30→AH:
leveraged shorts *must* cover into the close.

## Why the tape behaves differently

- **HFT algos are largely absent** — on a book map, layered orders appear at
  09:30 like a light switch and vanish at 16:00. Fewer algos + fewer traders
  = cleaner, bigger moves on real news
- **They also turn off during volatility** even in RTH — algos profit in
  compressed ranges; a breakout past ~1 standard deviation and they leave
- **No LULD halts** outside 09:30–16:00 — his stated reason for preferring
  pre-market on cheap stocks (a sub-$0.75-prior-close name halts every 15¢
  in RTH but trades freely pre-market)
- The **first pop on news is keyword algos** reading the wire (headlines
  release at round times — 8:00, 8:30, 9:00). His entry is never the pop:
  wait for the **micro pullback** — first dip after the pop, buy as it
  pushes back through, tape green, immediate resolution expected

## The volume tell

PM volume highest, declining after the open = the move is behind you (WXM,
OFAL). Also: a move that starts AH often gets its second wave at 07:00 when
retail brokers open.

## Chart setup

Shade pre-market and after-hours differently (his: dawn yellow / dusk blue).
Daily charts stay RTH-only — PM/AH highs and lows do NOT print on daily
levels, so a "break of yesterday's high" pre-market must be read off the
intraday chart.

## Repo integration

- `./now` phases already treat 07:00–09:30 as live; scan from 13:00 France
- `tape.py` halt detection only means anything 09:30–16:00 — an "empty"
  pre-market minute is thin tape, never a halt
- After hours: per his own measured stats, the answer to "should I trade
  AH?" is **no** — watch, note levels for the 07:00 wave, don't trade

Paper only. His results are not typical, and nothing here changes the
894-session negative expectancy of the replication.
