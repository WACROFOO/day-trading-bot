#!/usr/bin/env python3
"""One command for the trading day. Ross's morning, automated.

    python3 scripts/day.py            # do whatever this moment of the day needs
    python3 scripts/day.py --dry-run  # say what it would do, touch nothing

His sequence is scan → watch → setup → trade → review, and the pieces
already exist as separate tools. This file only puts them in order and
reads the clock:

  06:55–09:30 ET  gap scan (scripts/premarket_stars.py) picks the watchlist:
                  STAR and WATCH survivors, rejects left out by name.
                  Pre-market probe runs ONCE per day and records its verdict.
                  Desk starts on the watchlist with JOURNAL_DB set.
                  Runner starts in the mode exercise_state dictates.
  09:30–11:30 ET  desk and runner keep running. Nothing else to do.
  11:30 ET        hard stop — the runner flattens in TRADE mode (its job, not
                  this file's). This file waits for it.
  after 11:30     actuals from the ledger's own bars, replay check, controls,
                  the day's report written to research/paper-exercise/reports/,
                  sessions_done += 1.

What this file does NOT do, on purpose:
  - log in to TWS or the Gateway (2FA; a human does that, once, before 06:55)
  - move the exercise between phases — `exercise.py advance` checks the
    pre-registration gates and a human runs it
  - decide anything about a trade. The cascade, the detector and the runner
    decide; this file only starts them and reads the clock
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import ET, HARD_STOP  # noqa: E402
from execution.policy import premarket_allowed  # noqa: E402,F401
from journal import actuals, bars, controls, ledger as L, replay  # noqa: E402
from momentum_platform.holidays import why_closed  # noqa: E402
from momentum_platform.sessions import REGULAR_START  # noqa: E402

PREMARKET_OPEN = datetime.strptime("06:55", "%H:%M").time()
REPORTS = ROOT / "research" / "paper-exercise" / "reports"
DB = Path(os.environ.get("JOURNAL_DB") or L.DEFAULT_DB)
PROBE_ONCE = ROOT / "data" / "probe-orders.once"    # touch it the evening before; consumed at start

DIM, BOLD, OK, BAD, WARN, END = "\033[2m", "\033[1m", "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def say(m): print(m, flush=True)
def good(m): say(f"  {OK}ok{END}   {m}")
def bad(m): say(f"  {BAD}xx{END}   {m}")
def warn(m): say(f"  {WARN}!!{END}   {m}")
def note(m): say(f"       {DIM}{m}{END}")


# ------------------------------------------------------------ pure parts
def pick_watchlist(rows: list[dict], cap: int = 8) -> tuple[list[str], list[tuple[str, str]]]:
    """STAR first, then WATCH, up to `cap`. Rejects returned with their reason
    so the morning log shows what was thrown away, never just the survivors."""
    stars = [r["sym"] for r in rows if r.get("verdict") == "STAR"]
    watch = [r["sym"] for r in rows if r.get("verdict") == "WATCH"]
    rejects = [(r["sym"], (r.get("reasons") or ["?"])[0]) for r in rows if r.get("verdict") == "REJECT"]
    picked = (stars + watch)[:cap]
    return picked, rejects


def mode_for(state: dict) -> str:
    """Phase A logs only. B and beyond trade. D/E are read-outs: log only again."""
    return "TRADE" if state.get("phase") in ("B", "C") else "LOG_ONLY"


def _superseded_prospective(conn, rep: dict) -> int:
    """How many PROSPECTIVE decisions reproduce only under superseded rules.

    `replay.check` classifies every row; backfill rows are already excluded
    from `plans_prospective`, so they must be excluded here too or they would
    be subtracted twice.
    """
    ids = [r["decision_id"] for r in rep.get("superseded", ())]
    if not ids:
        return 0
    n = 0
    for chunk in (ids[i:i + 400] for i in range(0, len(ids), 400)):
        marks = ",".join("?" * len(chunk))
        n += conn.execute(
            f"SELECT COUNT(*) FROM decisions WHERE decision_id IN ({marks}) "
            "AND (data_status IS NULL OR data_status NOT LIKE '%-backfill')",
            chunk).fetchone()[0]
    return n


def gates_for_advance(conn, state: dict) -> tuple[str | None, list[str]]:
    """What blocks the next phase, per docs/preregistration.md §3. Empty list
    = may advance. Values here mirror the PROPOSED ones; when the owner sets
    them, change them HERE and in the doc in the same commit."""
    f = L.funnel(conn)
    rep = replay.check(conn)
    phase = state.get("phase", "A")
    blockers: list[str] = []
    if rep["diverged"]:
        blockers.append(f"replay check: {len(rep['diverged'])} decision(s) do not reproduce")
    if f.get("orders_unresolved"):
        blockers.append(f"{f['orders_unresolved']} order intent(s) unresolved at the broker — "
                        f"a human must clear them (exercise.py stuck)")
    if phase == "A":
        nxt = "B"
        # Three exclusions, and each one is a cohort that cannot answer the
        # question the gate asks — "do the rules I am about to trade produce 40
        # decisions I have watched?"
        #   backfill  : armed on history loaded at startup, with inputs from
        #               later. Diagnostic only (audit F3).
        #   superseded: made under a rule set an amendment has replaced. Owner's
        #               decision, 2026-09-18: the cohort resets on an amendment.
        #               A row whose answer the amendment did not change still
        #               counts — it reproduces under the current rules.
        current = f["plans_prospective"] - _superseded_prospective(conn, rep)
        if state.get("sessions_done", 0) < 5 or current < 40:
            blockers.append(f"phase A needs 5 sessions AND 40 prospective decisions under the "
                            f"CURRENT rules; have {state.get('sessions_done', 0)} sessions, "
                            f"{current} ({f['plans_backfill']} backfill and "
                            f"{f['plans_prospective'] - current} superseded excluded)")
        # `is None` alone was a loophole. On 2026-09-18 the Gateway was still
        # in Read-Only mode, IBKR refused both legs with warning 321 and the
        # probe recorded `inconclusive` — which is not None, so this gate
        # cleared on a question that was never asked. §5 of the pre-registration
        # defines two verdicts, `held` and `queued`; it has no row for a
        # non-answer. Tightening a gate against oneself is always allowed.
        if state.get("probe_verdict") in (None, "inconclusive"):
            blockers.append(
                "pre-market probe has not recorded a usable verdict "
                f"(have {state.get('probe_verdict') or 'none'}; need held or queued)")
    if phase in ("A", "B") and state.get("paper_data") != "realtime":
        blockers.append(f"paper session data is {state.get('paper_data') or 'unmeasured'} — fills would "
                        f"be judged against a different tape than the decision (scripts/alignment_probe.py)")
    if phase == "A":
        pass
    elif phase == "B":
        nxt = "C"
        if f["taken"] < 30:
            blockers.append(f"phase B needs 30 taken trades; have {f['taken']}")
        if f["fills"] and f["fills_with_nbbo"] / f["fills"] < 0.9:
            blockers.append(f"only {f['fills_with_nbbo']}/{f['fills']} fills carry NBBO (need 90%)")
        # Owner decision 2026-09-22 (delegated): the count restarts at a named
        # defect fix, recorded by `exercise.py reset-unprotected`. Before that
        # command the count runs from the start of the ledger.
        since = state.get("unprotected_reset_at")
        unprotected = L.unprotected_fills(conn, since)
        if unprotected:
            blockers.append(f"{unprotected} filled entry(ies) were unprotected"
                            + (f" since the reset at fix {state.get('unprotected_reset_fix')} ({since[:16]})" if since else "")
                            + " — zero allowed")
        # Operational readiness, prospective (review 2026-09-21, item 11): a
        # decision count validates activity, not order submission, protective
        # exits, reconciliation or recovery. Phase C needs one trade that went
        # the whole way on the broker's word — fill, stop leg, exit filled,
        # row closed, no human flag — and 30 taken trades do not unlock
        # pre-market on their own.
        if not L.reconciled_lifecycles(conn):
            blockers.append("phase C needs one fully reconciled paper trade lifecycle (fill, protective "
                            "stop leg, exit confirmed by the broker, ledger row closed); have none — "
                            "the exercise is in paper commissioning until then")
        if state.get("probe_verdict") not in ("held", "queued"):
            blockers.append("phase C needs a definite probe verdict (held or queued)")
    elif phase == "C":
        nxt = "D"
        if f["taken"] < 60:
            blockers.append(f"phase D read-out needs 60 taken trades; have {f['taken']}")
    else:
        return None, ["phase D/E: the read-out is evaluated once, by a human, per §4"]
    return nxt, blockers


def write_report(conn, day: str, source: str, synthetic: bool = False) -> Path:
    """The day's report, trading-report-design layout, as a markdown file."""
    REPORTS.mkdir(parents=True, exist_ok=True)
    f = L.funnel(conn)
    rep = replay.check(conn)
    ctl = controls.summary(conn)
    st = L.get_state(conn)
    lines = [f"# Paper exercise — {day}", "",
             f"**LEDGER** · `{DB.name}` · {source} · phase {st['phase']} · "
             f"session {st['sessions_done'] + 1} · written {datetime.now(ET):%Y-%m-%d %H:%M ET}", ""]
    if synthetic:
        lines += ["> **SYNTHETIC FIXTURE** — proves plumbing, never a market.", ""]
    lines += ["## Funnel", "",
              "| stage | n |", "|---|---:|",
              f"| symbols on the board | {f['board_symbols']} |",
              f"| plans armed | {f['plans_armed']} |",
              f"| suppressed by the cascade | {f['plans_suppressed']} |",
              f"| refused by the executor | {f['refused_by_executor']} |",
              f"| LOG_ONLY | {f['log_only']} |", f"| TAKEN | {f['taken']} |",
              f"| orders · fills · fills with NBBO | {f['orders']} · {f['fills']} · {f['fills_with_nbbo']} |",
              f"| halts | {f['halts']} |", ""]
    # The day's own decisions, by outcome — the funnel above is the whole
    # ledger. 2026-09-21: the report's rejects table listed seven sessions
    # of rows under one day's title, and the reader could not tell today's
    # from last week's without the log beside it.
    today_rows = conn.execute("SELECT outcome, COUNT(*) AS n FROM decisions WHERE substr(ts_et,1,10)=? "
                              "GROUP BY outcome ORDER BY outcome", (day,)).fetchall()
    lines += [f"Today ({day}): " + (" · ".join(f"{r['n']} {r['outcome']}" for r in today_rows) or "no decisions"), ""]
    lines += ["## Rejects (today only)", "", "| ET | symbol | verdict | outcome | last | why |", "|---|---|---|---|---:|---|"]
    for r in conn.execute("""SELECT ts_et, symbol, verdict, killed_by, outcome, refusal_reasons_json, last
                             FROM decisions WHERE outcome IN ('SUPPRESSED','REFUSED')
                             AND substr(ts_et,1,10)=? ORDER BY ts_et""", (day,)):
        why = r["killed_by"] or ""
        if r["outcome"] == "REFUSED" and r["refusal_reasons_json"]:
            why = "; ".join(json.loads(r["refusal_reasons_json"]))
        lines.append(f"| {r['ts_et'][11:16]} | {r['symbol']} | {r['verdict']} | {r['outcome']} | "
                     f"{r['last'] if r['last'] is not None else '—'} | {why} |")
    lines += ["", "## Controls (planned R · same rows · no CIs at this n)", "",
              "| series | n | mean R | median R | win |", "|---|---:|---:|---:|---:|"]
    for k, v in ctl.items():
        if v["n"] and v["mean_R"] is not None:
            lines.append(f"| {k} | {v['n']} | {v['mean_R']:.3f} | {v['median_R']:.3f} | {v['win_rate']:.0%} |")
        else:
            lines.append(f"| {k} | {v['n']} | — | — | — |")
    ex = controls.exit_summary(conn, bars.from_ledger(conn))
    lines += ["", "## Exit variants (simulated · same entry fill · same initial stop · same cutoff · planned R)", "",
              "| variant | n | mean R | median R | stopped | to close |", "|---|---:|---:|---:|---:|---:|"]
    for k, v in ex.items():
        if v["n"] and v["mean_R"] is not None:
            lines.append(f"| {k} | {v['n']} | {v['mean_R']:.3f} | {v['median_R']:.3f} | "
                         f"{v['stopped']:.0%} | {v['to_close']:.0%} |")
        else:
            lines.append(f"| {k} | {v['n']} | — | — | — | — |")
    lines += ["", "baseline = fixed +2 R target · no_target = initial stop only · trail_1r = A3, "
              "bar-ordered, the low is tested before the high raises the stop. \"close\" = the last "
              f"bar the desk recorded ({controls.last_bar_time(conn) or 'none'} UTC); hold_close and "
              "random_bar carry no stop; no costs in any series."]
    u = controls.units(conn)
    lines += ["", "## Statistical unit", "",
              f"{u['rows']} rows = {u['unique_setups']} unique setups on {u['unique_symbol_days']} unique "
              f"symbol-days over {u['sessions']} session(s).", "",
              "| session | n | mean R | median R |", "|---|---:|---:|---:|"]
    for day, v in u["per_session"].items():
        lines.append(f"| {day} | {v['n']} | {v['mean_R']:+.3f} | {v['median_R']:+.3f} |")
    if u["top3_symbol_days"]:
        lines += ["", "| largest winning symbol-day | rows | sum R |", "|---|---:|---:|"]
        for t in u["top3_symbol_days"]:
            lines.append(f"| {t['symbol']} {t['day']} | {t['rows']} | {t['sum_R']:+.2f} |")
        share = (f"{u['top3_share_of_total']:.0%} of the total" if u["top3_share_of_total"] is not None
                 else "total ≤ 0")
        lines.append("")
        lines.append(f"These three carry {share}; the mean without them is "
                     + (f"{u['mean_R_without_top3']:+.3f} R." if u["mean_R_without_top3"] is not None else "undefined."))
    viol = L.r0_violations(conn)
    lines += ["", f"R0 check: {f['fills']} fill(s); realised risk = qty × (fill − initial stop) on "
              + ("all." if not viol else f"all but {len(viol)}: " + ", ".join(f"#{v['order_id']}" for v in viol) + ".")]
    pd = st.get("paper_data")
    lines += ["", "## Alignment (decision tape → fill → fill tape)", "",
              f"Paper session data: **{pd or 'NOT MEASURED — run scripts/alignment_probe.py'}**"
              + (f" ({st.get('paper_data_date')})" if pd else ""), ""]
    al = L.alignment_rows(conn)
    if al:
        lines += ["| ET | symbol | decision bid/ask | trigger | fill | fill bid/ask | gap s | slippage |",
                  "|---|---|---|---:|---:|---|---:|---:|"]
        for r in al:
            dba = f"{r['d_bid']}/{r['d_ask']}" if r["d_bid"] is not None else "—"
            fba = f"{r['nbbo_bid']}/{r['nbbo_ask']}" if r["nbbo_bid"] is not None else "— (unverified)"
            gap = r["quote_gap_s"] if r["quote_gap_s"] is not None else "—"
            slip = f"{r['slippage_ratio']:.2f}×" if r["slippage_ratio"] is not None else "—"
            lines.append(f"| {r['fill_ts'][11:16]} | {r['symbol']} | {dba} | {r['trigger']:.2f} | "
                         f"{r['fill_price']:.2f} | {fba} | {gap} | {slip} |")
    else:
        lines.append("No fills.")
    lamp = "✓" if not rep["diverged"] else "✗"
    lines += ["", "## Replay (R11)", "",
              f"{lamp} {rep['reproduced']}/{rep['checked']} decisions reproduce their recorded verdict"]
    for d in rep["diverged"]:
        lines.append(f"- {d['ts_et'][11:16]} {d['symbol']}: recorded {d['recorded']} · replayed {d['replayed']}")
    lines += ["", "## Not checked", "",
              "Real fills (paper is simulated; NBBO plausibility only) · halt-resume fills · "
              "sub-minute entries · Level 2 · borrow · fees beyond IBKR's estimate · regime.", "",
              "*Paper only. The 894-session replication was negative expectancy "
              "(`research/momentum-replication/reports/2026-08-regime-filter.md`); this measures selection.*", ""]
    out = REPORTS / f"{day}.md"
    out.write_text("\n".join(lines))
    return out


# ------------------------------------------------------- orchestration
def write_float_overrides(rows: list[dict], today: str) -> int:
    """Hand the scan's finviz floats to the desk. Layer 0 and Layer 1 then
    agree on the one number that kills most names."""
    floats = {r["sym"].upper(): float(r["float"]) for r in rows
              if r.get("sym") and r.get("float") and r["float"] > 0}
    path = ROOT / "data" / "float_overrides.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"date": today, "source": "finviz via premarket_stars.py",
                                "floats": floats}, indent=1))
    return len(floats)


def gap_scan(dry: bool) -> list[dict]:
    if dry:
        return []
    try:
        out = subprocess.run([sys.executable, "scripts/premarket_stars.py", "--json", "--top", "20"],
                             cwd=ROOT, capture_output=True, text=True, timeout=180)
        return parse_scan_output(out.stdout) if out.returncode == 0 else []
    except Exception as exc:                            # noqa: BLE001
        warn(f"gap scan failed: {exc}")
        return []


def parse_scan_output(text: str) -> list[dict]:
    """The scan's JSON, tolerant of a stray line before it. 2026-09-09, 06:55
    ET, no network yet after wake: the scan printed a warning ahead of its
    JSON and the day read 'Extra data: line 1 column 5' instead of a list."""
    text = (text or "").strip()
    if not text:
        return []
    start = min([i for i in (text.find("["), text.find("{")) if i >= 0], default=-1)
    if start < 0:
        return []
    try:
        data = json.loads(text[start:])
    except json.JSONDecodeError:
        # the JSON may be followed by more text: take the first complete document
        dec = json.JSONDecoder()
        data, _ = dec.raw_decode(text[start:])
    return data if isinstance(data, list) else []


def run_probe_once(conn, today: str, dry: bool) -> None:
    st = L.get_state(conn)
    if st.get("probe_date") == today:
        good(f"probe already ran today — verdict {st['probe_verdict']!r}")
        return
    if dry:
        note("would run scripts/premarket_probe.py"); return
    env = {**os.environ, "JOURNAL_DB": str(DB)}
    r = subprocess.run([sys.executable, "scripts/premarket_probe.py"], cwd=ROOT, env=env)
    if r.returncode == 0:
        good(f"probe ran — verdict {L.get_state(conn).get('probe_verdict')!r}")
    else:
        warn(f"probe exit {r.returncode} — see its output above; verdict not recorded")


def run_alignment_once(conn, today: str, dry: bool) -> None:
    """Is the paper session on the same tape as the live one? Once per day."""
    st = L.get_state(conn)
    if st.get("paper_data_date") == today and st.get("paper_data") == "realtime":
        good(f"alignment probe already ran today — paper data {st['paper_data']!r}")
        return
    if st.get("paper_data_date") == today:
        # A 'competing' or 'delayed' reading is a condition to fix (TWS logged
        # in, sharing not yet active), not a fact about the day: measure again
        # on every start until it reads realtime (9 September 2026, 08:28 ET).
        note(f"alignment probe read {st.get('paper_data')!r} earlier today — measuring again")
    if dry:
        note("would run scripts/alignment_probe.py"); return
    env = {**os.environ, "JOURNAL_DB": str(DB)}
    r = subprocess.run([sys.executable, "scripts/alignment_probe.py"], cwd=ROOT, env=env)
    st = L.get_state(conn)
    if r.returncode == 0 and st.get("paper_data") == "realtime":
        good("paper session is on real-time data — decision tape and fill tape agree")
    elif r.returncode == 0:
        warn(f"paper session data: {st.get('paper_data')!r} — fills would be judged against a different tape")
        note("Client Portal › Settings › Paper Trading Account › share real-time market data. Then re-run.")
    else:
        warn(f"alignment probe exit {r.returncode} — see its output above")


IBKR_PORTS = ("4002", "7496")     # paper Gateway first, then TWS


def ibkr_port(env: dict | None = None) -> tuple[str, str]:
    """The IBKR API port for the desk and the runner. IBKR_PORT wins when set;
    otherwise the first port that accepts a TCP connect, Gateway (4002) before
    TWS (7496). 2026-09-21 10:11: the command was pasted without
    IBKR_PORT=4002 and the desk tried 7496, which nothing was listening on,
    while the Gateway sat logged in on 4002. The choice is written back to
    the environment so the desk and the runner see the same port."""
    import socket
    env = os.environ if env is None else env
    forced = (env.get("IBKR_PORT") or "").strip()
    if forced:
        return forced, "IBKR_PORT"
    host = env.get("IBKR_HOST", "127.0.0.1")
    for port in IBKR_PORTS:
        try:
            with socket.create_connection((host, int(port)), timeout=0.5):
                env["IBKR_PORT"] = port
                return port, "detected"
        except OSError:
            continue
    env["IBKR_PORT"] = IBKR_PORTS[0]
    return IBKR_PORTS[0], "nothing listening; default"


def start_desk(symbols: list[str], dry: bool):
    cmd = [sys.executable, "-m", "momentum_platform.dashboard.server", "--host", "127.0.0.1",
           "--port", os.environ.get("DESK_PORT", "8787"), "--ibkr", ",".join(symbols),
           "--ibkr-required"]
    note("desk: " + " ".join(cmd))
    if dry:
        return None
    env = {**os.environ, "JOURNAL_DB": str(DB), "PYTHONPATH": str(ROOT / "src")}
    return subprocess.Popen(cmd, cwd=ROOT, env=env)


def desk_is_on_ibkr(proc, timeout_s: int = 420) -> bool:
    """Poll the desk's health until it reports a live IBKR session, or give up.

    The old check was `proc.poll() is None`, which a desk serving the recorded
    fixture after a failed Gateway connect passes all morning (audit
    2026-09-08). --ibkr-required makes that fallback exit 3; this confirms the
    positive case as well.
    """
    import json as _json
    import urllib.request
    port = os.environ.get("DESK_PORT", "8787")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=3) as r:
                h = _json.loads(r.read().decode())
            if h.get("mode") == "live" and h.get("streaming"):
                state = h.get("provider", {}).get("state", "?")
                # "ok ... (feed OFFLINE)" was printed on 2026-09-21: an ok beside
                # the word OFFLINE. The desk is up; the feed is a separate fact.
                (good if state == "LIVE" else warn)(f"desk is up on IBKR — feed {state}")
                return True
        except Exception:                                 # noqa: BLE001
            pass
        time.sleep(3)
    return False


def start_runner(mode: str, risk: float, dry: bool):
    cmd = [sys.executable, "-u", "scripts/exercise.py", "--db", str(DB), "live", "--risk", str(risk)]
    if mode == "TRADE":
        cmd.append("--trade")
    note("runner: " + " ".join(cmd))
    if dry:
        return None
    return subprocess.Popen(cmd, cwd=ROOT, env={**os.environ, "JOURNAL_DB": str(DB)})


def after_close(conn, today: str, dry: bool) -> None:
    say(f"\n{BOLD}After the hard stop{END}")
    if dry:
        note("would fill actuals from ledger bars, run replay, write the report, bump sessions_done")
        return
    expired = L.expire_pending(conn, today)
    if expired:
        warn(f"{expired} allowed plan(s) armed with no runner alive to judge them — recorded EXPIRED")
    res = actuals.fill_all(conn, bars.from_ledger(conn))
    good(f"actuals: {res['computed']} computed, {len(res['no_tape'])} without tape")
    rep = replay.check(conn)
    (good if not rep["diverged"] else bad)(f"replay: {rep['reproduced']}/{rep['checked']} reproduce")
    path = write_report(conn, today, "IBKR · TWS read-only · live")
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    good(f"report: {shown}")
    st = L.get_state(conn)
    # Bars of the day being settled (UTC date == ET date for an 04:00-16:00
    # ET session), not of the wall-clock day: --settle runs this for a past day.
    bars_today = conn.execute("SELECT COUNT(*) FROM bars WHERE substr(ts,1,10)=?",
                              (today,)).fetchone()[0]
    if bars_today == 0:
        # A holiday or a dead feed. Counting it toward the five log-only
        # sessions would let the exercise leave phase A on days that taught
        # it nothing. 2026-09-07 (Labor Day) was the first such day.
        warn("no bars recorded today — market closed or feed dead; NOT counted as a session")
    elif st.get("last_session_date") == today:
        note("this session was already counted")
    else:
        L.set_state(conn, sessions_done=st["sessions_done"] + 1, last_session_date=today)
    nxt, blockers = gates_for_advance(conn, L.get_state(conn))
    if nxt:
        if blockers:
            note(f"phase {st['phase']} → {nxt} blocked by:")
            for b in blockers:
                note(f"  - {b}")
        else:
            warn(f"phase {st['phase']} → {nxt} gates are ALL clear — run: python3 scripts/exercise.py advance")


DAY_LOCK = Path(str(DB) + ".day.lock")


def day_lock(path: Path = DAY_LOCK):
    """One day per ledger. Returns the held lock file, or None if another
    day.py holds it — with that process's pid written inside.

    2026-09-21: the 06:55 launchd job was running; two manual starts at 07:04
    and 07:05 connected as IBKR client 27 on top of it. IBKR answered 326 to
    the newcomer — and the running desk's socket dropped ("socket dropped",
    four connect failures, reconnect gen 2 in its health log). A second copy
    is not merely refused, it can knock the live one offline. So the second
    copy must never reach the Gateway at all."""
    import fcntl
    fd = open(path, "a+")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        fd.seek(0)
        pid = fd.read().strip() or "?"
        fd.close()
        return None, pid
    fd.seek(0); fd.truncate(); fd.write(str(os.getpid())); fd.flush()
    return fd, None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--early", action="store_true",
                    help="start before 06:55 ET (owner's call, 2026-09-22); the 06:55 scheduled "
                         "start then finds the instance lock and steps aside")
    ap.add_argument("--risk", type=float, default=None, help="overrides exercise_state.dollar_risk")
    ap.add_argument("--symbols", help="skip the gap scan; comma-separated watchlist")
    ap.add_argument("--probe-orders", action="store_true",
                    help="allow the pre-market stop probe, which PLACES (and cancels) an unfillable "
                         "paper bracket. Off by default: an observational day dispatches nothing "
                         "order-shaped (audit 2026-09-08 F6).")
    ap.add_argument("--settle", metavar="YYYY-MM-DD",
                    help="run the after-close block for a past day (actuals from the ledger's bars, replay, "
                         "report, session count) — for a day the hard-stop block never ran, e.g. the Mac slept")
    ap.add_argument("--rehearsal", type=int, metavar="MINUTES", default=0,
                    help="closed-market rehearsal: start the desk and the runner (forced LOG_ONLY) "
                         "for this many minutes, then stop. Not counted as a session; no probes.")
    args = ap.parse_args(argv)
    if not args.dry_run and not args.settle:
        held, other = day_lock()
        if held is None:
            warn(f"a trading day is already running on this ledger (day.py pid {other}) — "
                 f"nothing started, nothing touched")
            note("it is most likely the 06:55 launchd job. Watch it with:")
            note("  tail -f ~/Library/Logs/day-trading-bot/day.out.log")
            note("to stop it deliberately:  kill -INT " + other)
            return 0
        args._day_lock = held           # held for the life of this process
    # The scheduled day cannot take a flag. A file the owner creates the
    # evening before stands in for --probe-orders, once: it is consumed here
    # so the probe cannot run on a day nobody asked for it.
    if not args.probe_orders and PROBE_ONCE.exists():
        args.probe_orders = True
        PROBE_ONCE.unlink()
        note(f"stop probe: ON for today — {PROBE_ONCE.name} found and removed")

    now = datetime.now(ET)
    today = now.date().isoformat()
    conn = L.connect(DB)
    st = L.get_state(conn)
    risk = args.risk or st.get("dollar_risk") or 20.0
    mode = mode_for(st)
    try:                     # pin what ran: rules hash and code commit, in the ledger
        from momentum_platform import desk_profile as DP
        L.set_state(conn, rules_hash=DP.fingerprint().get("hash"), code_commit=DP.build_commit())
    except Exception:        # noqa: BLE001
        pass
    say(f"\n{BOLD}Trading day {today} · {now:%H:%M ET}{END}  phase {st['phase']} · {mode} · ${risk:g} risk · {DB}")
    if args.settle:
        say(f"\n{BOLD}Settling {args.settle}{END}")
        after_close(conn, args.settle, args.dry_run)
        return 0
    closed = why_closed(now.date())
    if args.rehearsal:
        # The only way to exercise the desk → ledger → runner chain against
        # the real Gateway on a day the market is shut. Everything will read
        # STALE, nothing will arm, nothing is sent, nothing is counted.
        mode = "LOG_ONLY"
        warn(f"REHEARSAL for {args.rehearsal} min — {closed or 'market open'} · forced LOG_ONLY · not a session")
    elif closed:
        warn(f"{closed} — the market is closed; nothing to do")
        note("2026-09-07 taught this: the chain ran all morning on Labor Day, feed STALE, nothing said why.")
        return 0
    if not args.rehearsal and now.time() >= HARD_STOP:
        after_close(conn, today, args.dry_run); return 0
    if not args.rehearsal and now.time() < PREMARKET_OPEN and not args.early:
        # One login only (docs/day-runbook.md): the paper GATEWAY is up, TWS
        # stays logged out. The old text said "start TWS and the Gateway",
        # which is the 10197 competing-session trap this desk moved away from.
        warn(f"before {PREMARKET_OPEN:%H:%M} ET — Gateway up on paper, TWS logged out; "
             f"run this again at {PREMARKET_OPEN:%H:%M}, or pass --early to start now"); return 0
    if args.early and now.time() < PREMARKET_OPEN:
        warn(f"starting early at {now:%H:%M} ET — the tape before 07:00 is thin, phase {L.get_state(conn).get('phase', 'A')} "
             f"refuses pre-market entries anyway, and the {PREMARKET_OPEN:%H:%M} scheduled start will be refused by the lock")

    say(f"\n{BOLD}1. Watchlist{END}  (gap scan — STAR then WATCH; rejects named)")
    rows: list[dict] = []          # the gap scan's rows; empty when --symbols bypasses it
    if args.symbols:
        symbols, rejects = [s.strip().upper() for s in args.symbols.split(",") if s.strip()], []
    else:
        rows = gap_scan(args.dry_run)
        symbols, rejects = pick_watchlist(rows)
    for sym, why in rejects:
        note(f"✗ {sym:<6} {why}")
    if rows and not args.dry_run:
        n = write_float_overrides(rows, today)
        # R1 before the desk: every scan row, survivor or reject, into the ledger.
        L.record_candidates(conn, datetime.now(timezone.utc), "gap_scan", rows)
        note(f"{n} finviz float(s) handed to the desk (data/float_overrides.json)")
    if symbols:
        good(f"{len(symbols)} names: {' '.join(symbols)}")
    else:
        warn("gap scan returned nothing — the desk's own scanner picks (start.sh --ibkr behaviour)")

    say(f"\n{BOLD}2. Probes{END}  (once per day)")
    if args.rehearsal:
        note("skipped in a rehearsal")
    else:
        run_alignment_once(conn, today, args.dry_run)
        if not args.dry_run and L.get_state(conn).get("paper_data") == "competing":
            # 9 September 2026: TWS was logged in, IBKR refused the paper session
            # every quote (10197), and the desk would have run a whole morning
            # on no data. A competing login is a stop, not a warning.
            bad("TWS is logged in — IBKR gives the market data to that session, not to the paper one")
            note("log OUT of TWS (keep the Gateway on the paper account), then run this command again")
            return 1
    # The stop probe needs 07:00-09:30 and this command starts at 06:55, so it
    # is deferred to the main loop below rather than run here and refused.
    # The first Monday run did exactly that: exit 6 at 06:55, no verdict.
    if args.rehearsal:
        pass
    elif not args.probe_orders:
        note("stop probe: OFF — it places an order; pass --probe-orders to run it once, deliberately")
    elif now.time() >= REGULAR_START:
        note("past 09:30 — the stop probe only runs pre-market")
    else:
        note("stop probe: deferred to 07:00")
    ok, why = premarket_allowed(L.get_state(conn))
    (good if ok else note)(f"pre-market entries: {'ON' if ok else 'off'} — {why}")

    say(f"\n{BOLD}3. Desk + runner{END}")
    port, how = ibkr_port()
    note(f"IBKR data port {port} ({how}) · ledger {DB}")
    desk = start_desk(symbols, args.dry_run)
    if not args.dry_run and not desk_is_on_ibkr(desk):
        bad("the desk did not come up on IBKR — stopping the day")
        note(f"Gateway logged in on the paper account? API enabled on port {port}? "
             "Set IBKR_PORT to force a port")
        note("'reqHistoricalData: Timeout' lines above = IBKR's history farm is slow; run the command again")
        if desk and desk.poll() is None:
            desk.send_signal(signal.SIGINT)
        return 1
    runner = start_runner(mode, risk, args.dry_run)
    if args.dry_run:
        say(f"\n{DIM}dry run — nothing started{END}"); return 0

    restarts = 0

    def stop(*_):
        for p in (runner, desk):
            if p and p.poll() is None:
                p.send_signal(signal.SIGINT)
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)

    deadline = (datetime.now(ET) + timedelta(minutes=args.rehearsal)) if args.rehearsal else None
    say(f"{DIM}running until {deadline:%H:%M} ET (rehearsal); Ctrl-C stops both{END}" if deadline
        else f"{DIM}running until {HARD_STOP:%H:%M} ET; Ctrl-C stops both{END}")
    from execution.intent import PREMARKET_START
    while (datetime.now(ET) < deadline) if deadline else (datetime.now(ET).time() < HARD_STOP):
        t = datetime.now(ET).time()
        if (not args.rehearsal and PREMARKET_START <= t < REGULAR_START
                and args.probe_orders
                and L.get_state(conn).get("probe_date") != today):
            say(f"\n{BOLD}Pre-market stop probe{END}  ({t:%H:%M} ET)")
            run_probe_once(conn, today, False)
        if desk and desk.poll() is not None:
            bad(f"desk exited with {desk.returncode} — stopping the day")
            stop(); return 1
        if runner and runner.poll() is not None:
            # The runner is the actor; the desk is the recorder. A dead runner
            # must not take the recorder down with it (audit 2026-09-08).
            restarts += 1
            if restarts > 5:
                bad(f"runner exited {restarts} times — stopping the day"); stop(); return 1
            warn(f"runner exited with {runner.returncode} — restarting ({restarts}/5); the desk keeps recording")
            runner = start_runner(mode, risk, False)
        time.sleep(15)
    if args.rehearsal:
        stop()
        for p in (runner, desk):
            if p:
                try: p.wait(timeout=30)
                except subprocess.TimeoutExpired: p.kill()
        f = L.funnel(conn)
        say(f"\n{BOLD}Rehearsal result{END}")
        good(f"desk and runner ran for {args.rehearsal} min against port {os.environ.get('IBKR_PORT', '7496')}")
        good(f"ledger: {f['board_rows']} board rows · {f['plans_armed']} plans · {f['plans_suppressed']} suppressed")
        note("everything STALE and nothing armed is the correct result on a closed market")
        note("not counted as a session")
        return 0
    # give the runner its hard-stop flatten (TRADE mode) before closing it
    time.sleep(90)
    stop()
    for p in (runner, desk):
        if p:
            try: p.wait(timeout=30)
            except subprocess.TimeoutExpired: p.kill()
    after_close(conn, today, False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
