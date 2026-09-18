# src/execution/

**The only order path in this repository.** It lives outside
`momentum_platform/` on purpose: that package is read-only by design and by
test, and keeping the write path in a separate package is what makes the
guard there meaningful rather than aspirational.

| Module | What |
|---|---|
| `ibkr_trader.py` | `PaperTrader` — client id 31, port 4002, `readonly=False`. **Refuses any account whose id does not begin `DU`** (`NotPaperError`); the account is checked, never the port trusted |
| `intent.py` | `EntryIntent` and the session clock. The intent is written to the ledger BEFORE the send, so an acknowledgement lost to a crash is reconciled by `orderRef`, never resent |
| `runner.py` | the actor: reads pending decisions, applies the phase's mode, places, watches stops, flattens at the hard stop |
| `policy.py` | what the current phase permits. Refuses the monitored pre-market shape unless Amendment A1 has been accepted by a human |
| `bridge.py` | LOG_ONLY / TRADE, the seam the runner is tested through |

Phases, gates and amendments are defined in `docs/preregistration.md`, not
here. This package enforces them; it does not decide them.
