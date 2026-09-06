"""Build a deterministic dashboard replay session from a market fixture.

The session is produced by running the PRODUCTION scanner engine over the
fixture, so the UI prototype can never drift from the real scanner logic.
Same input -> byte-identical output.

Size discipline: every list row shares one column schema and is emitted as a
compact array. Five Pillars pass/fail is recomputed in the browser from the
row's own numbers plus the published Confirmed thresholds, so the UI shows the
arithmetic rather than a server verdict it cannot check. Alerts carry their
server-side reasons verbatim.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from ..cascade import Inputs as CascadeInputs
from ..cascade import evaluate as evaluate_cascade
from ..engine import ScannerEngine
from ..models import Bar, DataStatus, FloatQuality, NewsItem, flame_color
from ..notify import NotificationRouter, RouterConfig
from ..pullback import FirstPullbackDetector
from ..scanners import (
    FivePillarsAlert,
    FivePillarsList,
    HodMomentumScanner,
    RunningMoveScanner,
    UptrendScanner,
    TopGappersScanner,
    squeeze_5_in_5,
    squeeze_10_in_10,
    Breakout52wScanner,
    top_gainers,
    top_relative_volume,
    top_volume_5m,
)
from ..scanners.momentum_events import MIN_VOLUME_5M
from ..scanners.five_pillars import (
    PRICE_BAND_EVIDENCE,
    FLOAT_MAX_SHARES,
    GAIN_MIN_PCT,
    DESK_BAND_EVIDENCE,
    DESK_PRICE_MAX,
    DESK_PRICE_MIN,
    PRICE_MAX,
    PRICE_MIN,
    RVOL_MIN,
)
from ..state import HotState, MarketUpdate, ReferenceData

UTC = timezone.utc

ROW_COLUMNS = [
    "symbol", "price", "changePct", "gapPct", "volume",
    # `rvolDaily` is today over prior FULL days; `rvol` is the measure the
    # pillar actually judged (time-of-day when the desk has a volume profile).
    # A row that showed the daily number while the gate used the other one
    # looked impossible: 1.3x sitting in a list that requires 5x.
    "rvolDaily", "rvol5m", "spread", "hodDistPct", "rangePos", "volume5m",
    "rvol", "rvolMeasure",
]

LIST_META = {
    "five_pillars_list": {"title": "Top gainers · 5 pillars", "metric": "Change %",
                          "note": "Price, gain and RVOL pass; ranked by change from the previous "
                                  "close, premarket and regular alike. Float and news are columns, "
                                  "never gates."},
    "top_gappers": {"title": "Top Gappers", "metric": "Gap %",
                    "note": "Freezes at 09:30 ET, matching the captured platform."},
    "top_gainers": {"title": "Top Gainers", "metric": "Change from close %",
                    "note": "Continues updating all session."},
    "top_relative_volume": {"title": "Top Relative Volume", "metric": "RVOL",
                            "note": "Volume so far against what prior sessions had traded by this "
                                    "clock time, when the desk has a profile; today / mean prior "
                                    "full-day volume when it does not."},
    "top_volume_5m": {"title": "Top Volume 5 Minutes", "metric": "5m volume",
                      "note": "Raw share volume, never silently replaced by RVOL."},
}

ALERT_META = {
    "five_pillars_alert": {"title": "Ross's 5 Pillars Alert", "severity": "high"},
    "hod_momentum": {"title": "Small Cap - High of Day Momentum", "severity": "high"},
    "running_up": {"title": "Running Up · 10-minute uptrend", "severity": "medium"},
    "squeeze_5_in_5": {"title": "Squeeze - Up 5% in 5min", "severity": "medium"},
    "squeeze_10_in_10": {"title": "Squeeze - Up 10% in 10min", "severity": "medium"},
    "breakout_52w": {"title": "Squeeze - 52wk Breakout", "severity": "medium"},
    "halt": {"title": "Halt", "severity": "critical"},
}


def _num(v, nd=2):
    return None if v is None else round(v, nd)


def _row(ranked) -> list:
    """Build a row from the ranked result's OWN captured values, never from the
    live snapshot — otherwise a frozen list would keep updating its numbers."""
    v = ranked.values
    return [
        ranked.symbol, _num(v.get("last"), 4), v.get("change_pct"), v.get("gap_pct"),
        int(v.get("volume_today") or 0), v.get("rvol_daily"), v.get("rvol_5m"),
        v.get("spread"), v.get("hod_distance_pct"), v.get("range_position"),
        int(v.get("volume_5m") or 0),
        v.get("rvol"), v.get("rvol_measure"),
    ]


def build_session(fixture_path: str | Path, max_rows: int = 10,
                  journal=None) -> dict:
    """Build a session from a replay fixture file."""
    fixture_path = Path(fixture_path)
    records = [
        json.loads(line)
        for line in fixture_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return build_session_from_records(records, fixture_path.stem, fixture_path.name,
                                      max_rows, journal=journal)



def _et_clock(ts) -> "str | None":
    """'2026-09-02T08:12:33.12Z' -> '04:12:33' for the quote card.

    No ' ET' suffix: the whole desk runs on the ET clock and the header says
    so. The suffix was appended only on this path, so between a server rebuild
    and a streamed quote the same field alternated between '14:59:43 ET' and
    '14:59:43' — the suffix blinked on and off in the card.
    """
    if not ts:
        return None
    try:
        from zoneinfo import ZoneInfo
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return None


def build_session_from_records(
    records: list,
    session_id: str,
    source_name: str,
    max_rows: int = 10,
    data_status: str = "replay",
    volume_floor_scale: float = 1.0,
    trading_date: str | None = None,
    journal=None,
) -> dict:
    """Build the dashboard session.

    `journal` is an open `journal.ledger` connection, or None. When given,
    every plan the detector arms — allowed or suppressed — is written as a
    decision with the point-in-time snapshot and the full cascade result,
    every halt transition is recorded with the price before it, and the board
    is snapshotted at the end. Writes are idempotent, so the live desk's
    rebuild-every-few-seconds loop records each decision once. This is the
    desk's only relationship with the exercise: it writes what it saw. It
    never reads an order, and it never touches the order-path package.

    volume_floor_scale multiplies the scanners' absolute share-count floors
    (the 25,000-shares-per-5-minutes liquidity gates). Those floors are stated
    against the consolidated tape. A single-venue feed such as IEX carries a
    fraction of that volume, so the same floor applied unscaled keeps every
    event scanner silent on a stock that is plainly running — exactly what a
    full live session showed: two names up 35-75% on 80x relative volume, and
    zero alerts all day. Relative-volume gates are unaffected: both sides of
    those ratios come from the same venue.
    """
    """Build a session from normalized records. Replay fixtures and live
    provider pulls both land here, so the scanner behaviour is identical."""

    symbols: dict[str, dict] = {}
    news_queue: list[dict] = []
    halt_queue: list[dict] = []
    bar_records: list[dict] = []

    for rec in records:
        kind = rec.get("type")
        if kind == "reference":
            symbols[rec["symbol"]] = {
                "symbol": rec["symbol"],
                "prevClose": rec.get("prev_close"),
                "avgDailyVolume": rec.get("avg_daily_volume"),
                "volumeProfileDays": rec.get("volume_profile_days"),
                "high52w": rec.get("high_52w"),
                "floatShares": rec.get("float_shares"),
                "floatQuality": rec.get("float_quality", "unknown"),
                "floatAsOf": rec.get("float_asof"),
                "floatSource": rec.get("float_source"),
                "exchange": rec.get("exchange"),
                "country": rec.get("country"),
                "incorporatedIn": rec.get("incorporated_in"),
                "name": rec.get("name"),
                "iexLast": rec.get("iex_last_price"),
                "iexLastTime": _et_clock(rec.get("iex_last_ts")),
                "iexBid": rec.get("iex_bid"), "iexAsk": rec.get("iex_ask"),
                "iexBidSize": rec.get("iex_bid_size"), "iexAskSize": rec.get("iex_ask_size"),
                "iexLastTs": rec.get("iex_last_ts"),
                "lastSource": rec.get("last_source", "iex"),
                "dailyBars": rec.get("daily_bars", []),
                "news": [],
            }
        elif kind == "news":
            news_queue.append(rec)
        elif kind == "halt":
            halt_queue.append(rec)
        elif kind == "bar":
            bar_records.append(rec)

    # 10-second fixtures are the single source of truth: the 1-minute bars the
    # scanner engine consumes are aggregated from them, so no chart timeframe
    # can disagree with what the scanners saw. Feeds that only publish minute
    # bars (any live provider on a free tier) pass straight through.
    sub_bars: dict[str, list] = {}
    if any(r.get("tf") == "10s" for r in bar_records):
        minute_groups: dict[tuple, list] = {}
        order: list = []
        for rec in bar_records:
            if rec.get("tf") == "10s":
                sub_bars.setdefault(rec["symbol"], []).append([
                    int(datetime.fromisoformat(rec["ts"].replace("Z", "+00:00")).timestamp()),
                    rec["open"], rec["high"], rec["low"], rec["close"], rec["volume"],
                ])
            # A 1-minute record collapses to a one-bar chunk below, unchanged.
            minute_iso = rec["ts"][:17] + "00Z" if len(rec["ts"]) > 17 else rec["ts"]
            key = (rec["symbol"], minute_iso)
            if key not in minute_groups:
                minute_groups[key] = []
                order.append(key)
            minute_groups[key].append(rec)
        bar_records = []
        for symbol, minute_iso in order:
            chunk = minute_groups[(symbol, minute_iso)]
            bar_records.append({
                "type": "bar", "symbol": symbol, "ts": minute_iso,
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(c["volume"] for c in chunk),
                "bid": chunk[-1].get("bid"), "ask": chunk[-1].get("ask"),
            })

    profiles = {r["symbol"]: r.get("volume_profile") for r in records
                if r.get("type") == "reference" and r.get("volume_profile")}
    hot = HotState()
    hot.load_reference([
        ReferenceData(
            symbol=s["symbol"], prev_close=s["prevClose"],
            avg_daily_volume=s["avgDailyVolume"], high_52w=s["high52w"],
            volume_profile=profiles.get(s["symbol"]),
            float_shares=s["floatShares"],
            float_quality=FloatQuality(s["floatQuality"]),
        )
        for s in symbols.values()
    ])

    captured: list = []          # [(event, consolidation_group)]
    router = NotificationRouter(RouterConfig(), [_Collector(captured)])
    engine = ScannerEngine(
        hot=hot,
        scanners=[
            FivePillarsAlert(),
            HodMomentumScanner(min_volume_5m=MIN_VOLUME_5M * volume_floor_scale),
            UptrendScanner(min_volume_5m=MIN_VOLUME_5M * volume_floor_scale),
            RunningMoveScanner(direction="down", min_volume_5m=MIN_VOLUME_5M * volume_floor_scale),
            squeeze_5_in_5(), squeeze_10_in_10(),
            Breakout52wScanner(),
            FivePillarsList(max_rows=max_rows), TopGappersScanner(max_rows=max_rows),
            top_gainers(max_rows=max_rows), top_relative_volume(max_rows=max_rows),
            top_volume_5m(max_rows=max_rows),
        ],
        router=router,
    )

    detectors = {sym: FirstPullbackDetector() for sym in symbols}
    plans: list[dict] = []
    suppressed_plans: list[dict] = []
    bars_by_symbol: dict[str, list] = {sym: [] for sym in symbols}
    frames: list[dict] = []

    # group bar records by minute, preserving fixture order inside a minute
    minutes: dict[str, list] = {}
    for rec in bar_records:
        minutes.setdefault(rec["ts"], []).append(rec)

    pending_news = sorted(news_queue, key=lambda r: r.get("first_observed_at", r["published_at"]))
    pending_halts = sorted(halt_queue, key=lambda r: r.get("ts", ""))
    halt_state: dict[str, str] = {}

    for ts_iso in sorted(minutes):
        ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        captured.clear()

        # News becomes visible only at first_observed_at: this reproduces the
        # confirmed behaviour where a flame can appear after the alert.
        while pending_news:
            observed = pending_news[0].get("first_observed_at", pending_news[0]["published_at"])
            if datetime.fromisoformat(observed.replace("Z", "+00:00")) > ts:
                break
            rec = pending_news.pop(0)
            published = datetime.fromisoformat(rec["published_at"].replace("Z", "+00:00"))
            hot.attach_news(NewsItem(
                provider="fixture", provider_id=rec["provider_id"], published_at=published,
                headline=rec["headline"], symbols=[rec["symbol"]], category=rec.get("category"),
            ))
            symbols[rec["symbol"]]["news"].append({
                "id": rec["provider_id"], "publishedAt": rec["published_at"],
                "firstObservedAt": observed, "headline": rec["headline"],
                "category": rec.get("category"),
            })

        frame_alerts: list[dict] = []
        while pending_halts and pending_halts[0].get("ts", "") <= ts_iso:
            rec = pending_halts.pop(0)
            hot.set_halt(rec["symbol"], rec["status"])
            previous = halt_state.get(rec["symbol"], "trading")
            halt_state[rec["symbol"]] = rec["status"]
            if previous != rec["status"] and journal is not None:
                _hs = hot.symbols.get(rec["symbol"])
                _journal_halt(journal, rec, _hs.snapshot.last if _hs else None)
            if previous != rec["status"]:
                # Halt transitions come from an official status source and are
                # never suppressed by cooldown or consolidation.
                frame_alerts.append({
                    "eventId": f"halt-{rec['symbol']}-{ts_iso}",
                    "symbol": rec["symbol"], "scannerId": "halt",
                    "branch": "halt.started" if rec["status"] == "halted" else "halt.resumed",
                    "severity": "critical", "sourceTime": ts_iso, "observedTime": ts_iso,
                    "definitionVersion": "halt@1.0.0",
                    "reasons": [{"field": "official_status", "value": rec["status"],
                                 "passed": True, "evidence": "confirmed"}],
                    "values": {"last": _num(hot.get(rec["symbol"]).snapshot.last, 4)},
                })

        for rec in minutes[ts_iso]:
            bar = Bar(symbol=rec["symbol"], timeframe="1m", ts=ts, open=rec["open"],
                      high=rec["high"], low=rec["low"], close=rec["close"],
                      volume=rec["volume"])
            engine.process(MarketUpdate(
                symbol=rec["symbol"], ts=ts, price=rec["close"], size=rec["volume"],
                bid=rec.get("bid"), ask=rec.get("ask"), bar=bar,
                data_status=DataStatus.REPLAY,
            ))
            bars_by_symbol[rec["symbol"]].append([
                int(ts.timestamp()), rec["open"], rec["high"], rec["low"],
                rec["close"], rec["volume"],
            ])
            plan = detectors[rec["symbol"]].on_bar(bar)
            if plan is not None:
                # The state machine still runs on every bar — suppressing the
                # DETECTOR would lose the structure the moment a name became
                # tradeable. What is suppressed is the PLAN reaching the
                # payload: a name the cascade killed gets no entry, no stop and
                # no target, anywhere. IMRN 2026-09-04 failed the $2-20 price
                # gate and the desk still published `Entry 1.75 · Stop 1.71`.
                _st = hot.symbols.get(rec["symbol"])
                _snap = _st.snapshot if _st else None
                _meta = symbols.get(rec["symbol"], {})
                _inputs = cascade_inputs(_meta, halt_state.get(rec["symbol"]), snap=_snap)
                _res = evaluate_cascade(_inputs) if _meta else None
                allowed = bool(_res and _res.plan_allowed)
                if journal is not None and _res is not None:
                    _journal_decision(journal, rec, bar, plan, _res, _inputs, _snap,
                                      _meta, session_id, source_name, data_status)
                if allowed:
                    plans.append({
                        "planId": plan.plan_id, "symbol": plan.symbol,
                        "armedAt": int(plan.armed_at_bar.timestamp()),
                        "triggerHigh": plan.trigger_high, "entry": plan.entry,
                        "stop": plan.stop, "target": plan.target,
                        "riskShare": plan.risk_share, "rewardMultiple": plan.reward_multiple,
                        "pullbackLow": plan.pullback_low, "impulseHigh": plan.impulse_high,
                        "pullbackCandles": plan.pullback_candles, "volumeOk": plan.volume_ok,
                    })
                else:
                    suppressed_plans.append({
                        "planId": plan.plan_id, "symbol": plan.symbol,
                        "armedAt": int(plan.armed_at_bar.timestamp()),
                    })

        for event, group in captured:
            snap_values = dict(event.values)
            frame_alerts.append({
                "eventId": event.event_id, "idempotencyKey": event.idempotency_key,
                "symbol": event.symbol, "scannerId": event.scanner, "branch": event.branch,
                "severity": event.severity, "sourceTime": event.source_ts.isoformat(),
                "observedTime": event.scan_ts.isoformat(),
                "definitionVersion": event.definition_version,
                "values": snap_values,
                "reasons": [
                    {**r.to_dict(),
                     "evidence": "confirmed" if event.scanner == "five_pillars_alert"
                                 else "approximation"}
                    for r in event.reasons
                ],
                "news": event.news,
                # The group dict keeps filling as later same-symbol alerts are
                # consolidated into it, so "+N more" is exact by frame end.
                "group": group,
            })

        lists = {}
        for scanner in engine.scanners:
            rows = scanner.rank(hot, ts)
            if not rows:
                continue
            lists[scanner.scanner_id] = [_row(r) for r in rows]

        session_name = hot.calendar.session_at(ts).value
        frames.append({
            "ts": ts_iso,
            "t": int(ts.timestamp()),
            "session": session_name,
            "feed": {"status": "replay", "lastEventAgeSec": 0},
            "barIndex": len(bars_by_symbol[next(iter(symbols))]) - 1,
            "barIndex10s": len(bars_by_symbol[next(iter(symbols))]) * 6 - 1 if sub_bars else None,
            "lists": lists,
            "alerts": frame_alerts,
            "halts": dict(halt_state),
        })

    # Every desk name carries its own numbers. The Five Pillars board used to
    # scavenge them out of whatever ranked list a symbol happened to reach, so
    # a name in no list read UNKNOWN on every pillar however much was known
    # about it.
    for sym, meta in symbols.items():
        snap = hot.symbols[sym].snapshot if sym in hot.symbols else None
        if snap is None:
            continue
        meta["metrics"] = {
            "last": snap.last,
            "changePct": _num(snap.change_from_close_pct),
            "volumeToday": int(snap.volume_today or 0),
            "volume5m": None if snap.volume_5m is None else int(snap.volume_5m),
            "rvol": _num(snap.rvol),
            "rvolDaily": _num(snap.rvol_daily),
            "rvolTod": _num(snap.rvol_tod),
            "rvolMeasure": snap.rvol_measure,
            "rvolBaseline": None if snap.rvol_baseline is None else int(snap.rvol_baseline),
            "rvol5m": _num(snap.rvol_5m),
            "sessionHigh": snap.session_high,
            "sessionLow": snap.session_low,
            "hodDistPct": _num(snap.hod_distance_pct),
            "rangePos": _num(snap.range_position, 3),
            "spread": _num(snap.spread_abs, 4),
        }

    # A live desk names the session day it is showing; the first frame's date
    # is a replay convenience only. Derived from the frames, a desk holding
    # last night's tape at 04:03 ET labelled itself with yesterday.
    trading_date = trading_date or (
        frames[0]["ts"][:10] if frames else datetime.now(UTC).strftime("%Y-%m-%d")
    )
    # The cascade verdict is computed HERE, server-side, and shipped. The
    # browser recomputes pillar ARITHMETIC on purpose — so the UI shows the
    # sums rather than an opaque verdict — but the POLICY (what kills, in what
    # order, and what fails closed) is not arithmetic a reader can eyeball,
    # and two implementations of it can disagree. They did: app.js summed four
    # booleans into a score where FILTERS.md Layer 1 kills.
    cascade_by_symbol = {}
    for sym, meta in symbols.items():
        meta.setdefault("symbol", sym)
        res = evaluate_cascade(cascade_inputs(meta, halt_state.get(sym)))
        cascade_by_symbol[sym] = {
            "verdict": res.verdict.value,
            "killedBy": res.killed_by,
            "planAllowed": res.plan_allowed,
            "reasons": res.reasons,
            "warnings": res.warnings,
            "gates": [{"id": g.id, "label": g.label, "state": g.state.value,
                       "value": g.value, "reason": g.reason} for g in res.gates],
        }

    if journal is not None and frames:
        # R1, the denominator: every symbol on the board with its verdict,
        # stamped with the last bar this build saw. On the live desk that is
        # now; on a replay it is the end of the fixture, and the row says so
        # through its timestamp rather than pretending to be mid-session.
        _journal_board(journal, frames[-1]["ts"], session_id, symbols, cascade_by_symbol)
        # The tape itself, and the latest quote per name. Bars let actuals run
        # on a real session with no fixture; quotes are the runner's NBBO at
        # fill time. Neither is a decision, so neither touches `decisions`.
        _journal_tape(journal, bar_records, symbols)

    return {
        "sessionId": session_id,
        "generatedFrom": source_name,
        "dataStatus": data_status,
        "tradingDate": trading_date,
        "timezone": "America/New_York",
        "disclaimer": ("Clean-room approximations. Scanner events are research candidates, "
                       "never entry signals or orders."),
        "rowColumns": ROW_COLUMNS,
        "listMeta": LIST_META,
        "alertMeta": ALERT_META,
        "pillarThresholds": {
            "priceMin": PRICE_MIN, "priceMax": PRICE_MAX, "gainMinPct": GAIN_MIN_PCT,
            "rvolMin": RVOL_MIN, "floatMaxShares": FLOAT_MAX_SHARES,
            "evidence": PRICE_BAND_EVIDENCE,
            "deskPriceMin": DESK_PRICE_MIN, "deskPriceMax": DESK_PRICE_MAX,
            "deskBandEvidence": DESK_BAND_EVIDENCE,
        },
        "definitionVersions": {s.scanner_id: s.definition_version for s in engine.scanners},
        "symbols": symbols,
        "bars": bars_by_symbol,
        "bars10s": sub_bars,
        "frames": frames,
        "plans": plans,
        # Plans the detector armed but the cascade refused to publish. Counted
        # rather than dropped: a silent filter is the anti-pattern, and this
        # number is the first thing to look at if the desk shows no plans.
        "suppressedPlans": suppressed_plans,
        "cascade": cascade_by_symbol,
    }


def cascade_inputs(meta: dict, halt: Optional[str] = None,
                   feed_stale: bool = False, snap=None) -> CascadeInputs:
    """Adapt a session symbol record to the cascade's Inputs.

    Everything the cascade cannot establish is passed as None rather than
    guessed. That matters most for float: `floatQuality` distinguishes a
    verified figure from a shares-outstanding UPPER BOUND, and the cascade
    treats an over-cap bound as MANUAL_CONFIRMATION_REQUIRED — a question for
    a human, not a pass. On the desk that surfaces as REJECT with a reason,
    and the operator answers it with the "Float you verified" input that
    already exists on the card.
    """
    # `snap` is the live snapshot at THIS bar. It matters: meta["metrics"] is
    # attached after the bar loop finishes, so a plan arming mid-session would
    # otherwise be judged against an empty metrics dict, read no price, and
    # fail closed on the price gate. Every plan in the replay fixture was
    # suppressed that way before this argument existed.
    if snap is not None:
        m = {"last": snap.last, "changePct": snap.change_from_close_pct,
             "sessionHigh": snap.session_high, "rvol": snap.rvol,
             "volumeToday": snap.volume_today}
    else:
        m = meta.get("metrics") or {}
    quality = meta.get("floatQuality", "unknown")
    return CascadeInputs(
        symbol=meta.get("symbol", "?"),
        last=m.get("last"),
        change_pct=m.get("changePct"),
        session_high=m.get("sessionHigh"),
        float_shares=meta.get("floatShares"),
        float_is_shares_outstanding=(quality == "shares_outstanding_proxy"),
        float_verified=(quality in ("verified", "you verified")),
        catalyst_today=bool(meta.get("news")),
        session_volume=m.get("volumeToday"),
        rvol=m.get("rvol"),
        halted=(halt == "halted"),
        feed_stale=feed_stale,
    )


def _plan_allowed(meta: dict, halt: Optional[str], snap=None) -> bool:
    """A killed name gets no plan. Halt is NOT a kill — it is a WAIT — so a
    halted name may still carry a plan for when it reopens; what it must not
    carry is a plan the cascade rejected the name outright for."""
    if not meta:
        return False
    return evaluate_cascade(cascade_inputs(meta, halt, snap=snap)).plan_allowed


class _Collector:
    """Notification channel that captures delivered events for the session."""

    name = "session_collector"

    def __init__(self, sink: list) -> None:
        self.sink = sink

    def deliver(self, event, consolidated=None) -> None:
        self.sink.append((event, consolidated))



# ----------------------------------------------------------- the journal
# Lazy imports: the desk must keep working with no journal package on the
# path, and the journal must never pull an order path in behind it — it is
# neutral ground, and a test asserts the desk imports nothing of the order path.

def _journal_decision(journal, rec, bar, plan, res, inputs, snap, meta,
                      session_id, source_name, data_status) -> None:
    from journal import ledger as _L
    snapshot = {
        "last": getattr(snap, "last", None) if snap else rec.get("close"),
        "bid": rec.get("bid"), "ask": rec.get("ask"),
        "session_high": getattr(snap, "session_high", None) if snap else None,
        "volume": getattr(snap, "volume_today", None) if snap else None,
        "rvol": getattr(snap, "rvol", None) if snap else None,
        "change_pct": getattr(snap, "change_from_close_pct", None) if snap else None,
    }
    _L.record_decision(
        journal, symbol=rec["symbol"], armed_at=plan.armed_at_bar, plan=plan,
        cascade=res, inputs=inputs, snapshot=snapshot,
        session=_L.session_of(plan.armed_at_bar), session_id=session_id,
        source_name=source_name, data_status=data_status,
        bar_resolution=getattr(bar, "timeframe", "1m"),
        float_quality=meta.get("floatQuality"), float_source=meta.get("floatSource"),
    )


def _journal_halt(journal, rec, last_before) -> None:
    from journal import ledger as _L
    _L.record_halt(journal, rec["ts"], rec["symbol"], rec["status"], last_before)


def _journal_board(journal, ts, session_id, symbols, cascade_by_symbol) -> None:
    from journal import ledger as _L
    rows = []
    for sym, c in cascade_by_symbol.items():
        m = (symbols.get(sym) or {}).get("metrics") or {}
        rows.append({"symbol": sym, "verdict": c["verdict"], "killed_by": c["killedBy"],
                     "plan_allowed": c["planAllowed"], "last": m.get("last")})
    _L.record_board(journal, ts, session_id, rows)



def _journal_tape(journal, bar_records, symbols) -> None:
    from journal import ledger as _L
    by_sym: dict = {}
    latest: dict = {}
    for rec in bar_records:
        by_sym.setdefault(rec["symbol"], []).append(
            (rec["ts"], rec["open"], rec["high"], rec["low"], rec["close"], rec["volume"],
             rec.get("bid"), rec.get("ask")))
        if rec.get("bid") is not None or rec.get("ask") is not None:
            latest[rec["symbol"]] = {"bid": rec.get("bid"), "ask": rec.get("ask"),
                                     "bid_size": rec.get("bid_size"),
                                     "ask_size": rec.get("ask_size"), "ts": rec["ts"]}
    for sym, meta in symbols.items():
        # The reference record's stream quote is newer than any bar when the
        # desk is live; prefer it, keep its own timestamp.
        if meta.get("iexBid") is not None or meta.get("iexAsk") is not None:
            latest[sym] = {"bid": meta.get("iexBid"), "ask": meta.get("iexAsk"),
                           "bid_size": meta.get("iexBidSize"), "ask_size": meta.get("iexAskSize"),
                           "ts": meta.get("iexLastTs") or latest.get(sym, {}).get("ts")}
    _L.record_bars(journal, by_sym)
    _L.record_quotes(journal, latest)
