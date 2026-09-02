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


@lru_cache(maxsize=4)
def _session(fixture: str) -> dict:
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


def make_handler(fixture: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MomentumWorkstation/0.1"

        def log_message(self, fmt, *args):  # quieter console
            pass

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
            session = _session(fixture)

            if path in ("/", "/index.html"):
                return self._send((WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/session.js":
                body = b"window.__SESSION__=" + json.dumps(session, default=str).encode() + b";"
                return self._send(body, "application/javascript")
            if path == "/api/v1/health":
                return self._json({"status": "ok", "mode": "replay", "fixture": Path(fixture).name})
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
            if path == "/api/v1/replay/session":
                return self._json(session)
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
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)

    source = (f"alpaca:{args.alpaca}" if args.alpaca
              else f"live:{args.live}" if args.live
              else args.fixture)
    session = _session(source)
    print(f"session: {len(session['frames'])} frames, {len(session['symbols'])} symbols, "
          f"{sum(len(f['alerts']) for f in session['frames'])} alerts")
    print(f"workstation: http://{args.host}:{args.port}/")
    # Describe the feed the session ACTUALLY carries. Asking for --alpaca and
    # falling back to the fixture used to still print "Alpaca IEX feed", which
    # tells the user they are on live data when they are not.
    if session.get("dataStatus") in ("iex", "live"):
        print("Alpaca IEX feed — single venue, so absolute volume is a fraction of the "
              "consolidated tape. Research only.")
    elif args.alpaca:
        print("RECORDED SESSION — the live feed failed above, so this is not today's "
              "market. The header badge reads REPLAY.")
    if args.live:
        print("DELAYED data (~15 minutes) — research only, not an entitled feed")
    ThreadingHTTPServer((args.host, args.port), make_handler(source)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
