"""Simulated broker: quotes via yfinance, market fills with slippage."""

from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf

from . import ledger

DEFAULT_SLIPPAGE = 0.02  # $ per share, mirroring the strategy's slippage concern


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


def buy(symbol: str, qty: int, slippage: float = DEFAULT_SLIPPAGE,
        db_path=None) -> dict:
    """Market buy: fills at ask side (price + slippage)."""
    q = quote(symbol)
    fill = q.price + slippage
    trade_id = ledger.record_fill(symbol, "BUY", qty, fill, db_path=db_path)
    return {"trade_id": trade_id, "side": "BUY", "symbol": q.symbol,
            "qty": qty, "price": fill}


def sell(symbol: str, qty: int, slippage: float = DEFAULT_SLIPPAGE,
         db_path=None) -> dict:
    """Market sell: fills at bid side (price - slippage). No shorting."""
    symbol = symbol.upper()
    open_qty = sum(
        p["qty"] for p in ledger.get_open_positions(db_path) if p["symbol"] == symbol
    )
    if qty > open_qty + 1e-9:
        raise ValueError(f"cannot sell {qty} of {symbol}: only {open_qty:.0f} open")
    q = quote(symbol)
    fill = q.price - slippage
    trade_id = ledger.record_fill(symbol, "SELL", qty, fill, db_path=db_path)
    return {"trade_id": trade_id, "side": "SELL", "symbol": q.symbol,
            "qty": qty, "price": fill}
