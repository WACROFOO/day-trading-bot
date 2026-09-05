"""Local dashboard server (stdlib only).

    PYTHONPATH=src python -m momentum_platform.dashboard.server

Serves the workstation shell plus the REST surface from the platform spec,
backed by a deterministic replay session. No credentials, no outbound calls:
everything the browser receives is generated from a local fixture.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from datetime import datetime
import threading
import time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .session_builder import build_session

WEB = Path(__file__).parent / "web"
DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[3] / "fixtures" / "market_replay"
    / "workstation_open_2026-09-01.jsonl"
)


class LiveSession:
    """Holds the current session and rebuilds it on a timer.

    A replay is a picture of the tape at the moment it was fetched. Trading
    premarket needs the picture to move: Running Up and HOD must report the
    tape as it is now, and a new runner must be able to join the desk without
    a restart. So, when the source is Alpaca, a background thread rebuilds the
    session every `refresh` seconds and, every `rescan` minutes, re-scans the
    universe and adds any new survivor to the symbol list (capped, because the
    free feed allows about 200 requests a minute and a runner's trade prints
    page deep).

    Every build is stamped; the page polls the stamp and reloads its data when
    it changes. Nothing here places an order.
    """

    def __init__(self, source: str, refresh: int = 0, rescan: int = 0,
                 max_symbols: int = 8) -> None:
        self.source = source
        self.refresh = refresh
        self.rescan = rescan
        self.max_symbols = max_symbols
        self.symbols = source[7:].split(",") if source.startswith("alpaca:") else []
        self.lock = threading.Lock()
        self.screener: "ScreenerLoop | None" = None
        self.records: list = []          # the live session's normalized records
        self.session = self._build()
        self.built_at = time.time()
        self.last_scan = 0.0
        if source.startswith("alpaca:") and refresh > 0:
            threading.Thread(target=self._loop, daemon=True, name="desk-refresh").start()

    def _build(self) -> dict:
        if self.symbols:
            s = self._build_live(full=True)
        else:
            s = _session_from_source(self.source)
        s["live"] = bool(self.refresh) and self.source.startswith("alpaca:") \
            and s.get("dataStatus") in ("iex", "live")
        s["refreshSeconds"] = self.refresh
        s["builtAt"] = time.time()
        return s

    def _build_live(self, full: bool) -> dict:
        """Build the Alpaca session, incrementally when records are held.

        A full rebuild re-fetches a runner's whole day of trade prints — tens
        of pages — which is why the first cut refreshed only once a minute.
        Incrementally, only bars, prints and headlines since two minutes
        before the last held bar are fetched; references are always fresh
        (they carry the IEX last print). The merge is keyed so a re-fetched
        bar replaces its earlier copy rather than duplicating it, and the
        session is rebuilt from the merged records in memory, which is fast.
        """
        from ..datasources.alpaca_source import (
            IEX_VOLUME_FLOOR_SCALE, build_alpaca_session, client_from_env, fetch_records)
        if full or not self.records:
            session = build_alpaca_session(self.symbols)
            self.records = list(session.get("_records") or [])
            return session
        client = client_from_env()
        last_ts = max((r["ts"] for r in self.records if r["type"] == "bar"), default=None)
        since = None
        if last_ts:
            from datetime import datetime, timedelta, timezone
            t = datetime.fromisoformat(last_ts.replace("Z", "+00:00")) - timedelta(minutes=2)
            since = t.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        fresh = fetch_records(client, self.symbols, since=since, profiles=False)
        merged: dict = {}
        for r in self.records + fresh:
            if r["type"] == "bar":
                key = ("bar", r["symbol"], r.get("tf", "1m"), r["ts"])
            elif r["type"] == "news":
                key = ("news", r["symbol"], r.get("provider_id"))
            elif r["type"] == "reference":
                key = ("reference", r["symbol"])
                # keep the profile fields the incremental fetch skipped
                old = merged.get(key)
                if old:
                    for k in ("name", "country", "incorporated_in", "exchange",
                              "float_shares", "float_quality", "float_asof"):
                        if r.get(k) is None and old.get(k) is not None:
                            r[k] = old[k]
            else:
                key = (r["type"], r.get("symbol"), r.get("ts"))
            merged[key] = r
        self.records = list(merged.values())
        from ..dashboard.session_builder import build_session_from_records
        session = build_session_from_records(
            self.records, session_id="alpaca-" + "-".join(self.symbols[:3]),
            source_name="alpaca %s feed" % client.feed, max_rows=10,
            data_status="live" if client.feed == "sip" else "iex",
            volume_floor_scale=1.0 if client.feed == "sip" else IEX_VOLUME_FLOOR_SCALE)
        session["_records"] = self.records
        return session

    def current(self) -> dict:
        with self.lock:
            return self.session

    def add_symbols(self, symbols) -> list:
        """Put new names on the desk; the next refresh builds them in."""
        added = []
        for sym in symbols:
            sym = str(sym).strip().upper()
            if sym and sym not in self.symbols and len(self.symbols) < self.max_symbols:
                self.symbols.append(sym)
                added.append(sym)
        if added:
            self.records = []            # full build with the new names
        return added

    def _loop(self) -> None:
        from ..datasources.alpaca_source import (AlpacaError, client_from_env,
                                                 scan_market)
        from ..scanners.five_pillars import DESK_PRICE_MAX as PRICE_MAX, DESK_PRICE_MIN as PRICE_MIN
        while True:
            time.sleep(self.refresh)
            try:
                if self.rescan and time.time() - self.last_scan >= self.rescan * 60:
                    self.last_scan = time.time()
                    if self.screener is not None and self.screener.current()["rows"]:
                        found = {"rows": self.screener.current()["rows"], "stale": False}
                    else:
                        found = scan_market(client_from_env(), min_price=PRICE_MIN,
                                            max_price=PRICE_MAX, top=self.max_symbols)
                    fresh = [r["symbol"] for r in found["rows"] if r["symbol"] not in self.symbols]
                    if fresh and not found["stale"]:
                        room = max(0, self.max_symbols - len(self.symbols))
                        added = fresh[:room]
                        if added:
                            self.symbols = self.symbols + added
                            self.records = []          # forces a full build with the new names
                            print(f"  rescan: {', '.join(added)} joined the desk")
                s = self._build_live(full=False) if self.symbols else self._build()
                s["live"] = True
                s["refreshSeconds"] = self.refresh
                s["builtAt"] = time.time()
                with self.lock:
                    self.session = s
                    self.built_at = s["builtAt"]
                stamp = datetime.now().strftime("%H:%M:%S")
                print(f"  refreshed {stamp} — {len(s['frames'])} frames, "
                      f"{sum(len(f['alerts']) for f in s['frames'])} alerts")
            except AlpacaError as exc:
                print(f"  refresh failed, keeping the last good session: {exc}")
            except Exception as exc:          # never let the thread die silently
                print(f"  refresh error, keeping the last good session: {exc!r}")


class ScreenerLoop:
    """The screener table, refreshed on a timer, independent of the session.

    The desk session is a handful of symbols with bars. The screener is the
    whole band: every name moving in the current session, from delayed
    consolidated quotes when they are available and from IEX when they are
    not. It runs on its own thread so the page can poll it every few seconds
    without reloading, and its top rows are what join the desk on a rescan.
    """

    def __init__(self, every: int = 60, use_yahoo: bool = True, top: int = 30) -> None:
        self.every = every
        self.use_yahoo = use_yahoo
        self.top = top
        self.lock = threading.Lock()
        self.latest: dict = {"rows": [], "source": "none", "asof": None,
                             "notes": ["screener has not run yet"]}
        threading.Thread(target=self._loop, daemon=True, name="desk-screener").start()

    def current(self) -> dict:
        with self.lock:
            return self.latest

    def _loop(self) -> None:
        from ..datasources.alpaca_source import AlpacaError, client_from_env
        from ..datasources.screener import build_screener
        from ..scanners.five_pillars import DESK_PRICE_MAX as PRICE_MAX, DESK_PRICE_MIN as PRICE_MIN
        yahoo = None
        if self.use_yahoo:
            from ..datasources.yahoo_quotes import YahooQuotes
            yahoo = YahooQuotes()
        while True:
            try:
                out = build_screener(client_from_env(), yahoo=yahoo, min_price=PRICE_MIN,
                                     max_price=PRICE_MAX, top=self.top,
                                     log=lambda m: None)
                with self.lock:
                    self.latest = out
                stamp = datetime.now().strftime("%H:%M:%S")
                print(f"  screener {stamp} — {len(out['rows'])} rows from {out['source']}")
            except AlpacaError as exc:
                with self.lock:
                    self.latest = {"rows": [], "source": "none", "asof": None,
                                   "notes": [f"screener paused: {exc}"]}
                print(f"  screener failed: {exc}")
            except Exception as exc:
                print(f"  screener error: {exc!r}")
            time.sleep(self.every)


@lru_cache(maxsize=4)
def _session_from_source(fixture: str) -> dict:
    """`fixture` is a path, or "live:AAPL,TSLA" for real delayed data."""
    if fixture.startswith("alpaca:"):
        from ..datasources.alpaca_source import AlpacaError, build_alpaca_session
        try:
            return build_alpaca_session(fixture[7:].split(","))
        except AlpacaError as exc:
            # A live-session failure is a message, not a traceback, and it must
            # not leave the user staring at a dead terminal. Say why, then open
            # the recorded session; the header badge reads REPLAY, so the
            # substitution is visible, never silent.
            print("\nCould not build the live session:")
            print("  " + str(exc).replace("\n", "\n  "))
            print("\nOpening the recorded session instead so the desk still comes up.")
            print("Fix the cause above and restart to get live data.\n")
            return build_session(str(DEFAULT_FIXTURE))
    if fixture.startswith("live:"):
        from ..datasources.live_session import build_live_session
        return build_live_session(fixture[5:].split(","))
    return build_session(fixture)


_session = _session_from_source


def make_handler(fixture, live: "LiveSession | None" = None, screener: "ScreenerLoop | None" = None):
    holder = live or LiveSession(fixture)
    if screener is None and getattr(holder, "screener", None) is not None:
        screener = holder.screener
    hub = getattr(holder, "hub", None)              # IBKR desk: server-sent events
    class Handler(BaseHTTPRequestHandler):
        server_version = "MomentumWorkstation/0.1"

        def log_message(self, fmt, *args):  # quieter console
            pass

        def handle(self):
            try:
                super().handle()
            except (ConnectionResetError, BrokenPipeError):
                pass                     # the page closed its event stream; normal

        def _send(self, body: bytes, ctype: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload, status: int = 200) -> None:
            self._send(json.dumps(payload, default=str).encode(), "application/json", status)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            session = holder.current()

            if path in ("/", "/index.html"):
                return self._send((WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/session.js":
                public = {k: v for k, v in session.items() if not k.startswith("_")}
                body = b"window.__SESSION__=" + json.dumps(public, default=str).encode() + b";"
                return self._send(body, "application/javascript")
            if path == "/api/v1/health":
                payload = {"status": "ok",
                           "mode": "live" if session.get("live") else "replay",
                           "fixture": Path(str(fixture)).name,
                           "builtAt": session.get("builtAt"),
                           "refreshSeconds": session.get("refreshSeconds", 0),
                           "streaming": bool(hub is not None),
                           "symbols": list(session.get("symbols", {}).keys())}
                if hasattr(holder, "health"):
                    payload["provider"] = holder.health()
                if hasattr(holder, "fingerprint"):
                    payload["desk"] = holder.fingerprint()
                else:
                    from .. import desk_profile
                    payload["desk"] = desk_profile.fingerprint()
                return self._json(payload)
            if path == "/api/v1/stream":
                if hub is None:
                    return self._json({"error": "no live stream on this session; start with --ibkr"}, 404)
                from .stream import SSE_HEADERS, parse_last_event_id, serve_sse
                self.send_response(200)
                for k, v in SSE_HEADERS:
                    self.send_header(k, v)
                self.end_headers()
                serve_sse(hub, self.wfile, parse_last_event_id(self.headers.get("Last-Event-ID")),
                          flush=self.wfile.flush)
                return None
            if path == "/api/v1/data-health":
                return self._json({
                    "provider": "replay-fixture", "connectionState": "replay",
                    "frames": len(session["frames"]), "symbols": len(session["symbols"]),
                    "note": "Deterministic fixture. No live entitlement is in use.",
                })
            if path == "/api/v1/scanners":
                return self._json({
                    "lists": session["listMeta"], "alerts": session["alertMeta"],
                    "definitionVersions": session["definitionVersions"],
                })
            if path == "/api/v1/screener":
                return self._json(screener.current() if screener else
                                  {"rows": [], "source": "none", "asof": None,
                                   "notes": ["screener runs only with a live Alpaca session"]})
            if path == "/api/v1/desk/add":
                from urllib.parse import parse_qs
                wanted = parse_qs(urlparse(self.path).query).get("symbol", [])
                if not holder.symbols:
                    return self._json({"added": [], "symbols": [],
                                       "note": "the recorded session cannot take new symbols"}, 400)
                added = holder.add_symbols(wanted)
                return self._json({"added": added, "symbols": holder.symbols,
                                   "note": ("joins the desk in a few seconds" if hub is not None else
                                            "joins the desk on the next refresh") if added else
                                   "already on the desk, or the desk is full"})
            if path == "/api/v1/replay/session":
                return self._json({k: v for k, v in session.items() if not k.startswith("_")})
            if path == "/api/v1/scanner-events":
                events = [a for f in session["frames"] for a in f["alerts"]]
                return self._json({"count": len(events), "events": events})

            asset = (WEB / path.lstrip("/")).resolve()
            if asset.is_file() and WEB.resolve() in asset.parents:
                ctype = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                return self._send(asset.read_bytes(), ctype)
            self._json({"error": "not found", "path": path}, status=404)

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Momentum Workstation replay dashboard")
    ap.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    ap.add_argument("--alpaca", metavar="SYMBOLS",
                    help="comma-separated symbols to load from Alpaca (free IEX feed); "
                         "credentials come from .env")
    ap.add_argument("--live", metavar="SYMBOLS",
                    help="comma-separated real symbols to load from yfinance "
                         "(delayed ~15m) instead of a replay fixture")
    ap.add_argument("--refresh", type=int, default=None, metavar="SECONDS",
                    help="refresh a live Alpaca session this often (default 20 with --alpaca)")
    ap.add_argument("--rescan", type=int, default=0, metavar="MINUTES",
                    help="with --alpaca: re-scan the universe this often and add new runners")
    ap.add_argument("--screener-every", type=int, default=60, metavar="SECONDS",
                    help="with --alpaca: refresh the whole-band screener this often (0 = off)")
    ap.add_argument("--no-yahoo", action="store_true",
                    help="screener uses IEX snapshots only, never Yahoo delayed quotes")
    ap.add_argument("--ibkr", metavar="SYMBOLS", nargs="?", const="",
                    help="live IBKR desk over TWS (read-only). Optional comma-separated symbols; "
                         "with none, the scanner union picks today's runners. Needs TWS on "
                         "IBKR_HOST:IBKR_PORT (default 127.0.0.1:7496).")
    ap.add_argument("--ibkr-rescan", type=int, default=120, metavar="SECONDS",
                    help="with --ibkr: run the NASDAQ scanner union this often (0 = off)")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)

    source = (f"alpaca:{args.alpaca}" if args.alpaca
              else f"live:{args.live}" if args.live
              else args.fixture)
    refresh = args.refresh if args.refresh is not None else (20 if args.alpaca else 0)
    screener = None
    live = None
    if args.ibkr is not None:
        live = _ibkr_desk(args, refresh if args.refresh is not None else 3)
    if live is None:
        live = LiveSession(source, refresh=refresh if args.alpaca else 0, rescan=args.rescan)
    else:
        source = live.source
    if args.alpaca and args.screener_every > 0:
        import os
        use_yahoo = (not args.no_yahoo) and os.environ.get("PREMARKET_QUOTES", "yahoo").lower() != "off"
        screener = ScreenerLoop(every=args.screener_every, use_yahoo=use_yahoo)
        live.screener = screener
    session = live.current()
    print(f"session: {len(session['frames'])} frames, {len(session['symbols'])} symbols, "
          f"{sum(len(f['alerts']) for f in session['frames'])} alerts")
    print(f"workstation: http://{args.host}:{args.port}/")
    # Describe the feed the session ACTUALLY carries. Asking for --alpaca and
    # falling back to the fixture used to still print "Alpaca IEX feed", which
    # tells the user they are on live data when they are not.
    ibkr = getattr(live, "hub", None) is not None
    if ibkr:
        pass                                   # the IBKR lines below describe this desk
    elif session.get("dataStatus") in ("iex", "live"):
        print("Alpaca IEX feed — single venue, so absolute volume is a fraction of the "
              "consolidated tape. Research only.")
    elif args.alpaca:
        print("RECORDED SESSION — the live feed failed above, so this is not today's "
              "market. The header badge reads REPLAY.")
    if args.live:
        print("DELAYED data (~15 minutes) — research only, not an entitled feed")
    if session.get("live") and not ibkr:
        print(f"LIVE — the session rebuilds every {refresh}s"
              + (f" and re-scans the market every {args.rescan} min" if args.rescan else "")
              + ". The page follows the live edge on its own.")
    if screener is not None:
        print(f"SCREENER — the whole band, every {args.screener_every}s, "
              + ("Yahoo delayed quotes with IEX fallback" if screener.use_yahoo else "IEX only")
              + ". Click a row to put it on the desk.")
    if getattr(live, "hub", None) is not None:
        h = live.health()
        print(f"IBKR — TWS read-only, client {h.get('clientId')} (desk) / {h.get('scannerClientId')} "
              f"(scanner), market data type {h.get('marketDataType')}, feed {h.get('state')}.")
        print(f"STREAMING — candles, quotes and health reach the page as they happen; the session "
              f"rebuilds every {live.rebuild}s and the scanner union runs every {live.rescan}s.")
    ThreadingHTTPServer((args.host, args.port), make_handler(source, live, screener)).serve_forever()
    return 0


def _ibkr_desk(args, rebuild: int):
    """Start the IBKR desk, or say exactly why it could not and return None
    so the caller falls back to the recorded session — visibly."""
    import os
    from .ibkr_desk import IbkrDesk
    from ..datasources.ibkr_scanner import IbkrError
    from ..scanners.five_pillars import DESK_PRICE_MAX as PRICE_MAX, DESK_PRICE_MIN as PRICE_MIN
    symbols = [s for s in (args.ibkr or "").split(",") if s.strip()]
    print("Starting the IBKR desk. Scan, quotes and history take 30-90 s the first time; "
          "the line 'desk ready' means the page is up.", flush=True)
    desk = IbkrDesk(symbols, host=os.environ.get("IBKR_HOST", "127.0.0.1"),
                    port=int(os.environ.get("IBKR_PORT", "7496")),
                    rebuild=rebuild, rescan=args.ibkr_rescan,
                    min_price=PRICE_MIN, max_price=PRICE_MAX)
    try:
        desk.start()
        return desk
    except IbkrError as exc:
        print("\nCould not start the IBKR desk:")
        print("  " + str(exc).replace("\n", "\n  "))
        print("\nOpening the recorded session instead so the desk still comes up.")
        print("Fix the cause above and restart to get live data.\n")
        desk.stop()
        return None
    except Exception as exc:
        print(f"\nCould not start the IBKR desk: {exc!r}")
        print("Opening the recorded session instead. Run: python3 scripts/ibkr_preflight.py\n")
        desk.stop()
        return None


if __name__ == "__main__":
    raise SystemExit(main())
