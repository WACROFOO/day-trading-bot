"""The screener: what a TradingView screener tab shows, on this desk's data.

One table, refreshed on a timer, of every name in the price band that is
moving in the CURRENT session — premarket before 09:30, regular after — with
the number the operator actually wants: today's change against yesterday's
close, as of right now.

Two sources, used in this order:

  1. Yahoo delayed quotes (consolidated, ~15 min delayed, unofficial). Before
     the open this is the only free number that reflects the premarket move.
  2. Alpaca IEX snapshots (real-time, single venue). Premarket coverage in
     microcaps is thin; from ~07:00 ET it fills in and at 09:30 it is whole.

Every row says which source produced it and how old the print is. When Yahoo
is unavailable the table does not go quiet: it falls back to IEX and says so.
Discovery only — the pillars and scanners stay on the entitled feed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from .alpaca_source import AlpacaClient, AlpacaError, exchange_map, momentum_universe


def _pool(client: AlpacaClient, min_price: float, max_price: float,
          pool_limit: int, log) -> List[dict]:
    """Names worth quoting: in a lenient price band on the last IEX daily bar.

    Eleven thousand tickers is too many for any quote endpoint on a timer.
    Yesterday's close between half the band's floor and 1.5x its ceiling
    keeps a runner that gaps into the band while dropping the S&P 500."""
    universe = momentum_universe(client)
    try:
        ex_map = exchange_map(client)
    except AlpacaError:
        ex_map = {}
    snaps = client.snapshots(universe)
    lo, hi = min_price * 0.5, max_price * 1.5
    rows = []
    for sym, snap in snaps.items():
        if not snap:
            continue
        prev = snap.get("prevDailyBar") or {}
        day = snap.get("dailyBar") or {}
        pc = prev.get("c")
        if not pc or not (lo <= pc <= hi):
            continue
        last_tr = snap.get("latestTrade") or {}
        rows.append({
            "symbol": sym, "prev_close": pc, "exchange": ex_map.get(sym),
            "iex_price": last_tr.get("p"), "iex_time": last_tr.get("t"),
            "iex_day_volume": day.get("v") or 0, "iex_day_date": str(day.get("t") or "")[:10],
        })
    rows.sort(key=lambda r: -(r["iex_day_volume"] or 0))
    log(f"  pool: {len(rows):,} names near the band" + (f", quoting the first {pool_limit:,}" if len(rows) > pool_limit else ""))
    return rows[:pool_limit] if pool_limit else rows


def build_screener(client: AlpacaClient, yahoo=None, min_price: float = 2.0,
                   max_price: float = 20.0, min_gain: float = 10.0, top: int = 30,
                   pool_limit: int = 2000, log=None) -> dict:
    say = log or (lambda *_: None)
    today = datetime.now(timezone.utc).astimezone().date().isoformat()
    result = {"rows": [], "source": "iex", "asof": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "notes": [], "band": [min_price, max_price], "min_gain": min_gain}
    pool = _pool(client, min_price, max_price, pool_limit, say)
    by_sym = {r["symbol"]: r for r in pool}

    quotes = {}
    if yahoo is not None:
        try:
            quotes = yahoo.quotes([r["symbol"] for r in pool])
            result["source"] = "yahoo-delayed"
            say(f"  yahoo: {len(quotes):,} quotes")
        except Exception as exc:               # unofficial source: never fatal
            result["notes"].append(f"Yahoo premarket quotes unavailable ({exc}); showing IEX only.")
            say(f"  yahoo unavailable: {exc}")

    rows = []
    for sym, base in by_sym.items():
        q = quotes.get(sym)
        if q and q.get("price") is not None and q.get("change_pct") is not None:
            price, chg, src = q["price"], q["change_pct"], "yahoo"
            asof = q.get("as_of")
            session = q.get("session")
        else:
            price = base.get("iex_price")
            pc = base.get("prev_close")
            if not price or not pc:
                continue
            chg, src, asof, session = (price / pc - 1) * 100, "iex", base.get("iex_time"), None
        if not (min_price <= price <= max_price) or chg < min_gain:
            continue
        rows.append({
            "symbol": sym, "price": round(price, 4), "change_pct": round(chg, 2),
            "source": src, "as_of": asof, "session": session,
            "prev_close": base.get("prev_close"), "exchange": base.get("exchange"),
            "iex_day_volume": base.get("iex_day_volume"),
            "name": (q or {}).get("name"), "float_shares": (q or {}).get("float_shares"),
        })
    rows.sort(key=lambda r: -r["change_pct"])
    result["rows"] = rows[:top] if top else rows
    if not quotes and yahoo is not None and not result["notes"]:
        result["notes"].append("Yahoo returned no quotes; showing IEX only.")
    if result["source"] == "iex":
        result["notes"].append("IEX is one venue; before ~07:00 ET a runner may show no move here while other venues print.")
    say(f"  screener: {len(result['rows'])} rows from {result['source']}")
    return result
