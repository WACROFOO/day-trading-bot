"""SEC 8-K and finviz 'why' headlines for the desk (datasources/filings_news.py), offline."""
from datetime import datetime, timezone

from momentum_platform.catalyst import classify
from momentum_platform.datasources import filings_news as F

NOW = datetime(2026, 10, 2, 13, 5, tzinfo=timezone.utc)
DOC = ("<html><body><p>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</p><p>Item 8.01 Other Events.</p>"
       "<p>On October 1, 2026, Alpha Modus Holdings, Inc. (the Company) received a letter from the Listing "
       "Qualifications Department of the Nasdaq Stock Market indicating that the Company has regained "
       "compliance with the minimum bid price requirement. The matter is now closed.</p>"
       "<p>Item 9.01 Financial Statements and Exhibits.</p></body></html>")


class FakeSec:
    def cik_for(self, s): return 1862463

    def _get(self, url):
        return {"filings": {"recent": {
            "form": ["8-K", "8-K", "DEF 14C", "8-K"],
            "acceptanceDateTime": ["2026-10-02T12:35:36.000Z", "2026-10-01T19:30:52.000Z",
                                   "2026-09-09T17:06:38.000Z", "2026-09-01T12:00:00.000Z"],
            "items": ["8.01", "2.01,8.01", "", "8.01"],
            "accessionNumber": ["0001493152-26-045442", "0001493152-26-045296", "x", "y"],
            "primaryDocument": ["form8-k.htm", "form8-k.htm", "d.htm", "e.htm"]}}}


def test_an_8k_becomes_a_headline_with_the_item_body():
    recs = F.sec_records("AMOD", FakeSec(), now=NOW, fetch_doc=lambda url: DOC)
    assert [r["provider_id"] for r in recs] == ["sec-0001493152-26-045442", "sec-0001493152-26-045296"]
    first = recs[0]
    assert first["published_at"] == "2026-10-02T12:35:36Z" and first["category"] == "sec_filing"
    assert "Item 8.01" in first["headline"] and "Listing Qualifications" in first["headline"]
    assert "Other Events" not in first["headline"].split("—")[1]          # the title is skipped
    assert classify(first["headline"]).grade == "listing"


def test_a_filing_that_cannot_be_read_still_says_what_its_items_are():
    def boom(url):
        raise RuntimeError("offline")
    recs = F.sec_records("AMOD", FakeSec(), now=NOW, fetch_doc=boom)
    assert recs[1]["headline"].startswith("SEC 8-K · Item 2.01 completion of acquisition")


def test_finviz_why_counts_only_when_finviz_calls_it_a_catalyst_and_is_dated_et():
    page = {"why": "Bitcoin PIPE close and Nasdaq compliance 8-K lift AMOD 74% pre-market",
            "why_time": "2026-10-02T04:05:56.573", "why_catalyst": True}
    (r,) = F.finviz_record("AMOD", page, now=NOW)
    assert r["published_at"] == "2026-10-02T08:05:56Z" and r["headline"].startswith("finviz: ")
    assert F.finviz_record("AMOD", dict(page, why_catalyst=False), now=NOW) == []
    assert F.finviz_record("AMOD", dict(page, why_time="2026-09-20T04:05:56"), now=NOW) == []
