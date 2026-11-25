"""Check the OKX demo connection end to end, without any chance of a fill.

Usage, on YOUR machine (keys stay there), from the repo root:
    pip install -r systematic/requirements.txt
    python systematic/scripts/okx_demo_check.py

It reads the keys from systematic/.env (template: systematic/.env.example),
connects to OKX Europe's demo environment, and then:
  1. shows the demo balances;
  2. reads the BTC/USDC (or BTC/USDT) price;
  3. places a tiny post-only BUY at 50% below the market, so it cannot fill;
  4. confirms the order is open, cancels it, and confirms the cancel.
Nothing touches real money: demo mode is enforced by the connector.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from portfolio_bot.broker import okx  # noqa: E402


def run(exchange) -> list[str]:
    """The check itself; returns the report lines. Raises on any failure."""
    report = []
    markets = exchange.load_markets()
    symbol = okx.pick_symbol(markets)
    base, quote = symbol.split("/")

    balance = exchange.fetch_balance()
    totals = {c: balance.get("total", {}).get(c, 0) for c in (base, quote, "USDC", "USDT")}
    report.append("demo balances: " + ", ".join(f"{c} {v}" for c, v in totals.items()))

    ticker = exchange.fetch_ticker(symbol)
    bid = ticker.get("bid") or ticker.get("last")
    report.append(f"{symbol} bid {bid}")

    market = markets[symbol]
    amount = max(market.get("limits", {}).get("amount", {}).get("min") or 0.00001, 0.00001)
    price = float(exchange.price_to_precision(symbol, bid * 0.5))
    client_id = f"demochk{int(time.time())}"
    order = exchange.create_order(symbol, "limit", "buy", amount, price,
                                  {"postOnly": True, "clOrdId": client_id})
    report.append(f"placed post-only buy {amount} {base} at {price} (id {order['id']})")

    fetched = exchange.fetch_order(order["id"], symbol)
    if fetched.get("status") != "open":
        raise RuntimeError(f"expected an open order, got status {fetched.get('status')!r}")
    exchange.cancel_order(order["id"], symbol)
    after = exchange.fetch_order(order["id"], symbol)
    if after.get("status") not in ("canceled", "cancelled"):
        raise RuntimeError(f"cancel not confirmed, status {after.get('status')!r}")
    report.append("order confirmed open, then cancelled: the order path works")
    return report


def main() -> int:
    try:
        config = okx.OkxConfig.from_env()
        exchange = okx.connect(config)
        for line in run(exchange):
            print("  " + line)
    except Exception as exc:  # report the reason, never the keys
        print(f"DEMO CHECK FAILED: {type(exc).__name__}: {exc}")
        return 1
    print("DEMO CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
