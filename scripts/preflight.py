#!/usr/bin/env python3
"""Answer one question: can this machine use the live Alpaca feed right now?

    python scripts/preflight.py

Prints one human-readable line and exits with a code the launcher reads:

    0  live feed available
    1  no credentials on this machine
    2  credentials were rejected by Alpaca
    3  Alpaca could not be reached from this network
    4  something else went wrong
    5  this Python cannot verify HTTPS certificates

Reads only. Never places an order.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from momentum_platform.datasources.alpaca_source import (  # noqa: E402
    AlpacaError, client_from_env, load_dotenv,
)
from momentum_platform.datasources.tls import describe as describe_tls  # noqa: E402

ET = ZoneInfo("America/New_York")

NO_CREDS, REJECTED, UNREACHABLE, OTHER, CERT = 1, 2, 3, 4, 5


def _classify(message: str) -> int:
    """Distinguish "Alpaca said no" from "we never got to Alpaca".

    A proxy refusing the CONNECT tunnel also reports 403, so the tunnel
    wording is checked first — otherwise a blocked network is misreported
    as a bad key and the user regenerates a perfectly good pair.
    """
    low = message.lower()
    if "certificate" in low or "sslcertverification" in low:
        # Checked before the network cases: a cert failure never leaves the
        # machine, so calling it a network block sends the user to change
        # wifi and regenerate keys that were never the problem.
        return CERT
    if "tunnel" in low or "could not reach" in low or "connection" in low:
        return UNREACHABLE
    if "401" in low or "403" in low or "unauthorized" in low or "forbidden" in low:
        return REJECTED
    return OTHER


def main() -> int:
    load_dotenv()
    try:
        client = client_from_env()
    except AlpacaError as exc:
        print(f"no credentials: {exc}")
        return NO_CREDS

    try:
        account = client.account()
        clock = client.clock()
    except AlpacaError as exc:
        code = _classify(str(exc))
        if code == CERT:
            print(f"certificates: {describe_tls()}")
        label = {REJECTED: "credentials rejected",
                 UNREACHABLE: "network blocked",
                 CERT: "certificates not installed",
                 OTHER: "unexpected error"}[code]
        print(f"{label}: {exc}")
        return code
    except Exception as exc:  # pragma: no cover - defensive
        print(f"unexpected error: {exc}")
        return OTHER

    now = datetime.now(ET).strftime("%H:%M ET")
    state = "OPEN" if clock.get("is_open") else "closed"
    kind = "paper" if account.get("status") and client.trading_base.startswith(
        "https://paper-api") else "live"
    print(f"live feed available — {kind} account {account.get('status', '?')}, "
          f"market {state} at {now}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
