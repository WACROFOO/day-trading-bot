"""The per-symbol decision card — one server-side read a manual trader acts on.

Why (owner, 2026-10-08; docs/desk-assessment-2026-10-08.md): the card said
REVIEW when every Layer 1 gate passed and left the setup, the level, the size
and the bot's own answer to the reader. Its pieces existed — the cascade, the
first-pullback machine, the bot's order arithmetic, the catalyst grade — but
were shown apart, refreshed at different speeds, and partly recomputed in the
browser with drifting thresholds. This module joins them into one card:

  verdict   REVIEW / WATCH / WAIT / NO · the one reason that decides · one level
  lamps     every gate the bot applies, value beside threshold, reason only when red
  setup     where the first-pullback machine is, with the pending trigger
  ticket    the bot's own order for this plan, as numbers to type (order_math)
  position  a manual position's live levels under the bot's exit rule (A3)
  catalyst  catalyst.card_read: grade, type, age, two lines, flags
  bot       what the runner did with this symbol's latest plan

Vocabulary stays non-actionable (trading-report-design): REVIEW means "read
the chart, the plan is in front of you", never "buy". Every threshold is
imported from the module that enforces it; nothing here restates a number.
Pure: no I/O, no clock — the caller passes `now`.
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime, time
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

from . import order_math as OM
from .cascade import (FADE_MAX_PCT, FLOAT_MAX, PILLARS_MIN, PREMARKET_VOLUME_CEILING, PRICE_MAX,
                      PRICE_MIN, RVOL_TRADE_FLOOR, SESSION_VOLUME_FLOOR)
from .indicators import EMA9_MIN, MACD_MIN, ema, macd, vwap
from .pullback import SetupState
from .scanners.five_pillars import GAIN_MIN_PCT, RVOL_MIN

ET = ZoneInfo("America/New_York")
WORDS = ("REVIEW", "WATCH", "WAIT", "NO")
#: A session high this many times the session's median close is flagged as a
#: possible bad print (BIYA 2026-10-07: one 08:21 bar at 37.10 on a ~$2.5 stock
#: killed every later plan "94% off the high"). Approximation; a flag, not a gate.
SPIKE_MULTIPLE = 2.5


def _f(x) -> Optional[float]:
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def _px(x: Optional[float]) -> str:
    return "—" if x is None else f"{x:.2f}"


def _gate(cascade: dict, gid: str) -> dict:
    return next((g for g in (cascade or {}).get("gates") or [] if g.get("id") == gid), {})


def _pm_high(bars: Sequence) -> Optional[float]:
    highs = [b[2] for b in bars if datetime.fromtimestamp(b[0], ET).time() < time(9, 30)]
    return max(highs) if highs else None


def _next_half(price: float) -> float:
    nxt = math.ceil(price * 2 + 1e-9) / 2.0
    return nxt + 0.5 if abs(nxt - price) < 1e-9 else nxt


def _dejargon(reason: str) -> str:
    """The runner's refusal text, said plainly. The original stays on hover."""
    r = reason or ""
    rules = (
        ("selective (A13): stop", lambda: r.replace("selective (A13): stop", "stop").split(", under")[0]
         + f" — the bot needs ≥ {OM.SELECTIVE_MIN_STOP_PCT:g}% (A13)"),
        ("selective (A13): price", lambda: r.replace("selective (A13): ", "") + " (A13)"),
        ("Layer 2 not green: pullback volume", lambda: "pullback volume heavier than the push"),
        ("Layer 2 not green: MACD warm-up", lambda: "MACD still warming up (fewer than 35 one-minute bars)"),
        ("Layer 2 not green:", lambda: "chart gates red: " + r.split(":", 1)[1].split("(verdict")[0].strip()),
        ("one position at a time", lambda: "the bot already holds a position (one at a time)"),
        ("phase A", lambda: "log only — phase A sends no orders"),
        ("bar is outside", lambda: "outside the bot's 07:00–11:20 entry window"),
        ("quote clock", lambda: "no fresh quote when the order would have left"),
        ("bar clock", lambda: "the plan was too old when the bot saw it"),
        ("backfill decision", lambda: "armed on history loaded at start — not a live plan"),
        ("day locked", lambda: "risk gate: the bot's day is locked"),
    )
    for prefix, fn in rules:
        if r.startswith(prefix):
            return fn()
    if "inside 4x the spread" in r:
        return "stop inside 4× the spread — the round trip would eat it (A6)"
    if "A8" in r and "hard stop" in r:
        return "inside the last 10 minutes before the 11:30 flatten (A8)"
    return r


def bot_line(view: Optional[dict], journal_available: bool) -> dict:
    """The runner's answer for this symbol, in one line."""
    if not journal_available:
        return {"text": "no ledger on this desk — the bot's decisions are not visible here",
                "tone": "info", "outcome": None, "reasons": []}
    if not view:
        return {"text": "the bot has no plan on this name today", "tone": "info", "outcome": None, "reasons": []}
    oc, at = view.get("outcome"), str(view.get("ts_et") or "")[11:16]
    reasons = list(view.get("reasons") or [])
    o = view.get("order") or {}
    if oc == "TAKEN":
        if o.get("exit_price") is not None:
            text = (f"bot took the {at} plan at {_px(_f(o.get('fill_price')))} — out at "
                    f"{_px(_f(o.get('exit_price')))} ({o.get('exit_reason') or 'exit'})")
        elif o.get("fill_price") is not None:
            text = f"bot is IN since {at}: {o.get('shares')} sh at {_px(_f(o.get('fill_price')))}"
            if o.get("trail_stop") is not None:
                text += f" · stop trailed to {_px(_f(o.get('trail_stop')))}"
        else:
            text = f"bot sent the {at} plan — order {o.get('status') or 'working'}"
        tone = "ok"
    elif oc == "REFUSED":
        first = _dejargon(reasons[0]) if reasons else "refused"
        more = f" (+{len(reasons) - 1} more)" if len(reasons) > 1 else ""
        text, tone = f"bot refused the {at} plan: {first}{more}", "warn"
    elif oc == "PENDING":
        text, tone = f"bot armed the {at} plan — " + (_dejargon(reasons[0]) if reasons else "waiting"), "ok"
    elif oc == "LOG_ONLY":
        text, tone = f"bot logged the {at} plan only (phase {view.get('phase') or 'A'}: no orders)", "info"
    elif oc == "SUPPRESSED":
        text, tone = f"no bot plan: the cascade killed the {at} setup", "info"
    elif oc == "NOT_FILLED":
        text, tone = f"bot's {at} entry never filled in 3 min — cancelled (A10)", "info"
    else:
        text, tone = f"bot: {oc or '—'} on the {at} plan", "info"
    return {"text": text, "tone": tone, "outcome": oc, "at": at,
            "reasons": [{"plain": _dejargon(x), "raw": x} for x in reasons]}


def _kill(cascade: dict, last: Optional[float], session_high: Optional[float]) -> tuple:
    """(reason, level, level_label) for the gate that killed the name."""
    kb = cascade.get("killedBy")
    g = _gate(cascade, kb)
    if kb == "price":
        if last is not None and last < PRICE_MIN:
            return (f"${last:.2f} is under the ${PRICE_MIN:.2f} floor", PRICE_MIN, "back over")
        return (f"${_px(last)} is outside ${PRICE_MIN:.2f}–{PRICE_MAX:.2f}", None, None)
    if kb == "rising" and session_high:
        reopen = round(session_high * (1 - FADE_MAX_PCT / 100.0), 2)
        return (f"{g.get('value', '')} — more than {FADE_MAX_PCT:g}% off the high, back side of the move",
                reopen, "back above")
    if kb == "pillars":
        return (f"Five Pillars {g.get('value', '?/5')} — needs {PILLARS_MIN} of 5", None, None)
    if kb == "split":
        return (f"the gap is the split ({g.get('value', '')}), not a move", None, None)
    if kb == "instrument":
        return ("a fund or ETF — out of scope", None, None)
    if kb == "tick":
        return (f"quotes in {g.get('value', '')} increments", None, None)
    if kb == "buyout":
        return ("buyout announced — the price is pinned near the deal", None, None)
    return (g.get("reason") or f"killed on {kb}", None, None)


def plan_outcome(plan, bars: Sequence) -> str:
    """What the tape did with a frozen plan after it armed: the entry touched,
    then the stop or 2R first — read off the session's own 1-minute bars, the
    same bars the detector saw. 'open' while neither has printed."""
    armed = plan.armed_at_bar.timestamp()
    entered = None
    for b in bars:
        if b[0] <= armed:            # from the bar AFTER the break, as the detector reads it
            continue
        t = datetime.fromtimestamp(b[0], ET).strftime("%H:%M")
        if entered is None:
            if b[3] <= plan.stop:
                return f"stop broke before the entry ({t})"
            if b[2] >= plan.entry:
                entered = t
            else:
                continue
        if b[3] <= plan.stop:
            return f"stopped {t}"
        if b[2] >= plan.target:
            return f"reached 2R {t}"
    return f"triggered {entered}, open" if entered else "never triggered"


def _search_text(detector, bars: Sequence) -> str:
    """The first-pullback machine between setups, in words: the current push
    (green bars, how far it ran) and the last plan with what became of it."""
    if detector is None:
        return "no detector"
    pg = detector.progress()
    n, pct = pg["impulse_bars"], pg["impulse_pct"]
    if n == 0:
        now = "no push under way"
    elif not pg["impulse_valid"]:
        now = (f"{n} green bar{'s' if n > 1 else ''} (+{pct:.1f}%) — a push needs "
               f"{pg['min_impulse_bars']} in a row making ≥ {pg['min_impulse_pct']:g}%")
    else:
        now = f"push under way: {n} green bars, +{pct:.1f}% — the first red bar starts the pullback"
    if detector.plans:
        p = detector.plans[-1]
        return (f"{now} · last plan {p.armed_at_bar.astimezone(ET):%H:%M} "
                f"{p.entry:.2f}/{p.stop:.2f} → {plan_outcome(p, bars)}")
    return now


def build_card(symbol: str, *, meta: dict, cascade: dict, bars: Sequence, detector, now: datetime,
               halted: bool = False, halts_today: int = 0, five_minute: Optional[dict] = None,
               catalyst: Optional[dict] = None, risk: Optional[float] = None,
               risk_source: Optional[str] = None, max_notional: Optional[float] = None,
               bot: Optional[dict] = None, manual_open: Optional[dict] = None,
               last_manual: Optional[dict] = None) -> dict:
    """One symbol's card. `bars` are the session's [ts, o, h, l, c, v] rows up
    to `now`; `detector` is that symbol's FirstPullbackDetector after them."""
    m = meta.get("metrics") or {}
    last = _f(meta.get("iexLast")) or _f(m.get("last")) or (bars[-1][4] if bars else None)
    bid, ask = _f(meta.get("iexBid")), _f(meta.get("iexAsk"))
    sh = _f(m.get("sessionHigh")) or (max(b[2] for b in bars) if bars else None)
    now_et = now.astimezone(ET)
    t = now_et.time()
    closes = [b[4] for b in bars]
    vw = vwap(bars) if bars else None
    e9 = ema(closes, 9)[-1] if len(closes) >= EMA9_MIN else None
    mc = macd(closes)
    pend = detector.pending() if detector is not None else None
    state = detector.state if detector is not None else None
    plan = detector.active_plan if detector is not None else None
    fm = five_minute or {}
    warnings: list[dict] = []

    # -- the levels a plan would use: pending (pullback forming) or frozen ----
    setup = {"state": state.value if state is not None else None}
    trig = stop = None
    if pend:
        trig, stop = pend["entry"], pend["stop"]
        bar_t = pend["trigger_bar_ts"].astimezone(ET).strftime("%H:%M")
        setup.update(text=f"pullback {pend['bars']} bar{'s' if pend['bars'] > 1 else ''} "
                          f"(max {pend['max_bars']}) · volume {'lighter' if pend['volume_ok'] else 'HEAVIER'} than the push",
                     trigger=trig, stop=stop, triggerBar=bar_t, volumeOk=pend["volume_ok"], bars=pend["bars"])
    elif plan is not None and state in (SetupState.ARMED, SetupState.TRIGGERED):
        trig, stop = plan.entry, plan.stop
        armed = plan.armed_at_bar.astimezone(ET).strftime("%H:%M")
        text = (f"plan {armed} {plan.entry:.2f}/{plan.stop:.2f}: the pullback broke, the entry has not printed yet"
                if state == SetupState.ARMED else
                f"plan {armed} {plan.entry:.2f}/{plan.stop:.2f} triggered")
        setup.update(text=text, trigger=trig, stop=stop, armedAt=armed, volumeOk=plan.volume_ok,
                     bars=plan.pullback_candles)
    elif fm.get("state") == "EXTENDED":
        setup.update(text=f"extended — straight up since {str(fm.get('since') or '')[11:16]}, "
                          "no 1-minute pullback yet")
    else:
        setup.update(text=_search_text(detector, bars))

    # -- the verdict: first row that applies wins -------------------------------
    word, reason, level, level_label = None, None, None, None
    verdict = (cascade or {}).get("verdict")
    if verdict == "STALE":
        word, reason = "WAIT", "data stale — no verdict on a feed that is behind"
    elif halted:
        word, reason = "WAIT", "halted — no stop executes during a halt; the reopen sets the price"
    elif (cascade or {}).get("killedBy"):
        word = "NO"
        reason, level, level_label = _kill(cascade, last, sh)
    elif t >= OM.HARD_STOP:
        word, reason = "NO", "after 11:30 — the session is over (no trades 11:30–15:00)"
    elif t >= OM.ENTRY_CUTOFF:
        word, reason = "WAIT", "inside the last 10 minutes before the 11:30 flatten — the bot opens nothing (A8)"
    elif t < OM.PREMARKET_START:
        word, reason = "WATCH", "before 07:00 — thin tape; the bot's entries start at 07:00"
        level, level_label = (trig, "trigger") if trig else (sh, "high of day")
    if word is None:
        reds = []
        for gid, name, val in (("vwap", "VWAP", vw), ("ema9", "9 EMA", e9)):
            if _gate(cascade, gid).get("state") == "FAIL":
                reds.append((f"below the {name} {_px(val)}", val, f"reclaim the {name}"))
        if _gate(cascade, "macd").get("state") == "FAIL":
            h = mc[2][-1] if mc else None
            reds.append((f"MACD under its signal (hist {h:+.3f})" if h is not None else "MACD under its signal",
                         None, None))
        if reds:
            word = "WAIT"
            reason, level, level_label = reds[0]
            if len(reds) > 1:
                reason += f" (+{len(reds) - 1} more red)"
        elif _gate(cascade, "macd").get("state") == "UNKNOWN":
            word = "WATCH"
            reason = f"MACD warming up — {len(closes)} of {MACD_MIN} one-minute bars; the bot refuses until then"
            level, level_label = (trig, "trigger") if trig else (None, None)
    if word is None:
        if pend:
            if not pend["volume_ok"]:
                word, reason = "WAIT", "pullback volume heavier than the push — the bot refuses this one"
            else:
                word = "REVIEW"
                reason = f"first pullback, {pend['bars']} bar{'s' if pend['bars'] > 1 else ''} on lighter volume"
            level, level_label = trig, f"break of the {setup['triggerBar']} high"
        elif plan is not None and state in (SetupState.ARMED, SetupState.TRIGGERED):
            cap = OM.entry_limit(plan.entry)
            if last is not None and last <= plan.stop:
                word, reason = "NO", "the plan's stop is already broken"
            elif last is not None and last > cap:
                word, reason = "WAIT", f"ran past the entry band (limit {cap:.2f}) — no chase; wait for the next pullback"
            else:
                word = "REVIEW"
                reason = f"broke the pullback at {setup.get('armedAt')} — still inside the entry band (≤ {cap:.2f})"
                level, level_label = plan.entry, "trigger"
        elif fm.get("state") == "EXTENDED":
            word, reason = "WATCH", "extended — no 1-minute pullback yet; wait for the first red candle"
        else:
            word = "WATCH"
            reason = setup["text"]
            level, level_label = sh, "high of day"

    # -- lamps: the bot's own gates, value beside threshold ----------------------
    def lamp(lid, label, state_, value, rule, kind="gate", why=None):
        return {"id": lid, "label": label, "state": state_, "value": value, "rule": rule,
                "kind": kind, "why": why if state_ in ("FAIL", "UNKNOWN", "MANUAL_CONFIRMATION_REQUIRED",
                                                       "STALE") else None}

    lamps = []
    gp = _gate(cascade, "price")
    lamps.append(lamp("price", "Price", gp.get("state", "UNKNOWN"), f"${_px(last)}",
                      f"${PRICE_MIN:.0f}–{PRICE_MAX:.0f}", why=gp.get("reason")))
    chg = _f(m.get("changePct"))
    lamps.append(lamp("gain", "Gain", "UNKNOWN" if chg is None else ("PASS" if chg >= GAIN_MIN_PCT else "FAIL"),
                      "—" if chg is None else f"{chg:+.1f}%", f"≥ {GAIN_MIN_PCT:g}% (pillar)",
                      why=None if chg is None else f"{chg:+.1f}% is under {GAIN_MIN_PCT:g}%"))
    rv = _f(m.get("rvol"))
    lamps.append(lamp("rvol", "Rel. volume",
                      "UNKNOWN" if rv is None else ("PASS" if rv >= RVOL_MIN else "FAIL"),
                      "—" if rv is None else f"{rv:.1f}×",
                      f"≥ {RVOL_MIN:g}× pillar · ≥ {RVOL_TRADE_FLOOR:g}× trade floor",
                      why=None if rv is None else f"{rv:.1f}× is under the {RVOL_MIN:g}× pillar"))
    gf = _gate(cascade, "float")
    lamps.append(lamp("float", "Float", gf.get("state", "UNKNOWN"), gf.get("value", "—"),
                      f"< {FLOAT_MAX / 1e6:.0f}M (flag only, A5)", why=gf.get("reason")))
    gc = _gate(cascade, "catalyst")
    if catalyst and catalyst.get("grade") == "UNKNOWN":
        cat_value = "no headline feed on this desk"
    elif catalyst:
        cat_value = f"{catalyst['grade']} · {catalyst['type']} · {catalyst['age']}"
    else:
        cat_value = gc.get("value", "—")
    lamps.append(lamp("catalyst", "Catalyst", gc.get("state", "UNKNOWN"), cat_value,
                      "own news dated today (flag only, A2)", why=gc.get("reason")))
    gpl = _gate(cascade, "pillars")
    lamps.append(lamp("pillars", "Pillars", gpl.get("state", "UNKNOWN"), gpl.get("value", "—"),
                      f"≥ {PILLARS_MIN} of 5", why=gpl.get("reason")))
    gr = _gate(cascade, "rising")
    reopen = round(sh * (1 - FADE_MAX_PCT / 100.0), 2) if sh else None
    lamps.append(lamp("rising", "Still rising", gr.get("state", "UNKNOWN"), gr.get("value", "—"),
                      f"≤ {FADE_MAX_PCT:g}% off the high" + (f" (line {reopen:.2f})" if reopen else ""),
                      why=gr.get("reason")))
    struct = [g for g in (_gate(cascade, x) for x in ("split", "instrument", "tick", "buyout")) if g]
    states = [g.get("state") for g in struct]
    worst = next((g for g in struct if g.get("state") == "FAIL"), None) or \
        next((g for g in struct if g.get("state") == "UNKNOWN"), None)
    if worst is not None:
        sstate = worst.get("state")
    elif states and all(x == "NOT_APPLICABLE" for x in states):
        sstate = "NOT_APPLICABLE"
    else:
        sstate = "PASS" if states else "UNKNOWN"
    lamps.append(lamp("structure", "Split · type · tick · buyout", sstate,
                      " · ".join(f"{g.get('label', '?')}: {g.get('value', '—')}" for g in struct) or "—",
                      "gates 5–8", why=(worst.get("reason") or f"{worst.get('label')}: {worst.get('value')}")
                      if worst is not None else None))
    for gid, label, val in (("vwap", "VWAP", vw), ("ema9", "9 EMA", e9)):
        g = _gate(cascade, gid)
        st = g.get("state", "UNKNOWN") if g else "NOT_APPLICABLE"
        d = (f"{(last - val) / val * 100:+.1f}%" if (last is not None and val) else "")
        lamps.append(lamp(gid, label, st, f"{_px(last)} vs {_px(val)} {d}".strip(), "price above",
                          why=f"price is below the {label}" if st == "FAIL" else
                          ("not computed (cascade stopped earlier)" if st == "NOT_APPLICABLE" else None)))
    g = _gate(cascade, "macd")
    if mc:
        line, sig, hist = mc[0][-1], mc[1][-1], mc[2][-1]
        mv = f"line {line:+.3f} · signal {sig:+.3f} · hist {hist:+.3f}"
    else:
        mv = f"warming {len(closes)}/{MACD_MIN} bars"
    lamps.append(lamp("macd", "MACD 12/26/9", g.get("state", "UNKNOWN") if g else "NOT_APPLICABLE", mv,
                      "hist > 0 (line above signal)", why="MACD under its signal" if g.get("state") == "FAIL" else
                      (f"needs {MACD_MIN} bars" if g.get("state") == "UNKNOWN" else None)))
    vol_ok = pend["volume_ok"] if pend else (plan.volume_ok if plan is not None and state in
                                              (SetupState.ARMED, SetupState.TRIGGERED) else None)
    nbars = setup.get("bars")
    pb_value = ("no pullback in play" if vol_ok is None else
                f"{nbars} bar{'s' if nbars != 1 else ''} · volume {'lighter' if vol_ok else 'heavier'} than the push")
    lamps.append(lamp("pullback", "Pullback", "UNKNOWN" if vol_ok is None else ("PASS" if vol_ok else "FAIL"),
                      pb_value, "1–4 bars, volume lighter than the push",
                      why=None if vol_ok is None else "pullback volume heavier than the push — the bot refuses"))
    # Room overhead: information, never a gate (FILTERS.md "What is NOT a filter":
    # a reward:risk ratio is a realised number, not a pre-entry veto).
    room = {}
    if trig and stop and trig > stop:
        rps = trig - stop
        pm = _pm_high(bars)
        lv = [("high of day", sh)]
        if pm and (not sh or abs(pm - sh) > 0.005):
            lv.append(("pre-market high", pm))
        lv.append(("next half dollar", _next_half(trig)))
        room = {name: {"price": round(p, 2), "r": round((p - trig) / rps, 1)} for name, p in lv if p}
        parts = [f"{name} {v['price']:.2f} ({v['r']:+.1f}R)" for name, v in room.items()]
        lamps.append(lamp("room", "Room overhead", "INFO", " · ".join(parts), "information, not a gate", kind="info"))
    lamps.append(lamp("tape", "Tape · Level 2", "MANUAL_CONFIRMATION_REQUIRED", "your eyes",
                      "no tape and no book in this tool", kind="manual"))

    # -- Layer 3 and data warnings (they never change the word) -----------------
    vt = _f(m.get("volumeToday"))
    if vt is not None and vt < SESSION_VOLUME_FLOOR:
        warnings.append({"id": "volume", "text": f"session volume {vt / 1e6:.2f}M, under the 1M he lost money below"})
    if rv is not None and rv < RVOL_TRADE_FLOOR:
        warnings.append({"id": "rvol", "text": f"relative volume {rv:.1f}×, under the {RVOL_TRADE_FLOOR:g}× trade floor"})
    pmv = _f(m.get("volumePremarket"))
    if pmv is not None and pmv > PREMARKET_VOLUME_CEILING:
        warnings.append({"id": "pm_volume",
                         "text": f"pre-market volume {pmv / 1e6:.1f}M, over the ~1M ceiling — not the first to see it"})
    if sh and closes:
        med = statistics.median(closes)
        if med > 0 and sh > SPIKE_MULTIPLE * med:
            hi_bar = max(bars, key=lambda b: b[2])
            warnings.append({"id": "spike", "text":
                             f"the high {sh:.2f} ({datetime.fromtimestamp(hi_bar[0], ET):%H:%M}) is "
                             f"{sh / med:.1f}× the session's median price — check the print; "
                             "every '% off the high' is measured from it"})

    # -- the ticket: the bot's own order for these levels ------------------------
    ticket = None
    if trig and stop and word in ("REVIEW", "WATCH", "WAIT") and (cascade or {}).get("planAllowed"):
        tk = OM.ticket(symbol, trig, stop, risk or 0.0, session=OM.entry_session(t), bid=bid, ask=ask,
                       max_notional=max_notional, prev_close=_f(meta.get("prevClose")),
                       ranges=[b[2] - b[3] for b in bars if b[5] > 0 and b[2] > b[3]],
                       halts_today=halts_today, halted=halted)
        if tk is not None:
            ticket = tk.to_dict()
            ticket["risk_source"] = risk_source
            if not risk:
                ticket["shares"] = None
                ticket["order_line"] = "state your risk per trade to size this order"

    # -- a manual position, read with the bot's exit rule ------------------------
    position = None
    if manual_open:
        ent, stp, n = _f(manual_open.get("price")), _f(manual_open.get("stop")), manual_open.get("shares")
        try:
            since = datetime.fromisoformat(str(manual_open.get("ts")).replace("Z", "+00:00")).timestamp()
        except ValueError:
            since = None
        hi = max([b[2] for b in bars if since is None or b[0] + 60 > since] or [ent or 0])
        p = OM.position(ent or 0, stp or 0, int(n or 0), hi, last)
        if p is not None:
            position = p.to_dict()
            position["since"] = str(manual_open.get("ts_et") or "")[11:16]

    return {
        "symbol": symbol,
        "asOf": now.isoformat(timespec="seconds"),
        "asOfEt": now_et.strftime("%H:%M:%S"),
        "verdict": {"word": word, "reason": reason,
                    "level": round(level, 2) if level is not None else None, "levelLabel": level_label,
                    "cascade": verdict},
        "setup": setup,
        "lamps": lamps,
        "warnings": warnings,
        "ticket": ticket,
        "position": position,
        "catalyst": catalyst,
        "bot": bot,
        "manual": last_manual,
        "risk": {"dollars": risk, "source": risk_source},
    }
