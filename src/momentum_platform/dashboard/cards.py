"""Decision cards for a built session — the I/O around `decision_card.build_card`.

The session builder calls this at the end of every build (the live desk every
few seconds), and the fixture server calls it again after a manual button
press. It re-runs the first-pullback machine over the session's own bars (the
same default detector the builder runs, so the state is the builder's), reads
the catalyst, and — when a ledger connection is given — the runner's latest
decision, the owner's manual calls and the owner's stated risk.

Reading the ledger is the only I/O, and it is read-only except for nothing:
the desk still never touches the order path (`execution`).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from ..catalyst import card_read
from ..decision_card import bot_line, build_card
from ..models import Bar
from ..pullback import FirstPullbackDetector

RISK_KEY = "manual_dollar_risk"


def _now_of(session: dict) -> datetime:
    frames = session.get("frames") or []
    if frames:
        try:
            return datetime.fromisoformat(frames[-1]["ts"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            pass
    return datetime.now(timezone.utc)


def _risk(conn) -> tuple:
    """(dollars, source, account) — the owner's stated manual risk first, then
    the bot's own (exercise_state), else nothing: never an invented figure."""
    if conn is None:
        return None, None, None
    from journal import ledger as L
    try:
        manual = L.get_setting(conn, RISK_KEY)
        st = L.get_state(conn)
    except Exception:                                     # noqa: BLE001 — a desk without the tables
        return None, None, None
    account = st.get("account_size")
    if manual not in (None, ""):
        try:
            return float(manual), "yours", account
        except ValueError:
            pass
    if st.get("dollar_risk"):
        return float(st["dollar_risk"]), "the bot's", account
    return None, None, account


def cards_for(session: dict, conn=None, now: Optional[datetime] = None, bot_conn="same") -> dict:
    """{symbol: card} for every symbol of a built session. `conn` holds the
    owner's calls and stated risk; `bot_conn` the runner's decisions — the same
    ledger on the live desk, None on a replay (its in-memory ledger never saw
    the bot, and saying "no plan today" there would be false)."""
    if bot_conn == "same":
        bot_conn = conn
    now = now or _now_of(session)
    day = session.get("tradingDate")
    risk, risk_src, account = _risk(conn)
    halts_now = {}
    halt_counts: Counter = Counter()
    for f in session.get("frames") or []:
        for sym, st in (f.get("halts") or {}).items():
            if st == "halted" and halts_now.get(sym) != "halted":
                halt_counts[sym] += 1
            halts_now[sym] = st
    open_manual, manual_rows = {}, {}
    if conn is not None and day:
        from journal import ledger as L
        try:
            open_manual = L.open_manual(conn, day)
            for r in L.manual_rows(conn, day):
                manual_rows[r["symbol"]] = r
        except Exception:                                 # noqa: BLE001
            open_manual, manual_rows = {}, {}
    cards = {}
    for sym, meta in (session.get("symbols") or {}).items():
        rows = (session.get("bars") or {}).get(sym) or []
        det = FirstPullbackDetector()
        for b in rows:
            det.on_bar(Bar(symbol=sym, timeframe="1m", ts=datetime.fromtimestamp(b[0], timezone.utc),
                           open=b[1], high=b[2], low=b[3], close=b[4], volume=b[5]))
        cat = card_read(meta.get("news") or [], now=now, trading_date=meta.get("tradingDate") or day,
                        source_ok=bool(meta.get("newsSourceOk", True)), filings=meta.get("filings"),
                        filings_checked=meta.get("filingsCheckedAt") is not None,
                        split_checked=bool(meta.get("splitChecked")), split_ratio=meta.get("splitRatio"))
        view = None
        if bot_conn is not None and day:
            from journal import ledger as L
            try:
                view = L.bot_view(bot_conn, sym, day)
            except Exception:                             # noqa: BLE001
                view = None
        cards[sym] = build_card(
            sym, meta=meta, cascade=(session.get("cascade") or {}).get(sym) or {}, bars=rows, detector=det,
            now=now, halted=halts_now.get(sym) == "halted", halts_today=halt_counts.get(sym, 0),
            five_minute=(session.get("fiveMinute") or {}).get(sym), catalyst=cat,
            risk=risk, risk_source=risk_src, max_notional=account,
            bot=bot_line(view, bot_conn is not None), manual_open=open_manual.get(sym),
            last_manual=manual_rows.get(sym))
    return cards
