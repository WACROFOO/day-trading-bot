"""Catalyst grading — one source of truth for the desk and the CLI.

The browser card and `scripts/catalyst_score.py` must agree, or the flame you
see on screen means something different from the flame in your notes. The word
lists here are mirrored in `dashboard/web/app.js`; a test parses the JavaScript
and fails if the two drift apart.

Grades (Confirmed course distinction between a reason and an excuse):
  hard      quantifiable economic value  — contract, FDA, earnings, buyout
  soft      attention without value      — analyst note, partnership, appointment
  dilutive  supply is increasing         — offering, shelf, warrant, ATM

Flame is news AGE only, never quality (Confirmed):
  red 0-2h, orange 2-12h, yellow 12-24h, none beyond that.

Everything here supports SELECTION. Nothing here sizes or places an order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Sequence

# -- grading rules ------------------------------------------------------------
# Mirrored in dashboard/web/app.js (CATALYST_RULES). Order matters: dilutive is
# tested first, so "offering" wins over "agreement" in a headline carrying both.

DILUTIVE_WORDS = [
    "offering", "placement", "shelf", "s-3", "dilut", "warrant", "resale",
    "registered direct", "atm program", "convertible",
]
HARD_WORDS = [
    "fda", "approval", "breakthrough", "phase 1", "phase 2", "phase 3", "clinical",
    "contract", "awarded", "award", "order", "purchase agreement", "acquisition",
    "acquire", "merger", "buyout", "earnings", "revenue", "guidance", "profit",
    "patent", "uplist", "nasdaq listing",
]
SOFT_WORDS = [
    "partnership", "agreement", "mou", "collaboration", "analyst", "price target",
    "upgrade", "initiated", "appoint", "names", "joins", "announces", "reverse split",
    "conference", "presentation", "short interest",
]

RULES = [
    ("dilutive", "Dilutive", DILUTIVE_WORDS,
     "Supply is increasing. Ross treats this as risk context, not a green light — "
     "read the size before anything else."),
    ("hard", "Hard catalyst", HARD_WORDS,
     "Quantifiable economic value — this is the catalyst family the funnel is built for."),
    ("soft", "Soft catalyst", SOFT_WORDS,
     "Attention without quantifiable value. It can still move a low float, but it does "
     "not justify size on its own."),
]

# -- SEC form families --------------------------------------------------------
# A filing is not a headline. These say what the company is *allowed* to do to
# the share count, which is the supply half of the Five Pillars.

SHELF_FORMS = {"S-3", "S-3ASR", "S-1", "F-1", "F-3"}          # capacity to issue
TAKEDOWN_FORMS = {"424B1", "424B2", "424B3", "424B4", "424B5", "424B7", "FWP"}  # issuing now
INSIDER_FORMS = {"4", "144"}                                   # insiders selling
EVENT_FORMS = {"8-K", "6-K"}                                   # material event

DILUTION_FORMS = SHELF_FORMS | TAKEDOWN_FORMS


@dataclass
class Grade:
    grade: str
    label: str
    note: str


UNCLASSIFIED = Grade(
    "soft", "Unclassified",
    "No familiar catalyst family matched. Read the headline yourself before "
    "treating it as a reason.")


def classify(headline: str, category: str = "") -> Grade:
    """Grade a headline. Dilutive first, then hard, then soft."""
    hay = f"{headline or ''} {category or ''}".lower()
    for grade, label, words, note in RULES:
        if any(w in hay for w in words):
            return Grade(grade, label, note)
    return UNCLASSIFIED


def flame(age_minutes: Optional[float]) -> str:
    """Confirmed: flame encodes recency only. Quality never changes the colour."""
    if age_minutes is None or age_minutes < 0:
        return "none"
    if age_minutes <= 120:
        return "red"
    if age_minutes <= 720:
        return "orange"
    if age_minutes <= 1440:
        return "yellow"
    return "none"


FLAME_BAND = {"red": "0-2h", "orange": "2-12h", "yellow": "12-24h", "none": ">24h"}


def age_minutes(ts: datetime, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds() / 60.0


# -- assessment ---------------------------------------------------------------


@dataclass
class CatalystRead:
    """What the desk knows about why a symbol is moving."""

    symbol: str
    headline: Optional[str] = None
    published: Optional[datetime] = None
    grade: Grade = field(default_factory=lambda: UNCLASSIFIED)
    flame_color: str = "none"
    age_min: Optional[float] = None
    filings: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    # A lookup that FAILED is not a lookup that found nothing. "No news in the
    # last 48h" is a finding and fails the pillar honestly; "the news request
    # errored" is an absence of evidence and must never render as a verdict.
    news_checked: bool = True

    @property
    def dilution_filings(self) -> List[dict]:
        return [f for f in self.filings if f.get("form") in DILUTION_FORMS]

    @property
    def has_live_takedown(self) -> bool:
        """A 424B/FWP means shares are being sold into this move right now."""
        return any(f.get("form") in TAKEDOWN_FORMS for f in self.filings)

    def verdict(self) -> str:
        """Selection guidance only — never a size, never an order.

        A hard, fresh catalyst with no active takedown is what the funnel wants.
        An active takedown demotes everything: the float you are trading is
        growing while you hold it.
        """
        if not self.news_checked:
            return "UNKNOWN"
        if self.has_live_takedown:
            return "AVOID"
        if self.flame_color == "none":
            return "PASS"
        if self.grade.grade == "dilutive":
            return "CAUTION"
        if self.grade.grade == "hard" and self.flame_color in ("red", "orange"):
            return "QUALIFIED"
        return "WATCH"


VERDICT_MEANING = {
    "QUALIFIED": "Fresh hard catalyst, no active sale. Take it to the chart.",
    "WATCH":     "Real but soft, or ageing. Needs the chart to carry the whole case.",
    "CAUTION":   "The catalyst itself is a supply event. Read the size before anything else.",
    "AVOID":     "A live takedown is printing shares into this move.",
    "PASS":      "No catalyst inside 24h. The pillar fails.",
    "UNKNOWN":   "The news source could not be reached. Nothing was ruled in or out.",
}


def assess(symbol: str,
           headline: Optional[str] = None,
           published: Optional[datetime] = None,
           category: str = "",
           filings: Optional[Sequence[dict]] = None,
           now: Optional[datetime] = None,
           news_checked: bool = True) -> CatalystRead:
    read = CatalystRead(symbol=symbol.upper(), headline=headline,
                        published=published, filings=list(filings or []),
                        news_checked=news_checked)
    if headline:
        read.grade = classify(headline, category)
    if published is not None:
        read.age_min = age_minutes(published, now)
        read.flame_color = flame(read.age_min)

    if read.has_live_takedown:
        forms = sorted({f["form"] for f in read.filings if f.get("form") in TAKEDOWN_FORMS})
        read.notes.append(
            f"Active takedown on file ({', '.join(forms)}) — shares are being sold "
            f"into this move.")
    elif read.dilution_filings:
        forms = sorted({f["form"] for f in read.dilution_filings})
        read.notes.append(
            f"Shelf capacity on file ({', '.join(forms)}) — the company may issue "
            f"at any time. Risk context, not a signal.")
    if not read.filings:
        read.notes.append("No filings checked or none returned — supply risk unverified.")
    return read
