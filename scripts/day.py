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
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import ET, HARD_STOP  # noqa: E402
from execution.policy import premarket_allowed  # noqa: E402,F401
from journal import actuals, bars, controls, ledger as L, replay  # noqa: E402
from momentum_platform.sessions import REGULAR_START  # noqa: E402

PREMARKET_OPEN = datetime.strptime("06:55", "%H:%M").time()
REPORTS = ROOT / "research" / "paper-exercise" / "reports"
DB = Path(os.environ.get("JOURNAL_DB") or L.DEFAULT_DB)

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
    if phase == "A":
        nxt = "B"
        if state.get("sessions_done", 0) < 5 and f["plans_armed"] < 40:
            blockers.append(f"phase A needs 5 sessions or 40 decisions; have "
                            f"{state.get('sessions_done', 0)} sessions, {f['plans_armed']} decisions")
        if state.get("probe_verdict") is None:
            blockers.append("pre-market probe has not recorded a verdict")
    elif phase == "B":
        nxt = "C"
        if f["taken"] < 30:
            blockers.append(f"phase B needs 30 taken trades; have {f['taken']}")
        if f["fills"] and f["fills_with_nbbo"] / f["fills"] < 0.9:
            blockers.append(f"only {f['fills_with_nbbo']}/{f['fills']} fills carry NBBO (need 90%)")
        unprotected = conn.execute("SELECT COUNT(*) FROM orders WHERE protected=0 AND fill_price IS NOT NULL").fetchone()[0]
        if unprotected:
            blockers.append(f"{unprotected} filled entry(ies) were unprotected — zero allowed")
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
    lines += ["## Rejects", "", "| ET | symbol | verdict | outcome | last | why |", "|---|---|---|---|---:|---|"]
    for r in conn.execute("""SELECT ts_et, symbol, verdict, killed_by, outcome, refusal_reasons_json, last
                             FROM decisions WHERE outcome IN ('SUPPRESSED','REFUSED') ORDER BY ts_et"""):
        why = r["killed_by"] or ""
        if r["outcome"] == "REFUSED" and r["refusal_reasons_json"]:
            why = "; ".join(json.loads(r["refusal_reasons_json"]))
        lines.append(f"| {r['ts_et'][11:16]} | {r['symbol']} | {r['verdict']} | {r['outcome']} | "
                     f"{r['last'] if r['last'] is not None else '—'} | {why} |")
    lines += ["", "## Controls (planned R · same rows · no CIs at this n)", "",
              "| series | n | mean R | median R | win |", "|---|---:|---:|---:|---:|"]
    for k, v in ctl.items():
        if v["n"]:
            lines.append(f"| {k} | {v['n']} | {v['mean_R']:.3f} | {v['median_R']:.3f} | {v['win_rate']:.0%} |")
        else:
            lines.append(f"| {k} | 0 | — | — | — |")
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
def gap_scan(dry: bool) -> list[dict]:
    if dry:
        return []
    try:
        out = subprocess.run([sys.executable, "scripts/premarket_stars.py", "--json", "--top", "20"],
                             cwd=ROOT, capture_output=True, text=True, timeout=180)
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else []
    except Exception as exc:                            # noqa: BLE001
        warn(f"gap scan failed: {exc}")
        return []


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


def start_desk(symbols: list[str], dry: bool):
    cmd = [sys.executable, "-m", "momentum_platform.dashboard.server", "--host", "127.0.0.1",
           "--port", os.environ.get("DESK_PORT", "8787"), "--ibkr", ",".join(symbols)]
    note("desk: " + " ".join(cmd))
    if dry:
        return None
    env = {**os.environ, "JOURNAL_DB": str(DB), "PYTHONPATH": str(ROOT / "src")}
    return subprocess.Popen(cmd, cwd=ROOT, env=env)


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
    res = actuals.fill_all(conn, bars.from_ledger(conn))
    good(f"actuals: {res['computed']} computed, {len(res['no_tape'])} without tape")
    rep = replay.check(conn)
    (good if not rep["diverged"] else bad)(f"replay: {rep['reproduced']}/{rep['checked']} reproduce")
    path = write_report(conn, today, "IBKR · TWS read-only · live")
    good(f"report: {path.relative_to(ROOT)}")
    st = L.get_state(conn)
    L.set_state(conn, sessions_done=st["sessions_done"] + 1)
    nxt, blockers = gates_for_advance(conn, L.get_state(conn))
    if nxt:
        if blockers:
            note(f"phase {st['phase']} → {nxt} blocked by:")
            for b in blockers:
                note(f"  - {b}")
        else:
            warn(f"phase {st['phase']} → {nxt} gates are ALL clear — run: python3 scripts/exercise.py advance")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--risk", type=float, default=None, help="overrides exercise_state.dollar_risk")
    ap.add_argument("--symbols", help="skip the gap scan; comma-separated watchlist")
    args = ap.parse_args(argv)

    now = datetime.now(ET)
    today = now.date().isoformat()
    conn = L.connect(DB)
    st = L.get_state(conn)
    risk = args.risk or st.get("dollar_risk") or 20.0
    mode = mode_for(st)
    say(f"\n{BOLD}Trading day {today} · {now:%H:%M ET}{END}  phase {st['phase']} · {mode} · ${risk:g} risk · {DB}")
    if now.weekday() >= 5:
        warn("weekend — nothing to do"); return 0
    if now.time() >= HARD_STOP:
        after_close(conn, today, args.dry_run); return 0
    if now.time() < PREMARKET_OPEN:
        warn(f"before {PREMARKET_OPEN:%H:%M} ET — start TWS and the Gateway, come back at 06:55"); return 0

    say(f"\n{BOLD}1. Watchlist{END}  (gap scan — STAR then WATCH; rejects named)")
    if args.symbols:
        symbols, rejects = [s.strip().upper() for s in args.symbols.split(",") if s.strip()], []
    else:
        rows = gap_scan(args.dry_run)
        symbols, rejects = pick_watchlist(rows)
    for sym, why in rejects:
        note(f"✗ {sym:<6} {why}")
    if symbols:
        good(f"{len(symbols)} names: {' '.join(symbols)}")
    else:
        warn("gap scan returned nothing — the desk's own scanner picks (start.sh --ibkr behaviour)")

    say(f"\n{BOLD}2. Pre-market probe{END}  (once per day, before 09:30)")
    if now.time() < REGULAR_START:
        run_probe_once(conn, today, args.dry_run)
    else:
        note("past 09:30 — the probe only runs pre-market")
    ok, why = premarket_allowed(L.get_state(conn))
    (good if ok else note)(f"pre-market entries: {'ON' if ok else 'off'} — {why}")

    say(f"\n{BOLD}3. Desk + runner{END}")
    desk = start_desk(symbols, args.dry_run)
    time.sleep(0 if args.dry_run else 8)
    runner = start_runner(mode, risk, args.dry_run)
    if args.dry_run:
        say(f"\n{DIM}dry run — nothing started{END}"); return 0

    def stop(*_):
        for p in (runner, desk):
            if p and p.poll() is None:
                p.send_signal(signal.SIGINT)
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)

    say(f"{DIM}running until {HARD_STOP:%H:%M} ET; Ctrl-C stops both{END}")
    while datetime.now(ET).time() < HARD_STOP:
        for name, p in (("desk", desk), ("runner", runner)):
            if p and p.poll() is not None:
                bad(f"{name} exited with {p.returncode} — stopping the day")
                stop(); return 1
        time.sleep(15)
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
