"""Dashboard acceptance tests.

Data-layer tests run everywhere. UI tests drive the real page in Chromium and
are skipped when Playwright or a browser binary is unavailable, so the suite
stays green in a bare environment.

Each test name maps to a criterion in dashboard-scanner-chart-knowledge.md §25.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures" / "market_replay" / "workstation_open_2026-09-01.jsonl"
TIER1_LISTS = ["five_pillars_list", "top_gappers", "top_gainers",
               "top_relative_volume", "top_volume_5m"]


@pytest.fixture(scope="module")
def session():
    return build_session(FIXTURE)


def rows(session, frame, list_id):
    cols = session["rowColumns"]
    return [dict(zip(cols, r)) for r in frame["lists"].get(list_id, [])]


# ── data layer ────────────────────────────────────────────────────────────

def test_session_is_deterministic():
    a, b = build_session(FIXTURE), build_session(FIXTURE)
    def strip(s):
        out = []
        for frame in s["frames"]:
            cleaned = []
            for alert in frame["alerts"]:
                a = {k: v for k, v in alert.items() if k != "eventId"}
                if a.get("group"):
                    a["group"] = {k: v for k, v in a["group"].items() if k != "also_event_ids"}
                cleaned.append(a)
            out.append(cleaned)
        return out
    assert strip(a) == strip(b)
    assert a["bars"] == b["bars"] and a["frames"][0]["lists"] == b["frames"][0]["lists"]


def test_session_contains_tier1_lists(session):
    late = session["frames"][-1]
    for list_id in TIER1_LISTS:
        assert list_id in late["lists"], list_id


def test_frames_carry_feed_health(session):
    for frame in session["frames"]:
        assert frame["feed"]["status"] == "replay"
        assert frame["session"] in {"premarket", "regular", "after_hours", "closed"}


def test_gappers_frozen_after_open(session):
    frames = session["frames"]
    open_idx = next(i for i, f in enumerate(frames) if f["session"] == "regular")
    at_open = frames[open_idx]["lists"]["top_gappers"]
    later = frames[-1]["lists"]["top_gappers"]
    assert at_open == later, "Top Gappers must freeze its 09:30 snapshot"
    # ... while the continuously-updating list does keep moving.
    assert frames[open_idx]["lists"]["top_gainers"] != frames[-1]["lists"]["top_gainers"]


def test_minute_bars_are_aggregates_of_ten_second_bars(session):
    """The fixture is generated at 10-second resolution and the 1-minute series
    the scanners consume is built from it, so the timeframes cannot disagree."""
    sub = session["bars10s"]["ABCD"]
    minutes = session["bars"]["ABCD"]
    assert len(sub) == len(minutes) * 6
    for i, minute in enumerate(minutes):
        chunk = sub[i * 6:(i + 1) * 6]
        assert minute[0] == chunk[0][0]                      # same open time
        assert minute[1] == chunk[0][1]                      # open
        assert minute[2] == max(c[2] for c in chunk)         # high
        assert minute[3] == min(c[3] for c in chunk)         # low
        assert minute[4] == chunk[-1][4]                     # close
        assert minute[5] == sum(c[5] for c in chunk)         # volume


def test_pillar_reasons_are_itemised(session):
    alerts = [a for f in session["frames"] for a in f["alerts"]
              if a["scannerId"] == "five_pillars_alert"]
    assert alerts, "the fixture must produce Five Pillars alerts"
    filters = {r["filter"] for r in alerts[0]["reasons"]}
    assert filters == {"price_in_band", "gain_pct", "rvol_daily", "float_shares", "news_catalyst"}
    assert all(r["evidence"] == "confirmed" for r in alerts[0]["reasons"])


def test_news_is_not_a_gate(session):
    """BRXO carries no headline yet still qualifies technically (Confirmed
    platform: the Five Pillars scanner does not enforce news)."""
    assert session["symbols"]["BRXO"]["news"] == []
    qualified = any("BRXO" in [r[0] for r in f["lists"].get("five_pillars_list", [])]
                    for f in session["frames"])
    assert qualified


def test_float_proxy_is_never_silently_substituted(session):
    ephz = session["symbols"]["EPHZ"]
    assert ephz["floatQuality"] == "shares_outstanding_proxy"
    # A proxy above the cap must keep EPHZ out of the Five Pillars list.
    assert all("EPHZ" not in [r[0] for r in f["lists"].get("five_pillars_list", [])]
               for f in session["frames"])


def test_flame_matches_age_boundaries(session):
    from momentum_platform.models import flame_color
    assert (flame_color(0), flame_color(120), flame_color(121)) == ("red", "red", "orange")
    assert (flame_color(720), flame_color(721)) == ("orange", "yellow")
    assert (flame_color(1440), flame_color(1441)) == ("yellow", None)


def test_news_first_observed_after_publication(session):
    """The flame may legitimately appear after the alert; both stamps are kept
    so latency stays measurable instead of being hidden."""
    for meta in session["symbols"].values():
        for item in meta["news"]:
            assert item["firstObservedAt"] > item["publishedAt"]


def test_list_and_alert_tiles_distinct(session):
    assert set(session["listMeta"]) == set(TIER1_LISTS)
    assert "hod_momentum" in session["alertMeta"]
    assert not (set(session["listMeta"]) & set(session["alertMeta"]))


def test_branch_is_label_not_filter(session):
    branches = {a["branch"] for f in session["frames"] for a in f["alerts"]
                if a["scannerId"] == "hod_momentum"}
    assert branches, "HOD momentum should label its branches"
    for branch in branches:
        assert branch.startswith(("low_float", "medium_float"))


def test_replay_consolidates_same_symbol(session):
    grouped = [a for f in session["frames"] for a in f["alerts"]
               if a.get("group") and a["group"]["count"] > 1]
    assert grouped, "the fixture must exercise consolidation"
    for a in grouped:
        assert a["group"]["also_triggered"]
        assert len(a["group"]["also_event_ids"]) == a["group"]["count"] - 1


def test_no_duplicate_idempotency_keys(session):
    keys = [a["idempotencyKey"] for f in session["frames"] for a in f["alerts"]
            if "idempotencyKey" in a]
    assert len(keys) == len(set(keys))


def test_halt_transitions_are_critical_and_official(session):
    halts = [a for f in session["frames"] for a in f["alerts"] if a["scannerId"] == "halt"]
    assert [h["branch"] for h in halts] == ["halt.started", "halt.resumed"]
    assert all(h["severity"] == "critical" for h in halts)
    assert all(h["reasons"][0]["field"] == "official_status" for h in halts)


def test_plan_bands_do_not_repaint(session):
    plans = session["plans"]
    assert len(plans) >= 2, "the session should arm several setups"
    assert any(p["symbol"] == "ABCD" for p in plans), "the leader should arm one"
    for plan in plans:
        assert plan["stop"] < plan["entry"] < plan["target"]
        assert plan["target"] == pytest.approx(
            plan["entry"] + plan["rewardMultiple"] * plan["riskShare"], abs=0.011)
        assert 1 <= plan["pullbackCandles"] <= 4
    # Every plan is a distinct immutable id — a later setup never mutates an
    # earlier one.
    assert len({p["planId"] for p in session["plans"]}) == len(session["plans"])


def test_every_threshold_carries_evidence_label(session):
    for frame in session["frames"]:
        for alert in frame["alerts"]:
            for reason in alert["reasons"]:
                assert reason["evidence"] in {"confirmed", "approximation"}
    assert session["pillarThresholds"]["evidence"] == "confirmed_course"


def test_definition_versions_present(session):
    for frame in session["frames"]:
        for alert in frame["alerts"]:
            assert "@" in alert["definitionVersion"]


def test_live_session_shares_the_replay_shape(monkeypatch):
    """The live adapter emits the same normalized records, so the scanner
    engine and the dashboard behave identically on real data. The network is
    never touched here — only the record contract is exercised."""
    from momentum_platform.dashboard.session_builder import build_session_from_records
    records = [
        {"type": "reference", "symbol": "ZZZZ", "prev_close": 4.0,
         "avg_daily_volume": 100_000, "high_52w": 9.0, "float_shares": 8_000_000,
         "float_quality": "verified", "daily_bars": []},
        {"type": "news", "symbol": "ZZZZ", "provider_id": "n1",
         "published_at": "2026-09-01T13:00:00Z", "first_observed_at": "2026-09-01T13:02:00Z",
         "headline": "ZZZZ wins contract", "category": "contract"},
        {"type": "bar", "symbol": "ZZZZ", "ts": "2026-09-01T13:31:00Z",
         "open": 5.0, "high": 5.3, "low": 4.95, "close": 5.25, "volume": 400_000},
        {"type": "bar", "symbol": "ZZZZ", "ts": "2026-09-01T13:32:00Z",
         "open": 5.25, "high": 5.6, "low": 5.2, "close": 5.55, "volume": 500_000},
    ]
    live = build_session_from_records(records, "live-zzzz", "yfinance (delayed ~15m)",
                                      data_status="delayed")
    assert live["dataStatus"] == "delayed"
    assert live["tradingDate"] == "2026-09-01"
    assert set(live["rowColumns"]) == set(build_session(FIXTURE)["rowColumns"])
    assert live["symbols"]["ZZZZ"]["floatQuality"] == "verified"
    assert len(live["frames"]) == 2 and live["bars"]["ZZZZ"]


def test_session_json_has_no_secrets(session):
    blob = json.dumps(session).lower()
    for needle in ("api_key", "apikey", "authorization", "bearer ", "webhook",
                   "secret", "token", "password"):
        assert needle not in blob


# ── UI layer ──────────────────────────────────────────────────────────────

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    os.environ.get("CHROME_PATH", ""),
]


def _chrome() -> str | None:
    for path in CHROME_CANDIDATES:
        if path and Path(path).is_file():
            return path
    return None


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    pytest.importorskip("playwright.sync_api", reason="playwright not installed")
    from playwright.sync_api import sync_playwright

    chrome = _chrome()
    if not chrome:
        pytest.skip("no chromium binary available")

    out = tmp_path_factory.mktemp("artifact") / "workstation.html"
    subprocess.run([sys.executable, "scripts/build_dashboard_artifact.py", str(out)],
                   cwd=ROOT, check=True, capture_output=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1600, "height": 950})
        errors: list = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(out.as_uri())
        pg.wait_for_timeout(300)
        pg.errors = errors
        yield pg
        browser.close()


def _seek(page, frame: int):
    page.eval_on_selector("#scrub", f"e => {{ e.value = {frame}; e.dispatchEvent(new Event('input')) }}")
    page.wait_for_timeout(250)


def test_ui_opens_three_scanner_cards(page):
    """Three scanner cards in funnel order: candidates, acceleration, breakout."""
    _seek(page, 118)
    for card in ("scan-pillars", "scan-running", "scan-hod"):
        assert page.locator(f"[data-card={card}]").count() == 1


def test_ui_tiles_report_state(page):
    states = page.eval_on_selector_all(".tile-state", "els => els.map(e => e.textContent)")
    assert states and all(s in {"REPLAY", "FROZEN", "STALE", "OFFLINE", "LIVE"} for s in states)


def test_ui_alert_rows_show_session(page):
    _seek(page, 150)
    tags = page.eval_on_selector_all("[data-card=scan-hod] .pill.ses",
                                     "els => els.map(e => e.textContent)")
    assert tags and set(tags) <= {"PM", "RTH", "AH"}


def test_ui_row_click_links_everything(page):
    _seek(page, 118)
    page.locator("[data-card=scan-pillars] .trow").first.click()
    page.wait_for_timeout(250)
    symbol = page.locator("#symTicker").inner_text()
    assert symbol and symbol != "—"
    assert f"symbol={symbol}" in page.url
    assert page.locator("[data-card=scan-pillars] .trow.sel").count() >= 1
    assert page.locator("#quoteCard").inner_text().strip()
    assert page.locator("#verdictCard").inner_text().strip()


def test_ui_chart_stack_is_1m_large_over_5m_and_10s(page):
    """The requested stack: one large 1-minute chart, with 5-minute and
    10-second side by side beneath it."""
    _seek(page, 124)
    boxes = {c: page.locator(f"[data-card={c}] .chart-host").bounding_box()
             for c in ("chart-1m", "chart-5m", "chart-10s")}
    one, five, ten = boxes["chart-1m"], boxes["chart-5m"], boxes["chart-10s"]
    assert one["height"] > five["height"]                 # 1m is the big one
    assert one["width"] > five["width"] * 1.5             # and spans the pair
    assert abs(five["y"] - ten["y"]) < 4                  # 5m and 10s share a row
    assert ten["x"] > five["x"] + five["width"] - 4       # side by side
    assert five["y"] > one["y"] + one["height"] - 4       # below the 1m
    for cid in boxes:
        inner = page.locator(f"[data-card={cid}] .chart-host canvas").first.bounding_box()
        assert inner and abs(inner["width"] - boxes[cid]["width"]) < 4


def test_ui_ten_second_chart_has_finer_bars_than_one_minute(page):
    """10-second bars are the fixture's source of truth; the 1-minute series is
    their aggregate, so the micro chart must carry strictly more bars."""
    counts = page.evaluate("""() => {
      const s = window.__SESSION__, sym = 'ABCD';
      return {sub: (s.bars10s[sym] || []).length, min: s.bars[sym].length};
    }""")
    assert counts["sub"] == counts["min"] * 6


def test_ui_reports_its_chart_engine(page):
    engine = page.locator("#chartEngine").inner_text()
    assert engine in {"TRADINGVIEW", "CANVAS"}
    sub = page.locator("#chartEngineSub").inner_text()
    assert ("lightweight-charts" in sub) if engine == "TRADINGVIEW" else ("fallback" in sub)


def test_ui_fits_one_viewport(page):
    page.set_viewport_size({"width": 1680, "height": 1000})
    page.wait_for_timeout(400)
    metrics = page.evaluate("() => ({sh: document.body.scrollHeight, ih: window.innerHeight})")
    assert metrics["sh"] <= metrics["ih"] + 2


def test_ui_quote_card_sits_under_the_scanners(page):
    quote = page.locator("[data-card=quote]").bounding_box()
    scan = page.locator("[data-card=scan-pillars]").bounding_box()
    l2 = page.locator("[data-card=level2]").bounding_box()
    assert quote["y"] > scan["y"]
    assert abs(quote["x"] - scan["x"]) < 4
    assert l2["x"] > quote["x"] + quote["width"]


def test_ui_flames_on_every_scanner_row(page):
    _seek(page, 130)
    assert page.locator("[data-card=scan-pillars] .trow .flame").count() >= 1
    assert page.locator("[data-card=scan-hod] .trow .flame").count() >= 1
    title = page.locator("[data-card=scan-pillars] .trow .flame").first.get_attribute("title")
    assert "recency" in title or "no qualifying headline" in title


def test_ui_gutters_resize_panes_and_persist(page):
    """Cards are resizable, not just swappable: a gutter trades space between
    the two panes it sits between, and the sizes are remembered."""
    before = page.locator("[data-card=level2]").bounding_box()
    gutter = page.locator('[data-between="R1,R2"]')
    box = gutter.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2 + 110, steps=8)
    page.mouse.up()
    page.wait_for_timeout(300)
    after = page.locator("[data-card=level2]").bounding_box()
    assert after["height"] > before["height"] + 60
    saved = page.evaluate("JSON.parse(localStorage.getItem('momentum-workstation.layout.v2'))")
    assert saved["sizes"]["slots"]["R1"] > saved["sizes"]["slots"]["R2"]
    # the page must still fit after a resize
    metrics = page.evaluate("() => ({sh: document.body.scrollHeight, ih: window.innerHeight})")
    assert metrics["sh"] <= metrics["ih"] + 2
    page.locator("#btnLayout").click()
    page.wait_for_timeout(300)


def test_ui_columns_resize(page):
    """The whole right column can be widened for the book."""
    before = page.locator("[data-col=right]").bounding_box()
    gutter = page.locator('.gutter-h[data-cols=right]')
    box = gutter.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] - 80, box["y"] + box["height"] / 2, steps=8)
    page.mouse.up()
    page.wait_for_timeout(300)
    after = page.locator("[data-col=right]").bounding_box()
    assert after["width"] > before["width"] + 50
    page.locator("#btnLayout").click()
    page.wait_for_timeout(300)


def test_ui_level2_owns_more_than_half_the_right_column(page):
    """Level 2 and the book get the room by default, per the desk brief."""
    page.locator("#btnLayout").click()
    page.wait_for_timeout(300)
    column = page.locator("[data-col=right]").bounding_box()
    book = page.locator("[data-card=level2]").bounding_box()
    assert book["height"] / column["height"] > 0.5


def test_ui_bottom_right_card_is_off_the_desk(page):
    """The daily chart was removed from the desk but stays available in the
    tray rather than being deleted."""
    page.locator("#btnLayout").click()
    page.wait_for_timeout(250)
    assert page.locator(".slot [data-card=chart-daily]").count() == 0
    page.locator("#btnTray").click()
    page.wait_for_timeout(250)
    assert page.locator("[data-card=chart-daily]").count() == 1   # the card, not a tray row
    items = page.eval_on_selector_all(".tray-item", "els => els.map(e => e.dataset.trayCard)")
    assert items == ["chart-daily"]
    page.locator("#btnTray").click()
    page.wait_for_timeout(150)


def test_ui_catalyst_card_grades_the_news(page):
    """The catalyst reads at a glance: flame band, hard/soft/dilutive grade,
    age against the 24-hour window, and what it means for the funnel."""
    _seek(page, 124)
    rows = page.locator("[data-card=scan-pillars] .trow")
    for i in range(rows.count()):
        if rows.nth(i).inner_text().startswith("ABCD"):
            rows.nth(i).click()
            break
    page.wait_for_timeout(300)
    chip = page.locator(".flame-chip").inner_text()
    assert chip.startswith("RED") and "0–2h" in chip
    assert page.locator(".cat-quality").inner_text() == "Hard catalyst"
    assert page.locator(".age-bar i").count() == 1
    read = page.locator(".cat-read").inner_text()
    assert "4/4 candidate" in read and "chart still decides" in read


def test_ui_catalyst_flags_dilution(page):
    """An offering headline is graded dilutive however fresh the flame is."""
    _seek(page, 100)
    page.evaluate("""() => {
      const rows = document.querySelectorAll('[data-card=scan-hod] .trow, [data-card=scan-running] .trow');
      for (const r of rows) if (r.textContent.startsWith('CYQN')) { r.click(); return; }
      window.__selectFallback = true;
    }""")
    page.wait_for_timeout(300)
    if page.locator("#symTicker").inner_text() != "CYQN":
        page.goto(page.url.split("?")[0] + "?symbol=CYQN")
        page.wait_for_timeout(600)
        _seek(page, 100)
    assert page.locator(".cat-quality").inner_text() == "Dilutive"
    assert "Dilution risk" in page.locator(".cat-read").inner_text()


def test_ui_cards_swap_by_drag_and_persist(page):
    """Any card can be dragged onto any other to trade places, and the desk
    comes back the way it was left."""
    before = page.eval_on_selector("[data-card=chart-10s]", "e => e.parentElement.dataset.slot")
    target = page.eval_on_selector("[data-card=level2]", "e => e.parentElement.dataset.slot")
    page.evaluate("""() => {
      const dt = new DataTransfer();
      const src = document.querySelector('[data-card=chart-10s] .card-head');
      const dst = document.querySelector('[data-card=level2]');
      src.dispatchEvent(new DragEvent('dragstart', {dataTransfer: dt, bubbles: true}));
      dst.dispatchEvent(new DragEvent('dragover', {dataTransfer: dt, bubbles: true, cancelable: true}));
      dst.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
    }""")
    page.wait_for_timeout(300)
    assert page.eval_on_selector("[data-card=chart-10s]", "e => e.parentElement.dataset.slot") == target
    assert page.eval_on_selector("[data-card=level2]", "e => e.parentElement.dataset.slot") == before
    saved = page.evaluate("JSON.parse(localStorage.getItem('momentum-workstation.layout.v2'))")
    assert saved["layout"][target] == "chart-10s"
    page.locator("#btnLayout").click()
    page.wait_for_timeout(300)
    assert page.eval_on_selector("[data-card=chart-10s]", "e => e.parentElement.dataset.slot") == before


def test_ui_any_card_expands_and_restores(page):
    _seek(page, 124)
    for card in ("chart-1m", "level2", "scan-pillars"):
        page.locator(f"[data-card={card}] .expand").click()
        page.wait_for_timeout(250)
        box = page.locator(f"[data-card={card}]").bounding_box()
        assert box["width"] > 1400 and box["height"] > 700, card
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        assert page.locator(".card.expanded").count() == 0


def test_ui_freeze_pins_row_order(page):
    _seek(page, 110)
    sel = "[data-card=scan-pillars] .trow b"
    before = page.eval_on_selector_all(sel, "els => els.map(e => e.textContent)")
    page.locator("[data-card=scan-pillars] .card-head .icon-btn:not(.expand)").click()
    page.wait_for_timeout(150)
    _seek(page, 148)
    after = page.eval_on_selector_all(sel, "els => els.map(e => e.textContent)")
    assert before == after
    assert page.locator("[data-card=scan-pillars] .tile-state").inner_text() == "FROZEN"
    page.locator("[data-card=scan-pillars] .card-head .icon-btn:not(.expand)").click()
    page.wait_for_timeout(150)


def test_ui_reasons_drawer_shows_pillar_arithmetic(page):
    _seek(page, 125)
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    page.locator("[data-card=scan-pillars] .trow").first.click()
    page.wait_for_timeout(250)
    drawer = page.locator(".reasons")
    assert drawer.count() == 1
    text = drawer.inner_text()
    for token in ("price $2", "gain", "RVOL", "float", "confirmed course"):
        assert token in text


def test_ui_level2_ladder_renders(page):
    _seek(page, 125)
    page.locator("[data-card=scan-pillars] .trow").first.click()
    page.wait_for_timeout(250)
    assert page.locator(".ladder .lp").count() == 16
    assert page.locator(".tape .print").count() == 10
    bids = page.eval_on_selector_all(".ladder .lp.bid", "els => els.map(e => parseFloat(e.textContent))")
    asks = page.eval_on_selector_all(".ladder .lp.ask", "els => els.map(e => parseFloat(e.textContent))")
    assert bids == sorted(bids, reverse=True)
    assert asks == sorted(asks)
    assert bids[0] < asks[0]
    body = page.locator("#l2Card").inner_text().lower()
    assert "simulated" in body and "not licensed market data" in body


def test_ui_verdict_mirrors_pine_and_decides(page):
    _seek(page, 125)
    page.locator("[data-card=scan-pillars] .trow").first.click()
    page.wait_for_timeout(250)
    labels = page.eval_on_selector_all(".vlab", "els => els.map(e => e.textContent)")
    assert labels == ["Price", "Gain vs close", "Daily RVOL", "Float / supply", "News",
                      "Technical score", "5m RVOL", "HOD / Running", "Entry", "Stop", "Target"]
    assert page.locator(".verdict-banner b").inner_text() in {"GO", "WAIT", "PASS"}
    assert page.locator(".why-row").count() >= 1


def test_ui_sizing_needs_the_operators_own_risk(page):
    _seek(page, 125)
    page.locator("[data-card=scan-pillars] .trow").first.click()
    page.wait_for_timeout(250)
    assert "will not assume one for you" in page.locator(".sizing").inner_text()
    page.locator("#riskInput").fill("25")
    page.wait_for_timeout(250)
    sizing = page.locator(".sizing").inner_text()
    assert "Shares" in sizing and "Planned loss" in sizing


def test_ui_alert_click_seeks_charts(page):
    _seek(page, 150)
    first_alert_time = page.locator(".tl-row .tl-time").first.inner_text()
    page.locator(".tl-row").first.click()
    page.wait_for_timeout(250)
    assert page.locator("#clockET").inner_text().startswith(first_alert_time)
    assert page.locator(".tl-detail").count() == 1


def test_ui_no_javascript_errors(page):
    assert page.errors == []
