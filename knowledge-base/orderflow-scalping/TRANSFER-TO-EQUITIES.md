# Can this model be used on cash equities, in market hours?

Short answer: **the level logic yes, the order-flow core no, and the account
rules stop you before either.**

## First, what he actually trades

*"specifically for equities. So for NASDAQ"* [00:16:47] means the **equity index
futures** — NQ, and its micro MNQ. Not single stocks. Every size reference in
3½ hours is a contract: *"one contract in mini"* [01:15:19], *"per contract
$160"* [01:11:55], *"30 contract as a filter"* [01:31:49], *"more than 40
contract here"* [01:50:16]. **No individual stock is named once.**

So the question is a genuine port, not a clarification.

---

## 1. What transfers unchanged

These need no order-flow data at all, and they are the same three items
`PLAYBOOK.md` already puts first in its test order:

| rule | why it ports |
|---|---|
| **out of balance** as a pre-condition | a volume profile is just a histogram of traded volume by price — it computes on any instrument with volume |
| **break AND test**, never the break alone | pure price structure |
| first target = **previous daily high** | pure price structure |
| stop **1–2 ticks inside** the obvious high | ports, and arguably matters *more* on equities, where stop-runs at round numbers and prior highs are well documented |

`../strategies/PARAMETERS.md` §3 already carries the same idea from a different
direction — `at_support` requires two independent reasons at one price, and
whole/half dollars are one of them. A low-volume node is a third kind of reason.

**Session also ports cleanly.** His "New York session" is 09:30–16:00 ET, which
is exactly cash equity regular hours.

## 2. What degrades — and it is the trigger

Step 3, aggression, is the part that breaks, and it breaks for a structural
reason rather than a tuning one.

**NQ is one contract on one exchange.** Every trade prints to a single tape with
a determinable aggressor side. A footprint on NQ sees essentially all of the
flow.

**US cash equities are fragmented.** The same stock trades on many lit exchanges
simultaneously, plus a large share of volume executed off-exchange and reported
without venue detail. A footprint built from any one venue sees a slice; the
consolidated tape does not hand you a clean aggressor side the way a single
futures book does.

The consequence is specific: **delta and CVD on a single stock are measuring
something less complete than the same indicators on NQ.** Since the trigger of
the whole model is aggression read from that data, this is not a detail you can
work around by paying for a better feed.

It is not *useless* on equities — traders do read tape on liquid names — but any
claim transferred from this video about how reliable aggression is should be
discounted, and this repo has no measurement of by how much.

## 3. What breaks: the instrument choice collides with the rest of this repo

Order flow needs **depth** — continuous two-sided institutional flow. On cash
equities that means the most liquid names: index ETFs and mega-caps.

The Ross universe in `../strategies/PARAMETERS.md` §1 needs the **opposite**:
float under 20 million, which is a *supply constraint*, deliberately illiquid.
On a 5M-float small cap, "aggression" is a handful of retail market orders and
the book is a few hundred shares deep.

> **You cannot run both methods on the same names.** They select for opposite
> liquidity. Anything in `premarket_stars.py` is disqualified as an order-flow
> instrument by the very property that puts it on the list.

## 4. The blocker that decides it: a €500 account cannot scalp US equities

This is the practical answer, and it is not about the method at all.

- **Pattern Day Trader rule.** Four or more day trades within five business days
  in a **margin** account flags you PDT and requires **$25,000** minimum equity.
  Below that, the account is restricted.
- **A cash account avoids PDT**, but US settlement is **T+1** — you can only
  re-trade settled funds. With €500 that is roughly **one round trip a day**.
- **Scalping means many trades a day.** With €500, in cash equities, that is not
  available to you under either account type.

**Futures have no PDT rule.** That is a large part of why he trades them, and
why an MNQ contract is the instrument this model was built for. Day-trade margin
on a micro contract is small — but the notional is not, and leverage cuts both
ways.

## 5. So — what should you actually do

**Use the three bar-testable pieces on equities now.** Out of balance, break and
test, previous daily high as first target, and the stop placed inside rather
than beyond the high. They cost nothing, they need no new data, and they are
already the top of the test order in `PLAYBOOK.md`.

**Do not try to run the order-flow core on cash equities with this account.**
The data is weaker, the right instruments are the wrong ones for everything else
in this repo, and PDT settles it regardless.

**If you want the model as designed, the instrument is MNQ, not stocks** — and
that is a different broker, a leveraged product, and a point at which every
sizing tool here stops applying. `../../scripts/size.py` assumes cash equities
and a €500 account; a Nasdaq futures contract's notional is orders of magnitude
beyond that. **Nothing in this repo sizes futures. Do not reuse it.**

**And the standing prior applies here too.** This repo's replication of a far
better documented strategy came out negative over 894 sessions
(`../../research/momentum-replication/reports/2026-08-regime-filter.md`). A
method with one source and a non-automatable step deserves more scepticism, not
less. Paper first, on whichever instrument you pick.
