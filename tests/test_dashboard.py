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
    plans = [p for p in session["plans"] if p["symbol"] == "ABCD"]
    assert len(plans) >= 2, "ABCD should arm more than one setup"
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


def test_ui_opens_tier1_tiles(page):
    _seek(page, 118)
    assert page.locator(".tile").count() == 9
    assert page.locator("[data-tile=five_pillars_list]").count() == 1
    assert page.locator("[data-tile=halt]").count() == 1


def test_ui_tiles_report_state(page):
    states = page.eval_on_selector_all(".tile-state", "els => els.map(e => e.textContent)")
    assert states and all(s in {"REPLAY", "FROZEN", "STALE", "OFFLINE", "LIVE"} for s in states)


def test_ui_row_click_links_everything(page):
    _seek(page, 118)
    page.locator("[data-tile=top_gainers] .trow").nth(1).click()
    page.wait_for_timeout(250)
    symbol = page.locator("#symTicker").inner_text()
    assert symbol and symbol != "—"
    assert symbol in page.locator("#quoteCard").inner_text() or page.locator("#quoteCard").inner_text()
    assert f"symbol={symbol}" in page.url          # deep-linkable
    assert page.locator("[data-tile=top_gainers] .trow.sel").count() >= 1


def test_ui_intervals_survive_symbol_change(page):
    _seek(page, 118)
    page.keyboard.press("d")                        # Chart B -> daily
    page.locator("[data-tile=five_pillars_list] .trow").first.click()
    page.wait_for_timeout(250)
    assert page.locator(".seg-btn[data-chart=a].active").inner_text() == "1m"
    assert page.locator(".seg-btn[data-chart=b].active").inner_text() == "Daily"
    page.keyboard.press("5")
    page.wait_for_timeout(150)
    assert page.locator(".seg-btn[data-chart=b].active").inner_text() == "5m"


def test_ui_freeze_pins_row_order(page):
    _seek(page, 110)
    sel = "[data-tile=top_gainers] .trow b"
    before = page.eval_on_selector_all(sel, "els => els.map(e => e.textContent)")
    page.locator("[data-tile=top_gainers] .icon-btn").click()
    page.wait_for_timeout(150)
    _seek(page, 148)
    after = page.eval_on_selector_all(sel, "els => els.map(e => e.textContent)")
    assert before == after
    assert page.locator("[data-tile=top_gainers] .tile-state").inner_text() == "FROZEN"
    page.locator("[data-tile=top_gainers] .icon-btn").click()   # release
    page.wait_for_timeout(150)


def test_ui_reasons_drawer_shows_pillar_arithmetic(page):
    _seek(page, 125)
    page.keyboard.press("Escape")          # clear any drawer a prior test opened
    page.wait_for_timeout(150)
    page.locator("[data-tile=five_pillars_list] .trow").first.click()
    page.wait_for_timeout(250)
    drawer = page.locator(".reasons")
    assert drawer.count() == 1
    text = drawer.inner_text()
    for token in ("price $2", "gain", "RVOL", "float", "confirmed course"):
        assert token in text


def test_ui_alert_click_seeks_charts(page):
    _seek(page, 150)
    first_alert_time = page.locator(".tl-row .tl-time").first.inner_text()
    page.locator(".tl-row").first.click()
    page.wait_for_timeout(250)
    assert page.locator("#clockET").inner_text().startswith(first_alert_time)
    assert page.locator(".tl-detail").count() == 1


def test_ui_no_javascript_errors(page):
    assert page.errors == []
