"""Phase 0: measure the captured tape, then say GO or NO-GO.

The question this answers, and it can end the project in two days: **is a
10-second micro pullback's stop far enough from the trigger to survive the
spread?** A 10-second dip is smaller than a 1-minute dip by construction, and
at 1-minute the spread was already a median 25% of the risk.

Nothing here decides a trade. It describes the tape so a human can decide
whether building the detector is worth it, and it reports what it could not
check rather than omitting it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Iterable, Optional

from . import bars as B
from . import spread as S


@dataclass(frozen=True)
class Dip:
    """A candidate micro pullback found on the 10-second tape.

    Shape only — the Layer A context gates are NOT applied here. This is
    deliberately the optimistic count: if even the unfiltered population has
    unusable stops, the filtered one certainly does.
    """

    symbol: str
    push_high: float
    dip_low: float
    trigger: float          # the push high; entry is a break of it
    bars_in_dip: int
    at: datetime

    @property
    def risk_per_share(self) -> float:
        return self.trigger - self.dip_low

    @property
    def retrace_pct(self) -> Optional[float]:
        rng = self.push_high - self.dip_low
        return None if rng <= 0 else 100.0


def find_dips(candles: Iterable[B.Candle], cfg) -> list[Dip]:
    """Shape detection on closed 10-second candles, strictly left to right.

    push  : a candle that sets a NEW HIGH OF THE RUN
    dip   : 1..max_dip_bars candles that do not exceed that high
    ready : the next candle taking the high out would be the trigger

    The push must set a new run high, not merely exceed its neighbour. An
    earlier draft used the neighbour, and sideways chop under an old high
    then produced a string of one-candle "pullbacks" a few ticks deep —
    which would have dragged the measured stop distribution down and risked
    a false NO-GO on the spread gate. It is also what the spec means by
    "the move is the day's high or close to it" (`MICRO-PULLBACK-SPEC.md`
    §1). Caught by `test_a_pause_longer_than_the_pattern_is_not_a_micro_pullback`.

    When the pause outlives `max_dip_bars_10s` the setup expires and only a
    new run high re-arms it.

    Every dip found is returned, including ones a later gate would reject:
    counting only survivors hides how aggressive the gate is — the funnel
    line rule in `.claude/skills/trading-report-design/SKILL.md`. The Layer A
    context gates are NOT applied here, so this remains an upper bound.
    """
    cs = sorted(candles, key=lambda c: c.ts)
    out: list[Dip] = []
    run_high: Optional[float] = None
    dip: list[B.Candle] = []
    armed = False                      # a push has set the run high and we may dip from it
    for c in cs:
        if run_high is None or c.high > run_high:
            if armed and dip and cfg.min_dip_bars_10s <= len(dip) <= cfg.max_dip_bars_10s:
                out.append(Dip(c.symbol, run_high, min(d.low for d in dip),
                               run_high, len(dip), dip[0].ts))
            run_high, dip, armed = c.high, [], True
            continue
        if not armed:
            continue                   # still waiting for a new run high
        dip.append(c)
        if len(dip) > cfg.max_dip_bars_10s:
            dip, armed = [], False     # the pause outlived the pattern
    return out


def quote_at(conn, symbol: str, when: datetime) -> tuple[Optional[float], Optional[float]]:
    """The last quote at or before `when`, from `quote_ticks`. No quote is
    None, never a guess."""
    iso = when.isoformat().replace("+00:00", "Z")
    row = conn.execute(
        "SELECT bid, ask FROM quote_ticks WHERE symbol = ? AND ts <= ? "
        "ORDER BY ts DESC LIMIT 1", (symbol, iso)).fetchone()
    if row is None:
        return None, None
    return row["bid"], row["ask"]


def measure(conn, cfg, day: Optional[str] = None) -> dict:
    """The whole Phase 0 read-out as one dict."""
    fine = B.load(conn, day=day)
    per_symbol, dips_all = {}, []
    for sym, cs in fine.items():
        cov = B.coverage(cs)
        dips = find_dips(cs, cfg)
        per_symbol[sym] = {"candles": cov["candles"], "minutes": cov["minutes"],
                           "present_pct": cov["present_pct"], "gap_minutes": len(cov["gaps"]),
                           "dips": len(dips)}
        dips_all += dips

    rows = []
    for d in dips_all:
        bid, ask = quote_at(conn, d.symbol, d.at)
        v = S.gate(d.trigger, d.dip_low, bid, ask, cfg)
        rows.append({"symbol": d.symbol, "at": d.at, "risk": d.risk_per_share,
                     "spread": v.spread, "ratio": v.ratio, "state": v.state.value,
                     "bars_in_dip": d.bars_in_dip})

    risks = [r["risk"] for r in rows if r["risk"] and r["risk"] > 0]
    ratios = [r["ratio"] for r in rows if r["ratio"] is not None]
    quoted = [r for r in rows if r["ratio"] is not None]
    # The plan's own stop condition, measured directly (review 2026-09-21,
    # item 7): a dip is INSIDE the spread when its depth — which IS the stop
    # distance here, `Dip.risk_per_share = trigger − dip_low` — is at most
    # one spread, i.e. spread ÷ risk ≥ 1. The median of that ratio was 0.41,
    # so the median dip was NOT inside the spread; the NO-GO stood on the
    # k-survival line instead, and the report must say which.
    inside = [r for r in quoted if r["ratio"] >= 1.0]
    survive = {}
    for k in (2, 4, 6, 8, 10, 15, 20):
        n = sum(1 for r in quoted if r["ratio"] <= 1.0 / k)
        survive[k] = {"n": n, "pct": round(100.0 * n / len(quoted), 1) if quoted else None}

    return {
        "day": day or "all captured",
        "symbols": per_symbol,
        "candles": sum(v["candles"] for v in per_symbol.values()),
        "dips": len(dips_all),
        "dips_with_quote": len(quoted),
        "dips_without_quote": len(rows) - len(quoted),
        "risk_per_share": _dist(risks),
        "spread_over_risk": _dist(ratios),
        "dips_inside_spread": {"n": len(inside),
                               "pct": round(100.0 * len(inside) / len(quoted), 1) if quoted else None,
                               "median_dip_inside": bool(quoted) and median(ratios) >= 1.0},
        "survival_by_k": survive,
        "k_in_force": cfg.spread_k,
        "passing_at_k": sum(1 for r in rows if r["state"] == "PASS"),
        "rows": rows,
    }


def _dist(v: list) -> dict:
    if not v:
        return {"n": 0, "median": None, "min": None, "max": None}
    s = sorted(v)
    return {"n": len(s), "median": round(median(s), 4),
            "min": round(s[0], 4), "max": round(s[-1], 4),
            "p25": round(s[len(s) // 4], 4), "p75": round(s[(3 * len(s)) // 4], 4)}


def verdict(m: dict, cfg) -> tuple[str, list[str]]:
    """GO / NO-GO / INCONCLUSIVE, with the reasons that decided it.

    The thresholds are stated here, before the data exists, so the answer
    cannot be renegotiated once the number is known.
    """
    reasons = []
    if m["candles"] < 1000:
        return "INCONCLUSIVE", [
            f"only {m['candles']} ten-second candles captured — not a session. "
            "Check the desk ran and JOURNAL_DB was set."]
    if m["dips"] == 0:
        return "NO-GO", ["no micro pullback shape found on the 10-second tape at all."]
    if m["dips_with_quote"] < 20:
        return "INCONCLUSIVE", [
            f"only {m['dips_with_quote']} dips carry a quote; the spread gate "
            "cannot be judged on fewer than 20."]

    pct = m["survival_by_k"].get(int(cfg.spread_k), {}).get("pct")
    med = m["spread_over_risk"]["median"]
    if pct is not None and pct < 10:
        reasons.append(f"only {pct}% of dips clear k={cfg.spread_k:g} — the spread "
                       f"eats a 10-second stop on this universe.")
    if med is not None and med >= 1.0:
        reasons.append(f"the plan's stop condition fired: the median dip is inside the spread "
                       f"(median spread {med:.2f}x the whole stop).")
    elif med is not None and reasons:
        reasons.append(f"the plan's own stop condition (median dip inside the spread) did NOT fire: "
                       f"median spread is {med:.2f} of the stop; this verdict rests on k-survival.")
    if reasons:
        return "NO-GO", reasons

    reasons.append(f"{pct}% of {m['dips_with_quote']} quoted dips clear k={cfg.spread_k:g}.")
    reasons.append(f"median spread is {med:.2f} of the risk "
                   f"(a round trip costs {med:.2f} R).")
    return ("GO" if pct and pct >= 25 else "MARGINAL"), reasons


def limitations() -> list[str]:
    """What this measurement does NOT establish. Always printed."""
    return [
        "Shape only: the Layer A context gates (VWAP, 9 EMA, MACD, impulse) are "
        "NOT applied, so the dip count is an optimistic upper bound.",
        "The quote is the last tick at or before the dip, not the quote at a fill.",
        "No fill, no slippage, no partial fill and no commission is modelled.",
        "A halt inside a dip is not detected; the halts table has been empty for "
        "five sessions and that is unexplained.",
        "One universe, the days captured, no claim beyond them.",
    ]
