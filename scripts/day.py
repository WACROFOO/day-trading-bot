#!/usr/bin/env python3
"""One command for the trading day. Ross's morning, automated.

    python3 scripts/day.py                 # do whatever this moment of the day needs
    python3 scripts/day.py --dry-run       # say what it would do, touch nothing
    python3 scripts/day.py --restart-desk  # the running desk, again, on the code on disk

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
  any other time  the desk alone (owner, 2026-10-08: the platform whenever the
                  command runs): after the day, before 06:55, on closed days.
                  No runner, and the desk writes nothing to the exercise
                  ledger. It stays up until Ctrl-C; at the next trading day's
                  06:55 this run starts that day as the scheduled job would
                  (network, pull) — in the background, logging to the job's
                  log, when it was started from a terminal.

What this file does NOT do, on purpose:
  - log in to TWS or the Gateway (2FA; a human does that, once, before 06:55)
  - move the exercise between phases — `exercise.py advance` checks the
    pre-registration gates and a human runs it
  - decide anything about a trade. The cascade, the detector and the runner
    decide; this file only starts them and reads the clock
"""

from __future__ import annotations

import argparse
from typing import Optional
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
PROBE_ONCE = ROOT / "data" / "probe-orders.once"    # touch it the evening before; consumed when a day starts
# The desk outside the bot's day (owner, 2026-10-08). The bot's window is unchanged.
RUNNER_FLATTEN_S = 90          # the runner's hard-stop flatten, given before it is stopped
RECORD_SETTLE_S = 60           # a desk build begun before its recording cutoff has ended inside this
FORCED_PORT = (os.environ.get("IBKR_PORT") or "").strip()   # as launched; a detected port is not carried over

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
        if f["taken"] < 30 and not state.get("phase_c_opened_by"):
            blockers.append(f"phase B needs 30 taken trades; have {f['taken']} "
                            f"(the owner may open phase C early: exercise.py open-phase-c --confirm)")
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
             f"session {st['sessions_done'] + (0 if st.get('last_session_date') == day else 1)} · "
             f"written {datetime.now(ET):%Y-%m-%d %H:%M ET}", ""]
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


def start_desk(symbols: list[str], dry: bool, record_until: Optional[str] = None):
    """The desk, on IBKR. `record_until` is when it stops writing to the
    exercise ledger (DESK_RECORD_UNTIL): an ISO instant for the bot's day,
    "0" for the desk alone, None for no cutoff (a rehearsal, stopped with it)."""
    cmd = [sys.executable, "-m", "momentum_platform.dashboard.server", "--host", "127.0.0.1",
           "--port", os.environ.get("DESK_PORT", "8787"), "--ibkr", ",".join(symbols),
           "--ibkr-required"]
    note("desk: " + " ".join(cmd))
    if record_until == "0":
        note("desk: writes nothing to the exercise ledger (DESK_RECORD_UNTIL=0)")
    elif record_until:
        note(f"desk: writes to the exercise ledger until {datetime.fromisoformat(record_until):%H:%M:%S} ET")
    if dry:
        return None
    try:
        RESTART_MARK.unlink()           # a restart asked of a desk that no longer runs is void
    except OSError:
        pass
    env = {**os.environ, "JOURNAL_DB": str(DB), "PYTHONPATH": str(ROOT / "src")}
    env.pop("DESK_RECORD_UNTIL", None)
    if record_until is not None:
        env["DESK_RECORD_UNTIL"] = record_until
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
                rec = h.get("provider", {}).get("recordUntil")
                if rec is not None and rec.startswith("1970"):
                    note("it writes nothing to the exercise ledger — your calls and your risk are saved")
                elif rec is not None:
                    note(f"it writes to the exercise ledger until {datetime.fromisoformat(rec):%H:%M:%S} ET")
                return True
        except Exception:                                 # noqa: BLE001
            pass
        time.sleep(3)
    return False


def wait_for_gateway(host: str, port: str, timeout_s: float, sleep=time.sleep,
                     connect=None) -> bool:
    """True once the IBKR API port accepts a TCP connect, polling every 15 s
    up to `timeout_s`; False when it never does. The Gateway restarts itself
    after a lost link (2026-09-24, ~07:15: port 4002 refused for minutes, then
    the paper disclaimer waited for a click) — the day waits for it instead of
    ending."""
    import socket
    connect = connect or socket.create_connection
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            with connect((host, int(port)), timeout=2):
                return True
        except OSError:
            pass
        if time.monotonic() >= deadline:
            return False
        sleep(15)


DESK_RESTARTS_MAX = 5
GATEWAY_WAIT_S = 20 * 60
STOP = {"requested": False}       # set by the SIGINT handler; read by the day loop


def keep_awake(dry: bool):
    """macOS: hold an idle/system/display sleep assertion for the life of this
    process (`caffeinate -dims -w PID`). The IBKR link dropped every few
    minutes on 2026-09-25 when the laptop lost its network; a Mac that naps
    also drops Wi-Fi. This removes the sleep half of that. Elsewhere, or when
    caffeinate is missing, nothing happens."""
    if dry or sys.platform != "darwin":
        return None
    try:
        p = subprocess.Popen(["caffeinate", "-dims", "-w", str(os.getpid())],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        note("keeping the Mac awake until the day ends (caffeinate)")
        return p
    except OSError:
        return None


def start_runner(mode: str, risk: float, dry: bool, account: float | None = None):
    cmd = [sys.executable, "-u", "scripts/exercise.py", "--db", str(DB), "live", "--risk", str(risk)]
    if account:
        cmd += ["--account", str(account)]
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
    export_day(conn, today)


def settled(conn, day: str) -> bool:
    """The after-close block already ran for `day`: its report is written and
    no decision of the day waits for a grade. A relaunch after the day — the
    normal way back to the desk since 2026-10-08 — does not settle it again
    (a second run rewrote the report and pushed a new export each time)."""
    if not (REPORTS / f"{day}.md").exists():
        return False
    row = conn.execute("""SELECT COUNT(*) FROM decisions d LEFT JOIN actuals a USING(decision_id)
                          WHERE substr(d.ts_et,1,10)=? AND a.decision_id IS NULL""", (day,)).fetchone()
    return row[0] == 0


def _settle(conn, day: str, dry: bool) -> None:
    """The after-close block, where a desk goes on after it: a failure is said
    with its command and never takes the platform down (the next start settles
    a day it finds ungraded)."""
    try:
        after_close(conn, day, dry)
    except Exception as exc:                          # noqa: BLE001
        bad(f"the after-close block failed ({exc!r}) — settle by hand: python3 scripts/day.py --settle {day}")


def export_day(conn, day: str) -> None:
    """The daily learning loop (owner, 2026-10-06): the day's ledger and log go to
    the repo; the cloud review reads them after the close and writes the day's
    review. A failure here never touches the trading day — it is said, with the
    command."""
    hand = f"python3 scripts/day_export.py --day {day} --push"
    try:
        import day_export
        db_file = conn.execute("PRAGMA database_list").fetchone()[2] or ""
        if not db_file or Path(db_file).resolve() != DB.resolve() or os.environ.get("DAY_EXPORT", "1") != "1":
            # A test's ledger, a replay, or switched off: never ship it to the repo
            # (2026-10-06: the suite pushed four fixture days before this guard).
            note("daily export skipped: not the day's ledger")
            return
        meta = day_export.export(conn, day, day_export.OUT_ROOT / day)
        good(f"export: research/daily/{day} · " + " · ".join(f"{k} {v}" for k, v in meta["counts"].items()))
        if os.environ.get("DAY_EXPORT_PUSH", "1") == "1":
            if day_export.push(day):
                good("export pushed for the daily review")
            else:
                warn(f"export NOT pushed — run by hand: {hand}")
    except Exception as exc:                          # noqa: BLE001
        warn(f"daily export failed ({exc!r}) — run by hand: {hand}")


def _backfill(day: str) -> Optional[int]:
    """Best effort: the minute bars IBKR has for `day`, read-only, so the
    grading of a day the desk did not finish sees the whole tape and not just
    the bars recorded before it died. Returns the script's exit code, or None
    when it could not run. Never raises."""
    try:
        import backfill_tape
        os.environ.setdefault("JOURNAL_DB", str(DB))
        return backfill_tape.main([day])
    except Exception as exc:                          # noqa: BLE001
        note(f"backfill skipped: {exc!r}")
        return None


def settle_unsettled(conn, today: str, dry: bool) -> Optional[str]:
    """A previous day whose after-close block never ran.

    2026-09-24: the Gateway lost IBKR at 10:40, the desk went OFFLINE and the
    day command exited before 11:30, so nothing graded the day's decisions,
    the report was not written and the session was not counted. `missed`
    showed dashes on every row that evening. Now, at the next start, the most
    recent earlier day with ungraded decisions is settled first: its bars are
    completed from IBKR when the Gateway answers, then the normal after-close
    block runs for THAT day. Idempotent — a day already counted is not
    counted twice — and never for today."""
    row = conn.execute("""SELECT substr(d.ts_et, 1, 10) AS day, COUNT(*) AS n,
                                 SUM(a.decision_id IS NULL) AS ungraded
                          FROM decisions d LEFT JOIN actuals a USING(decision_id)
                          WHERE substr(d.ts_et, 1, 10) < ?
                          GROUP BY day ORDER BY day DESC LIMIT 1""", (today,)).fetchone()
    if row is None or not row["ungraded"]:
        return None
    day = row["day"]
    warn(f"{day} was never settled: {row['ungraded']} of {row['n']} decision(s) ungraded — "
         f"the after-close block did not run (the desk stopped before 11:30). Settling it now.")
    if dry:
        note("dry run — would fetch the day's bars from IBKR and run the after-close block for it")
        return day
    port, how = ibkr_port()
    note(f"completing {day}'s tape from IBKR on port {port} ({how}), read-only, then grading")
    _backfill(day)
    after_close(conn, day, dry)
    return day


DAY_LOCK = Path(str(DB) + ".day.lock")


def day_lock(path: Path = DAY_LOCK):
    """One day per ledger. Returns the held lock file, or None if another
    day.py holds it — with that process's pid written inside.

    2026-09-21: the 06:55 launchd job was running; two manual starts at 07:04
    and 07:05 connected as IBKR client 27 on top of it. IBKR answered 326 to
    the newcomer — and the running desk's socket dropped ("socket dropped",
    four connect failures, reconnect gen 2 in its health log). A second copy
    is not merely refused, it can knock the live one offline. So the second
    copy must never reach the Gateway at all.

    A run that starts the next trading day in place (`rollover`) hands its
    held descriptor across the exec in DAY_LOCK_FD: the lock is never let go,
    so the 06:55 scheduled start cannot slip in between."""
    import fcntl
    inherited = os.environ.pop("DAY_LOCK_FD", None)
    if inherited:
        try:
            fd = os.fdopen(int(inherited), "a+")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)      # already ours: the same open file
            os.set_inheritable(fd.fileno(), False)
            fd.seek(0); fd.truncate(); fd.write(str(os.getpid())); fd.flush()
            return fd, None
        except (OSError, ValueError):
            pass
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


# ------------------------------------------------- the platform at any hour
# Owner, 2026-10-08: "make the platform available whenever I launch the
# command; don't limit it to the window." The desk comes up at any hour and on
# closed days and stays up until Ctrl-C. The BOT keeps its window: the runner
# runs 06:55-11:30 ET as before, and a desk outside that window writes nothing
# to the exercise ledger, so the report, the replay check and settle measure
# exactly what they measured when the desk stopped with the runner.

RESTART_MARK = Path(str(DB) + ".desk.restart")
# The scheduled job's log (scripts/install_daily.sh). A day this command starts
# in the background writes there too: the daily export reads the day from it.
LOG_DIR = Path.home() / "Library" / "Logs" / "day-trading-bot"


def desk_url() -> str:
    return f"http://127.0.0.1:{os.environ.get('DESK_PORT', '8787')}/"


def record_until(day) -> str:
    """When the day's desk stops writing to the exercise ledger: the hard stop
    plus the runner's flatten, the moment this command used to stop the desk
    together with the runner. "close" in every control series is the last bar
    the desk wrote (journal/controls.py), so it keeps the meaning it had."""
    return (datetime.combine(day, HARD_STOP, tzinfo=ET) + timedelta(seconds=RUNNER_FLATTEN_S)).isoformat()


def next_day_start(now: datetime) -> datetime:
    """The first 06:55 ET of a trading day strictly after `now`."""
    d = now.date()
    for _ in range(15):                    # bounded: a calendar that closes every day must not hang
        start = datetime.combine(d, PREMARKET_OPEN, tzinfo=ET)
        if start > now and not why_closed(d):
            return start
        d += timedelta(days=1)
    return datetime.combine(now.date() + timedelta(days=1), PREMARKET_OPEN, tzinfo=ET)


def _left(until: datetime) -> float:
    """Seconds from now to `until`, never negative."""
    return max(0.0, (until - datetime.now(ET)).total_seconds())


def desk_only_symbols(conn, args) -> list[str]:
    """Names for the desk outside the bot's day: --symbols, else the last board
    the day's desk recorded, else none (the desk's own scanner picks)."""
    if args.symbols:
        return [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    try:
        rows = conn.execute("SELECT DISTINCT symbol FROM board_snapshots WHERE ts_et = "
                            "(SELECT MAX(ts_et) FROM board_snapshots) ORDER BY symbol").fetchall()
    except Exception:                                 # noqa: BLE001 — a ledger from before the table
        rows = []
    return [r[0] for r in rows]


def desk_health(timeout: float = 3.0) -> Optional[dict]:
    import urllib.request
    try:
        with urllib.request.urlopen(desk_url() + "api/v1/health", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:                                 # noqa: BLE001
        return None


def desk_up(h: Optional[dict]) -> bool:
    """A desk live on IBKR, by its health — the test `desk_is_on_ibkr` waits for."""
    return bool(h) and h.get("mode") == "live" and bool(h.get("streaming"))


def _git(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, timeout=120)


def desk_staleness(h: dict) -> Optional[str]:
    """Why the running desk is on older code than this checkout, or None.

    The page's files are read from disk on every load; the desk's Python is
    what it started on (2026-10-08: an updated page on an old desk showed no
    tape and no news). `codeAtStart` is the commit the desk started on."""
    code = h.get("codeAtStart")
    if not code:
        return "it started before this check existed"
    why = []
    try:
        from momentum_platform.dashboard.server import app_build
        page = app_build()
    except Exception:                                 # noqa: BLE001
        page = None
    if page and h.get("appBuildAtStart") and h["appBuildAtStart"] != page:
        why.append(f"page {h['appBuildAtStart']}, now {page}")
    try:
        head = _git("rev-parse", "--short", "HEAD").stdout.strip()
        if head and head != code and _git("diff", "--quiet", code, head, "--", "src").returncode == 1:
            why.append(f"src/ changed since {code} (now {head})")
    except Exception:                                 # noqa: BLE001
        pass
    return "; ".join(why) or None


def open_page(url: str, args) -> None:
    """The page in the browser, for a run started by hand — never for the
    scheduled one (no terminal), and not with --no-open."""
    if getattr(args, "no_open", False) or not sys.stdout.isatty():
        return
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:                                 # noqa: BLE001
        pass


def report_running(other: str, args) -> int:
    """A second launch while a day runs. Nothing starts — a second desk on
    client 27 knocks the first one offline (2026-09-21) — but the platform is
    one link away, and a desk on older code is named, with its fix."""
    warn(f"a trading day is already running on this ledger (day.py pid {other}) — "
         f"nothing started, nothing touched")
    url = desk_url()
    h = desk_health()
    if h is None:
        note(f"its desk does not answer at {url} yet — starting, or waiting for the Gateway")
    else:
        good(f"the platform is up: {url}  (feed {(h.get('provider') or {}).get('state', '?')})")
        why = desk_staleness(h)
        if why:
            warn(f"that desk runs older code than this checkout — {why}")
            if (h.get("provider") or {}).get("recording") is False:
                # Nothing records: the bot's window is closed (desk alone, or
                # after the day), so a restart costs the exercise nothing.
                # scripts/go.sh relies on it: update, then this (2026-10-09).
                note("it records nothing — the bot is not trading — so it restarts on this code now")
                restart_desk()
            else:
                note("restart it on this code (the bot keeps running):  python3 scripts/day.py --restart-desk")
        open_page(url, args)
    note("its output: the terminal that started it — or, for the scheduled 06:55 job and a day this")
    note("command started in the background:  tail -f ~/Library/Logs/day-trading-bot/day.out.log")
    note("to stop it deliberately:  kill -INT " + other)
    return 0


DESK_CMD_RE = r"momentum_platform.dashboard.server --host 127.0.0.1 --port {port} --ibkr .*--ibkr-required"


def find_desk_pids(run=subprocess.run) -> list[int]:
    """The desk this command started on DESK_PORT, by its command line — so a
    day.py from before this function is found too, and a desk from
    scripts/start.sh (no --ibkr-required) is not."""
    port = os.environ.get("DESK_PORT", "8787")
    try:
        out = run(["pgrep", "-f", DESK_CMD_RE.format(port=port)],
                  capture_output=True, text=True, timeout=10).stdout
    except Exception:                                 # noqa: BLE001 — no pgrep
        return []
    return [int(x) for x in out.split() if x.isdigit() and int(x) != os.getpid()]


def code_imports(run=subprocess.run) -> Optional[str]:
    """None when the desk's code on disk imports; else its error's last line.
    A restart onto code that cannot start would leave the day without a desk."""
    try:
        r = run([sys.executable, "-c", "import momentum_platform.dashboard.server, "
                 "momentum_platform.dashboard.ibkr_desk"], cwd=ROOT, capture_output=True, text=True,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, timeout=120)
    except Exception as exc:                          # noqa: BLE001
        return repr(exc)
    if r.returncode == 0:
        return None
    lines = (r.stderr or r.stdout or "").strip().splitlines()
    return lines[-1] if lines else f"exit {r.returncode}"


def restart_desk(kill=os.kill, find=find_desk_pids, health=desk_health, sleep=time.sleep,
                 imports=code_imports, wait_s: float = 420.0) -> int:
    """--restart-desk: stop the running desk; the day.py that started it starts
    it again on the code now on disk. The runner is its own process and is not
    touched. Refused when no day.py runs (nothing would start it again), while
    the desk is still coming up (the day would read that as a desk that failed
    to start), and when the code on disk does not import."""
    held, other = day_lock(DAY_LOCK)
    if held is not None:
        held.close()
        warn("no trading day is running on this ledger — nothing to restart. Bring the platform up with:")
        note("  python3 scripts/day.py")
        return 1
    if not desk_up(health()):
        warn(f"the desk at {desk_url()} is not up yet (starting, or waiting for the Gateway) — a restart "
             f"now could cost the day its desk; run this again once the page loads")
        return 1
    broken = imports()
    if broken:
        bad(f"the code on disk does not import ({broken}) — the running desk is left alone")
        return 1
    pids = find()
    if not pids:
        warn(f"day.py pid {other} runs, but no desk of it answers on {desk_url()} — "
             "it may be between restarts; watch its log")
        return 1
    RESTART_MARK.write_text(datetime.now(timezone.utc).isoformat())
    for pid in pids:
        kill(pid, signal.SIGINT)
    good(f"desk pid {' '.join(map(str, pids))} stopped — day.py pid {other} starts it again on this "
         f"checkout's code; the runner keeps running")
    head = _git("rev-parse", "--short", "HEAD").stdout.strip()
    deadline = time.monotonic() + wait_s
    try:
        while time.monotonic() < deadline:
            sleep(5)
            h = health()
            if desk_up(h) and "codeAtStart" in h and (not head or h["codeAtStart"] == head):
                good(f"the desk is back on {h['codeAtStart'] or 'this checkout'}: {desk_url()} — reload the page")
                return 0
    except KeyboardInterrupt:
        return 0
    warn(f"the desk is not back after {wait_s / 60:.0f} min — watch the day's log")
    return 1


def restart_asked(max_age_s: float = 300.0) -> bool:
    """A --restart-desk in the last five minutes, consumed. The desk's exit is
    then a restart, not an outage: not counted, no Gateway warning."""
    try:
        age = time.time() - RESTART_MARK.stat().st_mtime
        RESTART_MARK.unlink()
    except OSError:
        return False
    return age <= max_age_s


def _nap(seconds: float) -> None:
    """Sleep, waking within a second of a Ctrl-C."""
    end = time.monotonic() + seconds
    while not STOP["requested"] and time.monotonic() < end:
        time.sleep(min(1.0, max(0.0, end - time.monotonic())))


def _stop_proc(p) -> None:
    if p is None:
        return
    if p.poll() is None:
        p.send_signal(signal.SIGINT)
    try:
        p.wait(timeout=30)
    except subprocess.TimeoutExpired:
        p.kill()
        try:
            p.wait(timeout=10)                        # reaped: no zombie carried across the exec
        except subprocess.TimeoutExpired:
            pass


def _gateway_up(until: datetime) -> bool:
    """The desk alone waits for an IBKR API port with no time limit: the next
    trading day's start or Ctrl-C ends the wait. True once one answers."""
    host = os.environ.get("IBKR_HOST", "127.0.0.1")
    told = False
    while not STOP["requested"] and datetime.now(ET) < until:
        if not FORCED_PORT:
            os.environ.pop("IBKR_PORT", None)
        port, _how = ibkr_port()
        if wait_for_gateway(host, port, 0):
            return True
        if not told:
            warn(f"no IBKR API port answers (tried {port}) — the desk starts when the Gateway does "
                 f"(paper account, TWS logged out)")
            told = True
        _nap(15)
    return False


def _calls_mark(conn, day: Optional[str]) -> Optional[int]:
    """The newest of your calls of `day` (manual_decisions is append-only)."""
    if not day:
        return None
    try:
        return conn.execute("SELECT COALESCE(MAX(id), 0) FROM manual_decisions WHERE substr(ts_et,1,10)=?",
                            (day,)).fetchone()[0]
    except Exception:                                 # noqa: BLE001 — a ledger from before the table
        return None


class LateCalls:
    """Calls you log after the day's export (about 11:32 ET) go out too: the
    day is exported again ten minutes after the newest call, and when the
    desk-only run ends for whatever is left."""
    QUIET_S = 600.0

    def __init__(self, conn, day: Optional[str]):
        self.conn, self.day = conn, day
        self.sent = self.seen = _calls_mark(conn, day)
        self.since: Optional[float] = None

    def check(self, final: bool = False) -> None:
        if self.sent is None:
            return
        mark = _calls_mark(self.conn, self.day)
        if mark != self.seen:
            self.seen, self.since = mark, time.monotonic()
        if mark == self.sent:
            return
        if final or (self.since is not None and time.monotonic() - self.since >= self.QUIET_S):
            note(f"you logged calls on {self.day} after its export — exporting the day again")
            export_day(self.conn, self.day)
            self.sent = mark


def wait_for_network(host: str = "github.com", tries: int = 12, nap=None) -> bool:
    """What the scheduled job does first (scripts/install_daily.sh): up to two
    minutes for DNS. 2026-09-09: a Mac awake at 06:55 had none for a while,
    and the gap scan and the probes failed."""
    import socket
    for i in range(tries):
        try:
            socket.getaddrinfo(host, 443)
            return True
        except OSError:
            if STOP["requested"]:
                return False
            if i + 1 < tries:
                (nap or _nap)(10)
    return False


def pull_code(run=subprocess.run) -> bool:
    """The scheduled job's pull before each day: the branch, once; when it
    fails, the day runs on what is on disk."""
    try:
        branch = run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                     capture_output=True, text=True, timeout=30).stdout.strip()
        ok = run(["git", "-C", str(ROOT), "pull", "-q", "origin", branch],
                 capture_output=True, text=True, timeout=120).returncode == 0
    except Exception:                                 # noqa: BLE001 — a hung or missing git
        branch, ok = "the branch", False
    if ok:
        good(f"pulled {branch}")
    else:
        warn("pull failed — running what is on disk")
    return ok


def _has_terminal() -> bool:
    """A controlling terminal: a run started by hand. The scheduled job has none."""
    try:
        with open("/dev/tty"):
            return True
    except OSError:
        return False


def rollover(args, execv=None, spawn=None, network=wait_for_network, pull=pull_code,
             before=None, terminal=None) -> int:
    """Start the next trading day as the scheduled job would: the network, any
    late calls, the pull, then the day — with the lock held throughout, so the
    06:55 job finds it and steps aside.

    From the scheduled job (no terminal) the day replaces this process: same
    pid, same log, the lock crossing the exec as an inherited descriptor. From
    a terminal it starts in the background in its own session, its output in
    the scheduled job's log, and this command ends: a closed window would
    otherwise end the day mid-session (SIGHUP), and the daily export reads the
    day's lines from that log. The flags of this launch (--symbols, --early,
    --probe-orders) do not carry over."""
    held = getattr(args, "_day_lock", None)
    if held is None:
        return 0
    say(f"\n{BOLD}Next trading day{END}  {datetime.now(ET):%a %d %b %H:%M} ET")
    if not network():
        warn("no network after 2 min — the day starts on what is on disk")
    if before is not None:
        before()
    if not STOP["requested"]:
        pull()
    if STOP["requested"]:
        say("stopped by Ctrl-C before the day started — the same command starts it")
        return 0
    fd = held.fileno()
    os.environ["DAY_LOCK_FD"] = str(fd)
    if not FORCED_PORT:
        os.environ.pop("IBKR_PORT", None)
    argv = [sys.executable, str(Path(__file__).resolve()), "--no-open"]
    try:
        if terminal if terminal is not None else _has_terminal():
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_DIR / "day.out.log", "a") as out, open(LOG_DIR / "day.err.log", "a") as err:
                p = (spawn or subprocess.Popen)(argv, cwd=ROOT, env={**os.environ}, stdin=subprocess.DEVNULL,
                                                stdout=out, stderr=err, start_new_session=True, pass_fds=(fd,))
            good(f"the day runs in the background as pid {p.pid}, as the scheduled job would; "
                 f"the desk comes back at {desk_url()}")
            note(f"its log:  tail -f {LOG_DIR / 'day.out.log'}")
            note(f"to stop it:  kill -INT {p.pid}")
            return 0
        os.set_inheritable(fd, True)
        sys.stdout.flush(); sys.stderr.flush()
        (execv or os.execv)(sys.executable, argv)
    except OSError as exc:
        bad(f"could not start the next day ({exc}) — run: python3 scripts/day.py")
        return 1
    finally:
        os.environ.pop("DAY_LOCK_FD", None)       # only the next day's process may adopt it
    return 0                                          # reached only with a test's execv


def desk_only(args, conn, why: str, desk=None, symbols: Optional[list] = None,
              day: Optional[str] = None) -> int:
    """The desk alone, until the next trading day's 06:55 ET or Ctrl-C.

    No runner, and the desk writes nothing to the exercise ledger
    (DESK_RECORD_UNTIL=0); your calls and your risk are saved as at any other
    time. `desk` is the day's own desk when the day just ended: it carries on,
    past its recording cutoff, and is replaced only if it exits. At the next
    trading day's start this same run starts that day, holding the lock
    throughout, so an evening launch never costs the morning its start."""
    until = next_day_start(datetime.now(ET))
    say(f"\n{BOLD}Desk only{END}  ({why}) — the bot does not trade; nothing goes into the exercise ledger")
    note(f"until {until:%a %d %b %H:%M} ET, when this run starts that trading day · Ctrl-C stops it")
    if symbols is None:
        symbols = desk_only_symbols(conn, args)
    fresh = desk is None or desk.poll() is not None
    if fresh:
        if not args.dry_run:
            port, how = ibkr_port()                   # the desk reads IBKR_PORT; 7496 when unset
            note(f"IBKR data port {port} ({how})")
        desk = start_desk(symbols, args.dry_run, record_until="0")
        if desk is None:                              # a dry run, or a test's stub
            if args.dry_run:
                say(f"\n{DIM}dry run — nothing started{END}")
            return 0
    cur = {"desk": desk}

    def stop(*_):
        STOP["requested"] = True
        p = cur["desk"]
        if p and p.poll() is None:
            p.send_signal(signal.SIGINT)
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)
    # Every wait below ends by the next day's start: the morning is never late for the desk.
    if not fresh or desk_is_on_ibkr(desk, timeout_s=int(max(30, min(420, _left(until))))):
        good(f"the platform: {desk_url()}")
        if fresh:
            open_page(desk_url(), args)
    elif not STOP["requested"]:
        warn(f"the desk is not on IBKR yet — it is started again once the Gateway answers ({desk_url()})")
    late = LateCalls(conn, day)
    started, deaths = time.monotonic(), 0
    while True:
        if STOP["requested"]:
            _stop_proc(cur["desk"])
            late.check(final=True)
            say("stopped by Ctrl-C — the platform is down; the same command brings it back")
            return 0
        if datetime.now(ET) >= until:
            _stop_proc(cur["desk"])
            return rollover(args, before=lambda: late.check(final=True))
        late.check()
        p = cur["desk"]
        if p.poll() is not None:
            if restart_asked():
                deaths = 0
            else:
                # Not in a tight loop: a desk that keeps dying waits 1, 2, 4 ... 15 min.
                deaths = deaths + 1 if time.monotonic() - started < 600 else 1
                wait = min(900, 30 * 2 ** deaths)
                warn(f"desk exited with {p.returncode} — starting it again in {wait // 60} min, "
                     f"once the Gateway answers")
                _nap(min(wait, _left(until)))
            if _gateway_up(until):
                cur["desk"] = start_desk(symbols, False, record_until="0")
                started = time.monotonic()
                if desk_is_on_ibkr(cur["desk"], timeout_s=int(max(30, min(420, _left(until))))):
                    good(f"the platform is back: {desk_url()}")
            continue
        _nap(min(15.0, _left(until)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--early", action="store_true",
                    help="start before 06:55 ET (owner's call, 2026-09-22); the 06:55 scheduled "
                         "start then finds the instance lock and steps aside")
    ap.add_argument("--risk", type=float, default=None, help="overrides exercise_state.dollar_risk")
    ap.add_argument("--account", type=float, default=None,
                    help="real account size in $; caps every position's value (default: exercise_state.account_size)")
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
    ap.add_argument("--restart-desk", action="store_true",
                    help="stop the running day's desk so that day starts it again on the code now on "
                         "disk (after scripts/update.sh); the runner is not touched")
    ap.add_argument("--no-open", action="store_true", help="do not open the page in the browser")
    args = ap.parse_args(argv)
    if args.restart_desk:
        return restart_desk()
    if not args.dry_run and not args.settle:
        held, other = day_lock(DAY_LOCK)
        if held is None:
            return report_running(other, args)
        args._day_lock = held           # held for the life of this process

    now = datetime.now(ET)
    today = now.date().isoformat()
    conn = L.connect(DB)
    st = L.get_state(conn)
    risk = args.risk or st.get("dollar_risk") or 20.0
    account = args.account or st.get("account_size")
    acct_txt = f" · account ${account:,.0f}" if account else ""
    if args.risk or args.account:           # remembered for the next days
        L.set_state(conn, **({"dollar_risk": risk} if args.risk else {}), **({"account_size": account} if args.account else {}))
    mode = mode_for(st)
    try:                     # pin what ran: rules hash and code commit, in the ledger
        from momentum_platform import desk_profile as DP
        L.set_state(conn, rules_hash=DP.fingerprint().get("hash"), code_commit=DP.build_commit())
    except Exception:        # noqa: BLE001
        pass
    say(f"\n{BOLD}Trading day {today} · {now:%H:%M ET}{END}  phase {st['phase']} · {mode} · ${risk:g} risk{acct_txt} · {DB}")
    if args.settle:
        say(f"\n{BOLD}Settling {args.settle}{END}")
        after_close(conn, args.settle, args.dry_run)
        return 0
    if not args.rehearsal:
        try:
            settle_unsettled(conn, today, args.dry_run)
        except Exception as exc:                      # noqa: BLE001
            bad(f"settling an earlier day failed ({exc!r}) — the command goes on; settle it with --settle")
    closed = why_closed(now.date())
    if args.rehearsal:
        # The only way to exercise the desk → ledger → runner chain against
        # the real Gateway on a day the market is shut. Everything will read
        # STALE, nothing will arm, nothing is sent, nothing is counted.
        mode = "LOG_ONLY"
        warn(f"REHEARSAL for {args.rehearsal} min — {closed or 'market open'} · forced LOG_ONLY · not a session")
    elif closed:
        warn(f"{closed} — the market is closed; the bot does not run today")
        note("2026-09-07 taught this: the chain ran all morning on Labor Day, feed STALE, nothing said why.")
        return desk_only(args, conn, f"{closed}")
    if not args.rehearsal and now.time() >= HARD_STOP:
        if settled(conn, today):
            note(f"{today} is already settled — research/paper-exercise/reports/{today}.md")
        else:
            _settle(conn, today, args.dry_run)
        return desk_only(args, conn, "after the bot's day", day=today)
    if not args.rehearsal and now.time() < PREMARKET_OPEN and not args.early:
        # One login only (docs/day-runbook.md): the paper GATEWAY is up, TWS
        # stays logged out. The old text said "start TWS and the Gateway",
        # which is the 10197 competing-session trap this desk moved away from.
        warn(f"before {PREMARKET_OPEN:%H:%M} ET — Gateway up on paper, TWS logged out; the day starts at "
             f"{PREMARKET_OPEN:%H:%M} in this same run, or pass --early to start now")
        return desk_only(args, conn, "before the day")
    if args.early and now.time() < PREMARKET_OPEN:
        _ph = L.get_state(conn).get("phase", "A")
        warn(f"starting early at {now:%H:%M} ET — the tape before 07:00 is thin, entries before 07:00 are refused "
             f"(session window){' and phase ' + _ph + ' refuses pre-market entries anyway' if _ph != 'C' else ''}, "
             f"and the {PREMARKET_OPEN:%H:%M} scheduled start will be refused by the lock")

    # The scheduled day cannot take a flag. A file the owner creates the
    # evening before stands in for --probe-orders, once: it is consumed here,
    # when a day starts, so the probe cannot run on a day nobody asked for it
    # (and an evening launch of the desk alone does not use it up).
    if not args.probe_orders and not args.rehearsal and PROBE_ONCE.exists():
        args.probe_orders = True
        PROBE_ONCE.unlink()
        note(f"stop probe: ON for today — {PROBE_ONCE.name} found and removed")

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

    if not args.dry_run and not args.rehearsal:
        # 2026-09-25 05:49: the Gateway was not up yet, the probe and the desk
        # both failed and the day ended; the owner restarted it by hand a
        # minute later. Wait for the API port instead, up to GATEWAY_WAIT_S.
        port, how = ibkr_port()
        if how.startswith("nothing listening"):
            warn(f"no IBKR API port answers yet — waiting up to {GATEWAY_WAIT_S // 60} min for the Gateway "
                 f"(log it in on the PAPER account, TWS logged out)")
            if not wait_for_gateway(os.environ.get("IBKR_HOST", "127.0.0.1"), port, GATEWAY_WAIT_S):
                bad(f"the Gateway did not answer on {port} within {GATEWAY_WAIT_S // 60} min — stopping"); return 1
            os.environ.pop("IBKR_PORT", None)
            port, how = ibkr_port()
            good(f"Gateway answering on port {port} ({how})")
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
    # The day's desk writes to the exercise ledger until the moment the day
    # used to stop it; it stays up after that (owner, 2026-10-08).
    rec_until = None if args.rehearsal else record_until(now.date())
    desk = start_desk(symbols, args.dry_run, record_until=rec_until)
    if not args.dry_run and not desk_is_on_ibkr(desk):
        bad("the desk did not come up on IBKR — stopping the day")
        note(f"Gateway logged in on the paper account? API enabled on port {port}? "
             "Set IBKR_PORT to force a port")
        note("'reqHistoricalData: Timeout' lines above = IBKR's history farm is slow; run the command again")
        if desk and desk.poll() is None:
            desk.send_signal(signal.SIGINT)
        return 1
    runner = start_runner(mode, risk, args.dry_run, *([account] if account else []))
    awake = keep_awake(args.dry_run)
    if args.dry_run:
        say(f"\n{DIM}dry run — nothing started{END}"); return 0

    restarts = 0
    desk_restarts = 0
    STOP["requested"] = False

    def stop(*_):
        # A Ctrl-C is the owner ending the day. 2026-09-25: the desk-restart
        # logic read the resulting desk exit as an outage and started it again.
        STOP["requested"] = True
        for p in (runner, desk):
            if p and p.poll() is None:
                p.send_signal(signal.SIGINT)
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)

    deadline = (datetime.now(ET) + timedelta(minutes=args.rehearsal)) if args.rehearsal else None
    say(f"{DIM}running until {deadline:%H:%M} ET (rehearsal); Ctrl-C stops both{END}" if deadline
        else f"{DIM}the bot runs until {HARD_STOP:%H:%M} ET, the desk after it too; Ctrl-C stops both{END}")
    good(f"the platform: {desk_url()}")
    open_page(desk_url(), args)
    from execution.intent import PREMARKET_START
    while (datetime.now(ET) < deadline) if deadline else (datetime.now(ET).time() < HARD_STOP):
        if STOP["requested"]:
            warn("stopped by Ctrl-C — the day is not settled; the next start settles it")
            for p in (runner, desk):
                if p:
                    try: p.wait(timeout=30)
                    except subprocess.TimeoutExpired: p.kill()
            return 1
        t = datetime.now(ET).time()
        if (not args.rehearsal and PREMARKET_START <= t < REGULAR_START
                and args.probe_orders
                and L.get_state(conn).get("probe_date") != today):
            say(f"\n{BOLD}Pre-market stop probe{END}  ({t:%H:%M} ET)")
            run_probe_once(conn, today, False)
        if desk and desk.poll() is not None:
            # 2026-09-24: the Gateway lost IBKR twice (07:15, 10:40); the desk
            # exited and the day ended with it, blind until a human restarted it
            # 50 minutes later. The recorder is restarted once the Gateway's port
            # answers again; the runner keeps managing any open position meanwhile.
            asked = restart_asked()
            if asked:
                note("desk restarting on the code now on disk (--restart-desk); the runner keeps running")
            else:
                desk_restarts += 1
                if desk_restarts > DESK_RESTARTS_MAX:
                    bad(f"desk exited {desk_restarts} times — stopping the day"); stop(); return 1
                warn(f"desk exited with {desk.returncode} — waiting for the Gateway, then restarting "
                     f"({desk_restarts}/{DESK_RESTARTS_MAX}); the runner keeps watching any open position")
            port, how = ibkr_port()
            if not wait_for_gateway(os.environ.get("IBKR_HOST", "127.0.0.1"), port, GATEWAY_WAIT_S):
                bad(f"the Gateway on port {port} did not come back within {GATEWAY_WAIT_S // 60} min — stopping the day")
                note("if the Gateway shows the paper-trading disclaimer, click it, then run this command again")
                stop(); return 1
            desk = start_desk(symbols, False, record_until=rec_until)
            if not desk_is_on_ibkr(desk):
                if asked:
                    # The restart you asked for did not come up: from here it is an
                    # outage like any other — counted, retried — never the day's end.
                    warn("the restarted desk did not come up on IBKR — handled as an outage from here")
                    if desk.poll() is None:
                        desk.send_signal(signal.SIGINT)
                    continue
                bad("the desk did not come back up on IBKR — stopping the day"); stop(); return 1
            continue
        if runner and runner.poll() is not None:
            # The runner is the actor; the desk is the recorder. A dead runner
            # must not take the recorder down with it (audit 2026-09-08).
            restarts += 1
            if restarts > 5:
                bad(f"runner exited {restarts} times — stopping the day"); stop(); return 1
            warn(f"runner exited with {runner.returncode} — restarting ({restarts}/5); the desk keeps recording")
            runner = start_runner(mode, risk, False, *([account] if account else []))
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
    time.sleep(RUNNER_FLATTEN_S)
    _stop_proc(runner)
    if awake is not None:
        awake.terminate()               # the bot's day is over; the desk alone does not hold the Mac awake
        try:
            awake.wait(timeout=5)       # reaped: no zombie carried into the next day's exec
        except Exception:               # noqa: BLE001
            pass
    # The desk stays up (owner, 2026-10-08) and stopped writing to the ledger
    # at `rec_until`; a build begun just before that ends within
    # RECORD_SETTLE_S. The day is settled on a ledger nothing writes to.
    settle_at = datetime.fromisoformat(rec_until) + timedelta(seconds=RECORD_SETTLE_S)
    while datetime.now(ET) < settle_at and not STOP["requested"]:
        time.sleep(5)
    _settle(conn, today, False)
    if STOP["requested"]:               # Ctrl-C after the hard stop: settled, and everything stops
        _stop_proc(desk)
        return 0
    return desk_only(args, conn, "after the bot's day", desk=desk, symbols=symbols, day=today)


if __name__ == "__main__":
    sys.exit(main())
