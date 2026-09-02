"""SEC EDGAR filings — free, no key, no account.

Answers the supply half of the Five Pillars: not "what is the float" (EDGAR
does not publish that) but the question that actually decides a trade — *is
this company selling shares into the move you are about to buy?*

Two endpoints, both public:
  www.sec.gov/files/company_tickers.json   ticker -> CIK, one download, cached
  data.sec.gov/submissions/CIK##########.json   that company's recent filings

SEC requires a User-Agent naming a real contact and rate-limits to about ten
requests a second. Both are respected here; ignoring either gets an IP blocked.

Filings are public record, so nothing here is a credential and nothing needs
one. Reads only.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
CACHE = Path(__file__).resolve().parents[3] / "data" / "sec_cache"
MIN_INTERVAL = 0.12          # ~8 req/s, inside the SEC's ~10 req/s ceiling


from .tls import ssl_context


class SecError(RuntimeError):
    """Raised with a message written for a human, not a stack trace."""


def default_user_agent() -> str:
    """SEC policy: identify yourself with a contact address.

    Set SEC_USER_AGENT in .env to your own name and email. The fallback is
    deliberately obvious rather than an impersonation of a real filer agent.
    """
    return os.environ.get(
        "SEC_USER_AGENT",
        "day-trading-bot personal research (set SEC_USER_AGENT in .env)")


class SecClient:
    def __init__(self, user_agent: Optional[str] = None, timeout: float = 30.0,
                 cache_dir: Optional[Path] = None) -> None:
        self.user_agent = user_agent or default_user_agent()
        self.timeout = timeout
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE
        self._last_call = 0.0
        self._cik_map: Optional[Dict[str, int]] = None

    # -- transport ------------------------------------------------------------

    def _throttle(self) -> None:
        gap = time.monotonic() - self._last_call
        if gap < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - gap)
        self._last_call = time.monotonic()

    def _get(self, url: str) -> dict:
        self._throttle()
        req = urllib.request.Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout,
                                        context=ssl_context()) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise SecError(
                    "SEC refused the request (HTTP 403). This is almost always the "
                    "User-Agent: EDGAR requires one naming a real contact. Put "
                    "SEC_USER_AGENT='Your Name your@email.com' in .env."
                ) from None
            if exc.code == 404:
                raise SecError("Not found at %s — the company may have no EDGAR "
                               "history under that CIK." % url) from None
            if exc.code == 429:
                raise SecError(
                    "Rate limited by SEC (HTTP 429). EDGAR allows about ten requests "
                    "a second; wait a minute and scan fewer symbols."
                ) from None
            raise SecError("SEC returned HTTP %d for %s" % (exc.code, url)) from None
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "CERTIFICATE_VERIFY" in reason or "SSLCertVerification" in reason:
                raise SecError(
                    "Python on this machine cannot verify HTTPS certificates. On macOS "
                    "run '/Applications/Python 3.x/Install Certificates.command' once, "
                    "or 'python3 -m pip install --upgrade certifi'.\nDetail: %s" % reason
                ) from None
            raise SecError(
                "Could not reach SEC EDGAR (%s). Check your connection, and any "
                "proxy or VPN that might block sec.gov." % reason
            ) from None

    # -- ticker -> CIK --------------------------------------------------------

    def _cache_path(self) -> Path:
        return self.cache_dir / "company_tickers.json"

    def cik_map(self, max_age_days: int = 7) -> Dict[str, int]:
        """Ticker -> CIK. Cached on disk; the file changes slowly."""
        if self._cik_map is not None:
            return self._cik_map
        path = self._cache_path()
        if path.exists():
            age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
            if age < max_age_days * 86400:
                self._cik_map = json.loads(path.read_text())
                return self._cik_map
        payload = self._get(SEC_TICKERS)
        mapping = {row["ticker"].upper(): int(row["cik_str"])
                   for row in payload.values() if row.get("ticker")}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(mapping))
        self._cik_map = mapping
        return mapping

    def cik_for(self, symbol: str) -> Optional[int]:
        return self.cik_map().get(symbol.upper())

    # -- filings --------------------------------------------------------------

    def recent_filings(self, symbol: str, since_days: int = 90,
                       limit: int = 40) -> List[dict]:
        """Recent filings for a ticker, newest first.

        Returns [] for a symbol EDGAR does not know — many small caps trade
        under a ticker that maps to a different registrant name, and an ADR or
        a fund may have no submissions at all. That is missing data, not a
        clean bill of health, and the caller must say so.
        """
        cik = self.cik_for(symbol)
        if cik is None:
            return []
        payload = self._get(SEC_SUBMISSIONS.format(cik=cik))
        recent = (payload.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        accessions = recent.get("accessionNumber") or []
        docs = recent.get("primaryDocument") or []
        cutoff = date.today() - timedelta(days=since_days)

        out: List[dict] = []
        for i, form in enumerate(forms):
            if len(out) >= limit:
                break
            try:
                filed = date.fromisoformat(dates[i])
            except (IndexError, ValueError):
                continue
            if filed < cutoff:
                break                      # the array is newest-first
            accession = accessions[i] if i < len(accessions) else ""
            out.append({
                "form": form,
                "filed": filed.isoformat(),
                "age_days": (date.today() - filed).days,
                "accession": accession,
                "url": _filing_url(cik, accession, docs[i] if i < len(docs) else ""),
            })
        return out


    def shares_outstanding(self, symbol: str) -> Optional[dict]:
        """Latest dei:EntityCommonStockSharesOutstanding from XBRL company facts.

        This is what the company itself reported on its most recent 10-Q/10-K
        cover — free, official, and dated. It is NOT float: it includes
        locked-up insider and restricted stock. It is always >= float, which
        makes it a sound upper bound and nothing more. Returns
        {"shares": int, "as_of": "YYYY-MM-DD"} or None when EDGAR has no
        figure for the ticker."""
        cik = self.cik_for(symbol)
        if cik is None:
            return None
        payload = self._get(SEC_FACTS.format(cik=cik))
        facts = ((payload.get("facts") or {}).get("dei") or {}).get("EntityCommonStockSharesOutstanding") or {}
        entries = (facts.get("units") or {}).get("shares") or []
        best = None
        for e in entries:
            val, end = e.get("val"), e.get("end") or e.get("filed") or ""
            if not val or val <= 0:
                continue
            if best is None or end > best["as_of"]:
                best = {"shares": int(val), "as_of": end}
        return best


def _filing_url(cik: int, accession: str, document: str) -> str:
    if not accession:
        return ""
    plain = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{plain}"
    return f"{base}/{document}" if document else base


def client_from_env() -> SecClient:
    """Build a client, reading SEC_USER_AGENT from .env if present."""
    try:
        from .alpaca_source import load_dotenv
        load_dotenv()
    except Exception:                     # .env is optional for SEC
        pass
    return SecClient()
