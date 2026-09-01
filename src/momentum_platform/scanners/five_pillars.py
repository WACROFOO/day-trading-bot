"""Five Pillars candidate list and rising-edge alert.

Thresholds are Confirmed course values (Preview chapters 1-6):
price $2-$20, gain >= 10%, daily RVOL >= 5x, float < 20M, catalyst.

Two scores are kept separate on purpose (Confirmed platform behavior: the
Warrior scanner does not automatically require news):
- technical_score (0-4): the four measurable pillars;
- full_score (0-5): technical + confirmed catalyst.
A technical candidate is never failed solely because news is absent.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..models import RankedRow, Reason, ScannerEvent, SymbolSnapshot
from ..state import HotState, SymbolState
from .base import EdgeTracker, Scanner, _round

# Confirmed course thresholds.
PRICE_MIN = 2.0
PRICE_MAX = 20.0
GAIN_MIN_PCT = 10.0
RVOL_MIN = 5.0
FLOAT_MAX_SHARES = 20_000_000
# News younger than this counts as a live catalyst for the automated score;
# the flame handles finer age display. Configuration, not a confirmed value.
NEWS_MAX_AGE_MINUTES = 24 * 60


def score_pillars(
    snap: SymbolSnapshot,
    now: datetime,
    news_max_age_minutes: float = NEWS_MAX_AGE_MINUTES,
) -> tuple[List[Reason], int, bool]:
    """Returns (reasons, technical_score 0-4, news_ok)."""
    price_ok = snap.last is not None and PRICE_MIN <= snap.last <= PRICE_MAX
    gain_ok = (snap.change_from_close_pct or 0.0) >= GAIN_MIN_PCT
    rvol_ok = snap.rvol_daily is not None and snap.rvol_daily >= RVOL_MIN
    # Float pillar requires a known supply value below the cap. An unknown
    # float is a failed check, never silently substituted (spec 7.5) — but the
    # reason row says WHY it failed.
    float_known = snap.float_shares is not None
    float_ok = float_known and snap.float_shares < FLOAT_MAX_SHARES

    news_ok = False
    news_age = None
    if snap.latest_news_ts is not None:
        news_age = (now - snap.latest_news_ts).total_seconds() / 60.0
        news_ok = 0 <= news_age <= news_max_age_minutes

    reasons = [
        Reason("price_in_band", _round(snap.last), price_ok, f"{PRICE_MIN}-{PRICE_MAX}"),
        Reason("gain_pct", _round(snap.change_from_close_pct), gain_ok, GAIN_MIN_PCT),
        Reason("rvol_daily", _round(snap.rvol_daily), rvol_ok, RVOL_MIN),
        Reason(
            "float_shares",
            snap.float_shares if float_known else "unknown",
            float_ok,
            FLOAT_MAX_SHARES,
        ),
        Reason("news_catalyst", _round(news_age, 1), news_ok, f"<={news_max_age_minutes}m"),
    ]
    technical = sum([price_ok, gain_ok, rvol_ok, float_ok])
    return reasons, technical, news_ok


class FivePillarsList(Scanner):
    """Ranked list of candidates meeting all four technical pillars,
    sorted by daily RVOL descending. News is a displayed column, not a gate."""

    scanner_id = "five_pillars_list"
    definition_version = "five_pillars_list@1.0.0"
    classification = "confirmed_course_thresholds"

    def __init__(self, max_rows: int = 50) -> None:
        self.max_rows = max_rows

    def rank(self, hot: HotState, now: datetime) -> List[RankedRow]:
        rows: List[RankedRow] = []
        for state in hot.symbols.values():
            snap = state.snapshot
            if snap.last is None:
                continue
            reasons, technical, news_ok = score_pillars(snap, now)
            if technical < 4:
                continue
            rows.append(
                RankedRow(
                    symbol=snap.symbol,
                    rank_metric=snap.rvol_daily or 0.0,
                    values=self._base_values(snap)
                    | {
                        "technical_score": technical,
                        "full_score": technical + int(news_ok),
                        "news": self._news_block(snap, now),
                    },
                    reasons=reasons,
                )
            )
        rows.sort(key=lambda r: r.rank_metric, reverse=True)
        return rows[: self.max_rows]


class FivePillarsAlert(Scanner):
    """Emits one event on the rising edge from non-qualifying to qualifying
    (all four technical pillars). Re-arms only after the symbol has stayed
    non-qualifying for `rearm_after_fails` consecutive evaluations."""

    scanner_id = "five_pillars_alert"
    definition_version = "five_pillars_alert@1.0.0"
    classification = "confirmed_course_thresholds"

    def __init__(self, rearm_after_fails: int = 5) -> None:
        self._edges = EdgeTracker(rearm_after_fails=rearm_after_fails)

    def on_snapshot(
        self,
        current: SymbolSnapshot,
        previous: Optional[SymbolSnapshot],
        state: SymbolState,
        hot: HotState,
    ) -> List[ScannerEvent]:
        now = current.event_ts
        if now is None:
            return []
        reasons, technical, news_ok = score_pillars(current, now)
        qualifies = technical == 4
        if not self._edges.rising_edge(current.symbol, qualifies):
            return []
        return [
            self._event(
                current,
                now,
                event_type="qualified",
                severity="high",
                reasons=reasons,
                extra_values={
                    "technical_score": technical,
                    "full_score": technical + int(news_ok),
                },
            )
        ]
