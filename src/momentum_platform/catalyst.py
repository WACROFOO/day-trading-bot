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

# A market wrap ("12 Health Care Stocks Moving In Thursday's Session") names a
# dozen tickers and says nothing about any of them. It is not a catalyst and
# earns no flame; it used to read as fresh news and pass the pillar.
#
# Two families were added 2026-09-17 after reading the live endpoint: the
# macro wrap ("Dow Tumbles Over 600 Points as Fed Raises Rates", "Crude Oil
# Down Over 3%") and the literal provider category "market_roundup". Gate 3
# in session_builder imports this list, so the desk, the card and the CLI all
# draw the line in the same place.
ROUNDUP_WORDS = [
    "roundup", "stocks moving in", "stocks trading", "movers", "top gainers", "top losers",
    "biggest gainers", "biggest losers", "stocks to watch", "market wrap", "midday",
    "moving in", "dow ", "dow jones", "nasdaq ", "s&p", "russell", "crude oil",
    "treasury yield", "retail sales", "business inventories", "jobless", "nonfarm", "cpi",
    "inflation report", "fed raises", "fed cuts", "fomc", "market update", "sector update",
    "investor sentiment",
]
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
# A story ABOUT the move is not the cause of the move. "Why Is Greenland Mines
# Stock Surging on Monday?" (GRML's card, 2026-09-21 10:42) was graded
# Unclassified and counted as the news pillar; it is a reaction piece — the
# catalyst, if there is one, is inside the body, and the desk cannot read it.
REACTION_WORDS = [
    "why is", "why are", "why did", "here's why", "here is why", "what's going on",
    "surging", "soaring", "skyrocket", "jumps", "jumped", "jumping", "rallies", "rallying",
    "is up today", "shares are up", "shares rose", "shares climb", "climbing", "rocketing",
    "spiking", "explodes", "on the move", "trading higher", "trading up",
]
SOFT_WORDS = [
    "partnership", "agreement", "mou", "collaboration", "analyst", "price target",
    "upgrade", "initiated", "appoint", "names", "joins", "announces", "reverse split",
    "conference", "presentation", "short interest",
]

RULES = [
    ("roundup", "Market roundup", ROUNDUP_WORDS,
     "A list of names, not a story about this one. Not a catalyst; find the company's "
     "own headline."),
    ("dilutive", "Dilutive", DILUTIVE_WORDS,
     "Supply is increasing. Ross treats this as risk context, not a green light — "
     "read the size before anything else."),
    ("hard", "Hard catalyst", HARD_WORDS,
     "Quantifiable economic value — this is the catalyst family the funnel is built for."),
    ("reaction", "Reaction piece", REACTION_WORDS,
     "A story about the move, not its cause. Not a catalyst; the reason, if any, is in the "
     "body and the desk cannot read it."),
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


# -- the one word the card and the cascade speak ------------------------------
# Five states, chosen so a reader can act on the word without reading the
# headline. STRONG and WEAK pass the news pillar; the other three fail it.
# Ross's pillar is "news today" (FILTERS.md gate 3); which families count is
# this desk's Approximation, and the ledger records the word on every decision
# so the split can be measured instead of argued.
CATALYST_VERDICTS = {
    "STRONG":   "This company's own headline, hard family, inside 12 hours. "
                "The news pillar passes; the chart decides the entry.",
    "WEAK":     "This company's own headline, but soft, unclassified or 12-24 hours old. "
                "The news pillar passes; the chart carries the whole case.",
    "NONE":     "No headline of this company's own inside 24 hours. Roundups, reaction "
                "pieces and other names' stories do not count. The news pillar fails.",
    "DILUTIVE": "The freshest own headline is a supply event. Not a catalyst — a reason "
                "against; read the size before anything else.",
    "UNKNOWN":  "No headline feed on this desk. Nothing ruled in or out.",
}
NOT_A_CATALYST = ("roundup", "reaction")


def _iso(ts) -> Optional[datetime]:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def news_verdict(items, now: Optional[datetime] = None, source_ok: bool = True):
    """One word for a symbol's news, from the session's news records
    (`headline`, `category`, `publishedAt`, `firstObservedAt`, `sharedTag`).

    Returns (verdict, grade, item): the item the verdict rests on, or None.
    Only headlines already observed at `now` count — the replay must not see
    a flame before the desk did."""
    now = now or datetime.now(timezone.utc)
    own = []
    for it in items or []:
        seen = _iso(it.get("firstObservedAt") or it.get("publishedAt"))
        pub = _iso(it.get("publishedAt"))
        if pub is None or (seen is not None and seen > now):
            continue
        age = (now - pub).total_seconds() / 60.0
        if age < 0 or age > 1440:
            continue
        if it.get("sharedTag"):
            continue
        g = classify(it.get("headline") or "", it.get("category") or "")
        if g.grade in NOT_A_CATALYST:
            continue
        own.append((pub, age, g, it))
    if not own:
        return ("NONE" if source_ok else "UNKNOWN"), None, None
    pub, age, g, it = max(own, key=lambda t: t[0])
    if g.grade == "dilutive":
        return "DILUTIVE", g, it
    if g.grade == "hard" and age <= 720:
        return "STRONG", g, it
    return "WEAK", g, it


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
    if read.grade.grade == "roundup":
        read.flame_color = "none"            # recency of a list is not recency of news
        read.notes.append("The only headline is a market roundup — not a catalyst for this name.")

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
