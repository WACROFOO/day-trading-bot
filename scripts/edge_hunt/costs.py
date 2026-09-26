"""Trading costs in R at the owner's stated dollar risk ($20 a trade).

Three parts, each charged per ORDER actually sent:

  commission  IBKR FIXED  $0.005/share, $1.00 minimum, capped at 1 % of value
              IBKR TIERED $0.0035/share (<= 300k shares a month), $0.35
              minimum, 1 % cap, PLUS pass-through fees the fixed plan
              includes: exchange remove-liquidity ~$0.0030/share, clearing
              ~$0.0002/share, and on sells FINRA TAF ~$0.000166/share.
              These rates are modelling assumptions from IBKR's published
              schedule as I understand it, not repository facts — check them
              against the account's current schedule. Marketable orders
              remove liquidity, so tiered is NOT always cheaper: it wins
              under ~150 shares (the $0.35 minimum), loses above.
  spread      half the quoted spread on every marketable side (the entry
              stop-limit, a stop exit, a flatten, a bail), from the proxy
              calibrated on real Alpaca NBBO quotes (`spread_proxy`); a
              resting target limit pays none
  slippage    one cent a marketable side beyond the half spread (the old
              model's whole cost, kept as a floor)

A stop the bar opens through is already filled at that open by the engine,
so gap slippage is in the gross R, not here.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

DOLLAR_RISK = 20.0
ROOT = Path(__file__).resolve().parents[2]
PROXY_FILE = ROOT / "research" / "edge-hunt" / "results" / "spread_proxy.json"


def shares_for(rps: float, dollar_risk: float = DOLLAR_RISK) -> int:
    return max(1, int(dollar_risk // rps)) if rps > 0 else 0


def commission(shares: int, price: float, plan: str = "fixed", sell: bool = False) -> float:
    value = shares * price
    if plan == "fixed":
        return min(max(1.0, 0.005 * shares), max(1.0, 0.01 * value))
    base = min(max(0.35, 0.0035 * shares), max(0.35, 0.01 * value))
    fees = 0.0030 * shares + 0.0002 * shares + (min(8.30, 0.000166 * shares) if sell else 0.0)
    return base + fees


class SpreadProxy:
    """Estimated quoted spread in dollars from what a bar series shows at the
    moment: price tier x session window x recent dollar volume tercile.
    Falls back to 1 cent when no calibration table exists yet."""

    def __init__(self, path: Path = PROXY_FILE):
        self.table = json.loads(path.read_text()) if path.exists() else None

    @staticmethod
    def key(price: float, premarket: bool, dollar_vol_5m: float) -> str:
        tier = "2-5" if price < 5 else ("5-10" if price < 10 else "10-20+")
        vol = "lo" if dollar_vol_5m < 50_000 else ("mid" if dollar_vol_5m < 500_000 else "hi")
        return f"{tier}|{'pm' if premarket else 'rth'}|{vol}"

    def spread(self, price: float, premarket: bool, dollar_vol_5m: float) -> float:
        if not self.table:
            return 0.02
        k = self.key(price, premarket, dollar_vol_5m)
        rel = self.table["cells"].get(k, self.table["default"])     # median spread as a fraction of price
        return max(0.01, rel * price)


def cost_r(entry: float, stop: float, fill: float, exit_px: float, orders: int, stop_side: bool,
           half_spread: float, plan: str = "fixed", slip: float = 0.01,
           dollar_risk: float = DOLLAR_RISK) -> float:
    """Round-trip cost in R. `orders` = exit orders sent (a ladder sends up
    to three); every exit order after the first is a partial of the same
    share count, charged its own commission."""
    rps = entry - stop
    if rps <= 0:
        return math.nan
    q = shares_for(rps, dollar_risk)
    comm = commission(q, fill, plan)
    per = max(1, orders)
    for j in range(per):
        part = q if per == 1 else max(1, q // per)
        comm += commission(part, exit_px, plan, sell=True)
    marketable_sides = 1 + (1 if stop_side else 0)
    friction = q * (half_spread + slip) * marketable_sides
    return (comm + friction) / (q * rps)
