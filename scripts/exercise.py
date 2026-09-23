#!/usr/bin/env python3
"""The paper-trading exercise, from the terminal.

    python3 scripts/exercise.py replay FIXTURE [--db PATH] [--risk 20]
        Run a fixture through the desk with the journal on, act on every
        decision in LOG_ONLY, fill actuals from the same tape, print the report.
        This is step 2 of docs/paper-exercise-brief.md §⑧ — log only, no orders.

    python3 scripts/exercise.py check  [--db PATH]
        R11: re-run the cascade on every stored decision and prove it reproduces.

    python3 scripts/exercise.py report [--db PATH]
        The funnel, the controls, the replay result. Nothing else.

    python3 scripts/exercise.py live   [--db PATH] [--risk 20] [--trade]
        Act on the LIVE desk's decisions. Without --trade: LOG_ONLY, and the
        Gateway is never touched. With --trade: places brackets on the paper
        account through PaperTrader (client 31, port 4002) — refuses unless the
        account is DU*, and runs the end-of-day flatten at the hard stop.
        The desk must be running with JOURNAL_DB pointing at the same file.

The report is laid out the way .claude/skills/trading-report-design says a
document must be: provenance first, funnel with denominators, rejects
visible, verdict last, limitations always. A number here without its
source is a defect.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import actuals, bars, controls, ledger as L, replay  # noqa: E402

DIM, BOLD, OK, BAD, WARN, END = "\033[2m", "\033[1m", "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def _db(args) -> str:
    return args.db or os.environ.get("JOURNAL_DB") or str(L.DEFAULT_DB)


# ------------------------------------------------------------------ report
def print_trades(conn, last: int | None = None) -> None:
    """The trades as trades: entry, exit, reason, R. Held rows say so."""
    rows = L.trade_rows(conn)
    if last:
        rows = rows[-last:]
    closed = [r for r in rows if r["closed"]]
    head = f"{BOLD}TRADES{END}  {len(rows)} filled · {len(closed)} closed"
    if closed:
        tot = round(sum(r["r"] or 0.0 for r in closed), 2)
        wins = sum(1 for r in closed if (r["r"] or 0) > 0)
        head += f" · {wins} won · net {tot:+.2f} R (planned R, no costs)"
    print(f"\n{head}")
    if not rows:
        print("  no fills"); return
    print(f"  {'#':>3} {'day':<10} {'in':>5} {'sym':<6}{'qty':>5}{'fill':>8}{'out':>6}{'exit':>8}  {'reason':<14}{'$':>9}{'R':>7}")
    for r in rows:
        if r["closed"]:
            out_t, px = r["exit_ts"][11:16], f"{r['exit_price']:.2f}"
            who = f" ({r['exit_confirmed_by']})" if r["exit_confirmed_by"] else ""
            reason = f"{r['exit_reason'] or '—'}{who}"[:14]
            pnl, rr = f"{r['pnl']:+.2f}", f"{r['r']:+.2f}" if r["r"] is not None else "—"
        else:
            out_t, px, pnl, rr = "—", "—", "—", "—"
            reason = {"ExitPending": "sell working", "ExitFailed": "HELD, no exit"}.get(r["status"], "HELD")
        print(f"  {r['order_id']:>3} {r['fill_ts'][:10]:<10} {r['fill_ts'][11:16]:>5} {r['symbol']:<6}{r['qty']:>5}"
              f"{r['fill_price']:>8.2f}{out_t:>6}{px:>8}  {reason:<14}{pnl:>9}{rr:>7}")


def print_kill_rule(conn, tape) -> None:
    """Amendment A3's kill rule, read at every close-out (preregistration §5,
    amended 2026-09-22): clean fills only, binding from KILL_RULE_MIN_N."""
    k = controls.kill_rule_read(conn, tape)
    lamp = {"MET": f"{BAD}✗ MET — revert A3 in one commit and record it{END}",
            "NOT MET": f"{OK}✓ not met{END}",
            "READ-ONLY": f"{WARN}read-only{END} ({k['n']} clean fill(s); binds from {k['min_n']})"}[k["verdict"]]
    print(f"\n{BOLD}A3 KILL RULE{END}  live trail vs simulated baseline, same fills · {lamp}")
    if not k["rows"]:
        print("  no clean closed fills yet" + (f" · {k['excluded_defect']} defect exit(s) excluded" if k["excluded_defect"] else ""))
        return
    print(f"  {'#':>3} {'day':<10} {'sym':<6}{'exit':<10}{'live R':>8}{'baseline':>10}{'trail sim':>10}")
    for r in k["rows"]:
        f = lambda v, w: f"{v:>+{w}.2f}" if v is not None else f"{'—':>{w}}"   # noqa: E731
        print(f"  {r['order_id']:>3} {r['fill_ts'][:10]:<10} {r['symbol']:<6}{(r['exit_reason'] or '—'):<10}"
              f"{f(r['live_r'], 8)}{f(r['baseline_r'], 10)}{f(r['trail_r'], 10)}")
    f2 = lambda v: f"{v:+.2f}" if v is not None else "—"   # noqa: E731
    print(f"  mean over {k['n']}: live {f2(k['live_mean'])} R · baseline {f2(k['baseline_mean'])} R · "
          f"trail simulated {f2(k['trail_sim_mean'])} R"
          + (f" · {k['excluded_defect']} defect exit(s) excluded (exercise.py defect)" if k["excluded_defect"] else ""))


def report(conn, *, source: str, synthetic: bool, tape: dict | None = None) -> None:
    f = L.funnel(conn)
    rep = replay.check(conn)
    ctl = controls.summary(conn)
    now = datetime.now(timezone.utc).astimezone(L.ET).strftime("%Y-%m-%d %H:%M ET")

    print(f"\n{BOLD}PAPER EXERCISE · decision ledger{END}")
    print(f"LEDGER · {source} · checked {now}")
    if synthetic:
        print(f"{WARN}! SYNTHETIC FIXTURE — 10 generated symbols. Proves plumbing, never a market.{END}")
    first = conn.execute("SELECT MIN(ts_et), MAX(ts_et), COUNT(DISTINCT substr(ts_et,1,10)) FROM decisions").fetchone()
    if first[0]:
        print(f"decisions span {first[0][:16]} → {first[1][:16]} ET · {first[2]} session day(s)")

    print(f"\n{BOLD}FUNNEL{END}  (denominator at every stage)")
    print(f"  {f['board_symbols']:>4} symbols on the board · {f['board_plan_allowed']} rows plan-allowed"
          f" · {f['board_rows']} board rows")
    print(f"  {f['plans_armed']:>4} plans armed by the detector")
    print(f"  {f['plans_suppressed']:>4}   suppressed by the cascade      {DIM}(killed names, shown below){END}")
    print(f"  {f['plans_allowed']:>4}   allowed")
    print(f"  {f['refused_by_executor']:>4}     refused by the executor    {DIM}(reasons below){END}")
    print(f"  {f['log_only']:>4}     LOG_ONLY  · {f['taken']} TAKEN · {f['orders']} orders · "
          f"{f['fills']} fills · {f['fills_with_nbbo']} with NBBO")
    print(f"  {f['actuals']:>4} actuals computed · {f['halts']} halt transitions")
    rec = L.reconcile_allowed(conn)
    parts = " + ".join(f"{n} {k}" for k, n in rec["by_outcome"].items()) or "nothing"
    lamp = f"{OK}✓{END}" if rec["residual"] == 0 else f"{BAD}✗{END}"
    print(f"  {lamp} allowed reconciliation: {rec['allowed']} allowed = {parts}"
          f" · residual {rec['residual']}  {DIM}(every allowed decision carries one of "
          f"{', '.join(L.OUTCOMES)}){END}")

    print(f"\n{BOLD}REJECTS{END}  (never hidden)")
    rows = conn.execute("""SELECT ts_et, symbol, verdict, killed_by, outcome, refusal_reasons_json, last
                           FROM decisions WHERE outcome IN ('SUPPRESSED','REFUSED') ORDER BY ts_et""").fetchall()
    if not rows:
        print("  —")
    for r in rows:
        why = r["killed_by"] or ""
        if r["outcome"] == "REFUSED" and r["refusal_reasons_json"]:
            import json
            why = "; ".join(json.loads(r["refusal_reasons_json"]))[:90]
        print(f"  {r['ts_et'][11:16]}  {r['symbol']:<6} {r['verdict']:<8} {r['outcome']:<10} "
              f"last {r['last'] if r['last'] is not None else '—':<8} ✗ {why}")

    print(f"\n{BOLD}CONTROLS{END}  (planned R · same rows · no CIs at this n)")
    print(f"  {'series':<12}{'n':>4}{'mean R':>10}{'median R':>10}{'win':>7}")
    for k, v in ctl.items():
        if v["n"] and v["mean_R"] is not None:
            print(f"  {k:<12}{v['n']:>4}{v['mean_R']:>10.3f}{v['median_R']:>10.3f}{v['win_rate']:>7.0%}")
        else:
            print(f"  {k:<12}{v['n']:>4}{'—':>10}{'—':>10}{'—':>7}")

    last_bar = controls.last_bar_time(conn)
    print(f"  {DIM}\"close\" = the last bar the desk recorded that day"
          + (f" (latest in this ledger: {last_bar} UTC)" if last_bar else "")
          + f"; hold_close and random_bar carry NO stop; no costs in any series{END}")
    if tape is None:
        tape = bars.from_ledger(conn)
    ex = controls.exit_summary(conn, tape)
    print(f"\n{BOLD}EXIT VARIANTS{END}  (simulated · same entry fill · same initial stop · same cutoff · planned R)")
    print(f"  {'variant':<12}{'n':>4}{'mean R':>10}{'median R':>10}{'stopped':>9}{'to close':>10}")
    for k, v in ex.items():
        if v["n"] and v["mean_R"] is not None:
            print(f"  {k:<12}{v['n']:>4}{v['mean_R']:>10.3f}{v['median_R']:>10.3f}"
                  f"{v['stopped']:>9.0%}{v['to_close']:>10.0%}")
        else:
            print(f"  {k:<12}{v['n']:>4}{'—':>10}{'—':>10}{'—':>9}{'—':>10}")
    print(f"  {DIM}baseline = fixed +2R target · no_target = initial stop only (the rule in force until A3)"
          f" · trail_1r = A3, bar-ordered, low tested before the high raises the stop{END}")

    u = controls.units(conn)
    print(f"\n{BOLD}STATISTICAL UNIT{END}  (what the strategy series is made of)")
    print(f"  {u['rows']} rows = {u['unique_setups']} unique setups on {u['unique_symbol_days']} unique symbol-days "
          f"over {u['sessions']} session(s)")
    for day, v in u["per_session"].items():
        print(f"    {day}: n {v['n']:>3}  mean {v['mean_R']:+.3f}  median {v['median_R']:+.3f}")
    if u["top3_symbol_days"]:
        top = " · ".join(f"{t['symbol']} {t['day'][5:]} {t['sum_R']:+.2f}R ({t['rows']} rows)" for t in u["top3_symbol_days"])
        share = f"{u['top3_share_of_total']:.0%} of the total" if u["top3_share_of_total"] is not None else "total ≤ 0"
        print(f"  largest winning symbol-days: {top} — {share}; "
              f"mean without them {u['mean_R_without_top3']:+.3f}" if u["mean_R_without_top3"] is not None
              else f"  largest winning symbol-days: {top} — {share}")
    print(f"  {DIM}rows from one name on one morning are correlated, not independent; large winners stay "
          f"in the primary result, and their weight is shown so it cannot hide{END}")
    viol = L.r0_violations(conn)
    lamp = f"{OK}✓{END}" if not viol else f"{BAD}✗{END}"
    print(f"  {lamp} R0 check: {f['fills']} fill(s), realised risk = qty × (fill − INITIAL stop) on all"
          + (f" but {len(viol)}: " + ", ".join(f"#{v['order_id']} {v['symbol']}" for v in viol) if viol else ""))

    print_trades(conn)
    print_kill_rule(conn, tape)

    st = L.get_state(conn)
    print(f"\n{BOLD}ALIGNMENT{END}  (decision tape → fill → fill tape)")
    pd = st.get("paper_data")
    lampd = f"{OK}✓{END}" if pd == "realtime" else f"{BAD}✗{END}" if pd else f"{WARN}?{END}"
    print(f"  {lampd} paper session data: {pd or 'NOT MEASURED — run scripts/alignment_probe.py'}"
          + (f" ({st.get('paper_data_date')})" if pd else ""))
    al = L.alignment_rows(conn)
    if not al:
        print("  no fills yet")
    else:
        print(f"  {'ET':>5} {'sym':<6}{'decision bid/ask':>18}{'trigger':>9}{'fill':>8}{'fill bid/ask':>16}{'gap s':>7}{'slip':>7}")
        for r in al:
            dba = f"{r['d_bid']}/{r['d_ask']}" if r["d_bid"] is not None else "—"
            fba = f"{r['nbbo_bid']}/{r['nbbo_ask']}" if r["nbbo_bid"] is not None else "— (unverified)"
            gap = r["quote_gap_s"] if r["quote_gap_s"] is not None else "—"
            slip = f"{r['slippage_ratio']:.2f}x" if r["slippage_ratio"] is not None else "—"
            print(f"  {r['fill_ts'][11:16]:>5} {r['symbol']:<6}{dba:>18}{r['trigger']:>9.2f}{r['fill_price']:>8.2f}{fba:>16}{gap:>7}{slip:>7}")
        print(f"  {DIM}gap s = desk quote stamp minus IBKR fill stamp; a fill with no fill bid/ask is UNVERIFIED{END}")

    ok = not rep["diverged"]
    lamp = f"{OK}✓{END}" if ok else f"{BAD}✗{END}"
    print(f"\n{BOLD}REPLAY{END}  (R11)")
    print(f"  {lamp} {rep['reproduced']}/{rep['checked']} decisions reproduce their recorded verdict from stored inputs")
    for d in rep["diverged"][:10]:
        print(f"    {d['ts_et'][11:16]} {d['symbol']}: recorded {d['recorded']} · replayed {d['replayed']}")
    _print_superseded(rep)

    print(f"\n{DIM}NOT CHECKED: real fills (paper is simulated; NBBO plausibility only), halt-resume")
    print(f"fills, sub-minute entries, Level 2, borrow, fees beyond IBKR's estimate, regime.")
    print(f"Paper only. 894-session replication was negative expectancy; this measures selection.{END}\n")


# ---------------------------------------------------------------- commands
def cmd_replay(args) -> int:
    from execution.runner import Runner
    from momentum_platform.dashboard.session_builder import build_session

    fixture = Path(args.fixture)
    if not args.db:
        # A fixture replay into the production ledger would sit next to live
        # decisions with only HH:MM shown, indistinguishable from evidence
        # (audit 2026-09-08). Replays name their own file.
        print(f"{BAD}replay needs --db PATH{END}  (never the production ledger; try --db /tmp/replay.sqlite)")
        return 2
    conn = L.connect(_db(args))
    build_session(fixture, journal=conn)
    conn.commit()
    Runner(conn, mode="LOG_ONLY", dollar_risk=args.risk).step()
    actuals.fill_all(conn, bars.from_fixture(fixture))
    synthetic = "SYNTHETIC" in fixture.read_text()[:400].upper()
    report(conn, source=f"{fixture.name} · replay · LOG_ONLY · ${args.risk:g} risk/trade",
           synthetic=synthetic, tape=bars.from_fixture(fixture))
    return 0


def _print_superseded(rep: dict) -> None:
    """A superseded cohort is not a pass in disguise: name it every time.

    These rows reproduce, but under rules that no longer exist. That is a real
    fact about what the evidence base measures, so it is printed beside the
    replay result rather than folded into it.
    """
    if not rep.get("superseded"):
        return
    n = len(rep["superseded"])
    sets = ", ".join(f"{k} {v}" for k, v in sorted(rep["by_rules"].items()))
    print(f"  {WARN}!{END} {n} decision(s) reproduce only under SUPERSEDED rules — "
          f"they were recorded before an amendment changed the answer")
    print(f"    by rule set: {sets}  (current: {rep['current_rules']})")
    print(f"    {DIM}not a defect and not evidence for the current rules; "
          f"see docs/preregistration.md §5{END}")


def cmd_check(args) -> int:
    conn = L.connect(_db(args))
    rep = replay.check(conn)
    for d in rep["diverged"]:
        print(f"{BAD}✗{END} {d}")
    print(f"{rep['reproduced']}/{rep['checked']} reproduced")
    _print_superseded(rep)
    return 0 if not rep["diverged"] else 1


def cmd_report(args) -> int:
    conn = L.connect(_db(args))
    report(conn, source=_db(args), synthetic=False)
    return 0


def cmd_live(args) -> int:
    from execution.intent import ET, HARD_STOP
    from execution.runner import Runner

    conn = L.connect(_db(args))
    # One writer per ledger. Two runners on one file would both claim the same
    # pending decision (audit F4). The lock lives beside the database and is
    # released by the OS when this process ends, crash included.
    import fcntl
    lock_path = Path(str(_db(args)) + ".lock")
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        print(f"{BAD}another runner already holds {lock_path} — refusing to start a second{END}")
        return 4
    lock_fd.write(str(os.getpid())); lock_fd.flush()
    trader = None
    from journal.risk import JournalRiskGate, RiskVeto
    gate = JournalRiskGate(conn)
    if args.trade:
        phase = L.get_state(conn).get("phase", "A")
        if phase not in ("B", "C"):
            # The phase gate at the execution boundary (review round 2): the
            # day command chose the mode from the phase, but this command could
            # be run by hand with --trade in phase A.
            print(f"{BAD}phase {phase}: the exercise is log-only — --trade is refused{END}  "
                  f"(docs/preregistration.md §3; python3 scripts/exercise.py advance)")
            return 5
        from execution.ibkr_trader import PaperTrader
        # The daily risk gate reads THIS ledger and latches in it. Until the
        # 2026-09-07 review the trader was built with no gate at all.
        trader = PaperTrader(risk_gate=gate)
        acct = trader.connect()                 # raises NotPaperError on U*
        print(f"{OK}ok{END} {acct} — paper · client {trader.client_id} · TRADE mode · "
              f"risk gate {gate.limits}")
    else:
        print(f"{DIM}LOG_ONLY — no connection opened; decisions are judged and recorded only{END}")
    runner = Runner(conn, mode="TRADE" if args.trade else "LOG_ONLY",
                    dollar_risk=args.risk, trader=trader,
                    # NBBO at fill (brief R4) from the desk's latest quote in the
                    # ledger. None when older than 30s, and the fill is then
                    # recorded as unverified rather than decorated.
                    quote=L.quote_source(conn))
    for line in runner.startup_notes:
        print(f"  {WARN if 'UNRESOLVED' in line else OK}start{END}    {line}")
    print(f"{DIM}reading {_db(args)} every {args.every}s · hard stop {HARD_STOP:%H:%M} ET · Ctrl-C to stop{END}")
    flattened = False
    try:
        errors = 0
        while True:
            acted = []
            try:
                acted = runner.step()
                errors = 0
            except RiskVeto as veto:
                # The day is over for ENTRIES only. Flipping the mode to
                # LOG_ONLY also switched off fill sync, the monitored stop and
                # the 11:30 flatten (audit 2026-09-08); entries_enabled does not.
                print(f"  {datetime.now(ET):%H:%M:%S}  {BAD}DAY LOCKED{END} {veto.reason} — "
                      f"no more entries today; exits, stops and the flatten continue")
                runner.entries_enabled = False
            except KeyboardInterrupt:
                raise
            except Exception as exc:                     # noqa: BLE001
                # The runner is idempotent: pending() re-offers unfinished rows.
                # A locked database or a malformed row must not end the day —
                # and until now it also skipped the exit management below
                # (review round 2): an entry error is not a reason to leave a
                # position unwatched.
                errors += 1
                print(f"  {datetime.now(ET):%H:%M:%S}  {WARN}runner error{END} {exc!r} — retrying"
                      + (f" ({errors} in a row)" if errors > 1 else ""))
            # Plans the detector armed on the history the desk loaded at start
            # (04:00 onward on IBKR) are answered and refused like any other,
            # tagged backfill, kept out of every statistic. Printed one per
            # line they read as a morning of live refusals at 04:22; they are
            # one fact, so they get one line (owner, 2026-09-23).
            hist = [a for a in acted if a.backfill]
            if hist:
                syms = sorted({a.symbol for a in hist})
                print(f"  {DIM}{len(hist)} plan(s) armed on history loaded at start "
                      f"({hist[0].ts_et[11:16]}–{hist[-1].ts_et[11:16]} ET, {', '.join(syms)}) → refused, "
                      f"tagged backfill, not counted; each row is in the ledger{END}")
            for a in acted:
                if a.backfill:
                    continue
                tag = {"TAKEN": OK, "REFUSED": WARN, "LOG_ONLY": DIM}.get(a.outcome, "")
                print(f"  {a.ts_et[11:16]}  {a.symbol:<6} {tag}{a.outcome:<8}{END} "
                      f"{a.trigger:.2f}/{a.stop:.2f}"
                      + (f"  ✗ {'; '.join(a.reasons)[:90]}" if a.reasons else ""))
            if args.trade:
                flattened = manage_exits(runner, flattened, datetime.now(ET))
            time.sleep(min(30, args.every * errors) if errors else args.every)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        if trader is not None:
            # a second Ctrl-C during the disconnect used to end in a traceback
            import signal
            previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                trader.disconnect()
            except Exception as exc:          # the socket may already be gone
                print(f"  disconnect: {exc!r}")
            finally:
                signal.signal(signal.SIGINT, previous)
    return 0


def manage_exits(runner, flattened: bool, now_et) -> bool:
    """Everything that watches a position, each step on its own: a failure in
    one must not skip the next, and the hard-stop flatten is attempted
    whatever happened before it (review round 2). Returns the flatten flag."""
    from execution.intent import HARD_STOP

    def guarded(label, fn):
        try:
            return fn()
        except KeyboardInterrupt:
            raise
        except Exception as exc:                          # noqa: BLE001
            print(f"  {now_et:%H:%M:%S}  {WARN}{label} error{END} {exc!r} — the other exit checks continue")
            return None

    guarded("fill sync", runner.sync_fills)
    for line in guarded("reconcile", runner.reconcile_positions) or []:
        print(f"  {now_et:%H:%M:%S}  {BAD}RECONCILE{END} {line}")
    # A held position whose stop died gets a fresh one from the runner.
    for line in guarded("re-protect", runner.reprotect) or []:
        print(f"  {now_et:%H:%M:%S}  {OK}PROTECT{END}  {line}")
    # The monitored stop lives here and nowhere else: for a `queued`-verdict
    # pre-market entry this call IS the stop.
    for line in guarded("monitored stop", runner.watch_stops) or []:
        print(f"  {now_et:%H:%M:%S}  {WARN}STOP{END}     {line}")
    # A3: the resting stop follows the high at one initial risk, never down.
    for line in guarded("trailing stop", runner.trail_stops) or []:
        print(f"  {now_et:%H:%M:%S}  {OK}TRAIL{END}    {line}")
    for oid in guarded("after-hours flag", runner.flag_after_hours) or []:
        print(f"  {now_et:%H:%M:%S}  {BAD}HELD AFTER CLOSE{END} order {oid} — "
              f"exercise.py ah-exit {oid} --confirm")
    if now_et.time() >= HARD_STOP and not flattened:
        done = guarded("hard stop", runner.end_of_day)
        if done is not None:
            print(f"  {WARN}HARD STOP{END} flattened: {done or 'nothing open'}")
            return True
        print(f"  {BAD}HARD STOP{END} the flatten raised — retrying next loop; check the broker")
    elif flattened:
        # Sent is not filled: the broker's position state decides "flat".
        for line in guarded("flat check", runner.confirm_flat) or []:
            print(f"  {now_et:%H:%M:%S}  {BAD if line.startswith('NOT FLAT') else OK}FLAT{END}     {line}")
    return flattened


def cmd_advance(args) -> int:
    """Move to the next phase ONLY if every pre-registration gate is clear.
    A human runs this; the day runner only reports whether it could."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from day import gates_for_advance
    conn = L.connect(_db(args))
    st = L.get_state(conn)
    nxt, blockers = gates_for_advance(conn, st)
    if nxt is None:
        print(f"phase {st['phase']}: " + "; ".join(blockers)); return 1
    if blockers:
        print(f"{BAD}phase {st['phase']} → {nxt} blocked:{END}")
        for b in blockers:
            print(f"  ✗ {b}")
        return 1
    L.set_state(conn, phase=nxt)
    print(f"{OK}phase {st['phase']} → {nxt}{END}  every gate clear · recorded in exercise_state")
    print(f"{DIM}update docs/preregistration.md §5/§3 in the same commit if a value changed{END}")
    return 0


def cmd_stuck(args) -> int:
    conn = L.connect(_db(args))
    rows = L.stuck_orders(conn)
    if not rows:
        print("no filled, un-exited positions in the ledger"); return 0
    for o in rows:
        print(f"  order {o['order_id']:>4}  {o['symbol']:<6} x{o['shares']}  filled {o['fill_price']} "
              f"stop {o['stop']}  status {o['status']} / {o['stop_status']}")
    return 0


def held_row(o) -> bool:
    """A filled row the broker may still hold: never exited, or exited by a
    sell that FAILED (ExitFailed keeps the failed sell's exit_ts; the shares
    are still there — GRML x62 after the 2026-09-22 hard stop). An ExitPending
    row is not offered: its sell is working and a second one would sell
    shares that are not held."""
    if o is None or o["fill_price"] is None:
        return False
    return o["exit_ts"] is None or o["status"] == "ExitFailed"


def cmd_ah_exit(args) -> int:
    """The manual exit. Brief R10 after hours: exit-only, one order, a human
    confirms it here, and who confirmed is written into the ledger. With
    `--market`, inside regular hours: a SMART-routed market sell that needs no
    desk quote — the path for a position the hard-stop flatten failed to
    close (ExitFailed) when the desk is already down."""
    conn = L.connect(_db(args))
    o = conn.execute("SELECT * FROM orders WHERE order_id=?", (args.order_id,)).fetchone()
    if o is None:
        print(f"{BAD}no order {args.order_id}{END}"); return 1
    if not held_row(o):
        print(f"{BAD}order {args.order_id} is not a held position{END} (status {o['status']})"); return 1
    market = bool(getattr(args, "market", False))
    if not args.confirm:
        print(f"{WARN}MANUAL_CONFIRMATION_REQUIRED{END}  {o['symbol']} x{o['shares']} filled {o['fill_price']}"
              + (f"  status {o['status']}" if o["status"] == "ExitFailed" else ""))
        if market:
            print("  regular hours: re-run with --confirm to SELL at MARKET, SMART-routed. No quote")
            print("  is read; the broker's fill is written back. This is an exit; nothing is bought.")
        else:
            print("  after hours: no stops exist, margin is auto-liquidated at 16:00, and the")
            print("  source is measured not net profitable there. Re-run with --confirm to SELL")
            print("  at bid − 0.10, limit, extended hours. This is an exit; nothing is bought.")
        return 2
    from execution.intent import in_regular_hours
    from execution.ibkr_trader import PaperTrader
    who = os.environ.get("USER") or "operator"
    qty = int(o["filled_qty"]) if o["filled_qty"] else int(o["shares"])
    reason = "manual_market" if market else "AH_exception"
    if market:
        if not in_regular_hours():
            print(f"{BAD}--market only inside 09:30-16:00 ET: no market orders exist outside; "
                  f"use ah-exit without --market and a running desk{END}"); return 1
        q = {"bid": None}
    else:
        q = L.quote_source(conn, max_age_s=120)(o["symbol"])
        if not q or q.get("bid") is None:
            print(f"{BAD}no fresh quote for {o['symbol']} in the ledger — start the desk first, "
                  f"or inside regular hours use --market{END}"); return 1
    with PaperTrader() as t:
        # The resting stop leg goes first. A stop left resting after a hand
        # sale fills into a SHORT position; the flatten cancels first for the
        # same reason. If the sell then fails, the row reads ExitFailed and
        # the runner's reprotect places a fresh stop.
        if o["stop_id"] and hasattr(t, "cancel_order_id"):
            try:
                if t.cancel_order_id(int(o["stop_id"])):
                    t.ib.sleep(1)
                    print(f"  stop leg {o['stop_id']} cancelled first, so the position cannot be sold twice")
                    L.add_order_event(conn, o["order_id"], f"manual exit: stop leg {o['stop_id']} cancelled before the sell")
            except Exception as exc:                        # noqa: BLE001
                print(f"  {WARN}could not cancel stop leg {o['stop_id']}: {exc!r} — selling anyway; check the broker for a resting SELL{END}")
        if market:
            exit_id = t.exit_market(o["symbol"], qty)
            px = None
        else:
            px = t.exit_limit(o["symbol"], qty, float(q["bid"]), outside_rth=True)
            exit_id = getattr(t, "last_exit_order_id", None)
        # Wait briefly for the fill so the row can close with the real price;
        # otherwise it stays ExitPending and the next runner sync confirms it.
        fill = None
        for _ in range(10):
            t.ib.sleep(1)
            tr = next((x for x in t.ib.trades() if x.order.orderId == exit_id), None)
            if tr is not None and tr.orderStatus.status == "Filled" and tr.orderStatus.avgFillPrice:
                fill = tr.orderStatus.avgFillPrice
                break
    L.record_exit(conn, o["order_id"], reason=reason, price=fill if fill else px,
                  ts=datetime.now(timezone.utc), confirmed_by=who,
                  confirmed=fill is not None, exit_order_id=exit_id)
    sent = f"SELL MKT x{qty} (order {exit_id})" if market else f"SELL LMT {px} x{qty} (bid {q['bid']})"
    L.add_order_event(conn, o["order_id"], f"{reason} confirmed by {who}: {sent}"
                      + (f"; filled {fill}" if fill else "; fill NOT yet seen — row is ExitPending"))
    conn.commit()
    print(f"{OK}sent{END} {sent} {o['symbol']}  recorded as {reason} by {who}"
          + (f" · filled {fill}" if fill else f" · {WARN}fill not yet seen; check exercise.py stuck{END}"))
    return 0


def cmd_defect(args) -> int:
    """Name a fill whose exit was a code defect's. The row keeps its P&L and
    R everywhere; it leaves the A3 kill-rule comparison, which judges the
    exit rule and not the plumbing. A human act, written with a name."""
    conn = L.connect(_db(args))
    o = conn.execute("SELECT * FROM orders WHERE order_id=?", (args.order_id,)).fetchone()
    if o is None:
        print(f"{BAD}no order {args.order_id}{END}"); return 1
    if o["fill_price"] is None or o["exit_price"] is None:
        print(f"{BAD}order {args.order_id} has no closed exit to mark{END}"); return 1
    if o["defect_note"]:
        print(f"order {args.order_id} already marked: {o['defect_note']}"); return 0
    if not args.confirm:
        print(f"{WARN}would mark{END} order {args.order_id} {o['symbol']} exit {o['exit_price']} ({o['exit_reason']}) as a "
              f"DEFECT exit: \"{args.note}\". It stays in every P&L figure and leaves the A3 kill-rule "
              f"comparison. Re-run with --confirm.")
        return 2
    who = os.environ.get("USER") or "operator"
    L.mark_defect(conn, args.order_id, args.note, by=who); conn.commit()
    print(f"{OK}marked{END} order {args.order_id} {o['symbol']} as a defect exit by {who}")
    return 0


def cmd_reset_unprotected(args) -> int:
    """The B→C gate's 'zero unprotected fills' count restarts at the named
    defect fix (owner decision 2026-09-22). Records who, when and which
    commit; the gate prints all three."""
    conn = L.connect(_db(args))
    st = L.get_state(conn)
    before = L.unprotected_fills(conn)
    if not args.confirm:
        print(f"{WARN}would restart{END} the unprotected-fill count from now, naming fix {args.fix}; "
              f"{before} unprotected fill(s) in the ledger so far"
              + (f"; last reset {st.get('unprotected_reset_at')} at fix {st.get('unprotected_reset_fix')}" if st.get("unprotected_reset_at") else "")
              + ". Re-run with --confirm.")
        return 2
    who = os.environ.get("USER") or "operator"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L.set_state(conn, unprotected_reset_at=now, unprotected_reset_by=who, unprotected_reset_fix=args.fix)
    print(f"{OK}recorded{END} unprotected-fill count restarts at {now} (fix {args.fix}) by {who}; "
          f"{before} earlier unprotected fill(s) stay in the ledger and the reports")
    return 0


def cmd_accept_a1(args) -> int:
    """Record the owner's acceptance of amendment A1 (docs/preregistration.md
    §5): pre-market entries on a `queued` probe verdict get NO resting stop;
    the runner is the stop, and every such position is UNPROTECTED in the
    report. A human act, recorded with a name and a time. Code never sets it."""
    conn = L.connect(_db(args))
    st = L.get_state(conn)
    if st.get("a1_accepted") == "yes":
        print(f"A1 already accepted by {st.get('a1_accepted_by')} at {st.get('a1_accepted_at')}"); return 0
    if not args.confirm:
        print("Amendment A1 — monitored exit (docs/preregistration.md §5). Accepting means accepting,")
        print("by name, that a pre-market position has no stop at the broker: if the runner dies,")
        print("the quote goes stale, the name halts, or the limit does not fill, the exposure is yours.")
        print("The GPT review of 2026-09-08 recommends observing pre-market without orders instead.")
        print("Re-run with --confirm to record acceptance; then replace PROPOSED in §5 in the same commit.")
        return 2
    who = os.environ.get("USER") or "operator"
    L.set_state(conn, a1_accepted="yes", a1_accepted_by=who,
                a1_accepted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    print(f"{OK}recorded{END} A1 accepted by {who} — update docs/preregistration.md §5 in the same commit")
    return 0


def cmd_missed(args) -> int:
    """What the plans the runner did NOT take went on to do, next to the ones
    it did. Per row and per reason. Fill at the trigger, exits at their
    level, no slippage, no costs, no halts: an upper bound on what was
    'missed', never a P&L. Backfill rows are listed but kept out of the sums."""
    conn = L.connect(_db(args))
    day = args.day
    if day is None:
        row = conn.execute("SELECT MAX(substr(ts_et,1,10)) FROM decisions").fetchone()
        day = row[0] if row and row[0] else None
    if day is None:
        print("no decisions in the ledger"); return 1
    rows = controls.per_decision(conn, bars.from_ledger(conn), day)
    if not rows:
        print(f"no decisions on {day}"); return 1
    print(f"\n{BOLD}NOT TAKEN vs TAKEN · {day}{END}  {len(rows)} armed plans · fill at trigger, no slippage, no costs · planned R")
    print(f"  {'ET':>5} {'sym':<6}{'verdict':<8}{'outcome':<11}{'trig':>7}{'stop':>7} {'hit':<4}{'first':<12}{'MFE':>6}{'MAE':>6}{'strat':>7}{'trail':>7}  reason")
    for d in rows:
        if not args.all and d["outcome"] == "SUPPRESSED" and not d["trigger_hit"]:
            continue                                  # killed and never triggered: noise unless --all
        hit = "—" if d["trigger_hit"] is None else ("y" if d["trigger_hit"] else "n")
        f = lambda v, w=6: f"{v:>{w}.2f}" if v is not None else f"{'—':>{w}}"   # noqa: E731
        tag = (" [backfill]" if d["backfill"] else "") + (" ‡thin stop" if d["thin_stop"] else "")
        print(f"  {d['ts_et'][11:16]:>5} {d['symbol']:<6}{d['verdict']:<8}{d['outcome']:<11}"
              f"{f(d['trigger'], 7)}{f(d['stop'], 7)} {hit:<4}{(d['first_hit'] or '—'):<12}"
              f"{f(d['mfe_r_planned'])}{f(d['mae_r_planned'])}{f(d['strategy_r'], 7)}{f(d['trail_r'], 7)}"
              f"  {controls.reason_key(d)[:52]}{tag}")
    # per reason, prospective rows only
    from collections import defaultdict
    groups: dict[str, list[dict]] = defaultdict(list)
    for d in rows:
        if not d["backfill"]:
            groups[controls.reason_key(d)].append(d)
    print(f"\n{BOLD}BY REASON{END}  (prospective rows only; 'trig' = plans whose trigger the tape touched; means over triggered rows)")
    print(f"  {'n':>4}{'trig':>6}{'strat mean':>12}{'strat sum':>11}{'trail mean':>12}{'trail sum':>11}{'win':>6}  reason")
    def _m(vs):
        return f"{sum(vs)/len(vs):>+12.2f}" if vs else f"{'—':>12}"
    def _s(vs):
        return f"{sum(vs):>+11.2f}" if vs else f"{'—':>11}"
    for key, ds in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        trig = [d for d in ds if d["trigger_hit"] == 1]
        st = [d["strategy_r"] for d in trig if d["strategy_r"] is not None]
        tr = [d["trail_r"] for d in trig if d["trail_r"] is not None]
        win = f"{sum(1 for x in st if x > 0)/len(st):>6.0%}" if st else f"{'—':>6}"
        print(f"  {len(ds):>4}{len(trig):>6}{_m(st)}{_s(st)}{_m(tr)}{_s(tr)}{win}  {key}")
    thin = [d for d in rows if d["thin_stop"] and not d["backfill"]]
    pct = controls.THIN_STOP_PCT * 100
    if thin:
        st = [d["strategy_r"] for d in thin if d["strategy_r"] is not None]
        tr = [d["trail_r"] for d in thin if d["trail_r"] is not None]
        print(f"\n{BOLD}THIN STOPS{END}  {len(thin)} prospective plan(s) with the stop inside {pct:g}% of the trigger (‡): "
              f"strat sum {sum(st):+.2f} R over {len(st)} · trail sum {sum(tr):+.2f} R over {len(tr)}")
        for d in thin:
            print(f"    {d['ts_et'][11:16]} {d['symbol']:<6} {d['trigger']:.2f}/{d['stop']:.2f}  risk/share "
                  f"{(d['trigger'] - d['stop']):.2f} = {(d['trigger'] - d['stop']) / d['trigger'] * 100:.2f}% of price  "
                  f"{d['outcome']}  MFE {d['mfe_r_planned'] if d['mfe_r_planned'] is not None else '—'}  "
                  f"MAE {d['mae_r_planned'] if d['mae_r_planned'] is not None else '—'}")
        print(f"    {DIM}a measurement for amendment A9, not a gate: nothing refuses on it. Planned R on these rows is "
              f"inflated by the tiny denominator.{END}")
    print(f"\n{DIM}'strat' = fixed +2R target, −1R stop, else close (the strategy series). 'trail' = A3 trail_1r, bar-ordered.")
    print(f"A refused plan scored here assumes a fill at the trigger the runner never sent: an upper bound, not a trade.")
    print(f"Killed plans that never touched their trigger are hidden; pass --all to see them.{END}\n")
    return 0


def cmd_review(args) -> int:
    """Everything so far, across sessions. The continuous-improvement view:
    which gate kills most, which refusal dominates, how the strategy stands
    against the free baselines, whether every decision still replays."""
    import json as _json
    from collections import Counter
    conn = L.connect(_db(args))
    st = L.get_state(conn); f = L.funnel(conn); rep = replay.check(conn); ctl = controls.summary(conn)
    print(f"\n{BOLD}PAPER EXERCISE · cumulative review{END}   phase {st['phase']} · "
          f"{st['sessions_done']} session(s) counted · {_db(args)}")
    days = conn.execute("""SELECT substr(ts_et,1,10) d, COUNT(*) n,
                                  SUM(outcome='SUPPRESSED') sup, SUM(outcome='REFUSED') ref,
                                  SUM(outcome='LOG_ONLY') lo, SUM(outcome='TAKEN') tk,
                                  SUM(outcome='NOT_FILLED') nf
                           FROM decisions GROUP BY d ORDER BY d""").fetchall()
    print(f"\n{BOLD}SESSIONS{END}")
    print(f"  {'date':<12}{'decisions':>10}{'killed':>8}{'refused':>9}{'log':>6}{'taken':>7}{'unfilled':>10}")
    for d in days:
        print(f"  {d['d']:<12}{d['n']:>10}{d['sup']:>8}{d['ref']:>9}{d['lo']:>6}{d['tk']:>7}{d['nf']:>10}")
    if not days:
        print("  —")
    print(f"\n{BOLD}WHAT KILLS{END}  (Layer 1, cumulative)")
    kills = Counter(r[0] for r in conn.execute("SELECT killed_by FROM decisions WHERE killed_by IS NOT NULL"))
    for gate, n in kills.most_common():
        print(f"  {n:>4}  {gate}")
    if not kills:
        print("  —")
    print(f"\n{BOLD}WHAT THE EXECUTOR REFUSES{END}")
    reasons = Counter()
    for (j,) in conn.execute("SELECT refusal_reasons_json FROM decisions WHERE outcome='REFUSED'"):
        for r in _json.loads(j or "[]"):
            reasons[r.split(" — ")[0].split(":")[0][:60]] += 1
    for r, n in reasons.most_common(8):
        print(f"  {n:>4}  {r}")
    if not reasons:
        print("  —")
    print(f"\n{BOLD}VERDICTS AT THE PLAN{END}")
    for v, n in conn.execute("SELECT verdict, COUNT(*) FROM decisions GROUP BY verdict ORDER BY 2 DESC"):
        print(f"  {n:>4}  {v}")
    print(f"\n{BOLD}FILLS{END}  {f['fills']} of {f['orders']} orders · {f['fills_with_nbbo']} with NBBO")
    for r in L.alignment_rows(conn)[-10:]:
        print(f"  {r['fill_ts'][11:16]} {r['symbol']:<6} trigger {r['trigger']:.2f} fill {r['fill_price']:.2f} "
              f"slip {r['slippage_ratio'] if r['slippage_ratio'] is not None else '—'}")
    print_trades(conn, last=10)
    print_kill_rule(conn, bars.from_ledger(conn))
    print(f"\n{BOLD}CONTROLS{END}  (planned R · same rows)")
    for k, v in ctl.items():
        print(f"  {k:<12} n={v['n']:<4} mean {v['mean_R'] if v['mean_R'] is not None else '—'}  "
              f"median {v['median_R'] if v['median_R'] is not None else '—'}  win {v['win_rate'] if v['win_rate'] is not None else '—'}")
    lamp = f"{OK}✓{END}" if not rep["diverged"] else f"{BAD}✗{END}"
    print(f"\n{BOLD}REPLAY{END}  {lamp} {rep['reproduced']}/{rep['checked']}")
    _print_superseded(rep)
    from journal.risk import JournalRiskGate
    rs = JournalRiskGate(conn).state()
    print(f"\n{BOLD}RISK TODAY{END}  day {rs['day_r']} R · streak {rs['consecutive_losses']} · "
          f"entries {rs['entries']} · {'LOCKED: ' + rs['reason'] if rs['locked'] else 'open'}")
    print(f"\n{DIM}Improve the plumbing and the data, not the thresholds: FILTERS.md values and the detector are")
    print(f"frozen until the phase-D read-out (docs/preregistration.md §7). Paper only.{END}\n")
    return 0


def cmd_retag_backfill(args) -> int:
    """Mark decisions armed before the desk's first start of a day as backfill.

    The tag exists since 2026-09-08 midday; the morning of 8 September was
    recorded by code without it, so 35 rows armed on history loaded at 08:06
    ET count as prospective. This is the one-off correction: rows of that
    date with a bar time before the given ET time get '-backfill' appended to
    their data_status, each change kept as a revision. Dry run without
    --confirm."""
    conn = L.connect(_db(args))
    day, hhmm = args.before[:10], args.before[11:16]
    rows = conn.execute("""SELECT decision_id, ts_et, symbol, data_status FROM decisions
                           WHERE substr(ts_et,1,10)=? AND substr(ts_et,12,5) < ?
                             AND (data_status IS NULL OR data_status NOT LIKE '%-backfill')
                           ORDER BY ts_et""", (day, hhmm)).fetchall()
    print(f"{len(rows)} decision(s) on {day} armed before {hhmm} ET and not yet tagged backfill")
    for r in rows[:8]:
        print(f"  {r['ts_et'][11:16]}  {r['symbol']:<6} {r['data_status']}")
    if len(rows) > 8:
        print(f"  … {len(rows) - 8} more")
    if not rows:
        return 0
    if not args.confirm:
        print(f"{DIM}dry run — re-run with --confirm to tag them{END}"); return 2
    for r in rows:
        new = f"{r['data_status'] or 'live'}-backfill"
        conn.execute("UPDATE decisions SET data_status=? WHERE decision_id=?", (new, r["decision_id"]))
        conn.execute("""INSERT INTO decision_revisions (decision_id, recorded_at, data_status, verdict,
                            killed_by, plan_allowed, outcome, last, bid, ask, gates_json, warnings_json, inputs_json)
                        SELECT decision_id, ?, data_status, verdict, killed_by, plan_allowed, outcome, last,
                               bid, ask, gates_json, warnings_json, inputs_json FROM decisions WHERE decision_id=?""",
                     (datetime.now(timezone.utc).isoformat(timespec="seconds"), r["decision_id"]))
    conn.commit()
    f = L.funnel(conn)
    print(f"{OK}tagged {len(rows)}{END} · now {f['plans_prospective']} prospective, {f['plans_backfill']} backfill")
    return 0


def cmd_state(args) -> int:
    conn = L.connect(_db(args))
    for k, v in L.get_state(conn).items():
        print(f"  {k:<14} {v}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", help="ledger path (default $JOURNAL_DB or data/journal.sqlite)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("replay"); r.add_argument("fixture"); r.add_argument("--risk", type=float, default=20.0)
    sub.add_parser("check"); sub.add_parser("report"); sub.add_parser("advance"); sub.add_parser("state")
    sub.add_parser("stuck"); sub.add_parser("review")
    ms = sub.add_parser("missed", help="what the plans not taken went on to do, per row and per reason")
    ms.add_argument("--day", help="ET date, e.g. 2026-09-22 (default: the latest day in the ledger)")
    ms.add_argument("--all", action="store_true", help="also list killed plans whose trigger was never touched")
    ah = sub.add_parser("ah-exit", help="manual exit of one held position; --market inside regular hours needs no desk")
    ah.add_argument("order_id", type=int); ah.add_argument("--confirm", action="store_true")
    ah.add_argument("--market", action="store_true", help="SELL at market, SMART-routed, 09:30-16:00 ET only")
    df = sub.add_parser("defect", help="mark a closed fill's exit as a code defect's (kept in P&L, out of the A3 kill rule)")
    df.add_argument("order_id", type=int); df.add_argument("--note", required=True); df.add_argument("--confirm", action="store_true")
    ru = sub.add_parser("reset-unprotected", help="restart the B→C 'zero unprotected fills' count at a named defect fix")
    ru.add_argument("--fix", required=True, help="the commit that fixed the defect, e.g. d408644")
    ru.add_argument("--confirm", action="store_true")
    a1 = sub.add_parser("accept-a1", help="record the owner's acceptance of amendment A1 (monitored pre-market exit)")
    a1.add_argument("--confirm", action="store_true")
    rb = sub.add_parser("retag-backfill", help="tag decisions armed before the desk's first start of a day as backfill")
    rb.add_argument("--before", required=True, help="ET, e.g. 2026-09-08T08:06 — the desk's first start that day")
    rb.add_argument("--confirm", action="store_true")
    lv = sub.add_parser("live"); lv.add_argument("--risk", type=float, default=20.0)
    lv.add_argument("--trade", action="store_true", help="place paper orders (default: LOG_ONLY)")
    lv.add_argument("--every", type=int, default=5)
    args = ap.parse_args(argv)
    return {"replay": cmd_replay, "check": cmd_check, "report": cmd_report, "live": cmd_live,
            "advance": cmd_advance, "state": cmd_state, "stuck": cmd_stuck, "review": cmd_review,
            "missed": cmd_missed, "defect": cmd_defect, "reset-unprotected": cmd_reset_unprotected,
            "ah-exit": cmd_ah_exit, "accept-a1": cmd_accept_a1,
            "retag-backfill": cmd_retag_backfill}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
