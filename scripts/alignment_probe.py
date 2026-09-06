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

OK, BAD, WARN, DIM, END = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
def good(m): print(f"  {OK}ok{END}   {m}")
def bad(m): print(f"  {BAD}xx{END}   {m}")
def warn(m): print(f"  {WARN}!!{END}   {m}")
def note(m): print(f"       {DIM}{m}{END}")


def connect(IB, name, host, port, cid):
    ib = IB()
    try:
        ib.connect(host, port, clientId=cid, readonly=True, timeout=10)
    except Exception as exc:                        # noqa: BLE001
        bad(f"{name}: cannot reach {host}:{port} — {exc}")
        return None
    good(f"{name}: connected {host}:{port} client {cid} read-only · accounts {list(ib.managedAccounts())}")
    return ib


def main() -> int:
    print(f"\nData alignment probe   {SYMBOL}   live {LIVE[1]} vs paper {PAPER[1]}")
    note("both connections read-only; nothing order-shaped is sent")
    try:
        from ib_async import IB, Stock
    except ImportError:
        bad("ib_async is not installed"); note("python3 -m pip install ib_async==2.1.0"); return 1

    live = connect(IB, "LIVE ", *LIVE)
    paper = connect(IB, "PAPER", *PAPER)
    if live is None or paper is None:
        for ib in (live, paper):
            if ib: ib.disconnect()
        return 2
    try:
        if not all(a.startswith("DU") for a in paper.managedAccounts()):
            bad("the 'paper' session is not a paper account — stopping"); return 3

        stock = Stock(SYMBOL, "SMART", "USD")
        live.qualifyContracts(stock); paper.qualifyContracts(stock)
        # Ask for real-time explicitly on both; IBKR downgrades to delayed
        # (type 3) by itself when the account is not entitled, and the type
        # it actually serves is the first thing worth knowing.
        live.reqMarketDataType(1); paper.reqMarketDataType(1)
        tl = live.reqMktData(stock, "", False, False)
        tp = paper.reqMktData(stock, "", False, False)

        print(f"\nSampling {SAMPLE_S}s")
        print(f"  {'t':>3}  {'LIVE last':>10} {'bid':>8} {'ask':>8} {'ts':>9}   {'PAPER last':>10} {'bid':>8} {'ask':>8} {'ts':>9}")
        rows = []
        for i in range(SAMPLE_S // 2):
            live.sleep(1); paper.sleep(1)
            def f(x): return "—" if x is None or x != x or x < 0 else f"{x:.2f}"
            def ts(t): return t.time.astimezone().strftime("%H:%M:%S") if getattr(t, "time", None) else "—"
            rows.append((tl.last, tl.bid, tl.ask, tp.last, tp.bid, tp.ask, getattr(tl, "time", None), getattr(tp, "time", None)))
            print(f"  {2*i+2:>3}  {f(tl.last):>10} {f(tl.bid):>8} {f(tl.ask):>8} {ts(tl):>9}   {f(tp.last):>10} {f(tp.bid):>8} {f(tp.ask):>8} {ts(tp):>9}")

        live_ok = any(r[0] is not None and r[0] == r[0] and r[0] > 0 for r in rows)
        paper_ok = any(r[3] is not None and r[3] == r[3] and r[3] > 0 for r in rows)
        lags = [(a - b).total_seconds() for *_, a, b in rows if a and b]
        mtype_p = getattr(tp, "marketDataType", None)

        print("\nVERDICT")
        if not live_ok:
            warn("LIVE session shows no prints — market closed, or no subscription on the live account")
            verdict = "none"
        if not paper_ok:
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
            good(f"PAPER session is on real-time data (type {mtype_p}); median stamp gap {med if med is not None else '—'}s")
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
