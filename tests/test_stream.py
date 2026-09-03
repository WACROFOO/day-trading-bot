"""SSE transport: ids, framing, replay, resync, heartbeat, and the browser
module's dispatch (run under node when it is available)."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.dashboard import stream as st  # noqa: E402
from momentum_platform.dashboard.stream import (  # noqa: E402
    EventHub, UpdatePublisher, format_sse, parse_last_event_id, serve_sse)
from momentum_platform.datasources.ibkr_stream import Bar5s, BarStore  # noqa: E402
from momentum_platform.models import Bar, DataStatus  # noqa: E402
from momentum_platform.state import MarketUpdate  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 3, 14, 0, tzinfo=UTC)
LIVE_JS = ROOT / "src" / "momentum_platform" / "dashboard" / "web" / "live.js"


def test_ids_are_monotonic_and_frames_are_exact():
    hub = EventHub()
    a = hub.publish("quote", {"symbol": "AAA", "price": 4.2})
    b = hub.publish("health", {"state": "LIVE"})
    assert (a.id, b.id) == (1, 2) and hub.last_id == 2
    assert format_sse(a) == b'id: 1\nevent: quote\ndata: {"symbol":"AAA","price":4.2}\n\n'


def test_unknown_event_type_is_refused():
    with pytest.raises(ValueError):
        EventHub().publish("orders", {})


def test_since_replays_only_what_was_missed():
    hub = EventHub()
    for i in range(5):
        hub.publish("quote", {"i": i})
    assert [e.data["i"] for e in hub.since(3)] == [3, 4]
    assert hub.since(None) == [] and hub.since(5) == []


def test_falling_off_the_buffer_yields_a_resync_not_a_gap():
    hub = EventHub(capacity=3)
    for i in range(10):
        hub.publish("quote", {"i": i})
    got = hub.since(2)
    assert len(got) == 1 and got[0].type == "resync" and got[0].data["lastEventId"] == 2
    assert [e.data["i"] for e in hub.since(8)] == [8, 9], "an id still inside the buffer replays normally"
    assert [e.data["i"] for e in hub.since(7)] == [7, 8, 9], "the id just before the oldest kept event replays too"
    assert hub.since(6)[0].type == "resync"


def test_subscribe_with_last_id_preloads_the_backlog_and_live_events_follow():
    hub = EventHub()
    hub.publish("quote", {"i": 0})
    hub.publish("quote", {"i": 1})
    q = hub.subscribe(last_event_id=1)
    hub.publish("bar1m", {"i": 2})
    assert [q.get_nowait().data["i"] for _ in range(2)] == [1, 2]
    hub.unsubscribe(q)
    assert hub.subscribers == 0


def test_serve_sse_writes_frames_then_stops():
    hub = EventHub()
    out = io.BytesIO()
    hub.publish("health", {"state": "LIVE"})
    threading.Timer(0.05, lambda: hub.publish("quote", {"symbol": "AAA"})).start()
    n = serve_sse(hub, out, last_event_id=0, heartbeat_seconds=5, max_events=2)
    text = out.getvalue().decode()
    assert n == 2 and text.count("\n\n") == 2
    assert "event: health" in text and "event: quote" in text and "id: 2" in text


def test_serve_sse_heartbeats_when_quiet():
    hub = EventHub()
    out = io.BytesIO()
    beats = []

    def stop():
        beats.append(1)
        return len(beats) > 2
    serve_sse(hub, out, heartbeat_seconds=0.01, stop=stop)
    assert out.getvalue().startswith(b": ping\n\n")


def test_serve_sse_survives_a_broken_pipe():
    hub = EventHub()

    class Broken:
        def write(self, _):
            raise BrokenPipeError
    hub.publish("quote", {})
    assert serve_sse(hub, Broken(), last_event_id=0, max_events=5) == 0
    assert hub.subscribers == 0


def test_parse_last_event_id():
    assert parse_last_event_id("17") == 17
    assert parse_last_event_id("") is None and parse_last_event_id(None) is None
    assert parse_last_event_id("abc") is None


def test_update_publisher_maps_quotes_and_bars():
    hub = EventHub()
    pub = UpdatePublisher(hub)
    pub(MarketUpdate("AAA", T0, price=4.2, size=100, bid=4.19, ask=4.21, data_status=DataStatus.LIVE))
    bar = Bar("AAA", "1m", T0, 4, 4.3, 3.9, 4.2, 500)
    pub(MarketUpdate("AAA", T0, price=4.2, size=500, bar=bar, data_status=DataStatus.LIVE))
    evs = list(hub.since(0))
    assert [e.type for e in evs] == ["quote", "bar1m"]
    assert evs[0].data["status"] == "live" and evs[0].data["bid"] == 4.19
    assert evs[1].data["t"] == int(T0.timestamp()) and evs[1].data["tf"] == "1m"


def test_update_publisher_drains_closed_ten_second_candles_once():
    hub, store = EventHub(), BarStore()
    pub = UpdatePublisher(hub)
    store.append(Bar5s("AAA", T0, 1, 2, 0.5, 1.5, 10))
    assert pub.publish_closed_10s(store, ["AAA"]) == 0
    store.append(Bar5s("AAA", T0.replace(second=5), 1, 2, 0.5, 1.5, 10))
    assert pub.publish_closed_10s(store, ["AAA"]) == 1
    assert pub.publish_closed_10s(store, ["AAA"]) == 0
    assert hub.since(0)[0].type == "bar10s" and hub.since(0)[0].data["volume"] == 20


NODE_CHECK = r"""
const DeskLive = require(process.argv[1]);
const seen = [];
DeskLive.on("bar10s", (b, raw) => seen.push(["bar10s", b.symbol, raw.lastEventId]))
        .on("health", h => seen.push(["health", h.state]))
        .on("status", s => seen.push(["status", s.state]));
DeskLive._dispatch("bar10s", { data: JSON.stringify({symbol: "AAA"}), lastEventId: "41" });
DeskLive._dispatch("health", { data: JSON.stringify({state: "STALE"}), lastEventId: "42" });
DeskLive._dispatch("bar10s", { data: "{not json", lastEventId: "43" });
DeskLive.connect("/api/v1/stream");
console.log(JSON.stringify({seen, last: DeskLive.lastEventId, state: DeskLive.state,
                            counts: DeskLive.counts, types: DeskLive.types}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_live_js_dispatches_typed_handlers_and_tracks_last_id():
    res = subprocess.run(["node", "-e", NODE_CHECK, str(LIVE_JS)], capture_output=True, text=True, timeout=20)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout.strip().splitlines()[-1])
    assert out["seen"][:2] == [["bar10s", "AAA", "41"], ["health", "STALE"]]
    assert out["last"] == "42", "a bad frame must not advance the resume id"
    assert out["state"] == "unsupported", "node has no EventSource; the module says so instead of crashing"
    assert out["counts"]["bar10s"] == 1 and out["counts"]["health"] == 1
    assert set(st.EVENT_TYPES) == set(out["types"]), "server and browser agree on the event vocabulary"
