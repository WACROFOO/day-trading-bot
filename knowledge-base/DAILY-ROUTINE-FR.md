# The trading day, hour by hour — France time

France (CEST) is **+6h** on New York (EDT) from late March to late October.
In winter both shift and it stays +6h. Verify at the DST changeovers (US ends
1 Nov 2026, EU ends 25 Oct 2026 — for that one week the gap becomes +5h).

Times below are the session windows in `strategies/PARAMETERS.md` §2,
converted. Risk numbers are for a €500 account at the documented 2% per trade.

| France | ET | Phase | What happens |
|---|---|---|---|
| 10:00 | 04:00 | Early pre-market | Nothing to do. Scanners can run, but volume is too thin to judge |
| **13:00** | 07:00 | **Pre-market opens properly** | First real look. Gap scanner on |
| **14:00** | 08:00 | **News window** | Catalysts land. This is pillar #3 |
| **15:00** | 09:00 | **Final watchlist** | Plan written and closed. No new names after this |
| **15:30** | 09:30 | **OPEN** | Watch only. No orders |
| **15:35** | 09:35 | **Trading window opens** | First entries allowed |
| 15:35–16:30 | 09:35–10:30 | **PRIME** | Where the documented edge is |
| 16:30–17:30 | 10:30–11:30 | Late window | Reduced size |
| **17:30** | 11:30 | **HARD STOP** | Flat. Done for the day |
| 17:30–18:00 | | Journal | Log every trade while it is fresh |
| 22:00 | 16:00 | US close | Only relevant for tomorrow's watchlist |

---

## 13:00 — pre-market scan

Run the five pillars on whatever is gapping. All five or it is not a trade:

| # | Pillar | Pass |
|---|---|---|
| 1 | Price | $2–$20 |
| 2 | Float | < 20M shares |
| 3 | News | a real catalyst |
| 4 | Relative volume | ≥ 5× normal |
| 5 | Rate of change | up ≥10% and still rising |

Write the names down. Anything failing a pillar is deleted, not "watched
loosely".

## 14:00 — news

For each survivor: what is the catalyst, and is it real? No catalyst = no
trade, whatever the chart looks like. (His current market is an explicit
exception — foreign small caps squeezing with no news — but that is a
judgement a beginner should not be making.)

## 15:00 — write the plan, then stop looking

For each name, on paper, **before the open**:

- entry trigger price
- stop price → risk per share
- **share size = €10 ÷ risk per share**, capped by €500 ÷ entry
- target 1 (retest of high of day, usually $0.15–0.20 away)

If you cannot fill in all four, the name comes off the list.

**Hard limits for the day:**

| Rule | €500 account |
|---|---|
| Risk per trade | €10 (2%) |
| Max daily loss → stop trading | **€30 (6%)** |
| 3 losses in a row → stop trading | — |
| Max trades | 2–3 names |
| PDT (US margin acct under $25k) | 3 day trades per 5 business days |

## 15:30–15:35 — the opening five minutes

**No orders.** The open is the most violent five minutes of the day and the
documented rule is to sit through it. Watch which name is actually leading —
often not the one you expected.

## 15:35–16:30 — prime window

The only pattern: **micro pullback**. Strong move up → small dip (2–3 candles,
on lighter volume than the push) → buy the first candle that trades above the
previous candle's high. Stop under the pullback low.

Exit ladder: sell half at target 1 → **stop to breakeven** → sell 25% at the
next level → trail the last 25%.

Sell everything immediately on any one of: big red candle on heavy volume,
green candles shrinking, MACD turning negative, large seller on Level 2, new
low below the flag, big topping tail.

## 16:30–17:30 — late window

Same rules, smaller size. Momentum thins after 10:30 ET. If you are already
green, the highest-value action is usually to stop.

## 17:30 — hard stop

Flat, regardless of P&L. Then journal: entry, stop, size, exit, reason, and
**one sentence on whether you followed the plan** — that sentence is the part
that compounds.

---

## A note on the hours

The European timing is genuinely favourable: the whole preparation happens
during your afternoon, and the entire tradeable window is 15:35–17:30 — two
hours. What it costs you is the pre-market, which he considers the best part
of the session (*"I prefer trading pre-market where you don't have to worry
about halts"*). Trading pre-market from France means being at the screen from
13:00, which is doable.

**Standing caveat.** Our own replication of these documented rules over 17 real
sessions produced negative expectancy, and the live streams show his real
entries happen on a 10-second chart most retail platforms do not show. This
routine is for simulator practice. See `STUDY-PLAN.md` for the order to learn
it in.
