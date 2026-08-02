# The ISPO stream: 4½ hours of him against his own rulebook

`YuNvqwJftVY`, 2022-02-17, the longest live session on the channel. Watched as
a case study for one question: **did he apply his documented strategy?** The
answer is: the *risk discipline* yes, almost to the letter — and four of the
*rules*, no. The divergences are the valuable part, because each is a place
where the spec we implement describes his teaching, not his trading.

## The frame the title hides

- The 500% squeeze mostly happened **before the camera was on**. He opens by
  admitting it: *"a surprise 300% short squeeze on ISPO, I wasn't expecting
  it... I made a little on it, not a lot"* [0:00:35] — **$3,986** on the move
  itself: *"it was hard to trade"* [0:03:20], *"no way, I can't get in up
  here"* [0:02:43], halt after halt.
- The stream is the **afternoon**: morning P&L $12,343 stated at the open of
  the video; *"it's a little bit past noon"* [0:37:15]; power hour discussed at
  [3:03:24]. He finishes around **$78,000** [4:29:23] — the afternoon
  continuation, not the famous move, is where the day's money came from.
- Context he volunteers: *"these types of days would be $100–200k green days
  for me, but I haven't had a $100k day since the end of 2021, I'm trading a
  little bit [smaller]"* [0:36:21]. February 2022 was a cold streak and his
  size shows it — 100–500 shares on the $45–75 names.

## Where he followed the documented strategy exactly

| rule as documented | as executed |
|---|---|
| extension → cut size, never skip | *"clearly I'm chasing it, I just have to go with smaller size"* [0:03:45] |
| `stop_typical` $0.08–0.10 | *"10 cents stop on this and hold the rest"* [3:03:24] |
| starter → add ladder | *"small size... I can always add if I see"* [0:19:12]; adds at 47.50 → 48.50 → 51 |
| scale out into strength, add back | *"added at 48, took the gain at 66, watching the add at 75"* [1:45:27] |
| don't hold size through halts | *"I don't really want to hold big size during the halt"* [0:09:39] |
| five-pillar rejection of unknowns | RGV: *"don't know what the float is... leaving it alone"* [1:41:56]; CHIH: *"63M float, recent IPO, leave it alone"* [3:46:25] |
| protect gains as price extends | *"set my max share size... add profit without risking giving it all back, lowering share size as we climb"* [0:54:52] |

## Where his practice contradicts the spec we implement

**1. The session window.** `PARAMETERS.md` §2: prime window 9:30–10:30, hard
stop 11:30, *avoid 11:30–15:00*. This entire stream is 12:00–16:00, and it
produced ~$65k of the day's ~$78k. The real rule is conditional: *midday is
dead unless a monster is live* — and then the clock rule is suspended. Our
engine's `HARD_STOP` has no such override.

**2. Halt levels are targets.** *"67.63 is the halt level, so that's the
target right now"* [1:13:54]; adds keyed to *"halt level moved up"* [1:19:40];
next objective repeatedly quoted as the LULD up-band [0:52:31, 1:36:40,
2:54:36]. The spec — and our engine — treat halts purely as risk. He treats
the **up-band as the magnet** on a squeezing stock.

**3. He buys resumptions, with orders placed during the halt.** *"about 30
seconds to resumption, I'll put my order for 500 shares at 45.20"* [0:14:27];
*"held small size into the halt, then looked for dip and rip on resumption"*
[0:43:36]; and he reads the indicative price live: *"it's showing a 41
resumption, which is bullish"* [0:26:21]. Our only halt rule is a veto on
resumed-lower. His halt playbook is an entry strategy with three moving
parts: indicative price read, pre-placed order, small size.

**4. He anticipates.** `confirm_before_entry: true — no anticipating` (n=47,
from the teaching corpus). Live: *"bought the dip at 61.98, **looking for**
the first candle to make a new high through 62.63"* [1:08:20]; *"buying the
dip 103.50, **now looking for** the break of 107"* [2:11:19]. The
confirmation candle is his *target*, not his entry. On a halt-cascading
$50–100 stock, waiting for the break means buying the halt — the doctrine is
for beginners, the anticipation is the practice.

**5. Sympathy trading.** ANGH is traded explicitly as *"sort of a proxy, it's
lower price"* for ISPO [2:06:43]; *"one pops, the other one pops"* [3:06:01];
he watches for both to break together. No concept of a sympathy name exists
anywhere in our scanner or spec.

Also on display, minor but real: broker-side risk checks refusing his orders
twice ([0:42:47], [2:17:32]) — an external guardrail our model has no
equivalent of — and the economics of the other side: shorting 10,000 ISPO
would have cost **$16,500 in borrow fees** [2:30:09], which is why squeezes
like this happen at all.

## What a beginner should take from the video

1. **The monster is not the trade.** He made $4k on the 500% move and ~$65k
   on the boring afternoon continuation — dips bought at support, cents-away
   targets, adds only after profit was banked.
2. **Size is the universal answer.** Chasing? Smaller. Extended? Smaller.
   Cold streak? Smaller. Near a halt? Smaller. Every uncertainty in the
   session was answered with share count, never with a wider stop.
3. **Halts are the terrain, not an anomaly.** Halt clock (5:00 from
   11:45:24 → 11:50:24 [0:13:14]), indicative resumption reads, up-band
   targets. On these names the LULD mechanics *are* the market.
4. **He states the loss before the trade.** Every add has a number attached
   before it fills. The narration is a running risk ledger, not commentary.

## Standing caveat

One session, from his cold streak, on his own channel, titled for the
squeeze. It shows *what he does*; it cannot show how often it works.
