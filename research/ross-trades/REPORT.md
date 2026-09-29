# His trades against the bot — report (2026-09-28)

```
SOURCE · his own words: video recaps (June-July 2026), live streams (2021-2023), blog
         recaps (2017-2025) in knowledge-base/, one row per trade with a verbatim quote
         (machine-checked: 1,529 of 1,529 found in their file)
COVERAGE · 22 of 61 extraction batches (the rest stopped on the account's usage limit
         and were NOT re-run to save credits): 1,073 blog-recap rows, 236 video-recap,
         203 stream — the stream register is the least covered
TAPE  · Alpaca SIP 1-minute bars, raw prices · point-in-time runner universe: every
        name that traded >= +10 % 2016-2026 (269,508 symbol-days, splits removed by
        Alpaca corporate actions) · costs as research/edge-hunt/PREREGISTRATION.md
```

Paper only. Figures from `results/analysis.txt` and `results/f7_cost_sensitivity.txt`.

## 1. The ledger

| | count |
|---|---:|
| trade rows (his own) | 1,512 |
| with a stated entry price | 914 |
| dated (text 447 · tape 471) | 918 |
| rebuilt on the tape | 702 |
| stated price never printed that day (flagged, kept) | 15 |
| outcome as he states it | 811 wins · 423 losses · 38 scratches · 240 not stated |

## 2. What he does, measured

| factor | measured |
|---|---|
| **selection** | at the minute before his entry his stock was the **#1 gainer** among names then up ≥ 10 % in 57 % of cases, top 3 in 88 % (median 6 such names) · only 31 % were in the bot's 09:30-gap list |
| **entry** | 90 % buy a **new high of day**, a median +3 % above the prior high, on a stock already up a median +50 %, 10 % above VWAP · 43 % pre-market, 50 % 09:30-10:30 |
| **stop** | stated on only 30 trades (median 6 %) |
| **exit** | holds a **median 2 minutes**; entry-to-exit move median +2 % · 60 minutes after he leaves, the stock trades a median 14.5 % lower |
| **sizing** | his top 10 % of trades make 182 % of his stated net; without them the rest lose $498k |
| **results as stated** | 66 % winners, average win ÷ average loss 0.90 · live streams only: 57 %, 0.29 |
| **Level 2 / tape** | cited as the reason on 7 % of trades · halts 9 % |

## 3. Why the bot does not do it

* **It is not looking at his stocks.** 69 % of his names are outside the bot's
  09:30-gap universe.
* **When it is, it refuses.** A desk plan sat within 5 minutes of his entry 63 % of
  the time; all gates green and filled only 9 % — MACD (226) and pullback volume
  (203) are the gates that say no.
* **On his own symbol-days the bot loses**: −101 R over 408 symbol-days.
* **His exact entries, managed like the bot** (stop under the last bar, trail 1 R):
  −0.44 R a trade. Buying the high works for him because he is out in two minutes and
  sizes up on the rare runner — not because the entry itself carries an edge.

## 4. The rule that copies him — F7, tested

Preregistered before its first run (`research/edge-hunt/PREREGISTRATION.md`,
addendum 2026-09-28): the minute's #1 gainer, buy the break of its high of day,
his scalp exits, one position.

| best configuration on 2016-2022 | train | validation 2023 | holdout |
|---|---|---|---|
| 09:30-11:00, stop under the last bar, bail after 2 min unless +1 R, trail 1 R | **gross +0.171** · net −0.167 (2,269) | gross +0.008 · net −0.270 (273) | ✗ closed — validation gate not met |

The same configuration with the cheapest cost model (one cent a side): −0.035 on train,
−0.187 on validation. **Not adopted; nothing built.**

This is the first positive gross found in any family on a point-in-time universe: the
leader breakout is where his edge lives, and it is real before costs on 2016-2022. It
is about +0.17 R a trade, spreads take 0.2-0.34 R, and in 2023 it was gone.

## 5. What this could not check

* The recaps over-represent good days and the best trades; the live-stream register,
  the least biased, is the least covered here and shows his worst ratio (0.29).
* His stop is mental and he trades on 10-second charts and the tape; this uses 1-minute
  bars, resting stops and a fixed $20 risk.
* 39 of 61 batches were not extracted (usage limit); 581 rows have no date.

## 5b. My earlier call, scored

"His edge sits in what one-minute bars cannot see — tape, Level 2, which one name of
twenty" (`research/edge-hunt/REPORT.md`). **Partly wrong:** which name he picks IS
visible in bars (the #1 gainer) and does carry a gross edge; Level 2 is his stated
reason on only 7 % of trades. What bars cannot give the bot is his two-minute exit
discretion, his size on the rare runner, and executions cheaper than the spread.

## 6. Verdict

**His edge is real in the data but cannot be mechanised profitably with what we have.**
He picks the day's top gainer and buys its new high — that part is in the bars and is
worth about +0.17 R a trade before costs. What turns it into money is what the bot
cannot copy: out in two minutes on a read of the tape, huge size on the one runner that
pays for everything, executions better than the spread. At $20 of risk with real spreads
it loses, and in 2023 the gross edge disappeared.

## 7. F8 — the same rule where the spread is small (2026-09-29)

Preregistered before the run (`research/edge-hunt/PREREGISTRATION.md`, addendum
2026-09-29): F7, taken only when the estimated round-trip spread at arming is
≤ 5 / 10 / 20 % of the stop, costed at $40 risk and a $2,000 cap.

| chosen on 2016-2022 | train | validation 2023 | holdout 2024-2026 |
|---|---|---|---|
| trail 1 R, stop under the arming bar, 07:00-09:30, spread ≤ 5 % | −0.061 net (370) | +0.037 (147) | **−0.188 net (592), gross −0.071** |

Holdout: 0 of 3 years positive, 0.243 R worse than random entry on the same
names; four of five checks fail. **Not adopted.** Filtering on the spread made
train and 2023 look close to breakeven, and the gross edge was gone in
2024-2026. With F7 and F8 both closed, the leader breakout has been tested at
both sizings and both cost levels; it does not carry a tradable edge here.
