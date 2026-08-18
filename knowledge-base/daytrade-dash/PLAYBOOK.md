# Day Trade Dash — the session, block by block

```
SCOPE · THE PLATFORM ONLY. Which widget, which column, which colour, at which
minute. Entries, stops, targets and sizing are NOT here — those are
knowledge-base/strategies/FILTERS.md and knowledge-base/tradingview/ross-fp-v4.pine.
A scanner row is a name worth charting. It is never a trade.

SOURCES · three classes, never blended:
  VENDOR    warrior-support/stock-scanners-day-trade-dash/19000117763-scanners-
            how-to-load-use-them-in-the-chat-room-wt.md — Warrior's own help
            desk, "Modified Thu, Jan 8, 2026". Primary for platform BEHAVIOUR.
  CORPUS    transcripts, cited by video id + timestamp. Primary for what HE
            does with it. Mapping in strategies/SCANNERS.md.
  MEASURED  daytrade-dash/captures/2026-08-18-momo-alerts.csv — 301 alert rows,
            04:02–05:42 ET, one session. The only rows anyone here has counted.

! NO NUMERIC THRESHOLD IS DISCLOSED ANYWHERE IN ANY OF THE THREE. The server
  config is bearer-protected and the support page describes behaviour without
  ever giving a filter value. Nothing below is a threshold. Where a number
  appears it is a CLOCK time, a vendor-stated window, or a measured bound.

! TIMES ARE ET, France in the second column. FR = ET + 6h in summer. The
  offset breaks for one week each autumn: EU ends DST 25 Oct 2026, US 1 Nov
  2026, so 26–31 Oct is ET + 5h. Check before trusting the FR column then.
```

---

## Boundaries — what this document changes, and why

Four repo documents disagreed about the shape of the day. This resolves them
against `strategies/PARAMETERS.md` §2, which is the only one carrying sample
counts. Stated up front so a reader who disagrees can see exactly what moved.

| conflict | what the documents said | resolved | why |
|---|---|---|---|
| money window ends | 10:30 + late window to 11:30 (`DAILY-ROUTINE-FR.md`) vs 11:00 (`trading-day` skill, `now.py`, `CLAUDE.md`) | **prime 09:35–10:30 · typical close 10:30–11:00 · outer edge 11:30** | both were half-right. `PARAMETERS.md` §2: `prime_window` 09:30–10:30 (n=44), `session_typical_close` 10:30–11:00 "the 90-minute mark", `session_close` 11:30 "outer edge, not the centre" (n=16). He frames it as a **duration**, not a clock time |
| pre-market starts | 04:00 (`now.py` has no 07:00 boundary at all) vs 07:00 (`FILTERS.md`, skills) | **platform opens 04:00 · the session starts 07:00** | both are true of different things. Vendor: scanners viewable "as early as 4 AM EST". Corpus: `07:00` named 78× against 36× for `09:30` across 36 July recaps (`research/momentum-replication/reports/2026-07-challenge.md`) |
| watchlist locks | 09:00 vs 08:30 ET | **08:30 build, 09:00 lock** | not actually a conflict — one is when you draft, the other when you stop adding |
| account basis | €500 / €10 risk vs $100k paper / $150–500 | **NOT RESOLVED — flagged** | that is the operator's decision, not a documentation one. Sizing is out of scope here anyway |

`premarket_start` carries a warning worth repeating: the 07:00 rule **reversed
direction**. In 2017 he said *"I've traded pre-market maybe half a dozen times
in the last year"*; by July 2026 the pre-market is where the challenge lives.
Any pre-market rule sourced from a 2017–2019 article is stale.

**Two eras coexist in the corpus and this document commits to neither
silently.** The classic shape — 09:30 start, first 90 minutes — is what
`PARAMETERS.md` §2 measured (n=44) and what the pre-2020 material says. But his
own current description is **earlier**:

> *"my most lucrative hours … are between **8:00 a.m. and 10:00 a.m.**"* —
> `warrior-blog/terminology/best-time-to-day-trade.md`, lastmod 2025-11-18

and post-2020 he describes the distribution as *"from 7 to 8 to 9 and then a
little less to 10 and to 11"* (`PjVivCcM1B0` @00:23:00). The blocks below keep
the measured 09:35–10:30 prime because that is the one with a sample count
attached, and flag that **his stated peak now starts 90 minutes earlier**. If
the two ever have to be reconciled it should be by measurement, not by
preferring the newer quote.

---

## Before the day — the layout, once

| item | detail | source |
|---|---|---|
| windows | max **3 separate browser windows**, unlimited widgets inside the main one | VENDOR |
| data health | the Scanners button carries a **green dot** = live data. Red = market-data problem, scanners may be stale | VENDOR |
| audio | available on **Alert scanners only**, never List scanners. Bell icon top-right; crossed-out red = off, green = on | VENDOR |
| his audio set | *"Select all strategies except the Medium Float scanners"* | VENDOR |
| update rates | **List scanners 30 s · Alert scanners every second** | VENDOR |
| agreements | market-data agreements are signed **separately** for scanners and for the Sim | VENDOR |
| history | **Scanner History Widget** holds the last **6 months**, one widget at a time | VENDOR |

**His actual window set, in the order he opens them** — `w97KlUrVDk0`
@00:48:44–00:49:03: **Top Gainers → Small-Cap HOD Momentum → Running Up → Halt
Scanner.** Four, not three. He names three as the daily set (@01:01:11) and
physically opens four; the Halt Scanner is the one that gets forgotten in the
telling and never in the layout.

**A divergence kept rather than resolved:** on video he says audio is on for
**two** strategies — *"I only have the audio alerts enabled for low float and
squeezing up 10 in 10 minutes"* (`yg5E_mqGFGg` @00:19:36). The vendor page says
all except Medium Float. Both are sources and neither is obviously stale. They
agree on the thing that matters: **Medium Float is the tier he does not want
interrupting him.**

---

## 04:00 ET · 10:00 FR — the platform opens

| | |
|---|---|
| **primary** | nothing |
| **secondary** | Top Gappers, if you are awake |
| **looking for** | nothing actionable |
| **action** | none. The platform is available from 04:00 (VENDOR) but liquidity is not |
| **stop signal** | — |

`DAILY-ROUTINE-FR.md` calls this *"nothing to do, volume too thin"* and that
survives. The measured export opens at 04:02 with WETO already alerting, so
names **do** print here — but 7 symbols in 94 minutes is a trickle, and the
first alert of the day is not the same object as a tradeable move.

---

## 07:00 ET · 13:00 FR — the session actually starts

| | |
|---|---|
| **primary** | **Top Gappers** + **Ross's 5 Pillar Scan List** |
| **secondary** | Running Up alert (news hour), Former Momo |
| **looking for** | the leading gappers, each with a **red or orange flame** |
| **action** | first real read. Build the raw candidate list. Check the flame colour on every name you keep |
| **stop signal** | none — this block is discovery, not decision |

**He sits down at 06:30, not 07:00** — *"when I'm in Eastern Standard Time I
usually sit down around 6:30 so I can be watching the market starting at about
7"* (`PjVivCcM1B0` @00:20:28). And the first scanner of the day is not on the
desk: *"this **top gainer scanner is the first scanner that I look at every
morning**. So even when I'm still laying in bed, I grab my phone and I check
these scans on my phone… always sorted by leading gain"* (`w97KlUrVDk0`
@00:49:16).

Why 07:00 and not 04:00 — *"most retail Brokers don't allow trading before
7 a.m. so 7 a.m. to 9:30 a.m. is sort of right now our most active pre-market
session"*, and *"typically right at 7 a.m. you'll see a surge of volume come
in"* (`PjVivCcM1B0` @00:18:41, @00:19:10).

This is the highest-leverage block in the day and the one most easily slept
through. `07:00` is named **78 times against 36 for `09:30`** across 36 July
recaps; `pre-market` **161 times against 9 for "the close"**
(`research/momentum-replication/reports/2026-07-challenge.md`). He names 07:06
and 07:15 specifically.

**Running Up belongs here, by his own preference:** *"Ross likes to watch this
during the news release hours (7 AM, 8 AM, 9 AM ET)"* (VENDOR — the support
article; this binding is **not** in `SCANNERS.md`).

It is not merely faster than HOD Momo, it hunts a different state:

> *"the running up scanner tells me when a stock is squeezing up right now
> **even if it's below its high of day. In fact, it has to be below the high of
> day.** Otherwise we'll put it on the high of day momentum scanner."*
> — `w97KlUrVDk0` @01:00:52

So the two are complements, not alternatives: Running Up catches the move
**before** it makes a new high; HOD Momo catches it at the high. In the
pre-market, where new highs are sparse, Running Up is the one that speaks.

**News lands at the top AND bottom of the hour**, which makes 07:30 and 08:30
live too:

> *"news usually comes out at the top and the bottom of the hour. So 7 a.m.
> news comes out and a stock has news and it squeezes up. 7:15, 7:25, it's
> moving higher. And at 7:30, another stock comes out with news and the headline
> on that other one is a little juicier… now stock number one, people abandon
> that completely and switch to stock number two."* — `w97KlUrVDk0` @01:42:07

That last clause is also an **exit** signal, not just a discovery one: your name
being abandoned for a juicier headline is the platform telling you the crowd
left.

**Flame reading, from the vendor's own table** (column header: *"Age of
Headline"*):

| indicator | age |
|---|---|
| 🔴 red | 0–2 hours |
| 🟠 orange | 2–12 hours |
| 🟡 yellow | 12–24 hours |
| none | over 24 hours |

*"I like to see stocks with red and orange Flames which means I'm hopefully
trading the very beginning of a breaking news squeeze"* — `oxob0x0Xz7s`
@00:58:06.

**Two mechanical traps here, both vendor-stated:**
- On alert scanners the flame **can lag its own alert by up to 5 minutes**. A
  fresh alert with no flame may still be a news move. Do not judge catalyst on
  the first paint.
- **The 5 Pillar scanners do not filter news at all** — *"we do not currently
  filter out whether a stock has news or not… you will want to ensure that the
  stock also features a flame indicator."* The fifth pillar is manual even on
  the scanner named after the five pillars.

---

## 08:00 ET · 14:00 FR — the press-release wave

| | |
|---|---|
| **primary** | **Running Up** alert + Top Gappers refresh |
| **secondary** | News Room / Squawk audio |
| **looking for** | new names entering, and **flames turning red** on names already on your list |
| **action** | re-scan. A name that was yellow at 07:00 and is red now has fresh news |
| **stop signal** | — |

The 08:00 ET press-release wave is the second of the three news hours the
vendor names. A flame that **changes colour** is the cheapest catalyst signal
the platform gives, and nothing in the repo tooling reproduces it.

---

## 09:00 ET · 15:00 FR — the list locks

| | |
|---|---|
| **primary** | **Ross's 5 Pillar Scan List** |
| **secondary** | Top Gappers, Low Float Top Gainers |
| **looking for** | which of your names still qualify — and which have faded |
| **action** | **stop adding names.** Draft from 08:30, closed at 09:00 |
| **stop signal** | a name >25% off its pre-market high is dead (`FILTERS.md`) |

`FILTERS.md` is blunt about late additions: distrust anything discovered after
09:00. The list you take into the bell should be the list you built before it.

**Top Gappers stops updating at 09:30** (VENDOR). If you want a gap view after
the bell it must come from Top Gainers or Change Since Open, which keep running.

---

## 09:30 ET · 15:30 FR — the bell

| | |
|---|---|
| **primary** | **Small-Cap HOD Momo** (alert) |
| **secondary** | Halt Scanner — LULD halts begin existing at this second |
| **looking for** | which of your names alerts first, and how often |
| **action** | our rule: **hands off five minutes.** His practice: see below |
| **stop signal** | both leaders opening below their open = sit out |

**The 5-minute blackout is OUR rule, not his, and the playbook should not
pretend otherwise.** `PARAMETERS.md` §2 carries `entry_blackout_end` 09:35 with
n=44 rule statements behind it, but on video he says the opposite:

> *"as early as 9:30 and one second… and I've been up to [a] thousand dollars in
> the first five minutes more times than I can count. **I trade aggressively at
> the open.**"* — `txWaMpSzHhM` @00:38:51

What a live stream actually shows is **conditional** patience rather than a
blackout. On `ZfwTJAMLroA` he is three minutes in @01:02:34, then @01:02:53
*"it's 9:33, so at this point I'm sitting and waiting. 9:35, I'm still sitting
and waiting"*, still flat at 09:42 @01:04:45 — because both his primary names
opened below their open. And @01:03:07, decisive: *"you can see down here some
stocks are hitting my scanner"* — **the scanner keeps firing and he declines.**

So the honest instruction is not "no orders for five minutes". It is: **the
scanner firing is not permission.** If you want a hard blackout, keep ours and
know it is ours.

What is measured rather than folklore is that the gap is spent by the bell.
`research/momentum-replication/reports/2026-08-short-hold.md`: the **09:29 → 09:30 leg alone is −0.20% mean,
−1.50% median, positive only 34% of the time** — *"whatever the gap has to
give, it has largely given by 09:30."*

The Halt Scanner matters from here and not before: **LULD halts only exist
09:30–16:00**.

---

## 09:35 ET · 15:35 FR — prime window opens

| | |
|---|---|
| **primary** | **Small-Cap HOD Momo** (alert, audio on) |
| **secondary** | Squeeze 5%/5min and 10%/10min, Halt Scanner |
| **looking for** | **repeat alerts on one symbol**, and new highs of day |
| **action** | trade the plan you wrote before the bell |
| **stop signal** | your daily stop, or three losses |

**This is where the stacking rule earns its keep.** The single most useful
thing the platform does is not any one scanner:

> *"a stock hitting scanners more and more times is definitely a good indicator
> that it's got some momentum"* — `yg5E_mqGFGg` @00:17:02

Measured: in the 08-18 export, SGLY produced **154 alert rows and WETO 2**.
The feed is chronological and carries no ranking, so **re-alert frequency is
the de facto ranking** — and it is emergent, not computed. Count the rows.

He states the negative case as clearly as the positive one: *"KSPN hit the low
float former momo stock but **only triggered it once**… probably not going to
trade it"* (`yg5E_mqGFGg` @00:16:47). **One alert is not a candidate.**

The six Small-Cap HOD sub-strategies are qualification lanes sharing one
trigger. Measured on that export: `event` was `New High` on **301/301 rows**,
and against continuous 1-minute bars the alert bar set a new high of day in
**299/299** measurable cases versus a **4.7%** base rate. The vendor states the
same thing independently — the parent scanner *"Scans for New HOD price alerts
on above-average momentum."*

**Former Momo runs looser on purpose**, and a replica that applies one
threshold set to all lanes destroys it:

> *"low float former momo stocks, when they pick up, they can start moving
> really quickly, and so for that reason I want to see them a little sooner…
> some of the filters are adjusted a little bit so I could see it quicker. I
> don't do that for every type of stock because otherwise you start getting a
> lot of false alerts."* — `yg5E_mqGFGg` @00:16:03

Measured: Former Momo fired at daily RVOL **2.13** on IPST — the lowest value
anywhere in the export.

---

## 10:30 ET · 16:30 FR — prime ends, the 90-minute mark

| | |
|---|---|
| **primary** | HOD Momo, unchanged |
| **secondary** | Large Cap Highest Volume (his stated micro-scalp use, VENDOR) |
| **looking for** | whether anything is still making new highs |
| **action** | reduce. Existing positions managed, new ones need to be better |
| **stop signal** | alerts thinning across all lanes = the day is done |

> *"For me, I'm in the zone… for most days, it's from **9:30 until 10:30 or
> 11:00**. So right around that **90 minute mark**."*
> — `warrior-blog/recaps/starting-off-september-grateful-334.md`, via `PARAMETERS.md` §2

`PARAMETERS.md` notes the consequence plainly: **a backtest holding to 11:30
trades 30–60 minutes he is not in.**

---

## 11:00 ET · 17:00 FR — wind-down

| | |
|---|---|
| **primary** | Halt Scanner |
| **secondary** | — |
| **looking for** | nothing new |
| **action** | manage what is open. New entries only on something exceptional |
| **stop signal** | 11:30 |

---

## 11:30 ET · 17:30 FR — hard stop

Flat. `session_close` 11:30 is the **outer edge, not the centre** (n=16).

---

## 11:30–15:00 ET · 17:30–21:00 FR — the dead zone

| | |
|---|---|
| **primary** | nothing |
| **action** | **no trades.** `midday_avoid` 11:30–15:00 (`PARAMETERS.md` §2, n=16) |

Marked dead rather than left blank, because a blank invites filling.

Two reasons beyond the P&L, both his own. The population changes — *"midday
trading is dominated by traders that have lost in the morning and they're
aggressively [trying to make it back]"* (`txWaMpSzHhM` @00:41:24). And **you**
change: the corpus carries a claim that *"decision fatigue accumulates with each
scanner alert throughout day; by noon, accuracy declines significantly"*
(`EzHEGVb_9-c`). That is a scanner-specific argument for closing the widget, not
just for not clicking.

**One documented exception, and it is not a loophole.** The ISPO stream runs
12:00–16:00, entirely inside this zone
(`research/momentum-replication/reports/2026-08-ispo-stream.md`). The reading recorded there: midday is dead
**unless a monster is already live**, and then the clock rule is suspended
rather than bent. If you are asking whether today qualifies, it does not.

---

## 15:00 ET · 21:00 FR — power hour

| | |
|---|---|
| **primary** | **Top of Trend** |
| **secondary** | Top Gainers, Large Cap Highest Volume |
| **looking for** | stocks near the top of their daily range with momentum intact |
| **action** | **watch only** for this account |
| **stop signal** | — |

The vendor is explicit that this scanner is built for this hour: Top of Trend
*"tracks stocks that are showing strength and momentum while being near the top
of their daily range… great to have up later in the day during Power Hour from
3–4 PM ET."*

It is in the playbook because the platform supports it and you will see it.
**Watch-only is not caution here — he has the number.**

> *"Afternoon trading loss: $177,000 total profit but **$26,000 lost to
> afternoon trading**"* — claims from `jvC5GUHPl1I`; the same month is described
> elsewhere as *"$177,000 clean"* had he not traded the afternoon.

> *"afternoons cost me money… I was consistently losing money trading in the
> afternoon, and **'Power Hour' never felt powerful for me**. That taught me to
> know when to stop."* — `warrior-blog/terminology/best-time-to-day-trade.md`

And a worked example of the failure: *"I made the mistake of coming back for
the power hour. I ended up giving everything back and then some. In just a few
trades, I spiraled from being up $5k to **down $7,500**"*
(`warrior-blog/recaps/7-5k-in-2-hours-of-day-trading.md`).

Note also that his own broker breakdown by 30-minute bucket puts *"the bulk of
my profit, between 9:30 and 10:00 AM… **Every time I traded in the afternoon, I
lost money.** That's $10,000 right there in losses"*
(`warrior-blog/reviews/january-2020-in-review.md`).

Trading this hour would be a new strategy, and the one person with a track
record in it stopped.

---

## 16:00 ET · 22:00 FR — after hours

| | |
|---|---|
| **primary** | **After Hours Top Gainers** (16:00–20:00, VENDOR) |
| **secondary** | Top Losers |
| **looking for** | tomorrow's names, not today's trades |
| **action** | note levels. Build the overnight list |
| **stop signal** | — |

The scanner is genuinely time-boxed, not merely preferred: *"this **starts
working at 4 pm**… it doesn't work during regular trading hours, **it is just an
after hours scanner**"* (`yg5E_mqGFGg` @00:11:18).

`FILTERS.md`: no trades 16:00–20:00 — *"doesn't look like I'm net profitable
trading after hours"* (`PjVivCcM1B0` @00:23:06). Watch, note levels, **trade the 07:00 wave instead**. An
after-hours move often gets a second wave at 07:00, which is the block that
pays.

**Halts do not exist here, and that is a feature he names.** *"there's no halts
pre-market, there's no halts after hours, but during regular trading hours
there are halts"* (`5aWoZdbXJrA` @00:47:03), and `FILTERS.md` carries his
preference directly: *"I actually prefer trading in the pre-market session when
there's no halts."*

The Halt Scanner is therefore a **09:30–16:00 instrument only**, and so is
halt detection in any of our tooling — an empty pre-market minute is thin tape,
never a halt. Bands are keyed to the **prior close** and never update intraday:
under $0.75 → 15¢, $0.75–3 → 20%, over $3 → 10%. That is why the penny tier is
tradeable pre-market and hostile after the bell.

---

## 20:00 ET · 02:00 FR — close

Nothing runs. The next decision is 07:00.

---

## The full scanner inventory, by when it is useful

| scanner | class | when |
|---|---|---|
| Top Gappers (top 100) | list | 07:00–09:30 — **freezes at 09:30** |
| Ross's 5 Pillar Scan List / Alert | both | 07:00–09:30, then as a filter |
| Penny-Top Gappers (<$5) | list | 07:00–09:30 |
| Ross's Top Gappers · Large Cap · Large Cap Earnings with Gap | list | 07:00–09:30 |
| Top Gainers / Top Losers | list | **all day** |
| Low Float Top Gainers | list | all day |
| Penny Top Gainers / Losers | list | all day |
| After Hours Top Gainers | list | 16:00–20:00 |
| Recent IPO Top Moving | list | pre-market context (last 90 days) |
| **Recent Reverse Split** | list | pre-market context — last 30 days, **>10:1**; the column value IS the ratio |
| Change Since Open | list | after 09:30 |
| **Top of Trend** | list | **15:00–16:00** |
| Continuation | list | pre-market context (2-week range held) |
| Top RSI Trend · Top Relative Volume · Top Volume 5 Minutes | list | intraday |
| Large Cap Highest Volume | list | **10:00+**, micro-scalp ideas |
| **Small-Cap HOD Momo** + 11 sub-strategies | alert | 09:30–11:30 |
| **Penny HOD Momo** (under $2.00) + 3 | alert | 09:30–11:30 |
| **Running Up** / Running Down | alert | **07:00, 08:00, 09:00** news hours |
| Reversal | alert | intraday |
| Large Cap HOD Momo | alert | intraday |
| **Halt Scanner** | alert | **09:30–16:00 only** |

`Recent Reverse Split` is the list that `FILTERS.md` gate 5 exists to survive —
a reverse split shrinks the float into exactly the band this method hunts, so
the list is a **source of candidates**, not a rejection list. (MSGY 2026-08-11:
rejected untested on gate 5, ran 2.54 → 5.43.)

---

## Columns, and the two that lie

Standard across scanners: Symbol/News · Price · Volume Today · Relative Volume
(Daily) · Relative Volume (5 min) · Gap % · **ATR** · Change From Close % ·
Short Interest · **Short Ratio**. Volume, Float and Gap% are gradient-coloured
by value; the HOD scanner adds a **Strategy column colour-coded per lane**.

**Float can read zero** for IPOs and new listings, and real float data can be
absent for **24–48 hours**, when the platform shows a **"Check Filings"**
indicator. That is the vendor conceding the same unknown-float hole that forced
`allowUnknownFloat` in our scanner replica — **their scanner does not fail
closed either.** A blank float is "verify", never "dead": ONFO, WETO and SXTC
all had no published float in the week they ran.

**Both RVOL columns are biased, in opposite directions** (measured, see
`daytrade-dash/README.md`). Daily RVOL divides a partial day by whole-day
averages, so it reads **low all morning** — exactly when it matters. The 5-min
average includes overnight bars on extended-hours charts, so pre-market bursts
read **high**. Knowing which way each leans is the difference between using
them and being fooled by them.

---

## What the platform will not do for you

Named explicitly, because "Dash only" means saying where Dash stops:

**Reverse-split arithmetic** (the list flags the split; it does not tell you
whether the gap IS the split) · **dilution, shelf and ATM filings** ·
**buyout pinning** (a stock pinned to a deal price will not run) ·
**foreign private issuers** — 6-K/20-F filers have no S-3/424B tripwire at all ·
**halt-band width** relative to your stop · **spread and executable size** ·
**borrow availability** · **catalyst quality** — the flame times the headline,
it does not read it. A $50M offering lights the flame red.

Every one of those has cost money in this repo's own log. The scanner's job is
to put a name in front of you; the reject cascade is yours.

---

## Limitations

- **No threshold in this document is a platform threshold**, because none is
  disclosed. Server config is bearer-protected. Clock times are vendor-stated
  or corpus-stated; the only measured numbers are bounds from one session.
- **The measured export is 7 symbols over 94 minutes, pre-market only.**
  Branch behaviour after 09:30 is untested.
- **The audio-alert divergence is unresolved** — video says two strategies, the
  vendor page says all but Medium Float.
- **The vendor page is dated Jan 2026** and the platform ships new scanners
  regularly; the inventory will drift.
- **Power hour and after hours are watch-only here**, not because they are
  unprofitable but because nothing has measured them.
- **Paper only.** Knowing the platform's shape is selection evidence, not edge.
  The 894-session replication of this strategy class was negative expectancy,
  and a well-organised screen does not overturn it.
