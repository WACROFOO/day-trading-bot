"""Streamlit paper-trading dashboard.

Launch:  streamlit run src/paper_trading/dashboard.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

# Allow running directly with `streamlit run src/paper_trading/dashboard.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paper_trading import broker, datafeed, indicators, ledger, risk  # noqa: E402

st.set_page_config(page_title="Paper Trading Dashboard", layout="wide")

# Strategy universe thresholds (PARAMETERS.md §1)
PRICE_MIN, PRICE_MAX = 2.0, 20.0
GAIN_PCT_MIN = 10.0
VOLUME_MIN = 500_000
STOP_MAX_DISTANCE = 0.20
RISK_PCT_DEFAULT = 2.0


def badge(ok: bool, label: str, detail: str = "") -> str:
    icon = "🟢" if ok else "🔴"
    return f"{icon} {label}" + (f" — {detail}" if detail else "")


def safe(fn, what: str):
    """Run fn, showing a UI error instead of crashing on failure."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - surface any yfinance/data error
        st.error(f"{what} failed: {exc}")
        return None


# ---------------------------------------------------------------- account
account = ledger.get_account()
positions = ledger.get_open_positions()

quotes: dict[str, broker.Quote] = {}
for p in positions:
    q = safe(lambda s=p["symbol"]: datafeed.get_quote(s), f"Quote for {p['symbol']}")
    if q:
        quotes[p["symbol"]] = q

unrealized = sum(
    p["qty"] * (quotes[p["symbol"]].price - p["avg_cost"])
    for p in positions if p["symbol"] in quotes
)
open_value = sum(
    p["qty"] * quotes[p["symbol"]].price for p in positions if p["symbol"] in quotes
)
equity = account.cash + open_value

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
daily = ledger.get_daily_pnl(today)
day_pnl = daily["realized_pnl"] + unrealized

# peak of the day's equity path (snapshots + current), for giveback rule
curve = ledger.get_equity_curve()
today_equities = [
    s["equity"] for s in curve if s["timestamp"][:10] == today
]
day_peak_pnl = max(
    [e - account.starting_cash for e in today_equities] + [day_pnl, 0.0]
)

st.title("Paper Trading Dashboard")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Equity", f"${equity:,.2f}",
          f"{(equity - account.starting_cash) / account.starting_cash * 100:+.2f}%")
c2.metric("Cash", f"${account.cash:,.2f}")
c3.metric("Day P&L", f"${day_pnl:,.2f}")
c4.metric("Open risk", f"${open_value:,.2f}", f"{len(positions)} position(s)")

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Symbol")
    symbol = st.text_input("Ticker", value="AAPL").strip().upper()
    q = None
    if symbol:
        q = safe(lambda: datafeed.get_quote(symbol), "Quote")
    if q:
        st.subheader(f"{q.symbol} — ${q.price:,.2f}")
        st.caption(
            f"O {q.open:,.2f}  H {q.high:,.2f}  L {q.low:,.2f}  "
            f"Vol {q.volume:,.0f}  Day {q.change_pct:+.1f}%"
        )
        st.markdown("**Universe checks (strategy §1)**")
        st.markdown(badge(PRICE_MIN <= q.price <= PRICE_MAX,
                          f"Price ${PRICE_MIN:.0f}–${PRICE_MAX:.0f}",
                          f"${q.price:,.2f}"))
        st.markdown(badge(q.change_pct >= GAIN_PCT_MIN,
                          f"Day change ≥ {GAIN_PCT_MIN:.0f}%",
                          f"{q.change_pct:+.1f}%"))
        st.markdown(badge(q.volume >= VOLUME_MIN,
                          f"Volume ≥ {VOLUME_MIN:,}", f"{q.volume:,.0f}"))
        st.caption("Float and catalyst are not available from yfinance — check them manually.")

    st.divider()
    st.header("Reset account")
    confirm = st.checkbox("Confirm reset (wipes all trades)")
    new_cash = st.number_input("Starting cash", min_value=100.0,
                               value=ledger.DEFAULT_STARTING_CASH, step=1000.0)
    if st.button("Reset account", disabled=not confirm):
        ledger.reset_account(new_cash)
        st.success(f"Account reset with ${new_cash:,.2f}")
        st.rerun()

# ---------------------------------------------------------------- chart
st.subheader("Chart")
bars = None
if symbol:
    bars = safe(lambda: datafeed.get_intraday_bars(symbol, period="1d", interval="1m"),
                "Intraday data")
if bars is not None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    df = bars.copy()
    df["EMA9"] = indicators.ema9(df["Close"])
    df["VWAP"] = indicators.vwap(df)
    m = indicators.macd(df["Close"])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="1m"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA9",
                             line=dict(width=1, color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP",
                             line=dict(width=1, color="purple")), row=1, col=1)
    colors = ["green" if h >= 0 else "red" for h in m["hist"]]
    fig.add_trace(go.Bar(x=df.index, y=m["hist"], name="MACD hist",
                         marker_color=colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m["macd"], name="MACD",
                             line=dict(width=1, color="blue")), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m["signal"], name="Signal",
                             line=dict(width=1, color="red")), row=2, col=1)
    fig.update_layout(height=600, xaxis_rangeslider_visible=False,
                      margin=dict(l=40, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- ticket
st.subheader("Order ticket")
t1, t2, t3, t4 = st.columns(4)
t_symbol = t1.text_input("Symbol", value=symbol).strip().upper()
default_entry = q.price if (q and t_symbol == q.symbol) else 0.0
entry = t2.number_input("Entry price", min_value=0.0,
                        value=round(default_entry, 2), step=0.01, format="%.2f")
stop = t3.number_input("Stop price", min_value=0.0,
                       value=round(max(default_entry - 0.10, 0.0), 2),
                       step=0.01, format="%.2f")
target = t4.number_input("Target price", min_value=0.0,
                         value=round(default_entry + 0.20, 0.0),
                         step=0.01, format="%.2f")
risk_budget = st.number_input(
    "Risk budget $", min_value=0.0,
    value=round(equity * RISK_PCT_DEFAULT / 100.0, 2), step=10.0)

shares = 0
if entry > 0 and stop > 0 and risk_budget > 0:
    if stop >= entry:
        st.warning("Stop is at/above entry — invalid for a long trade.")
    else:
        shares = broker.position_size(risk_budget, entry, stop)
        stop_dist = entry - stop
        cols = st.columns(3)
        cols[0].info(f"**Shares:** {shares:,}")
        cols[1].info(f"**Position value:** ${shares * entry:,.2f}")
        if target > entry:
            rr = broker.reward_risk(entry, stop, target)
            cols[2].info(f"**R:R:** {rr:.2f}")
            if rr < risk.MIN_REWARD_RISK:
                st.warning(f"R:R {rr:.2f} < {risk.MIN_REWARD_RISK:.1f} — strategy minimum not met.")
        if stop_dist > STOP_MAX_DISTANCE:
            st.warning(f"Stop distance ${stop_dist:.2f} > ${STOP_MAX_DISTANCE:.2f} "
                       "max — reduce size or skip (strategy §5).")
        if shares * entry > account.cash:
            st.warning(f"Position value ${shares * entry:,.2f} exceeds cash "
                       f"${account.cash:,.2f} (no margin).")

b1, b2 = st.columns(2)
if b1.button("BUY", type="primary", use_container_width=True,
             disabled=shares <= 0):
    res = safe(lambda: broker.buy(t_symbol, shares), "Buy")
    if res:
        st.success(f"Bought {res['qty']} {res['symbol']} @ ${res['price']:.2f}")
        st.rerun()
sell_qty_open = sum(p["qty"] for p in positions if p["symbol"] == t_symbol)
if b2.button("SELL (close all)", use_container_width=True,
             disabled=sell_qty_open <= 0):
    res = safe(lambda: broker.sell(t_symbol, int(sell_qty_open)), "Sell")
    if res:
        st.success(f"Sold {res['qty']} {res['symbol']} @ ${res['price']:.2f}")
        st.rerun()

# ---------------------------------------------------------------- positions
st.subheader("Open positions")
if positions:
    rows = []
    for p in positions:
        qpos = quotes.get(p["symbol"])
        cur = qpos.price if qpos else None
        upnl = p["qty"] * (cur - p["avg_cost"]) if cur else None
        rows.append({
            "Symbol": p["symbol"], "Qty": p["qty"],
            "Avg cost": round(p["avg_cost"], 4),
            "Current": round(cur, 2) if cur else None,
            "Unrealized P&L": round(upnl, 2) if upnl is not None else None,
            "P&L %": round((cur / p["avg_cost"] - 1) * 100, 2) if cur else None,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    close_sym = st.selectbox("Close position", [p["symbol"] for p in positions])
    if st.button(f"Close {close_sym}"):
        qty = int(next(p["qty"] for p in positions if p["symbol"] == close_sym))
        res = safe(lambda: broker.sell(close_sym, qty), "Close position")
        if res:
            st.success(f"Closed {res['qty']} {res['symbol']} @ ${res['price']:.2f}")
            st.rerun()
else:
    st.caption("No open positions.")

# ---------------------------------------------------------------- risk panel
st.subheader("Daily risk rules (strategy §8)")
report = risk.daily_report(day_pnl, day_peak_pnl, equity, daily["round_trips"])
rcols = st.columns(len(report.rules))
for col, rule in zip(rcols, report.rules):
    col.markdown(badge(rule.ok, rule.name))
    col.caption(rule.detail)
if report.should_stop:
    st.error("Daily rule violated — the strategy says stop trading for today.")

# ---------------------------------------------------------------- equity curve
st.subheader("Equity curve")
if curve:
    edf = pd.DataFrame(curve)
    edf["timestamp"] = pd.to_datetime(edf["timestamp"])
    st.line_chart(edf.set_index("timestamp")["equity"])
else:
    st.caption("No trades yet — equity curve starts after the first fill.")

# ---------------------------------------------------------------- trade log
st.subheader("Trade log")
history = ledger.get_trade_history()
if history:
    hdf = pd.DataFrame(history)[["timestamp", "symbol", "side", "qty", "price"]]
    st.dataframe(hdf, use_container_width=True, hide_index=True)
else:
    st.caption("No trades yet.")
