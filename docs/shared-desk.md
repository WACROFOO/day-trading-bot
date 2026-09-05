# Two traders, one desk

Two people trading the same strategy want the same scanners and the same
alerts, each from their own machine and their own IBKR connection. This is how
that is set up and how you prove it is working.

## Why not one shared server

IBKR market-data subscriptions are per-subscriber and non-redistributable —
that restriction comes from the exchange agreements behind them (Nasdaq, NYSE,
the CTA/UTP tapes), not from IBKR. Serving one person's live IBKR prices to a
second person is what those terms exist to prevent, and the usual consequence
is the data subscription being terminated. So: one desk each, own TWS, own
subscription. The platform is the code, not the data.

The desk also has no authentication and `/api/v1/desk/add` changes the running
desk, so it stays bound to `127.0.0.1`.

## Setting up the second desk

```
git clone <repo>            # both of you already have GitHub access
cd day-trading-bot
bash scripts/setup.sh
cp .env.example .env        # then fill in YOUR OWN keys
python3 scripts/ibkr_preflight.py
bash scripts/start.sh --ibkr
```

Never share `.env`, API keys, or a TWS session. Two API clients on one TWS
also fight over market-data lines and client ids.

## What makes the two desks agree

`config/desk-profile.json` is committed and holds every rule that decides what
a desk admits and what it fires:

| Section | Rule | What it changes |
|---|---|---|
| `desk` | `priceMin` `priceMax` | the discovery band the scanner and screener use |
| | `minGainPct` | how much a name must be up to be scanned |
| | `maxSymbols` `scanTop` | how many names the desk holds and the scan returns |
| `cadence` | `rebuildSeconds` | how often the scanners re-run |
| | `rescanSeconds` | how often the IBKR scanner union runs |
| | `historyEverySeconds` | the rolling minute-history refresh |
| | `volumeProfileDays` | sessions in the time-of-day RVOL baseline |
| | `barStallSeconds` | how long without a bar before the desk re-subscribes |
| `liquidity` | `minVolume5m` `minPillars` | the Approximation gate on Running Up and High of Day |

Pull the same commit and you run the same rules. `.env` still overrides them
per machine — that is deliberate, for testing — but an override is recorded in
the fingerprint rather than hidden, so it cannot silently split the two desks.

The Confirmed course pillars ($2–20, ≥10%, RVOL ≥5×, float <20M, news) are
**not** in the profile. They are Ross's analysis, not an operator setting, so
they live in code — and the fingerprint hashes them, so an edit to one shows up
as a mismatch.

## Proving it

The header carries a **RULES** badge: the first eight characters of the
fingerprint, the build commit, and whether any local override is in force.
Hover it for the full rule set. Same hash on both screens means the same
scanners and the same alerts from the same data.

From a terminal:

```
python3 scripts/desk_parity.py                     # this checkout
python3 scripts/desk_parity.py --url http://127.0.0.1:8787   # the running desk
python3 scripts/desk_parity.py --compare 33dfeedb3f51        # against a partner's hash
python3 scripts/desk_parity.py --json > mine.json            # to send them
```

A mismatch prints the differing rules line by line.

## What a matching hash does NOT promise

**Entitlements.** They are reported beside the hash, never inside it. A desk
without IBKR fundamentals scores the float pillar from SEC shares outstanding
(an upper bound) or leaves it unknown; a desk without Alpaca news keys scores
the news pillar differently. Both change `pillars_passed`, which is one of the
two ways a name clears the liquidity gate — so the same rules can still
produce different alerts if one of you is missing a source. The badge turns
amber and names what is missing.

**Timing.** The scan is aligned to the wall clock rather than to each process's
start time, so two desks started ten minutes apart still scan on the same
phase and converge on the same names within one cycle. A desk started at 09:00
still has no five-second bars from 08:00, so its ten-second pane is shorter —
the scanners read minute bars and are unaffected.

**Data.** Each desk gets its own IBKR feed. They should agree bar for bar; if
they do not, that is a feed question, not a rules question, and the RULES badge
is what tells you which of the two you are looking at.
