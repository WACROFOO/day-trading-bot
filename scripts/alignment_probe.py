#!/usr/bin/env python3
"""Is the paper session looking at the same tape as the live one?

    python3 scripts/alignment_probe.py [SYMBOL]      # any time the market is open

Decisions are made on the LIVE TWS feed (7496, read-only). Orders go to
the PAPER Gateway (4002). IBKR simulates paper fills against whatever data
the paper account can see — and the paper preflight showed it can see
nothing (`last=nan bid=-1`). If IBKR's default for paper is delayed data,
every simulated fill is judged against a tape 15 minutes behind the one
the decision was made on, and no slippage number means anything.

IBKR lets a paper account share the live account's market-data
subscriptions (Client Portal › Settings › Paper Trading Account). This
script measures whether that is in effect, rather than assuming either way:
it subscribes to the same symbol on both sessions, read-only, for twenty
seconds, and compares what each reports and when.

Nothing here places, prices or cancels an order. Both connections are
read-only. Client ids 33 (live) and 34 (paper) so nothing collides with the
desk (27/28), the preflights (29/32) or the executor (31).

Exit codes:
  0  probe ran; read the verdict
  1  ib_async is not installed
  2  a session was not reachable (which one is printed)
  3  the paper session is NOT a paper account — stopped, nothing sent
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SYMBOL = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ALIGN_SYMBOL", "AAPL")).upper()
LIVE = ("127.0.0.1", int(os.environ.get("IBKR_PORT", "7496")), 33)
PAPER = ("127.0.0.1", int(os.environ.get("IBKR_PAPER_PORT", "4002")), 34)
SAMPLE_S = 20
from zoneinfo import ZoneInfo  # noqa: E402
ET = ZoneInfo("America/New_York")

OK, BAD, WARN, DIM, END = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
def good(m): print(f"  {OK}ok{END}   {m}")
def bad(m): print(f"  {BAD}xx{END}   {m}")
def warn(m): print(f"  {WARN}!!{END}   {m}")
def note(m): print(f"       {DIM}{m}{END}")


def mask(acct: str) -> str:
    """U27412209 -> U****2209. Outputs get pasted into chats; the id need not."""
    return acct[:1] + "****" + acct[-4:] if len(acct) > 5 else acct


ERRORS: dict[str, list[tuple[int, str]]] = {"LIVE ": [], "PAPER": []}


def connect(IB, name, host, port, cid):
    ib = IB()
    try:
        ib.connect(host, port, clientId=cid, readonly=True, timeout=10)
    except Exception as exc:                        # noqa: BLE001
        bad(f"{name}: cannot reach {host}:{port} — {exc}")
        return None
    # Every API error is kept, by session. Error 10197 on the paper side is a
    # verdict of its own (see main), and it arrives as an event, not a value.
    ib.errorEvent += lambda reqId, code, msg, contract=None, *a: ERRORS[name].append((code, msg))
    good(f"{name}: connected {host}:{port} client {cid} read-only · "
         f"accounts {[mask(a) for a in ib.managedAccounts()]}")
    return ib


def probe_mode(live_port: int, paper_port: int, live_reachable: bool) -> str:
    """'single' when both point at one session (IBKR_PORT=4002 — the desk and
    the executor share the paper login and there is one tape by construction);
    'paper-only' when TWS is logged out and only the paper session answers;
    'compare' when both sessions are up."""
    if live_port == paper_port:
        return "single"
    return "compare" if live_reachable else "paper-only"


def main() -> int:
    print(f"\nData alignment probe   {SYMBOL}   live {LIVE[1]} vs paper {PAPER[1]}")
    note("both connections read-only; nothing order-shaped is sent")
    try:
        from ib_async import IB, Stock
    except ImportError:
        bad("ib_async is not installed"); note("python3 -m pip install ib_async==2.1.0"); return 1

    single = LIVE[1] == PAPER[1]
    live = None if single else connect(IB, "LIVE ", *LIVE)
    paper = connect(IB, "PAPER", *PAPER)
    if paper is None:
        if live: live.disconnect()
        return 2
    mode = probe_mode(LIVE[1], PAPER[1], live is not None)
    if mode == "single":
        note("single-login mode: desk and executor share the paper session (IBKR_PORT=4002).")
        note("Decision tape and fill tape are the same tape by construction; the only")
        note("question left is whether that tape is real-time.")
    elif mode == "paper-only":
        warn("LIVE session not reachable — TWS logged out? Judging the paper session alone.")
    try:
        if not all(a.startswith("DU") for a in paper.managedAccounts()):
            bad("the 'paper' session is not a paper account — stopping"); return 3

        stock = Stock(SYMBOL, "SMART", "USD")
        paper.qualifyContracts(stock)
        # Ask for real-time explicitly; IBKR downgrades to delayed (type 3) by
        # itself when the account is not entitled, and the type it actually
        # serves is the first thing worth knowing.
        paper.reqMarketDataType(1)
        tp = paper.reqMktData(stock, "", False, False)
        if live is not None:
            live.qualifyContracts(stock); live.reqMarketDataType(1)
            tl = live.reqMktData(stock, "", False, False)
        else:
            class _Empty:                         # a live side that says nothing
                last = bid = ask = None; time = None; marketDataType = None
            tl = _Empty()

        print(f"\nSampling {SAMPLE_S}s")
        print(f"  {'t':>3}  {'LIVE last':>10} {'bid':>8} {'ask':>8} {'ts':>9}   {'PAPER last':>10} {'bid':>8} {'ask':>8} {'ts':>9}")
        rows = []
        for i in range(SAMPLE_S // 2):
            paper.sleep(2 if live is None else 1)
            if live is not None: live.sleep(1)
            def f(x): return "—" if x is None or x != x or x < 0 else f"{x:.2f}"
            def ts(t): return t.time.astimezone(ET).strftime("%H:%M:%S") if getattr(t, "time", None) else "—"
            rows.append((tl.last, tl.bid, tl.ask, tp.last, tp.bid, tp.ask, getattr(tl, "time", None), getattr(tp, "time", None)))
            print(f"  {2*i+2:>3}  {f(tl.last):>10} {f(tl.bid):>8} {f(tl.ask):>8} {ts(tl):>9}   {f(tp.last):>10} {f(tp.bid):>8} {f(tp.ask):>8} {ts(tp):>9}")

        live_ok = any(r[0] is not None and r[0] == r[0] and r[0] > 0 for r in rows)
        paper_ok = any(r[3] is not None and r[3] == r[3] and r[3] > 0 for r in rows)
        lags = [(a - b).total_seconds() for *_, a, b in rows if a and b]
        mtype_p = getattr(tp, "marketDataType", None)

        competing = any(code == 10197 for code, _ in ERRORS["PAPER"])
        try:
            from momentum_platform.holidays import why_closed
            closed = why_closed(datetime.now(timezone.utc).astimezone(ET).date())
        except Exception:                            # noqa: BLE001
            closed = None

        print("\nVERDICT")
        if closed and not competing and not paper_ok:
            # No prints can exist on a closed market. The two facts that CAN be
            # read today — the entitlement type and the absence of 10197 — are
            # reported, and the realtime/delayed/none verdict waits for an
            # open market rather than being written as 'none' (2026-09-07).
            good(f"paper session entitlement: market data type {mtype_p} · no competing-session error")
            warn(f"{closed} — no prints to judge; verdict deferred to the next open market")
            print("VERDICT: deferred")
            return 0
        if live is not None and not live_ok:
            warn("LIVE session shows no prints — market closed, or no subscription on the live account")
            verdict = "none"
        if competing:
            # IBKR error 10197, seen on the first live run (2026-09-07): the
            # paper session is refused market data BECAUSE the live TWS
            # session is logged in and holds the same subscriptions. This is
            # not the holiday, not the Client Portal setting, and not fixable
            # from this side while both are logged in.
            bad("PAPER session refused market data: IBKR 10197 'No market data during "
                "competing live session'")
            note("Your live TWS login holds the subscriptions; the paper session cannot")
            note("share them while TWS is logged in. Two ways to test on a trading day:")
            note("  a) log OUT of TWS, keep the Gateway (paper) up, re-run this probe;")
            note("  b) run the whole desk off the paper Gateway for a day:")
            note("     IBKR_PORT=4002 python3 scripts/day.py   (with TWS logged out)")
            note("If (a) reads realtime, the exercise should run as (b): one login, one tape.")
            verdict = "competing"
        elif not paper_ok:
            bad("PAPER session shows NO market data")
            note("IBKR simulates paper fills against the data the paper account can see.")
            note("With none, fills are against something you cannot see or check.")
            verdict = "none"
        elif mtype_p in (3, 4):
            bad(f"PAPER session is on DELAYED data (market data type {mtype_p})")
            note("Every simulated fill would be judged against a tape ~15 min behind the")
            note("decision. Fix in Client Portal › Settings › Paper Trading Account:")
            note("'Share real-time market data subscriptions with paper trading account'.")
            verdict = "delayed"
        else:
            med = sorted(lags)[len(lags) // 2] if lags else None
            good(f"PAPER session is on real-time data (type {mtype_p})"
                 + (f"; median stamp gap vs live {med}s" if med is not None else
                    " — the only session, so nothing to lag against"))
            note("Decision tape and fill tape are the same tape. Slippage is measurable.")
            verdict = "realtime"
        print(f"VERDICT: {verdict}")
        try:
            from journal import ledger as L
            conn = L.connect(os.environ.get("JOURNAL_DB") or L.DEFAULT_DB)
            L.set_state(conn, paper_data=verdict,
                        paper_data_date=datetime.now(timezone.utc).astimezone(L.ET).date().isoformat())
            note("recorded in exercise_state")
        except Exception as exc:                    # noqa: BLE001
            warn(f"verdict NOT recorded: {exc}")
        return 0
    finally:
        for ib in (live, paper):
            try: ib.disconnect()
            except Exception: pass                  # noqa: BLE001


if __name__ == "__main__":
    sys.exit(main())
