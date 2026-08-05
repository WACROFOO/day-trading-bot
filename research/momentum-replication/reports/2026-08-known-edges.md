# The documented edge in this population — and it points the other way

Asked: what is the best-known edge related to this strategy? The literature has
a clear answer, and **this project has been measuring it from the wrong side for
weeks.**

## What our own data already says

From `2026-08-regime-filter.md`, 8,828 qualifying symbol-days over 894 sessions,
Dec 2022 → Aug 2026:

| | |
|---|---|
| closed **green** | **31%** |
| mean open→close | **−2.44%** |
| median open→close | **−4.88%** |
| years with negative mean | **5 of 5** (2022–2026) |

We read that as "the long strategy has no edge." It is more than that. **A
population that declines on 69% of days, with a −4.88% median, in every year
measured, is a large and persistent one-sided edge.** We kept testing entries on
the side that loses.

## The three literatures that explain it

### 1. The MAX effect — Bali, Cakici & Whitelaw (2011), *Journal of Financial Economics*

Stocks with the **highest maximum daily return over the previous month
subsequently underperform**. The raw and risk-adjusted return spread between
the lowest and highest MAX deciles **exceeds 1% per month**.

Our screen selects on gap ≥10% with a $2–20 price — it is, almost by
construction, a daily sample of the highest-MAX names in the market. The
proposed explanation is a retail preference for lottery-like payoffs among
poorly diversified investors; later work
([Macquarie](https://researchers.mq.edu.au/en/publications/it-could-be-overreaction-not-lottery-seeking-that-is-behind-bali-/))
argues the event-study pattern looks more like **overreaction** than
lottery-seeking. Either way the sign is the same.

This is the single closest published match to what we are screening for.

### 2. Miller (1977) — short-sale constraints and divergence of opinion

When pessimists cannot short, the price is set by **the most optimistic
holders**, and the security is overpriced. The overpricing is largest where
**divergence of opinion is high and the lendable supply is small** — which is
the definition of a low-float microcap on a news spike.

Empirically: stocks that are expensive to short or that newly enter the
borrowing market show **size-adjusted returns 1–2% lower per month**, and the
overpricing corrects only slowly.

This is also the mechanism behind what we observed directly on 2026-08-05:
ASTC running 70% with **no news, a $24.5M ATM and a $200M shelf against a $21M
market cap**; INLF twelve days from authorising **8.5 billion shares**. Dilution
into strength is how the overpricing gets corrected, and the filings said so
before the open.

### 3. The day-trader profitability studies

- **Barber, Lee, Liu & Odean** — complete Taiwan market records 1992–2006:
  **under 1%** of day traders were consistently profitable; about 3% positive
  net of fees.
- **Chague, De-Losso & Giovannetti** — every new Brazilian equity-futures day
  trader 2013–2015: of those who persisted beyond 300 trading days, **97% lost
  money**; under 1% earned more than the Brazilian minimum wage.

These are the base rates the strategy is being attempted against.

## The honest catch

**The edge is real, documented, and largely unharvestable by a retail account —
and those facts are the same fact.** Miller's whole point is that the
overpricing exists *because* the stock cannot be shorted. Specifically:

- These are the **hardest-to-borrow names in the market**. Borrow can cost
  triple digits annualised, when locates exist at all.
- **Halts trap the position.** YXT halted 30 times on 2026-08-05 and printed
  +1,136% from its prior close before finishing at +531%.
- Loss is unbounded, and a €500 account cannot survive one YXT.

So the correct reading is not "start shorting." It is that **the anomaly
survives precisely because the barrier to harvesting it is real**, and that any
long strategy in this population is trading against a documented, persistent,
economically-motivated drift.

## What is actually usable from this

1. **The population is the problem, not the entry rule.** No exit tested —
   bracket, trail, ladder, 30-minute clock, regime filter — fixed a long
   position in a group that closes red 69% of the time. That is now explained
   rather than merely observed.
2. **The tradeable version of the short edge is a filter, not a position.**
   Four of the six traps on 2026-08-05 were visible in filings before the bell:
   reverse-split history, an effective shelf or ATM sized against market cap,
   the share-authorisation vote, short interest as a percentage of float. Using
   those to *decline* trades costs nothing and needs no borrow.
3. **If a long edge exists here it is not in the daily bar.** Everything the
   documented method relies on — a micro-pullback after a confirmed move, an
   entry on a 10-second chart, exits off Level 2 and candle structure — is
   invisible at our resolution. The MAX and Miller results say the *drift* is
   down; they say nothing about whether a disciplined intraday trader can take
   the first leg up. That question is still open and still blocked on
   sub-minute data.

## Sources

- Bali, Cakici & Whitelaw, *Maxing Out: Stocks as Lotteries and the
  Cross-Section of Expected Returns*, JFE 2011 —
  https://www.sciencedirect.com/science/article/abs/pii/S0304405X1000190X
- Lamont, *Short Sale Constraints and Overpricing*, NBER —
  https://www.nber.org/reporter/spring05/short-sale-constraints-and-overpricing
- Patatoukas, *Short-Sales Constraints and Aftermarket IPO Pricing*, MIT Sloan —
  https://mitsloan.mit.edu/sites/default/files/inline-files/Short-sales%20Constraints%20and%20Aftermarket%20IPO%20Pricing.pdf
- Barber, Lee, Liu & Odean, *Day Trading for a Living?* (Taiwan)
- Chague, De-Losso & Giovannetti, *Day Trading for a Living?* (Brazil)
