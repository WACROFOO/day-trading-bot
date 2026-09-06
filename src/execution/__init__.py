"""The order path. Separate package, separate connection, paper only.

`momentum_platform` must never import this. The desk is read-only by
construction and two tests fail if an order verb appears in its IBKR
modules; keeping execution in its own package is what lets that guard stay
green while an executor exists at all.

Nothing here can reach a live account: `ibkr_trader` refuses any account id
that does not begin with `DU`, and the refusal is not configurable.
"""
