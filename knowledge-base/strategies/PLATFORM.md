# The platform, as a build spec

What he actually runs, and what it has to do. `STRATEGY.md` and `PARAMETERS.md`
cover what to trade; this covers the software, which is a separate problem and
the one you are solving if you are building rather than backtesting.

Counts are from `../data/platform_features.md`
(`scripts/pipeline/11_platform_features.py`). Video breadth is the ranking
signal — raw mentions inflate whenever one video happens to be a tutorial on
that one feature.

---

## 1. What he uses

| Platform | mentions | videos | Role |
|---|---|---|---|
| own momentum scanner | 486 | 144 | finds the stock |
| Thinkorswim / TD | 380 | 48 | charts, and the small-account series |
| Lightspeed | 172 | 33 | execution on the main account |
| Schwab | 67 | 35 | discussed, not primary |
| Robinhood | 65 | 29 | discussed as what not to use |
| TradeStation | 50 | 8 | mentioned |
| Interactive Brokers | 45 | 18 | mentioned |

He runs two screens of software at once: *"Lightspeed on the left and I've got
TD…"*. The split matters for a replica — **scanning, charting and execution are
three separate jobs and he does not use one tool for all three.** Build them as
three services, not one app.

The scanner is the piece he controls and talks about most. It is also the only
piece that is his own product rather than a broker's, which is worth holding in
mind when reading how essential he says it is.

---

## 2. Hotkeys — the part specified precisely enough to copy

This is the highest-value section for a replica. Everything else he describes in
prose; the key bindings he states outright, so they can be reproduced exactly
rather than approximated.

| Key | Action | Times stated |
|---|---|---|
| `Shift+1` | set share size, then buy | 103 |
| `Shift+2` | buy at ask / market buy | 20 |
| `Ctrl+Z` | sell at the bid — full exit | 33 |
| `Ctrl+X` | sell half | 5 |
| `Ctrl+Q` | cancel all open orders | 12 |
| `Ctrl+K` | sell at ask — passive exit | 7 |
| `Shift+B` | buy | 8 |

The sizing binding, verbatim:

> *"the way I have this set up is shift one is share size, my share size is
> buying power times 90%… so if I have $10,000 of buying power to make the math
> easy it's going to enter share size equal to $9,000 of stock"*
> — `2kMgCjsmFzY` [00:34:24]

The scale-out pair:

> *"we're going to set that to Control Z, Control X to sell half, and so now
> you're able to move in and out of the market — selling half, adding back,
> selling half — and then you create another hotkey for selling full"*
> — `EIULmW7UCq8` [00:20:41]

**Conflict worth noting.** In one setup `Shift+N` means *N × 1,000 shares*
(*"shift two is 2,000, 3 is 3,000, four…"*); in another `Shift+1` means *90% of
buying power*. These are different configurations from different periods, not a
single scheme. Pick one deliberately.

**The 90%-of-buying-power binding contradicts §7 of `PARAMETERS.md`**, which
sizes from the stop distance: `shares = risk_budget / (entry − stop)`. A key
that always deploys 90% of buying power is not risk-based sizing — it is
maximum sizing. If you build the hotkey as he describes it, you have built
something that ignores the risk rule the rest of the strategy rests on. Build
the risk-based version and treat the 90% key as what it is: a fast-fill button
for a trader who is separately deciding size in his head.

---

## 3. Components, ranked by how often he relies on them

Build order. Breadth first.

| Capability | videos | Build note |
|---|---|---|
| indicator overlay (VWAP, 9/20 EMA, 200 MA, MACD) | 198 | trivial; pure arithmetic on bars |
| Level 2 / depth of book | 140 | expensive data, see §5 |
| simulator / paper trading | 119 | build this **first** — it is the harness for everything else |
| commissions / borrow costs | 117 | must be in the sim or results are fiction |
| multi-timeframe charts (1m / 5m / daily) | 114 | 1-minute is the working timeframe |
| hotkey order entry | 112 | §2 |
| metrics / trade journal | 107 | he treats this as the feedback loop, not a report |
| audio / visual alerts | 94 | scanner → alert is the whole discovery path |
| halt indicator | 89 | halts are frequent on this universe, not an edge case |
| momentum / gapper scanner | 84 | §4 |
| news feed | 80 | catalyst is a §1 pillar, so this is required not optional |
| market vs limit order control | 68 | marketable limit at ask + $0.15 |
| time and sales | 62 | tick data |
| watchlist | 47 | trivial |
| bracket / auto stop | 35 | |
| hard daily loss lockout | 22 | small count, large consequence — see §6 |
| execution speed | 20 | |
| auto share sizing from stop | 6 | rarely discussed, but it is §7 of PARAMETERS |
| scanner filter configuration | 5 | he shows results far more than settings |

The last two rows are the interesting ones. **The two features that most
directly implement his own written risk rules are the two he discusses least.**
That is a gap between what the strategy says and what the tooling does, and it
is exactly the kind of gap a replica silently inherits if you build from what he
demonstrates rather than from what he prescribes.

---

## 4. The scanner

Discovery path, in order: scanner sorts by momentum → a name spikes → audio or
visual alert → he opens the chart → §1 filter is applied by eye → trade or pass.

Scan criteria are §1 of `PARAMETERS.md` — price, float, news, relative volume,
rate of change. Nothing new is needed here; the scanner is that filter applied
continuously rather than once.

Implementation notes:

- **Refresh rate matters more than criteria.** The setup lives 9:30–10:30 and
  the entry is a single 1-minute candle. A scanner on a 60-second poll misses
  the trade it exists to find. Push or sub-second poll.
- **Rank, do not just filter.** He watches an ordered list and reacts to what
  moves up it. A boolean pass/fail list loses the signal he is actually reading.
- **Cap the output.** ~8,000 equities → ~50 hits → 3–5 watchlist. If your
  scanner returns 200 names it has failed even if every one passes the filter.

---

## 5. Data you need, and what it costs

This is where a replica usually dies, so decide it before writing code.

| Data | Needed for | Reality |
|---|---|---|
| 1-minute OHLCV | charts, indicators, entry trigger, backtest | cheap, widely available |
| real-time quotes (NBBO) | spread gate, marketable limit pricing | moderate |
| tick / time and sales | aggressive-buying reads | moderate |
| **Level 2 depth** | seller walls, refresh/reload | **expensive, per-exchange, and not in any retail API** |
| float / shares outstanding | §1 pillar | reference data, updates slowly |
| news with timestamps | §1 pillar | expensive if you need it fast enough to matter |
| halt status | halt indicator | available via SIP / exchange feeds |

Per §10 of `PARAMETERS.md`, most of what he attributes to "Level 2" does not
actually need depth of book — `confirmation to act` is the entry trigger,
`whole-dollar orders` is a support component, `spread width` comes from quotes.
Only seller-wall detection (104 mentions, 31 videos) and order refresh (29)
genuinely require the book.

**So build tiers one and two first and see whether the edge is already there.**
Depth of book is the last thing to add, not the first, and if the strategy only
works once you add it, you have learned something important about how testable
it is.

---

## 6. The one feature worth building above spec

`hard daily loss lockout` appears in only 22 videos, but §8 of `PARAMETERS.md`
carries the claim that breaking the max-loss rule leads to doubling that loss
roughly 80% of the time. If that number is anywhere near right, the lockout is
the single highest-value component in the entire system — and it is the one he
implements socially (rules, walking away) rather than technically.

A bot has no discipline problem to solve, which means this is free to enforce in
software and impossible to enforce in a human. Make it a hard stop at the
account layer that the strategy code cannot override: max daily loss, giveback
percentage, green-to-red, three consecutive losses, 20% drawdown walkaway. All
five are in §8 and all five are pure arithmetic on the day's ledger.

---

## 7. Suggested architecture

Three services, matching how he actually runs it:

```
scanner    → streams ranked candidates      (§1 filter, continuous)
strategy   → evaluates entry/exit on 1m bars (§3, §4, §5, §6)
execution  → places and manages orders      (§2 hotkeys, §7 sizing)
    └─ risk gate sits between strategy and execution and can veto (§8)
```

The risk gate being a separate layer with veto power is the part worth being
strict about. If sizing and daily limits live inside strategy code, then a bug
in strategy logic is also a bug in risk control. Keep them apart.

Start against the simulator, with commissions and realistic slippage on. §12 of
`PARAMETERS.md` has the falsification order — run that before building anything
live, because most of this tooling is wasted effort if step 2 fails.

---

*Derived from 257 transcripts. Counts measure how often he says a thing, not
whether it works. See `STRATEGY.md` §12.*
