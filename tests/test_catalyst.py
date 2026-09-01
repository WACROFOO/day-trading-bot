"""Catalyst grading, filing risk, and parity with the browser card."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.catalyst import (  # noqa: E402
    DILUTIVE_WORDS, HARD_WORDS, SOFT_WORDS, assess, classify, flame,
)
from momentum_platform.datasources.sec_source import (  # noqa: E402
    SecClient, SecError, _filing_url,
)

NOW = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)


def ago(minutes):
    return NOW - timedelta(minutes=minutes)


# -- flame is age, never quality ---------------------------------------------

@pytest.mark.parametrize("minutes,expected", [
    (0, "red"), (119, "red"), (120, "red"),
    (121, "orange"), (719, "orange"), (720, "orange"),
    (721, "yellow"), (1440, "yellow"), (1441, "none"),
])
def test_flame_bands(minutes, expected):
    assert flame(minutes) == expected


def test_flame_is_blind_to_quality():
    """A dilutive offering an hour old is just as red as an FDA approval."""
    good = assess("AAA", "FDA grants approval", ago(60), now=NOW)
    bad = assess("BBB", "Announces registered direct offering", ago(60), now=NOW)
    assert good.flame_color == bad.flame_color == "red"
    assert good.grade.grade != bad.grade.grade


# -- grading ------------------------------------------------------------------

def test_dilutive_wins_over_a_softer_word_in_the_same_headline():
    """'Offering' and 'agreement' both appear; supply must win."""
    g = classify("Company enters agreement for $20M registered direct offering")
    assert g.grade == "dilutive"


def test_hard_catalyst():
    assert classify("Awarded $40M defense contract").grade == "hard"


def test_soft_catalyst():
    assert classify("Analyst initiates coverage with price target").grade == "soft"


def test_unmatched_headline_is_flagged_not_guessed():
    g = classify("Company issues corporate update")
    assert g.label == "Unclassified"


# -- verdicts -----------------------------------------------------------------

def test_fresh_hard_catalyst_qualifies():
    r = assess("AAA", "Awarded $40M contract", ago(30), filings=[{"form": "8-K"}], now=NOW)
    assert r.verdict() == "QUALIFIED"


def test_live_takedown_overrides_a_red_flame():
    """The headline can be perfect; if a 424B is live the float is growing."""
    r = assess("AAA", "Awarded $40M contract", ago(10),
               filings=[{"form": "424B5"}], now=NOW)
    assert r.verdict() == "AVOID"
    assert r.flame_color == "red"


def test_shelf_alone_is_caution_context_not_avoid():
    r = assess("AAA", "Awarded $40M contract", ago(30),
               filings=[{"form": "S-3"}], now=NOW)
    assert r.verdict() == "QUALIFIED"
    assert "Shelf capacity" in r.notes[0]


def test_stale_news_fails_the_pillar():
    assert assess("AAA", "Awarded contract", ago(3000), now=NOW).verdict() == "PASS"


def test_unreachable_news_is_unknown_never_pass():
    """Absence of evidence must not render as a finding."""
    r = assess("AAA", headline=None, published=None, news_checked=False, now=NOW)
    assert r.verdict() == "UNKNOWN"


def test_checked_but_empty_news_is_a_real_pass():
    r = assess("AAA", headline=None, published=None, news_checked=True, now=NOW)
    assert r.verdict() == "PASS"


def test_missing_filings_are_reported_as_unverified():
    r = assess("AAA", "Awarded contract", ago(30), filings=[], now=NOW)
    assert any("unverified" in n.lower() for n in r.notes)


# -- parity with the browser card ---------------------------------------------

def test_python_and_javascript_grade_the_same_words():
    """The card and the CLI must not drift apart.

    If they do, the flame you see on screen means something different from the
    flame in your notes, and you would never know which one was lying.
    """
    js = (ROOT / "src" / "momentum_platform" / "dashboard" / "web"
          / "app.js").read_text()
    block = re.search(r"const CATALYST_RULES = \[(.*?)\n\];", js, re.S)
    assert block, "CATALYST_RULES not found in app.js"

    found = {}
    for grade, words in re.findall(
            r'grade:\s*"(\w+)".*?words:\s*\[(.*?)\]', block.group(1), re.S):
        found[grade] = [w.strip().strip('"') for w in words.split(",") if w.strip()]

    assert found["dilutive"] == DILUTIVE_WORDS
    assert found["hard"] == HARD_WORDS
    assert found["soft"] == SOFT_WORDS


# -- SEC client ---------------------------------------------------------------

class FakeSec(SecClient):
    def __init__(self, payloads):
        super().__init__(user_agent="test", cache_dir=Path("/tmp/sec-test-cache"))
        self.payloads = payloads
        self.calls = []

    def _get(self, url):
        self.calls.append(url)
        for key, payload in self.payloads.items():
            if key in url:
                return payload
        raise SecError(f"unexpected url {url}")


TICKERS = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
           "1": {"cik_str": 111, "ticker": "ABCD", "title": "Abcd Corp"}}


def _submissions(forms, dates):
    return {"filings": {"recent": {
        "form": forms, "filingDate": dates,
        "accessionNumber": [f"0000000000-26-{i:06d}" for i in range(len(forms))],
        "primaryDocument": ["doc.htm"] * len(forms),
    }}}


def test_recent_filings_parses_and_dates():
    today = datetime.now(timezone.utc).date()
    payloads = {
        "company_tickers.json": TICKERS,
        "CIK0000000111.json": _submissions(
            ["424B5", "S-3", "8-K"],
            [str(today), str(today - timedelta(days=5)), str(today - timedelta(days=20))]),
    }
    filings = FakeSec(payloads).recent_filings("ABCD", since_days=90)
    assert [f["form"] for f in filings] == ["424B5", "S-3", "8-K"]
    assert filings[0]["age_days"] == 0
    assert filings[1]["age_days"] == 5


def test_filings_outside_the_window_are_dropped():
    today = datetime.now(timezone.utc).date()
    payloads = {
        "company_tickers.json": TICKERS,
        "CIK0000000111.json": _submissions(
            ["8-K", "S-3"], [str(today), str(today - timedelta(days=200))]),
    }
    filings = FakeSec(payloads).recent_filings("ABCD", since_days=90)
    assert [f["form"] for f in filings] == ["8-K"]


def test_unknown_ticker_returns_empty_without_calling_submissions():
    client = FakeSec({"company_tickers.json": TICKERS})
    assert client.recent_filings("ZZZZ") == []
    assert not any("submissions" in c for c in client.calls)


def test_filing_url_is_well_formed():
    url = _filing_url(111, "0000000000-26-000001", "doc.htm")
    assert url == "https://www.sec.gov/Archives/edgar/data/111/000000000026000001/doc.htm"


# -- certificate failures are not network failures ----------------------------
# A macOS python.org build ships its own CA store and ignores the system
# keychain, so every HTTPS call fails until it is populated. Reporting that as
# "check your connection" sends the user to change wifi and regenerate keys
# that were never the problem — which is exactly what happened once.

import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location("preflight", ROOT / "scripts" / "preflight.py")
preflight = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(preflight)

CERT_MESSAGE = ("Could not reach Alpaca ([SSL: CERTIFICATE_VERIFY_FAILED] certificate "
                "verify failed: unable to get local issuer certificate (_ssl.c:1082))")


def test_certificate_failure_is_not_reported_as_a_network_block():
    assert preflight._classify(CERT_MESSAGE) == preflight.CERT


def test_certificate_failure_is_not_reported_as_a_bad_key():
    assert preflight._classify(CERT_MESSAGE) != preflight.REJECTED


def test_alpaca_ssl_error_names_the_actual_fix():
    from momentum_platform.datasources import alpaca_source as al
    import urllib.error

    client = al.AlpacaClient(key_id="PKTEST", secret_key="s" * 40)

    def boom(req, timeout=None, **kwargs):
        raise urllib.error.URLError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "unable to get local issuer certificate")

    import urllib.request
    original = urllib.request.urlopen
    urllib.request.urlopen = boom
    try:
        with pytest.raises(al.AlpacaError) as exc:
            client.account()
    finally:
        urllib.request.urlopen = original

    message = str(exc.value)
    assert "Install Certificates.command" in message
    assert "certifi" in message
    assert "keys and your network are fine" in message.lower()


# -- certificate discovery ----------------------------------------------------
# Install Certificates.command writes into /Library and needs an administrator,
# which many people on a work laptop do not have. The desk finds a CA bundle on
# its own instead, so a stock machine works with no install and no admin.

from momentum_platform.datasources import tls  # noqa: E402


def test_a_context_is_always_returned():
    assert tls.ssl_context() is not None


def test_verification_is_never_disabled():
    """A silently-trusting context on a machine holding brokerage keys would
    be far worse than a visible failure."""
    import ssl as _ssl
    ctx = tls.ssl_context()
    assert ctx.verify_mode == _ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_an_explicit_environment_setting_wins(monkeypatch):
    monkeypatch.setattr(tls, "_cached", None)
    monkeypatch.setenv("SSL_CERT_FILE", "/somewhere/roots.pem")
    tls._cached = None
    tls.ssl_context()
    assert "SSL_CERT" in tls.ca_source()
    tls._cached = None


def test_the_source_is_reported_for_diagnostics():
    tls._cached = None
    assert "certificates from" in tls.describe()
    tls._cached = None
