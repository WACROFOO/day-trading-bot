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

from ..engine import ScannerEngine
from ..models import Bar, DataStatus, FloatQuality, NewsItem, flame_color
from ..notify import NotificationRouter, RouterConfig
from ..pullback import FirstPullbackDetector
from ..scanners import (
    FivePillarsAlert,
    FivePillarsList,
    HodMomentumScanner,
    RunningMoveScanner,
    TopGappersScanner,
    squeeze_5_in_5,
    squeeze_10_in_10,
    Breakout52wScanner,
    top_gainers,
    top_relative_volume,
    top_volume_5m,
)
from ..scanners.five_pillars import (
    FLOAT_MAX_SHARES,
    GAIN_MIN_PCT,
    PRICE_MAX,
    PRICE_MIN,
    RVOL_MIN,
)
from ..state import HotState, MarketUpdate, ReferenceData

UTC = timezone.utc

ROW_COLUMNS = [
    "symbol", "price", "changePct", "gapPct", "volume",
    "rvolDaily", "rvol5m", "spread", "hodDistPct", "rangePos",
]

LIST_META = {
    "five_pillars_list": {"title": "Ross-style Five Pillars Scan", "metric": "Daily RVOL",
                          "note": "All four technical pillars pass. News is a column, not a gate."},
    "top_gappers": {"title": "Top Gappers", "metric": "Gap %",
                    "note": "Freezes at 09:30 ET, matching the captured platform."},
    "top_gainers": {"title": "Top Gainers", "metric": "Change from close %",
                    "note": "Continues updating all session."},
    "top_relative_volume": {"title": "Top Relative Volume", "metric": "Daily RVOL",
                            "note": "Simple daily RVOL: today's volume / mean prior full-day volume."},
    "top_volume_5m": {"title": "Top Volume 5 Minutes", "metric": "5m volume",
                      "note": "Raw share volume, never silently replaced by RVOL."},
}

ALERT_META = {
    "five_pillars_alert": {"title": "Ross's 5 Pillars Alert", "severity": "high"},
    "hod_momentum": {"title": "Small Cap - High of Day Momentum", "severity": "high"},
    "running_up": {"title": "Running Up", "severity": "medium"},
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
    ]


def build_session(fixture_path: str | Path, max_rows: int = 10) -> dict:
    fixture_path = Path(fixture_path)
    records = [
        json.loads(line)
        for line in fixture_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

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
                "high52w": rec.get("high_52w"),
                "floatShares": rec.get("float_shares"),
                "floatQuality": rec.get("float_quality", "unknown"),
                "dailyBars": rec.get("daily_bars", []),
                "news": [],
            }
        elif kind == "news":
            news_queue.append(rec)
        elif kind == "halt":
            halt_queue.append(rec)
        elif kind == "bar":
            bar_records.append(rec)

    hot = HotState()
    hot.load_reference([
        ReferenceData(
            symbol=s["symbol"], prev_close=s["prevClose"],
            avg_daily_volume=s["avgDailyVolume"], high_52w=s["high52w"],
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
            FivePillarsAlert(), HodMomentumScanner(), RunningMoveScanner(direction="up"),
            RunningMoveScanner(direction="down"), squeeze_5_in_5(), squeeze_10_in_10(),
            Breakout52wScanner(),
            FivePillarsList(max_rows=max_rows), TopGappersScanner(max_rows=max_rows),
            top_gainers(max_rows=max_rows), top_relative_volume(max_rows=max_rows),
            top_volume_5m(max_rows=max_rows),
        ],
        router=router,
    )

    detectors = {sym: FirstPullbackDetector() for sym in symbols}
    plans: list[dict] = []
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
                plans.append({
                    "planId": plan.plan_id, "symbol": plan.symbol,
                    "armedAt": int(plan.armed_at_bar.timestamp()),
                    "triggerHigh": plan.trigger_high, "entry": plan.entry,
                    "stop": plan.stop, "target": plan.target,
                    "riskShare": plan.risk_share, "rewardMultiple": plan.reward_multiple,
                    "pullbackLow": plan.pullback_low, "impulseHigh": plan.impulse_high,
                    "pullbackCandles": plan.pullback_candles, "volumeOk": plan.volume_ok,
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
            "lists": lists,
            "alerts": frame_alerts,
            "halts": dict(halt_state),
        })

    return {
        "sessionId": fixture_path.stem,
        "generatedFrom": fixture_path.name,
        "tradingDate": "2026-09-01",
        "timezone": "America/New_York",
        "disclaimer": ("Synthetic symbols and clean-room approximations. Scanner events are "
                       "research candidates, never entry signals or orders."),
        "rowColumns": ROW_COLUMNS,
        "listMeta": LIST_META,
        "alertMeta": ALERT_META,
        "pillarThresholds": {
            "priceMin": PRICE_MIN, "priceMax": PRICE_MAX, "gainMinPct": GAIN_MIN_PCT,
            "rvolMin": RVOL_MIN, "floatMaxShares": FLOAT_MAX_SHARES,
            "evidence": "confirmed_course",
        },
        "definitionVersions": {s.scanner_id: s.definition_version for s in engine.scanners},
        "symbols": symbols,
        "bars": bars_by_symbol,
        "frames": frames,
        "plans": plans,
    }


class _Collector:
    """Notification channel that captures delivered events for the session."""

    name = "session_collector"

    def __init__(self, sink: list) -> None:
        self.sink = sink

    def deliver(self, event, consolidated=None) -> None:
        self.sink.append((event, consolidated))
