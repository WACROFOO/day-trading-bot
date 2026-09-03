"""Streamlit paper-trading platform: five tabs (Scanner / Charts / Trade /
Journal / Risk) over the simulated broker, with a hard, broker-enforced
risk gate.

Launch:  streamlit run src/paper_trading/app.py

Design notes:
- Live panels are ``@st.fragment(run_every=...)`` so quotes, positions and
  risk rules refresh without a full-page rerun. ALL order-action buttons
  live in the main body — a fragment rerun only re-renders its own body.
- Every user selection (ticker, timeframe, ticket inputs, scan results,
  seen-symbols set) lives in ``st.session_state``, seeded once via
  ``setdefault`` with explicit widget keys, so fragment refreshes never
  clobber typing. Ticket prices are re-seeded from the live quote ONLY when
  the ticker changes (guard key ``_ticket_symbol``).
- Bracket stops fire only while this app is running (the stop checker is a
  10s fragment), and free yfinance data is ~15 min delayed.
- UI code never calls ``ledger.record_fill`` directly — every order path
  goes through ``broker`` (which enforces the risk gate on buys).
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# Allow running directly with `streamlit run src/paper_trading/app.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paper_trading import (  # noqa: E402
    broker, datafeed, indicators, ledger, risk, risk_gate, scanner,
)

st.set_page_config(page_title="Paper Trading", layout="wide")

MAX_SCANNER_ROWS = 50      # scanner output cap (PLATFORM.md §4: ~50 hits)
QUICK_SCAN_SIZE = 100
STOP_MAX_DISTANCE = 0.20   # strategy §5: max entry -> stop distance

SESSION_DEFAULTS = {
    "ticker": "AAPL",
    "timeframe": "1m",
    "scan_results": None,
    "seen_symbols": set(),
    "ticket_entry": 0.0,
    "ticket_stop": 0.0,
    "ticket_target": 0.0,
    "ticket_risk": 200.0,
    "attach_stop": True,
}
for _key, _value in SESSION_DEFAULTS.items():
    st.session_state.setdefault(_key, _value)


def _safe(fn, what: str):
    """Run fn, showing a UI error instead of crashing on failure."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - surface any yfinance/data error
        st.error(f"{what} failed: {exc}")
        return None


def _account_snapshot() -> dict:
    """Live account snapshot: positions marked with TTL-cached quotes.

    Offline-tolerant: a symbol whose quote fails is valued at cost, so the
    panels and the risk gate still evaluate during a data outage.
    """
    account = ledger.get_account()
    positions = ledger.get_open_positions()
    quotes: dict[str, broker.Quote] = {}
    for p in positions:
        try:
            quotes[p["symbol"]] = datafeed.get_quote(p["symbol"])
        except Exception:  # noqa: BLE001 - a missing quote must not break panels
            continue
    open_value = sum(
        p["qty"] * (quotes[p["symbol"]].price if p["symbol"] in quotes
                    else p["avg_cost"])
        for p in positions
    )
    unrealized = sum(
        p["qty"] * (quotes[p["symbol"]].price - p["avg_cost"])
        for p in positions if p["symbol"] in quotes
    )
    return {
        "account": account,
        "positions": positions,
        "quotes": quotes,
        "unrealized": unrealized,
        "open_value": open_value,
        "equity": account.cash + open_value,
    }


# ---------------------------------------------------------------- fragments
@st.fragment(run_every=10)
def header_panel() -> None:
    """Account metrics + red lockout banner (refreshes every 10s)."""
    snap = _account_snapshot()
    account = snap["account"]
    gate = risk_gate.RiskGate().state(equity=snap["equity"],
                                      unrealized=snap["unrealized"])
    c1, c2, c3, c4 = st.columns(4)
    equity_delta = ((snap["equity"] - account.starting_cash)
                    / account.starting_cash * 100)
    c1.metric("Equity", f"${snap['equity']:,.2f}", f"{equity_delta:+.2f}%")
    c2.metric("Cash", f"${account.cash:,.2f}")
    c3.metric("Day P&L", f"${gate.day_pnl:,.2f}")
    c4.metric("Open risk", f"${snap['open_value']:,.2f}",
              f"{len(snap['positions'])} position(s)")
    if gate.locked:
        st.error(f"🔒 RISK LOCKOUT — new buys are blocked: "
                 f"{gate.lock_reason}. Exits are always allowed; "
                 "see the Risk tab.")


@st.fragment(run_every=15)
def chart_panel() -> None:
    """Candlesticks + EMA9/EMA20 (VWAP intraday only) with a MACD subplot."""
    symbol = st.session_state["ticker"].strip().upper()
    timeframe = st.session_state["timeframe"]
    if not symbol:
        st.info("Enter a ticker in the sidebar.")
        return
    if timeframe == "D":
        bars = _safe(lambda: datafeed.get_daily_bars(symbol, period="3mo"),
                     "Daily data")
    else:
        bars = _safe(lambda: datafeed.get_intraday_bars(symbol, period="5d",
                                                        interval="1m"),
                     "Intraday data")
    if bars is None or bars.empty:
        return
    if timeframe == "D":
        df = bars.copy()
    else:
        one_min = bars.copy()
        one_min["VWAP"] = indicators.vwap(one_min)  # needs the tz-aware index
        if timeframe == "5m":  # resampled locally from 1m
            df = one_min.resample("5min").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum", "VWAP": "last",
            }).dropna(subset=["Close"])
        else:
            df = one_min
    if df.empty:
        st.info("No chart data.")
        return

    df["EMA9"] = indicators.ema9(df["Close"])
    df["EMA20"] = indicators.ema20(df["Close"])
    m = indicators.macd(df["Close"])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=timeframe), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA9",
                             line=dict(width=1, color="orange")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA20",
                             line=dict(width=1, color="deepskyblue")),
                  row=1, col=1)
    if "VWAP" in df.columns:  # VWAP is intraday-only
        fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP",
                                 line=dict(width=1, color="purple")),
                      row=1, col=1)
    colors = ["green" if h >= 0 else "red" for h in m["hist"]]
    fig.add_trace(go.Bar(x=df.index, y=m["hist"], name="MACD hist",
                         marker_color=colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m["macd"], name="MACD",
                             line=dict(width=1, color="blue")), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m["signal"], name="Signal",
                             line=dict(width=1, color="red")), row=2, col=1)
    fig.update_layout(height=600, xaxis_rangeslider_visible=False,
                      margin=dict(l=40, r=20, t=30, b=20))
    last = df.iloc[-1]
    st.caption(f"{symbol} · {timeframe} · last {last['Close']:,.2f} · "
               f"{len(df)} bars · free data is ~15 min delayed")
    st.plotly_chart(fig)


@st.fragment(run_every=10)
def positions_panel() -> None:
    """Positions with live marks + open orders, and the bracket-stop loop.

    The loop below is what fires attached bracket stops: every 10s it pulls
    the latest 1m bar (open, low) for each symbol with an open STOP order
    and calls ``broker.check_stops``. Stops therefore only fire WHILE THIS
    APP IS RUNNING, and free yfinance data is ~15 min delayed — stop fills
    are simulation-grade, not real-time.
    """
    stop_symbols = sorted({o["symbol"] for o in ledger.get_open_orders()
                           if o["order_type"] == "STOP"})
    traded: dict[str, tuple[float, float]] = {}
    for sym in stop_symbols:
        try:
            bar = datafeed.get_intraday_bars(sym, period="1d",
                                             interval="1m").iloc[-1]
        except Exception:  # noqa: BLE001 - skip symbols with no data
            continue
        traded[sym] = (float(bar["Open"]), float(bar["Low"]))
    if traded:
        for fill in broker.check_stops(traded):
            st.toast(f"STOP fired: sold {fill['qty']:.0f} {fill['symbol']} "
                     f"@ ${fill['price']:.2f}", icon="🛑")

    snap = _account_snapshot()
    st.markdown("**Open positions**")
    if snap["positions"]:
        rows = []
        for p in snap["positions"]:
            q = snap["quotes"].get(p["symbol"])
            cur = q.price if q else None
            upnl = p["qty"] * (cur - p["avg_cost"]) if cur else None
            rows.append({
                "Symbol": p["symbol"], "Qty": p["qty"],
                "Avg cost": round(p["avg_cost"], 4),
                "Current": round(cur, 2) if cur else None,
                "Unrealized P&L": round(upnl, 2) if upnl is not None else None,
                "P&L %": round((cur / p["avg_cost"] - 1) * 100, 2) if cur else None,
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    else:
        st.caption("No open positions.")

    st.markdown("**Open orders**")
    orders = ledger.get_open_orders()
    if orders:
        st.dataframe(pd.DataFrame([{
            "ID": o["id"], "Symbol": o["symbol"], "Side": o["side"],
            "Qty": o["qty"], "Type": o["order_type"],
            "Limit": o["limit_price"], "Stop": o["stop_price"],
            "Reason": o["reason"], "Created": o["created_at"][:19],
        } for o in orders]), hide_index=True)
        st.caption("Cancel orders individually below, or all at once with "
                   "Cancel All — Ctrl+Q.")
    else:
        st.caption("No open orders.")


@st.fragment(run_every=30)
def journal_panel() -> None:
    """Trade-journal metrics, per-day net P&L, and the full fill log."""
    trips = ledger.get_round_trips()
    closed = [t for t in trips if t.closed_at is not None]
    if closed:
        wins = [t.pnl for t in closed if t.pnl > 0]
        losses = [t.pnl for t in closed if t.pnl <= 0]
        r_multiples = [t.pnl / (t.qty * t.risk_per_share)
                       for t in closed
                       if t.risk_per_share is not None
                       and t.risk_per_share > 0 and t.qty > 0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Win rate", f"{len(wins) / len(closed) * 100:.1f}%",
                  f"{len(closed)} round trips")
        c2.metric("Expectancy", f"${statistics.mean(t.pnl for t in closed):,.2f}")
        c3.metric("Avg win", f"${statistics.mean(wins):,.2f}" if wins else "—")
        c4.metric("Avg loss", f"${statistics.mean(losses):,.2f}" if losses else "—")
        c5.metric("Avg R", f"{statistics.mean(r_multiples):.2f}R"
                  if r_multiples else "N/A")
        if not r_multiples:
            st.caption("Avg R is available only for round trips whose entry "
                       "carried a bracket stop (risk per share is unknown "
                       "otherwise).")
    else:
        st.caption("No closed round trips yet.")

    history = ledger.get_trade_history()
    if not history:
        st.caption("No trades yet.")
        return
    st.markdown("**Per-day P&L** (net of commissions)")
    days = sorted({ledger._et_date(t["timestamp"]) for t in history})
    day_rows = []
    for d in days:
        pnl = ledger.get_daily_pnl(d)
        day_rows.append({
            "Date": d, "Trades": pnl["n_trades"], "Sells": pnl["n_sells"],
            "Commissions": round(pnl["commissions"], 2),
            "Net P&L": round(pnl["realized_pnl"], 2),
        })
    st.dataframe(pd.DataFrame(day_rows), hide_index=True)

    st.markdown("**Trade log**")
    st.dataframe(
        pd.DataFrame(history)[["timestamp", "symbol", "side", "qty",
                               "price", "commission", "reason"]],
        hide_index=True)


@st.fragment(run_every=10)
def risk_panel() -> None:
    """Live status of the 5 daily rules + the persisted lockout latch."""
    snap = _account_snapshot()
    gate = risk_gate.RiskGate().state(equity=snap["equity"],
                                      unrealized=snap["unrealized"])
    cols = st.columns(len(gate.report.rules))
    for col, rule in zip(cols, gate.report.rules):
        col.markdown(f"{'🟢' if rule.ok else '🔴'} {rule.name}")
        col.caption(rule.detail)
    if gate.locked:
        st.error(f"Locked ({gate.date}): {gate.lock_reason}. The latch "
                 "persists until a reset below or the next trading day.")
    else:
        st.success("Unlocked — all rules passing.")
    dd_pct = ((1.0 - snap["equity"] / gate.equity_hwm) * 100.0
              if gate.equity_hwm > 0 else 0.0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Equity HWM", f"${gate.equity_hwm:,.2f}")
    c2.metric("Drawdown from HWM", f"{dd_pct:.1f}%")
    c3.metric("Walkaway lock", "ON" if ledger.is_walkaway_locked() else "off")


# ---------------------------------------------------------------- layout
st.title("Paper Trading")
header_panel()

with st.sidebar:
    st.header("Symbol")
    st.text_input("Ticker", key="ticker")
    st.caption("One global ticker for the Charts and Trade tabs. "
               "Free yfinance data is ~15 min delayed.")

tab_scanner, tab_charts, tab_trade, tab_journal, tab_risk = st.tabs(
    ["Scanner", "Charts", "Trade", "Journal", "Risk"])

# ---------------------------------------------------------------- Scanner
with tab_scanner:
    st.subheader("Universe scanner (strategy §1)")
    st.warning("Free yfinance data is ~15 min delayed. A full scan of the "
               "NASDAQ universe (~3,300 symbols) takes several minutes.")
    sc1, sc2 = st.columns(2)
    run_full = sc1.button("Run full scan", key="scan_full", width="stretch")
    run_quick = sc2.button(f"Quick scan (first {QUICK_SCAN_SIZE})",
                           key="scan_quick", width="stretch")
    if run_full or run_quick:
        try:
            universe = scanner.fetch_nasdaq_universe()
        except scanner.NetworkError as exc:
            st.error(f"Could not load symbol directory: {exc}")
            universe = None
        if universe is not None:
            symbols = universe["symbol"].tolist()
            if run_quick:
                symbols = symbols[:QUICK_SCAN_SIZE]
            bar = st.progress(0.0, text="Starting scan...")

            def _progress(done: int, total: int, message: str) -> None:
                bar.progress(done / max(total, 1), text=message)

            results = _safe(
                lambda: scanner.scan(symbols=symbols, progress_cb=_progress),
                "Scan")
            bar.empty()
            if results is not None:
                coverage = results.attrs.get("coverage")
                results = results.head(MAX_SCANNER_ROWS)
                # .head() may drop attrs depending on the pandas version.
                results.attrs["coverage"] = coverage
                current = set(results["symbol"])
                seen = st.session_state["seen_symbols"]
                # The first scan only seeds the baseline silently; later
                # scans toast symbols that newly appear in the hit list.
                if seen:
                    for sym in sorted(current - seen):
                        st.toast(f"New scanner hit: {sym}", icon="🚨")
                st.session_state["seen_symbols"] = seen | current
                st.session_state["scan_results"] = results

    results = st.session_state["scan_results"]
    if results is not None:
        coverage = results.attrs.get("coverage")
        if coverage and coverage.is_degraded:
            st.error(
                f"Incomplete scan — {coverage.summary()}. This is not a "
                "watchlist: most of the universe never returned data, so "
                "passers cannot be told apart from a quiet market. Re-run "
                "once downloads are working.")
    if results is None:
        st.caption("Run a scan to populate the hit list — results are kept "
                   "across refreshes.")
    elif results.empty:
        st.info("No symbols passed the universe filter.")
    else:
        view = results.copy()
        for flag in ("pass_price", "pass_gain", "pass_rvol", "pass_volume"):
            view[flag] = view[flag].map({True: "🟢", False: "🔴"})
        view["float_shares"] = view["float_shares"].apply(
            lambda v: f"{v:,.0f}" if pd.notna(v) else "manual check")
        view["catalyst"] = "manual check"
        st.dataframe(view, hide_index=True)
        st.caption("float_shares and catalyst are manual checks — not "
                   "reliably available from free data.")

        def _load_ticker(sym: str) -> None:
            st.session_state["ticker"] = sym
            st.toast(f"{sym} loaded into the ticker", icon="📈")

        lc1, lc2 = st.columns([3, 1], vertical_alignment="bottom")
        pick = lc1.selectbox("Load a hit into the ticker",
                             results["symbol"].tolist(), key="scan_pick")
        lc2.button("Load", key="scan_load", on_click=_load_ticker,
                   args=(pick,), width="stretch")

# ---------------------------------------------------------------- Charts
with tab_charts:
    st.radio("Timeframe", ["1m", "5m", "D"], key="timeframe", horizontal=True)
    chart_panel()

# ---------------------------------------------------------------- Trade
with tab_trade:
    ticker = st.session_state["ticker"].strip().upper()
    st.subheader(f"Order ticket — {ticker}" if ticker else "Order ticket")
    account = ledger.get_account()

    # Re-seed ticket prices from the live quote ONLY when the ticker changes
    # (guard key "_ticket_symbol"), so auto-refreshing fragments never
    # clobber typing. Widgets below are bound to these session_state keys,
    # so this assignment must run before they are instantiated.
    if ticker and st.session_state.get("_ticket_symbol") != ticker:
        st.session_state["_ticket_symbol"] = ticker
        try:
            px = datafeed.get_quote(ticker).price
        except Exception:  # noqa: BLE001 - the ticket still works quote-less
            px = 0.0
        st.session_state["ticket_entry"] = round(px, 2)
        st.session_state["ticket_stop"] = round(max(px - 0.10, 0.0), 2)
        st.session_state["ticket_target"] = round(px + 0.20, 2)

    t1, t2, t3, t4 = st.columns(4)
    entry = t1.number_input("Entry price", min_value=0.0, step=0.01,
                            format="%.2f", key="ticket_entry")
    stop = t2.number_input("Stop price", min_value=0.0, step=0.01,
                           format="%.2f", key="ticket_stop")
    target = t3.number_input("Target price", min_value=0.0, step=0.01,
                             format="%.2f", key="ticket_target")
    risk_budget = t4.number_input("Risk budget $", min_value=0.0, step=10.0,
                                  format="%.2f", key="ticket_risk")
    attach_stop = st.checkbox("Attach bracket stop (SELL STOP at the stop "
                              "price; fires while the app is running)",
                              key="attach_stop")

    shares = 0
    if entry > 0 and stop > 0 and risk_budget > 0:
        if stop >= entry:
            st.warning("Stop is at/above entry — invalid for a long trade.")
        else:
            sized = broker.position_size(risk_budget, entry, stop)
            affordable = broker.affordable_shares(account.cash, entry)
            shares = min(sized, affordable)
            stop_dist = entry - stop
            cols = st.columns(4)
            cols[0].info(f"**Shares:** {shares:,}")
            cols[1].info(f"**Position value:** ${shares * entry:,.2f}")
            cols[2].info(f"**Est. commission:** "
                         f"${broker.commission_for(shares):,.2f}")
            if target > entry:
                rr = broker.reward_risk(entry, stop, target)
                cols[3].info(f"**R:R:** {rr:.2f}")
                if rr < risk.MIN_REWARD_RISK:
                    st.warning(f"R:R {rr:.2f} < {risk.MIN_REWARD_RISK:.1f} — "
                               "strategy minimum not met.")
            if shares < sized:
                st.caption(f"Size capped by cash: risk-based {sized:,} "
                           f"shares, affordable {affordable:,} (no margin).")
            if shares <= 0:
                st.warning("Size is 0 shares — increase the risk budget or "
                           "the account cash.")
            if stop_dist > STOP_MAX_DISTANCE:
                st.warning(f"Stop distance ${stop_dist:.2f} > "
                           f"${STOP_MAX_DISTANCE:.2f} max — reduce size or "
                           "skip (strategy §5).")

    open_qty = sum(p["qty"] for p in ledger.get_open_positions()
                   if p["symbol"] == ticker)
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("Buy — Shift+2", key="buy_btn", type="primary",
                 width="stretch", disabled=shares <= 0 or not ticker):
        try:
            res = broker.buy(ticker, shares,
                             stop_price=stop if attach_stop else None)
        except risk_gate.RiskVeto as veto:
            st.error(f"Order refused by risk gate: {veto}")
        except Exception as exc:  # noqa: BLE001 - show any broker/data error
            st.error(f"Buy failed: {exc}")
        else:
            st.toast(f"Bought {res['qty']} {res['symbol']} @ "
                     f"${res['price']:.2f}"
                     + (f" · bracket stop @ ${stop:.2f}" if attach_stop
                        else ""), icon="✅")
            st.rerun()
    if b2.button("Sell Full — Ctrl+Z", key="sell_full_btn", width="stretch",
                 disabled=open_qty < 1):
        try:
            res = broker.sell_all(ticker)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Sell failed: {exc}")
        else:
            st.toast(f"Sold {res['qty']} {res['symbol']} @ "
                     f"${res['price']:.2f}", icon="✅")
            st.rerun()
    if b3.button("Sell Half — Ctrl+X", key="sell_half_btn", width="stretch",
                 disabled=open_qty < 2):
        try:
            res = broker.sell_half(ticker)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Sell half failed: {exc}")
        else:
            st.toast(f"Sold {res['qty']} {res['symbol']} @ "
                     f"${res['price']:.2f}", icon="✅")
            st.rerun()
    if b4.button("Cancel All — Ctrl+Q", key="cancel_all_btn", width="stretch"):
        n = broker.cancel_all()
        st.toast(f"Canceled {n} open order(s).", icon="✅")
        st.rerun()
    st.caption("Buttons are labeled with the hotkeys they mirror "
               "(PLATFORM.md §2); Streamlit has no key bindings, so these "
               "are click-only. Exits are never blocked by the risk gate.")

    st.divider()
    positions_panel()

    orders = ledger.get_open_orders()
    if orders:
        with st.expander("Cancel an individual order"):
            for o in orders:
                desc = (f"#{o['id']} · {o['symbol']} {o['side']} "
                        f"{o['qty']:.0f} {o['order_type']}"
                        + (f" @ stop {o['stop_price']:.2f}"
                           if o["stop_price"] else "")
                        + (f" · {o['reason']}" if o["reason"] else ""))
                if st.button(f"Cancel {desc}", key=f"cancel_order_{o['id']}"):
                    ledger.cancel_order(o["id"])
                    st.toast(f"Canceled order #{o['id']}.", icon="✅")
                    st.rerun()

# ---------------------------------------------------------------- Journal
with tab_journal:
    journal_panel()

# ---------------------------------------------------------------- Risk
with tab_risk:
    risk_panel()

    st.divider()
    st.subheader("Manual resets")
    confirm_risk = st.checkbox("Confirm risk resets", key="confirm_risk_reset")
    r1, r2 = st.columns(2)
    if r1.button("Reset for new day", key="reset_day_btn", width="stretch",
                 disabled=not confirm_risk):
        risk_gate.RiskGate().reset_for_new_day()
        st.toast("Today's lockout latch cleared. Rules driven by today's "
                 "realized P&L will re-trip if still violated.", icon="✅")
        st.rerun()
    if r2.button("Reset walkaway lock", key="reset_walkaway_btn",
                 width="stretch", disabled=not confirm_risk):
        risk_gate.RiskGate().reset_walkaway()
        st.toast("Walkaway lock cleared and equity HWM rebased.", icon="✅")
        st.rerun()

    st.divider()
    st.subheader("Reset account")
    confirm_reset = st.checkbox("Confirm reset (wipes all trades)",
                                key="confirm_account_reset")
    new_cash = st.number_input("Starting cash", min_value=100.0,
                               value=ledger.DEFAULT_STARTING_CASH,
                               step=1000.0, key="reset_starting_cash")
    if st.button("Reset account", key="account_reset_btn",
                 disabled=not confirm_reset):
        ledger.reset_account(new_cash)
        st.toast(f"Account reset with ${new_cash:,.2f}", icon="✅")
        st.rerun()
