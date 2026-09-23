#!/usr/bin/env python3
"""What the desk's scanners fired, from the running desk, filtered.

    python3 scripts/alerts.py WHLR MSS --from 09:30 --to 09:45
    python3 scripts/alerts.py --from 09:30            # every symbol

Reads /api/v1/scanner-events on the live desk (default 127.0.0.1:8787).
Nothing is computed here: every line is an event the desk recorded, with
the scanner, the branch, the price and each condition's value. Its use is
the question "why did the scanner not fire on X at HH:MM": what DID fire on X
around then is the evidence, and a scanner absent from the list is the
scanner to read. The desk keeps events in memory for the session; once it
stops, this is empty.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def et_hhmm(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ET).strftime("%H:%M:%S")
    except ValueError:
        return iso[11:19]


def select(events: list[dict], symbols: list[str], t_from: str | None, t_to: str | None,
           scanners: list[str] | None = None) -> list[dict]:
    """Filter by symbol, ET time window (HH:MM, inclusive) and scanner id."""
    want = {s.upper() for s in symbols}
    out = []
    for e in events:
        if want and e.get("symbol", "").upper() not in want:
            continue
        if scanners and e.get("scannerId") not in scanners:
            continue
        hhmm = et_hhmm(e.get("sourceTime") or e.get("observedTime") or "")[:5]
        if t_from and hhmm < t_from:
            continue
        if t_to and hhmm > t_to:
            continue
        out.append(e)
    out.sort(key=lambda e: e.get("sourceTime") or "")
    return out


def format_event(e: dict) -> str:
    vals = e.get("values") or {}
    last = vals.get("last")
    reasons = e.get("reasons") or []
    parts = []
    for r in reasons:
        mark = "✓" if r.get("passed") else "✗"
        thr = r.get("threshold")
        parts.append(f"{mark}{r.get('field')}={r.get('value')}" + (f"/{thr}" if thr is not None else ""))
    return (f"  {et_hhmm(e.get('sourceTime') or '')} {e.get('symbol', '?'):<6}{e.get('scannerId', '?'):<18}"
            f"{(e.get('branch') or '—'):<24}{(e.get('severity') or ''):<9}"
            f"{('last ' + str(last)) if last is not None else '':<12} {' '.join(parts)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="*", help="symbols to show (default: all)")
    ap.add_argument("--from", dest="t_from", help="ET HH:MM, inclusive")
    ap.add_argument("--to", dest="t_to", help="ET HH:MM, inclusive")
    ap.add_argument("--scanner", action="append", help="scanner id, repeatable (hod_momentum, running_up, squeeze_5_in_5, ...)")
    ap.add_argument("--url", default="http://127.0.0.1:8787", help="the desk (default 127.0.0.1:8787)")
    args = ap.parse_args(argv)
    try:
        with urllib.request.urlopen(f"{args.url}/api/v1/scanner-events", timeout=10) as r:
            payload = json.load(r)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"desk not reachable at {args.url}: {exc!r} — the desk must be running; its events live in memory "
              f"for the session only")
        return 1
    events = payload.get("events") or []
    rows = select(events, args.symbols, args.t_from, args.t_to, args.scanner)
    print(f"DESK SCANNER EVENTS  {len(rows)} of {len(events)} recorded"
          + (f" · {' '.join(s.upper() for s in args.symbols)}" if args.symbols else " · all symbols")
          + (f" · from {args.t_from}" if args.t_from else "") + (f" · to {args.t_to}" if args.t_to else "") + " ET")
    if not rows:
        print("  none — a scanner that did not fire leaves no event; read its rule for the reason"); return 0
    for e in rows:
        print(format_event(e))
    scanners = sorted({e.get("scannerId") for e in rows})
    print(f"  scanners present: {', '.join(scanners)}. Absent means silent: running_up is silent AT the high of day by rule "
          f"(that event is hod_momentum's); the squeezes fire once per edge and stay silent while the move holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
