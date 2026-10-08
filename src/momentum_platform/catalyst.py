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

import re
from dataclasses import dataclass, field
from functools import lru_cache
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
# A Nasdaq/NYSE listing notice: compliance regained (AMOD 2026-10-02, an 8-K
# under Item 8.01) or a deficiency. Administrative, not economic value; it is
# tested FIRST because "nasdaq " is a roundup word and swallowed the company's
# own notice as a market wrap.
LISTING_WORDS = [
    "listing qualifications", "minimum bid", "bid price requirement", "bid price rule",
    "regains compliance", "regained compliance", "confirming compliance", "nasdaq compliance",
    "compliance with nasdaq", "compliance with the nasdaq", "listing rule", "continued listing",
    "deficiency notice", "delisting notice", "notice of delisting",
]
DILUTIVE_WORDS = [
    "offering", "placement", "shelf", "s-3", "dilut", "warrant", "resale",
    "registered direct", "atm program", "convertible", "securities purchase agreement",
    "pipe deal", "pipe financing", "pipe transaction", "closes pipe", "pipe offering",
    "unregistered sales",
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
    "spiking", "explodes", "on the move", "trading higher", "trading up", "spike",
    "what you should know", "what to know",
]
SOFT_WORDS = [
    "partnership", "agreement", "mou", "collaboration", "analyst", "price target",
    "upgrade", "initiated", "appoint", "names", "joins", "announces", "reverse split",
    "conference", "presentation", "short interest",
]

RULES = [
    ("listing", "Listing notice", LISTING_WORDS,
     "An exchange listing notice — compliance regained or a deficiency. Administrative, "
     "not economic value: it lifts or flags a delisting risk; the chart carries the case."),
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


@lru_cache(maxsize=64)
def _pattern(words: Sequence[str]) -> "re.Pattern":
    """Whole-word matching, from the left. A plain substring test read "window"
    as a market wrap ("dow "), "disorder" as hard news ("order") and "nonprofit"
    as a profit headline (catalyst map, 2026-10-08). A word must start after a
    non-alphanumeric character; it may carry a suffix ("orders", "awarded").
    "dow " and "nasdaq " keep their trailing space, which is how the list says
    "the index on its own, not a ticker tag" — "(Nasdaq: ABCD)" stays out."""
    return re.compile("|".join(r"(?<![a-z0-9])" + re.escape(w) for w in words))


_RULE_PATTERNS = None


def matches(words: Sequence[str], hay: str) -> bool:
    """True when one of `words` occurs in `hay` (lower case) as a whole word."""
    return bool(_pattern(tuple(words)).search(hay))


# An SEC filing turned into a headline with nothing readable behind the form
# and item codes: a 6-K carries no item codes at all ("SEC 6-K · 6-K"), and
# an 8-K under "other events" or "Regulation FD" with no body sentence says
# nothing either. It used to grade Unclassified, read WEAK and PASS the news
# pillar. What the desk could not read is not news; it is a filing to open.
_UNREAD_ITEMS = re.compile(
    r"^sec [\w/-]+ · (?:[\w/-]+|(?:item (?:7\.01|8\.01|9\.01)[^;—]*(?:; )?)+)$")
UNREAD_FILING = Grade(
    "filing", "Unread filing",
    "An SEC filing with nothing readable behind its form and item codes. Open it; "
    "the desk cannot tell what it says, so it is not counted as news.")


def classify(headline: str, category: str = "") -> Grade:
    """Grade a headline. Listing, roundup, dilutive, hard, reaction, soft."""
    global _RULE_PATTERNS
    if _RULE_PATTERNS is None:
        _RULE_PATTERNS = [(g, lab, _pattern(tuple(w)), note) for g, lab, w, note in RULES]
    head = (headline or "").strip().lower()
    if (category or "") == "sec_filing" and _UNREAD_ITEMS.match(head):
        return UNREAD_FILING
    hay = f"{head} {(category or '').lower()}"
    for grade, label, pat, note in _RULE_PATTERNS:
        if pat.search(hay):
            return Grade(grade, label, note)
    return UNCLASSIFIED


# -- the one word the card and the cascade speak ------------------------------
# Five states, chosen so a reader can act on the word without reading the
# headline. STRONG and WEAK pass the news pillar; the other three fail it.
# Ross's pillar is "news today" (FILTERS.md gate 3); which families count is
# this desk's Approximation, and the ledger records the word on every decision
# so the split can be measured instead of argued.
# -- buyout (cascade gate 8) ---------------------------------------------------
# Only phrases that make THIS company the target. "XYZ to acquire ABC" tagged to
# the acquirer is not a pinned price, so "acquire" and "merger" alone never
# fire: a false buyout kill throws away a live name. Desk-only (not mirrored in
# app.js: the card shows the gate the server computed).
BUYOUT_TARGET_WORDS = [
    "to be acquired", "agrees to be acquired", "agreed to be acquired",
    "to be taken private", "take-private", "take private", "go-private", "going private",
    "go private transaction",
]


def buyout_in(headlines: Sequence[str]) -> bool:
    """True when one of the company's own headlines says it is being bought."""
    return any(matches(BUYOUT_TARGET_WORDS, (h or "").lower()) for h in headlines)


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
NOT_A_CATALYST = ("roundup", "reaction", "filing")


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


# =============================================================================
# The desk's two-line catalyst read — knowledge-base/strategies/CATALYST.md
# =============================================================================
# One grade a trader can act on without reading the headline twice: STRONG,
# MODERATE or WEAK (UNKNOWN only when the desk has no headline feed at all).
# Every branch below carries the id of its rule in CATALYST.md, where each rule
# names its origin: the corpus (path, video id, timestamp) or "Approximation"
# for this desk's own boundary. The grade is DISPLAY: the cascade's gate 3 and
# the pillar count still decide on `catalyst_today`, and nothing here sizes or
# places an order.

TYPE_RULES = [
    # (type, words) — the first match names the headline's type. Shown, not graded.
    ("FDA", ["fda", "approval", "breakthrough", "phase 1", "phase 2", "phase 3", "clinical", "pdufa"]),
    ("earnings", ["earnings", "revenue", "guidance", "profit", "results of operations"]),
    ("contract", ["contract", "awarded", "award", "order", "purchase agreement"]),
    ("deal", ["acquisition", "acquire", "merger", "buyout"]),
    ("patent", ["patent"]),
    ("uplist", ["uplist", "nasdaq listing"]),
    ("analyst", ["analyst", "price target", "upgrade", "initiated"]),
    ("partnership", ["partnership", "agreement", "mou", "collaboration"]),
]
#: Soft-family words that carry attention but no counterparty and no value:
#: the "PR without substance" type (rule C5).
PR_WORDS = ["appoint", "names", "joins", "announces", "conference", "presentation",
            "short interest", "reverse split"]
#: A 424B/FWP this recent is a sale into the market now; older is history.
TAKEDOWN_RECENT_DAYS = 30           # Approximation (rule C11)
FOREIGN_FORMS = {"6-K", "20-F", "40-F", "F-1", "F-3"}   # CLAUDE.md rule 7
HEADLINE_MAX = 180                  # characters; the card clamps to two lines


def _type_of(headline: str, grade: str) -> str:
    hay = (headline or "").lower()
    if grade == "dilutive":
        return "offering/dilution"
    if grade == "filing":
        return "filing"
    if grade == "listing":
        return "listing notice"
    for name, words in TYPE_RULES:
        if matches(words, hay):
            return name
    return "PR"


def news_cutoff(trading_date) -> Optional[datetime]:
    """16:00 ET of the trading day before `trading_date`: news published after
    it is "dated today" (FILTERS.md gate 3; the overnight extension is rule C2,
    an Approximation). Weekends and NYSE holidays are skipped, so Friday's
    after-close news is still Monday's catalyst."""
    from datetime import date as _date, timedelta
    from zoneinfo import ZoneInfo
    from .holidays import is_trading_day
    if not trading_date:
        return None
    try:
        day = trading_date if isinstance(trading_date, _date) else _date.fromisoformat(str(trading_date)[:10])
    except ValueError:
        return None
    prev = day - timedelta(days=1)
    for _ in range(10):
        if is_trading_day(prev):
            break
        prev -= timedelta(days=1)
    return datetime(prev.year, prev.month, prev.day, 16, 0, tzinfo=ZoneInfo("America/New_York"))


def _age_label(pub: datetime, trading_date, cutoff: Optional[datetime]) -> tuple:
    """('today_pre' | 'today' | 'after_close' | 'prior' | 'older', words)."""
    from zoneinfo import ZoneInfo
    et = pub.astimezone(ZoneInfo("America/New_York"))
    day = str(trading_date)[:10] if trading_date else None
    if day and et.date().isoformat() == day:
        if et.hour < 9 or (et.hour == 9 and et.minute < 30):
            return "today_pre", f"today {et:%H:%M} · pre-market"
        return "today", f"today {et:%H:%M}"
    from datetime import date as _date
    gap = (_date.fromisoformat(day) - cutoff.date()).days if (day and cutoff is not None) else None
    prior = "yesterday" if gap == 1 else (f"{cutoff:%a}" if cutoff is not None else "")
    if cutoff is not None and et >= cutoff:
        when = f"{et:%H:%M}" if et.date() == cutoff.date() else f"{et:%a %H:%M}"
        return "after_close", f"after {prior}'s close · {when}"
    if cutoff is not None and et.date() == cutoff.date():
        return "prior", f"{prior} {et:%H:%M}"
    if cutoff is not None:
        days = (cutoff.date() - et.date()).days + 1
        return "older", f"{days} days old"
    return "older", f"{et:%Y-%m-%d %H:%M}"


def _clip(text: str, n: int = HEADLINE_MAX) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def card_read(items, *, now: Optional[datetime] = None, trading_date=None,
              source_ok: bool = True, filings: Optional[Sequence[dict]] = None,
              filings_checked: bool = False, split_checked: bool = False,
              split_ratio: Optional[float] = None) -> dict:
    """The catalyst block of the desk card: grade, one-line reason, type, age,
    the headline (clipped), its source and the flags. Rule ids refer to
    knowledge-base/strategies/CATALYST.md."""
    now = now or datetime.now(timezone.utc)
    cutoff = news_cutoff(trading_date)
    flags: List[dict] = []

    def flag(fid: str, text: str, level: str = "warn", rule: str = "") -> None:
        flags.append({"id": fid, "text": text, "level": level, "rule": rule})

    # -- the candidates: the company's own headlines the desk had seen by now (C1)
    own = []
    for it in items or []:
        pub = _iso(it.get("publishedAt"))
        seen = _iso(it.get("firstObservedAt") or it.get("publishedAt"))
        if pub is None or pub > now or (seen is not None and seen > now) or it.get("sharedTag"):
            continue
        g = classify(it.get("headline") or "", it.get("category") or "")
        if g.grade in ("roundup", "reaction"):
            continue
        bucket, words = _age_label(pub, trading_date, cutoff)
        own.append({"item": it, "grade": g, "pub": pub, "bucket": bucket, "age": words,
                    "today": cutoff is None or pub >= cutoff,
                    "type": _type_of(it.get("headline") or "", g.grade),
                    "buyout": buyout_in([it.get("headline") or ""])})
    own.sort(key=lambda c: c["pub"], reverse=True)
    today = [c for c in own if c["today"]]

    # -- flags first: they hold whatever the grade decides (C6, C7, C9-C12)
    for c in today:
        if c["grade"].grade == "dilutive":
            flag("dilution_news", f"offering/dilution in today's news: \"{_clip(c['item'].get('headline') or '', 70)}\"",
                 "bad", "C6")
            break
    if any(c["buyout"] for c in today):
        flag("buyout", "buyout headline — the price pins near the deal (FILTERS.md gate 8)", "bad", "C7")
    fl = list(filings or [])
    foreign = sorted({f.get("form") for f in fl if f.get("form") in FOREIGN_FORMS}
                     | {"6-K" for c in own if (c["item"].get("headline") or "").startswith("SEC 6-K")})
    if foreign:
        flag("foreign_filer", f"foreign issuer ({', '.join(foreign)}): no S-3/424B tripwire — "
             "check EDGAR by hand (CLAUDE.md rule 7)", "warn", "C12")
    take = [f for f in fl if f.get("form") in TAKEDOWN_FORMS]
    recent = [f for f in take if (f.get("age_days") if f.get("age_days") is not None else 9999) <= TAKEDOWN_RECENT_DAYS]
    if recent:
        f = min(recent, key=lambda x: x.get("age_days", 9999))
        flag("takedown", f"{f['form']} filed {f.get('age_days')} d ago — shares are being sold", "bad", "C11")
    elif take:
        f = min(take, key=lambda x: x.get("age_days", 9999))
        flag("takedown_old", f"{f['form']} on file ({f.get('age_days')} d) — an earlier sale", "info", "C11")
    shelves = [f for f in fl if f.get("form") in SHELF_FORMS]
    if shelves:
        f = min(shelves, key=lambda x: x.get("age_days", 9999))
        flag("shelf", f"{f['form']} shelf on file ({f.get('filed')}) — can issue at any time", "warn", "C10")
    if not filings_checked:
        flag("filings_unchecked", "filings not checked — dilution unverified", "info", "C10")
    if split_ratio:
        flag("split", f"the gap is a {split_ratio:g}-for-1 reverse split, not a move", "bad", "C13")
    elif split_checked:
        flag("split", "split test: the gap is not arithmetic", "ok", "C13")
    else:
        flag("split", "split test not run (CLAUDE.md rule 6)", "info", "C13")

    # -- the grade ------------------------------------------------------------
    def out(grade, reason, rule, c=None, typ=None):
        it = (c or {}).get("item") or {}
        return {
            "grade": grade, "reason": reason, "rule": rule,
            "type": typ or (c or {}).get("type") or "none found",
            "age": (c or {}).get("age") or "—", "ageBucket": (c or {}).get("bucket"),
            "headline": _clip(it.get("headline") or "") or None,
            "publishedAt": it.get("publishedAt"),
            "source": ("SEC" if it.get("category") == "sec_filing" else
                       "finviz" if it.get("category") == "finviz_why" else ("wire" if it else None)),
            "url": it.get("url"),
            "cutoff": cutoff.isoformat() if cutoff else None,
            "flags": flags,
        }

    if not source_ok:
        return out("UNKNOWN", "no headline feed on this desk — nothing ruled in or out", "C0", None, "—")
    catalysts = [c for c in today if c["grade"].grade not in ("dilutive", "filing")]
    hard = [c for c in catalysts if c["grade"].grade == "hard" and not c["buyout"]]
    if hard:
        c = hard[0]
        return out("STRONG", f"{c['type']} — the company's own news, dated today: quantifiable value", "C3", c)
    if any(c["buyout"] for c in catalysts):
        c = next(c for c in catalysts if c["buyout"])
        return out("WEAK", "buyout target — the price is pinned near the deal; no momentum left", "C7", c, "deal")
    soft = [c for c in catalysts if c["grade"].grade == "soft"
            and c["type"] in ("analyst", "partnership", "patent", "uplist", "contract", "deal", "earnings", "FDA")]
    if soft:
        c = soft[0]
        return out("MODERATE", f"{c['type']} — attention, no stated value: the chart has to carry it", "C4", c)
    older_hard = [c for c in own if not c["today"] and c["grade"].grade == "hard" and not c["buyout"]
                  and c["bucket"] in ("prior",)]
    if older_hard:
        c = older_hard[0]
        return out("MODERATE", f"yesterday's {c['type']} — day-2 interest, not fresh news", "C8", c)
    pr = [c for c in catalysts if c["grade"].grade in ("soft", "listing")]
    if pr:
        c = pr[0]
        why = ("listing notice — administrative, not economic value" if c["grade"].grade == "listing"
               else "PR without substance — attention, no counterparty, no value")
        return out("WEAK", why, "C5", c, "listing notice" if c["grade"].grade == "listing" else "PR")
    dil = [c for c in today if c["grade"].grade == "dilutive"]
    if dil:
        return out("WEAK", "offering/dilution — supply, not a catalyst", "C6", dil[0])
    unread = [c for c in today if c["grade"].grade == "filing"]
    if unread:
        return out("WEAK", "unread SEC filing — open it; the desk cannot tell what it says", "C9", unread[0])
    since = f"the {cutoff:%a} 16:00 close" if cutoff else "the last close"
    if own:
        return out("WEAK", f"no company news since {since} — the newest own headline is {own[0]['age']}",
                   "C5", own[0], "none found")
    return out("WEAK", f"no company news since {since} — the news pillar fails", "C5")
