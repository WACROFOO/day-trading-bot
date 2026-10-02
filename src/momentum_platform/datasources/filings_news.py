"""Two more headline sources for the desk: SEC 8-K/6-K filings and finviz's
"why is it moving" line.

Why (2026-10-02, AMOD): the desk's only headline feed is Alpaca's (Benzinga).
It carried a reaction piece ("Bitcoin Boost Gives Alpha Modus (AMOD) Stock 61%
Spike After Hours") and market roundups, but not the news itself: the Nasdaq
bid-price compliance notice was an 8-K filed at 08:35 ET under Item 8.01, and
finviz's own summary read "Bitcoin PIPE close and Nasdaq compliance 8-K lift
AMOD 74% pre-market". The card said WEAK on the reaction piece.

Each source becomes an ordinary news record (same shape as `news_records`), so
`catalyst.classify` grades it with the same words as everything else. A filing
is turned into a headline from its item codes AND the first sentence of the
item's body, because "Item 8.01 Other Events" says nothing on its own.

Network: SEC (www.sec.gov / data.sec.gov, with the repo's SEC_USER_AGENT — never
a personal address the owner did not configure) and finviz (the gap scan's
existing page reader). Both are called at most once per symbol per
REFRESH_SECONDS by the desk.
"""
from __future__ import annotations

import html
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
EVENT_FORMS = ("8-K", "6-K")
WINDOW_HOURS = 36            # yesterday after the close counts as today's news (FILTERS.md gate 3)

# EDGAR 8-K item codes -> words the catalyst classifier understands.
ITEM_TEXT = {
    "1.01": "entry into a material definitive agreement",
    "1.02": "termination of a material definitive agreement",
    "2.01": "completion of acquisition or disposition of assets",
    "2.02": "results of operations (earnings)",
    "2.03": "creation of a direct financial obligation",
    "3.01": "listing rule notice (item 3.01)",
    "3.02": "unregistered sales of equity securities (item 3.02)",
    "3.03": "material modification to rights of security holders",
    "5.01": "change in control",
    "5.02": "director or officer change",
    "5.03": "amendment to articles or bylaws",
    "5.07": "shareholder vote",
    "7.01": "regulation fd disclosure",
    "8.01": "other events",
    "9.01": "financial statements and exhibits",
}


def _text(raw_html: str) -> str:
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw_html or "")
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


# The official item titles, skipped so the headline carries the body, not the title.
ITEM_TITLES = {
    "1.01": "Entry into a Material Definitive Agreement",
    "1.02": "Termination of a Material Definitive Agreement",
    "2.01": "Completion of Acquisition or Disposition of Assets",
    "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of a Direct Financial Obligation",
    "3.01": "Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing",
    "3.02": "Unregistered Sales of Equity Securities",
    "3.03": "Material Modification to Rights of Security Holders",
    "5.02": "Departure of Directors or Certain Officers",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Events",
}


def item_sentence(body: str, items: List[str], limit: int = 240) -> Optional[str]:
    """The opening of the body under the first substantive item heading: the
    title is skipped and the text is cut at a sentence end after 120 characters
    (abbreviations such as "Inc." inside the first 120 do not end it)."""
    for code in [i for i in items if i and i != "9.01"]:
        for m in re.finditer(r"item\s*" + re.escape(code) + r"\b\.?", body, re.I):
            rest = body[m.end():m.end() + 1500].lstrip(" .:-–")
            title = ITEM_TITLES.get(code, "")
            if title and rest.lower().startswith(title.lower()[:25]):
                end = rest.lower().find(title.lower()[-12:])
                rest = rest[end + 12:] if end >= 0 else rest[len(title):]
                rest = rest.lstrip(" .:;-–")
            if len(rest) < 40 or not rest[:1].isalpha():
                continue
            cut = re.search(r"\.\s+(?=[A-Z])", rest[120:limit + 60])
            text = rest[:120 + cut.start() + 1] if cut else rest[:limit]
            return text.strip()[:limit]
    return None


def filing_headline(form: str, items: List[str], sentence: Optional[str]) -> str:
    codes = [i for i in items if i and i != "9.01"] or items
    what = "; ".join(f"Item {c} {ITEM_TEXT.get(c, '')}".strip() for c in codes) or form
    return f"SEC {form} · {what}" + (f" — {sentence}" if sentence else "")


def sec_records(symbol: str, client, now: Optional[datetime] = None,
                fetch_doc: Optional[Callable[[str], str]] = None) -> List[dict]:
    """News records from the symbol's 8-K/6-K filings accepted in the last
    WINDOW_HOURS. `client` is a `sec_source.SecClient`; `fetch_doc(url)` returns
    the document's HTML (defaults to the client's own throttled session)."""
    from .sec_source import SEC_SUBMISSIONS
    now = now or datetime.now(timezone.utc)
    cik = client.cik_for(symbol)
    if cik is None:
        return []
    recent = ((client._get(SEC_SUBMISSIONS.format(cik=cik)).get("filings") or {}).get("recent") or {})
    forms = recent.get("form") or []
    out = []
    for i, form in enumerate(forms):
        if form not in EVENT_FORMS:
            continue
        try:
            acc = datetime.fromisoformat(recent["acceptanceDateTime"][i].replace("Z", "+00:00"))
        except (KeyError, IndexError, ValueError):
            continue
        if now - acc > timedelta(hours=WINDOW_HOURS):
            break                                   # newest first
        if acc > now:
            continue
        items = [x.strip() for x in ((recent.get("items") or [""] * len(forms))[i] or "").split(",") if x.strip()]
        accession = recent["accessionNumber"][i]
        doc = (recent.get("primaryDocument") or [""] * len(forms))[i]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{doc}"
        sentence = None
        try:
            raw = fetch_doc(url) if fetch_doc else client._get_text(url)
            sentence = item_sentence(_text(raw), items)
        except Exception:                           # noqa: BLE001 — the item codes still say something
            sentence = None
        out.append({"type": "news", "symbol": symbol, "provider_id": f"sec-{accession}",
                    "published_at": acc.isoformat().replace("+00:00", "Z"),
                    "first_observed_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "headline": filing_headline(form, items, sentence), "category": "sec_filing",
                    "tagged": [symbol], "url": url})
    return out


def finviz_record(symbol: str, page: dict, now: Optional[datetime] = None) -> List[dict]:
    """finviz's dated "why is it moving" line, when finviz itself flags it as a
    catalyst. `page` is `scripts/premarket_stars.finviz(symbol)`; its time is ET."""
    now = now or datetime.now(timezone.utc)
    why, when = (page or {}).get("why"), (page or {}).get("why_time")
    if not why or not when or not page.get("why_catalyst"):
        return []
    try:
        t = datetime.fromisoformat(str(when).split(".")[0])
    except ValueError:
        return []
    t = (t.replace(tzinfo=ET) if t.tzinfo is None else t).astimezone(timezone.utc)
    if t > now or now - t > timedelta(hours=WINDOW_HOURS):
        return []
    return [{"type": "news", "symbol": symbol, "provider_id": f"finviz-why-{symbol}-{when}",
             "published_at": t.isoformat().replace("+00:00", "Z"),
             "first_observed_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
             "headline": f"finviz: {why}", "category": "finviz_why", "tagged": [symbol]}]


def finviz_page(symbol: str) -> dict:
    """The gap scan's finviz reader (scripts/premarket_stars.py), imported lazily."""
    scripts = str(Path(__file__).resolve().parents[3] / "scripts")
    if scripts not in sys.path:
        sys.path.append(scripts)
    import premarket_stars
    return premarket_stars.finviz(symbol)
