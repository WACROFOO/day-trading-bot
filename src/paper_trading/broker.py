"""Simulated broker: quotes via yfinance, market/marketable-limit fills with
slippage and commissions, bracket stops, and a hard risk gate on entries.

Every order path funnels through this module: ``buy`` consults the risk
gate BEFORE pricing (raises ``risk_gate.RiskVeto`` when locked); exits are
never gated — sells always execute. ``ledger.record_fill`` stays unguarded
by design (raw ledger); UI code must never call it directly.

Never import datafeed here (datafeed imports broker — circular).
"""

from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf

from . import ledger
from .risk_gate import RiskGate, RiskVeto  # noqa: F401  (RiskVeto re-exported)

DEFAULT_SLIPPAGE = 0.02  # $ per share, mirroring the strategy's slippage concern
DEFAULT_COMMISSION_PER_SHARE = 0.005  # $ per share
MARKETABLE_LIMIT_OFFSET = 0.15  # marketable limit = last +/- this offset (§4: ask + $0.15)


@dataclass
class Quote:
    symbol: str
    price: float
    open: float
    high: float
    low: float
    volume: float
    prev_close: float

    @property
    def change_pct(self) -> float:
        if self.prev_close:
            return (self.price - self.prev_close) / self.prev_close * 100.0
        return 0.0


def quote(symbol: str) -> Quote:
    """Latest quote for ``symbol`` from yfinance (fast_info with fallback)."""
    symbol = symbol.upper()
    ticker = yf.Ticker(symbol)
    price = open_ = high = low = volume = prev_close = None
    try:
        fi = ticker.fast_info
        price = fi.get("lastPrice")
        open_ = fi.get("open")
        high = fi.get("dayHigh")
        low = fi.get("dayLow")
        volume = fi.get("lastVolume")
        prev_close = fi.get("previousClose")
    except Exception:
        pass
    if price is None:
        hist = ticker.history(period="5d", interval="1d")
        if hist.empty:
            raise ValueError(f"no data for {symbol}")
        last = hist.iloc[-1]
        price = float(last["Close"])
        open_ = open_ if open_ is not None else float(last["Open"])
        high = high if high is not None else float(last["High"])
        low = low if low is not None else float(last["Low"])
        volume = volume if volume is not None else float(last["Volume"])
        if prev_close is None and len(hist) > 1:
            prev_close = float(hist.iloc[-2]["Close"])
    return Quote(
        symbol=symbol,
        price=float(price),
        open=float(open_ or price),
        high=float(high or price),
        low=float(low or price),
        volume=float(volume or 0.0),
        prev_close=float(prev_close or price),
    )


def position_size(risk_budget: float, entry_price: float, stop_price: float) -> int:
    """Shares = risk_budget / (entry - stop). The strategy's core formula (§7)."""
    risk_per_share = entry_price - stop_price
    if risk_per_share <= 0:
        raise ValueError("stop must be below entry for a long trade")
    if risk_budget <= 0:
        raise ValueError("risk budget must be positive")
    return int(risk_budget / risk_per_share)


def reward_risk(entry_price: float, stop_price: float, target_price: float) -> float:
    """(target - entry) / (entry - stop)."""
    risk = entry_price - stop_price
    if risk <= 0:
        raise ValueError("stop must be below entry")
    return (target_price - entry_price) / risk


def commission_for(qty: float,
                   per_share: float = DEFAULT_COMMISSION_PER_SHARE) -> float:
    """Total commission for ``qty`` shares. Never rounded (feeds fill math)."""
    return qty * per_share


def affordable_shares(cash: float, price: float, *,
                      slippage: float = DEFAULT_SLIPPAGE,
                      per_share: float = DEFAULT_COMMISSION_PER_SHARE) -> int:
    """Max shares the cash can buy incl. slippage and commission (no margin)."""
    per_share_cost = price + slippage + per_share
    if per_share_cost <= 0 or cash <= 0:
        return 0
    return int(cash / per_share_cost)


def marketable_limit_price(side: str, last: float,
                           offset: float = MARKETABLE_LIMIT_OFFSET) -> float:
    """Marketable limit: BUY = last + offset; SELL = last - offset."""
    side = side.upper()
    if side == "BUY":
        return last + offset
    if side == "SELL":
        return last - offset
    raise ValueError(f"side must be BUY or SELL, got {side!r}")


def _fill_price(side: str, order_type: str, last: float,
                limit_price: float | None, slippage: float) -> float:
    """Fill price for a MARKET or marketable LIMIT order.

    MARKET: buy at last + slippage, sell at last - slippage.
    LIMIT must be marketable (buy limit >= last, sell limit <= last); the
    fill is the better of the limit and the slippage-adjusted last. The
    paper sim does not rest unfilled limits (except STOPs) — keep scope tight.
    """
    order_type = order_type.upper()
    if order_type == "MARKET":
        return last + slippage if side == "BUY" else last - slippage
    if order_type == "LIMIT":
        if limit_price is None:
            raise ValueError("limit_price required for LIMIT orders")
        if side == "BUY":
            if limit_price < last:
                raise ValueError("limit not marketable")
            return min(limit_price, last + slippage)
        if limit_price > last:
            raise ValueError("limit not marketable")
        return max(limit_price, last - slippage)
    raise ValueError(f"order_type must be MARKET or LIMIT, got {order_type!r}")


def buy(symbol: str, qty: int, *, order_type: str = "MARKET",
        limit_price: float | None = None, stop_price: float | None = None,
        slippage: float = DEFAULT_SLIPPAGE,
        commission_per_share: float = DEFAULT_COMMISSION_PER_SHARE,
        reason: str = "ENTRY", db_path=None) -> dict:
    """Buy ``qty`` shares (MARKET or marketable LIMIT), gated by RiskGate.

    1. gate veto check (raises RiskVeto before any pricing or fill)
    2. quote + fill price
    3. record the fill (with commission) via an order row marked FILLED
    4. attach a bracket STOP order when ``stop_price`` is given
    5. gate.on_fill() to update peaks/latch
    """
    qty = int(qty)
    if qty <= 0:
        raise ValueError("qty must be positive")
    gate = RiskGate(db_path)
    gate.assert_can_buy()
    q = quote(symbol)
    fill = _fill_price("BUY", order_type, q.price, limit_price, slippage)
    comm = commission_for(qty, commission_per_share)
    order_id = ledger.create_order(
        symbol, "BUY", qty, order_type.upper(), limit_price=limit_price,
        stop_price=stop_price, reason=reason, db_path=db_path)
    try:
        trade_id = ledger.fill_order(order_id, fill, commission=comm,
                                     db_path=db_path)
    except Exception:
        ledger.cancel_order(order_id, db_path=db_path)  # no orphan OPEN entry
        raise
    stop_order_id = None
    if stop_price is not None:
        stop_order_id = ledger.create_order(
            symbol, "SELL", qty, "STOP", stop_price=stop_price,
            reason="BRACKET", db_path=db_path)
    gate.on_fill()
    return {"trade_id": trade_id, "order_id": order_id,
            "stop_order_id": stop_order_id, "side": "BUY", "symbol": q.symbol,
            "qty": qty, "price": fill, "commission": comm, "reason": reason}


def _open_qty(symbol: str, db_path=None) -> float:
    symbol = symbol.upper()
    return sum(p["qty"] for p in ledger.get_open_positions(db_path)
               if p["symbol"] == symbol)


def sell(symbol: str, qty: int, *, order_type: str = "MARKET",
         limit_price: float | None = None,
         slippage: float = DEFAULT_SLIPPAGE,
         commission_per_share: float = DEFAULT_COMMISSION_PER_SHARE,
         reason: str = "EXIT", db_path=None) -> dict:
    """Sell ``qty`` shares (MARKET or marketable LIMIT). No shorting.

    Exits are never gated — the gate only refuses new risk (plan §8). After
    the fill, open STOPs are synced with the remaining position and the
    gate's latch/peak state is refreshed.
    """
    qty = int(qty)
    if qty <= 0:
        raise ValueError("qty must be positive")
    symbol = symbol.upper()
    open_qty = _open_qty(symbol, db_path)
    if qty > open_qty + 1e-9:
        raise ValueError(f"cannot sell {qty} of {symbol}: only {open_qty:.0f} open")
    q = quote(symbol)
    fill = _fill_price("SELL", order_type, q.price, limit_price, slippage)
    comm = commission_for(qty, commission_per_share)
    order_id = ledger.create_order(
        symbol, "SELL", qty, order_type.upper(), limit_price=limit_price,
        reason=reason, db_path=db_path)
    try:
        trade_id = ledger.fill_order(order_id, fill, commission=comm,
                                     db_path=db_path)
    except Exception:
        ledger.cancel_order(order_id, db_path=db_path)
        raise
    ledger.sync_stops_with_positions(db_path=db_path)
    RiskGate(db_path).on_fill()
    return {"trade_id": trade_id, "order_id": order_id, "side": "SELL",
            "symbol": q.symbol, "qty": qty, "price": fill,
            "commission": comm, "reason": reason}


def sell_half(symbol: str, *, db_path=None, **kw) -> dict:
    """Sell half the open position (floored). Errors on a 1-share position."""
    qty = int(_open_qty(symbol, db_path) // 2)
    if qty < 1:
        raise ValueError(f"cannot sell half of {symbol.upper()}: less than 2 shares open")
    return sell(symbol, qty, db_path=db_path, **kw)


def sell_all(symbol: str, *, db_path=None, **kw) -> dict:
    """Sell the entire open position."""
    qty = int(_open_qty(symbol, db_path))
    if qty < 1:
        raise ValueError(f"no open position in {symbol.upper()}")
    return sell(symbol, qty, db_path=db_path, **kw)


def cancel_all(symbol: str | None = None, *, db_path=None) -> int:
    """Cancel every OPEN order (optionally one symbol's); returns the count."""
    return ledger.cancel_all_open_orders(db_path, symbol=symbol)


def check_stops(traded: dict[str, tuple[float, float]], *,
                slippage: float = DEFAULT_SLIPPAGE,
                commission_per_share: float = DEFAULT_COMMISSION_PER_SHARE,
                db_path=None) -> list[dict]:
    """Fire OPEN STOP orders against the latest 1m bars; returns the fills.

    ``traded`` maps symbol -> (bar_open, bar_low). A STOP triggers when
    ``bar_low <= stop_price`` and fills at ``stop_price - slippage`` — or at
    ``bar_open - slippage`` when the bar gapped through the stop
    (``bar_open < stop_price``). Fills go through the ledger fill path with
    reason "STOP" (commission applies, order marked FILLED, gate latch
    refreshed). Takes bar data as a parameter: no datafeed import (would be
    circular) and trivially testable with synthetic bars.
    """
    fills = []
    for o in ledger.get_open_orders(db_path):
        if o["order_type"] != "STOP":
            continue
        sym = o["symbol"]
        if sym not in traded:
            continue
        bar_open, bar_low = traded[sym]
        if bar_low > o["stop_price"]:
            continue
        fill_price = (bar_open if bar_open < o["stop_price"]
                      else o["stop_price"]) - slippage
        comm = commission_for(o["qty"], commission_per_share)
        try:
            trade_id = ledger.fill_order(o["id"], fill_price, commission=comm,
                                         reason="STOP", db_path=db_path)
        except ValueError:
            continue  # e.g. position already gone; leave the order OPEN
        ledger.sync_stops_with_positions(db_path=db_path)
        RiskGate(db_path).on_fill()
        fills.append({"order_id": o["id"], "trade_id": trade_id, "side": "SELL",
                      "symbol": sym, "qty": o["qty"], "price": fill_price,
                      "commission": comm, "reason": "STOP"})
    return fills
