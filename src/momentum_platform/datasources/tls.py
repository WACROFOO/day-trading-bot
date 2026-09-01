"""Find a usable set of certificate authorities without needing an installer.

A Python built by python.org carries its own CA store and ignores the macOS
keychain, so every HTTPS call fails with CERTIFICATE_VERIFY_FAILED until that
store is filled. The official fix, `Install Certificates.command`, writes into
/Library and therefore needs an administrator — which many people on a work
laptop simply do not have.

None of that is necessary. macOS already ships a CA bundle at /etc/ssl/cert.pem
and most Linux distributions ship one too; certifi carries one as well when it
happens to be installed. This module finds whichever exists and hands back an
SSL context built from it, so the desk works on a stock machine with no
install, no administrator and no environment fiddling.

Search order, most explicit first:
  1. SSL_CERT_FILE / SSL_CERT_DIR   — an operator's deliberate choice wins
  2. the interpreter's own store    — a correctly configured Python
  3. certifi                        — present in many environments already
  4. the operating system's bundle  — /etc/ssl/cert.pem and friends

Verification is never disabled. If nothing is found the caller gets the normal
strict context and a real error, because silently trusting everything on a
machine that handles brokerage credentials would be far worse than a failure.
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from typing import List, Optional, Tuple

# macOS ships the first; the rest cover common Linux layouts.
SYSTEM_BUNDLES = (
    "/etc/ssl/cert.pem",
    "/private/etc/ssl/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/ca-bundle.pem",
)

_cached: Optional[Tuple[ssl.SSLContext, str]] = None


def _has_any_root(context: ssl.SSLContext) -> bool:
    try:
        return bool(context.get_ca_certs())
    except Exception:
        return False


def _build() -> Tuple[ssl.SSLContext, str]:
    # 1. An explicit environment setting is a deliberate choice: honour it and
    #    let it fail loudly rather than quietly substituting something else.
    if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
        return ssl.create_default_context(), "SSL_CERT_FILE/SSL_CERT_DIR"

    context = ssl.create_default_context()
    if _has_any_root(context):
        return context, "python default store"

    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where()), "certifi"
    except Exception:
        pass

    for candidate in SYSTEM_BUNDLES:
        path = Path(candidate)
        if path.is_file():
            try:
                return ssl.create_default_context(cafile=str(path)), candidate
            except Exception:
                continue

    # Strict context with an empty store: HTTPS will fail, which is correct.
    # The adapters turn that failure into instructions the user can act on.
    return context, "none found"


def ssl_context() -> ssl.SSLContext:
    global _cached
    if _cached is None:
        _cached = _build()
    return _cached[0]


def ca_source() -> str:
    """Where the trusted roots came from — for diagnostics, never for trust."""
    global _cached
    if _cached is None:
        _cached = _build()
    return _cached[1]


def describe() -> str:
    context, source = (ssl_context(), ca_source())
    try:
        count = len(context.get_ca_certs())
    except Exception:
        count = 0
    return f"{count} root certificates from {source}"
