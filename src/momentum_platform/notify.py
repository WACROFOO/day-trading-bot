"""Notification engine (spec section 14).

Pipeline: validation -> idempotency -> cooldown/re-arm -> consolidation ->
channel fan-out -> audit. Channel failure never blocks scanning: fan-out
exceptions are caught, recorded and reported, not raised.

Severity is configuration about delivery urgency, never a claim about trade
quality. A scanner event is a research candidate, not an entry signal.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .models import ScannerEvent


class Channel:
    """One delivery target. deliver() raises on failure; the router catches."""

    name = "channel"

    def deliver(self, event: ScannerEvent, consolidated: Optional[dict] = None) -> None:
        raise NotImplementedError


class ConsoleChannel(Channel):
    name = "console"

    def __init__(self, stream=None) -> None:
        self.stream = stream or sys.stdout

    def deliver(self, event: ScannerEvent, consolidated: Optional[dict] = None) -> None:
        v = event.values
        news = event.news or {}
        flame = {"red": "🔥", "orange": "🟠", "yellow": "🟡"}.get(news.get("flame"), "")
        also = ""
        if consolidated and consolidated.get("also_triggered"):
            also = " (+" + ",".join(consolidated["also_triggered"]) + ")"
        line = (
            f"[{event.scan_ts.strftime('%H:%M:%S')}] {event.severity.upper():8s} "
            f"{event.symbol:6s} {event.scanner}"
            + (f"/{event.branch}" if event.branch else "")
            + also
            + f"  last={v.get('last')} chg={v.get('change_pct')}% "
            f"rvol={v.get('rvol_daily')} float={v.get('float_m')}M {flame}"
        )
        print(line, file=self.stream)


class JsonlChannel(Channel):
    """Appends every delivered event as one JSON line — the durable alert
    timeline and the audit trail for replay comparison."""

    name = "jsonl"

    def __init__(self, path: str) -> None:
        self.path = path

    def deliver(self, event: ScannerEvent, consolidated: Optional[dict] = None) -> None:
        record = event.to_dict()
        if consolidated:
            record["consolidated"] = consolidated
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")


class WebhookChannel(Channel):
    """POSTs a Slack-compatible payload to a webhook URL. The URL is a secret:
    pass it from the environment, never commit it."""

    name = "webhook"

    def __init__(self, url: str, timeout: float = 5.0) -> None:
        self.url = url
        self.timeout = timeout

    def deliver(self, event: ScannerEvent, consolidated: Optional[dict] = None) -> None:
        v = event.values
        news = event.news or {}
        text = (
            f"*{event.symbol}* {event.scanner}"
            + (f"/{event.branch}" if event.branch else "")
            + f" [{event.severity}] last={v.get('last')} chg={v.get('change_pct')}%"
            + f" rvol={v.get('rvol_daily')} float={v.get('float_m')}M"
            + (f" news({news.get('flame')}, {news.get('age_minutes')}m)" if news.get("flame") else "")
            + " — research candidate, not an entry signal"
        )
        payload = json.dumps({"text": text}).encode()
        req = urllib.request.Request(
            self.url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"webhook returned {resp.status}")


class CallbackChannel(Channel):
    """Adapter for in-process consumers (dashboards, tests)."""

    name = "callback"

    def __init__(self, fn: Callable[[ScannerEvent, Optional[dict]], None]) -> None:
        self.fn = fn

    def deliver(self, event: ScannerEvent, consolidated: Optional[dict] = None) -> None:
        self.fn(event, consolidated)


@dataclass
class RouterConfig:
    cooldown_seconds: Dict[str, float] = field(
        default_factory=lambda: {
            "hod_momentum": 180.0,
            "running_up": 120.0,
            "running_down": 120.0,
            "squeeze_5_in_5": 120.0,
            "squeeze_10_in_10": 120.0,
            "breakout_52w": 600.0,
            "five_pillars_alert": 60.0,
        }
    )
    default_cooldown_seconds: float = 60.0
    # A new price tier overrides the cooldown (spec 14.5): alert again if price
    # advanced at least this fraction above the last alerted price.
    price_tier_advance_pct: float = 2.0
    consolidation_window_seconds: float = 3.0
    min_severity: str = "low"          # low|medium|high|critical
    idempotency_ttl_seconds: float = 24 * 3600.0

    def cooldown_for(self, scanner: str) -> float:
        return self.cooldown_seconds.get(scanner, self.default_cooldown_seconds)


_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class Delivery:
    event: ScannerEvent
    channel: str
    status: str          # delivered | failed | suppressed
    detail: str = ""


class NotificationRouter:
    def __init__(self, config: Optional[RouterConfig] = None, channels: Optional[List[Channel]] = None) -> None:
        self.config = config or RouterConfig()
        self.channels = channels or [ConsoleChannel()]
        self._seen_keys: Dict[str, datetime] = {}
        self._last_alert: Dict[str, tuple] = {}     # (symbol, scanner, branch) -> (ts, price)
        self._recent_symbol_alert: Dict[str, tuple] = {}  # symbol -> (ts, group dict)
        self.deliveries: List[Delivery] = []
        self.suppressed_count = 0

    def _suppress(self, event: ScannerEvent, why: str) -> None:
        self.suppressed_count += 1
        self.deliveries.append(Delivery(event, "-", "suppressed", why))

    def handle(self, event: ScannerEvent) -> bool:
        """Returns True when the event was fanned out to channels."""
        now = event.scan_ts

        if _SEVERITY_ORDER.get(event.severity, 0) < _SEVERITY_ORDER.get(self.config.min_severity, 0):
            self._suppress(event, "below_min_severity")
            return False

        # Idempotency: identical logical event never delivers twice.
        cutoff = now - timedelta(seconds=self.config.idempotency_ttl_seconds)
        self._seen_keys = {k: t for k, t in self._seen_keys.items() if t >= cutoff}
        if event.idempotency_key in self._seen_keys:
            self._suppress(event, "duplicate_idempotency_key")
            return False
        self._seen_keys[event.idempotency_key] = now

        # Cooldown per symbol/scanner/branch, overridden by a new price tier.
        cd_key = f"{event.symbol}|{event.scanner}|{event.branch or '-'}"
        last = self._last_alert.get(cd_key)
        if last is not None:
            last_ts, last_price = last
            elapsed = (now - last_ts).total_seconds()
            price = event.values.get("last")
            tier_advanced = (
                price is not None
                and last_price is not None
                and last_price > 0
                and 100.0 * (price / last_price - 1.0) >= self.config.price_tier_advance_pct
            )
            if elapsed < self.config.cooldown_for(event.scanner) and not tier_advanced:
                self._suppress(event, "cooldown")
                return False
        self._last_alert[cd_key] = (now, event.values.get("last"))

        # Consolidation: same-symbol alerts inside the window join the first
        # (primary) alert's group rather than firing separately. The group dict
        # is handed to the channels by reference and keeps filling, so a
        # consumer sees "+N more" without losing any raw event.
        recent = self._recent_symbol_alert.get(event.symbol)
        if recent is not None:
            first_ts, group = recent
            if (now - first_ts).total_seconds() <= self.config.consolidation_window_seconds:
                if event.scanner != group["primary"] and event.scanner not in group["also_triggered"]:
                    group["also_triggered"].append(event.scanner)
                group["also_event_ids"].append(event.event_id)
                group["latest_ts"] = now.isoformat()
                group["count"] += 1
                self._suppress(event, f"consolidated_under_{group['primary']}")
                return False
        consolidated = {
            "symbol": event.symbol,
            "primary": event.scanner,
            "also_triggered": [],
            "also_event_ids": [],
            "first_ts": now.isoformat(),
            "latest_ts": now.isoformat(),
            "count": 1,
        }
        self._recent_symbol_alert[event.symbol] = (now, consolidated)

        for channel in self.channels:
            try:
                channel.deliver(event, consolidated)
                self.deliveries.append(Delivery(event, channel.name, "delivered"))
            except Exception as exc:  # channel failure must not block scanning
                self.deliveries.append(Delivery(event, channel.name, "failed", str(exc)))
        return True
