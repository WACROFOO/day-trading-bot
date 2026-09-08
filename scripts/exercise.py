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
def report(conn, *, source: str, synthetic: bool) -> None:
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
           synthetic=synthetic)
    return 0


def cmd_check(args) -> int:
    conn = L.connect(_db(args))
    rep = replay.check(conn)
    for d in rep["diverged"]:
        print(f"{BAD}✗{END} {d}")
    print(f"{rep['reproduced']}/{rep['checked']} reproduced")
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
                acted = []
            except KeyboardInterrupt:
                raise
            except Exception as exc:                     # noqa: BLE001
                # The runner is idempotent: pending() re-offers unfinished rows.
                # A locked database or a malformed row must not end the day —
                # and until now it also took the desk (the recorder) down.
                errors += 1
                print(f"  {datetime.now(ET):%H:%M:%S}  {WARN}runner error{END} {exc!r} — retrying"
                      + (f" ({errors} in a row)" if errors > 1 else ""))
                time.sleep(min(30, args.every * errors))
                continue
            for a in acted:
                tag = {"TAKEN": OK, "REFUSED": WARN, "LOG_ONLY": DIM}.get(a.outcome, "")
                print(f"  {a.ts_et[11:16]}  {a.symbol:<6} {tag}{a.outcome:<8}{END} "
                      f"{a.trigger:.2f}/{a.stop:.2f}"
                      + (f"  ✗ {'; '.join(a.reasons)[:90]}" if a.reasons else ""))
            if args.trade:
                runner.sync_fills()
                for line in runner.reconcile_positions():
                    print(f"  {datetime.now(ET):%H:%M:%S}  {BAD}RECONCILE{END} {line}")
                # The monitored stop lives here and nowhere else: for a
                # `queued`-verdict pre-market entry this call IS the stop.
                for line in runner.watch_stops():
                    print(f"  {datetime.now(ET):%H:%M:%S}  {WARN}STOP{END}     {line}")
                for oid in runner.flag_after_hours():
                    print(f"  {datetime.now(ET):%H:%M:%S}  {BAD}HELD AFTER CLOSE{END} order {oid} — "
                          f"exercise.py ah-exit {oid} --confirm")
                if datetime.now(ET).time() >= HARD_STOP and not flattened:
                    done = runner.end_of_day()
                    print(f"  {WARN}HARD STOP{END} flattened: {done or 'nothing open'}")
                    flattened = True
            time.sleep(args.every)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        if trader is not None:
            trader.disconnect()
    return 0


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
              f"stop {o['stop']}  status {o['stop_status']}")
    return 0


def cmd_ah_exit(args) -> int:
    """The after-hours exception, brief R10: exit-only, one order, a human
    confirms it here, and who confirmed is written into the ledger."""
    conn = L.connect(_db(args))
    o = conn.execute("SELECT * FROM orders WHERE order_id=?", (args.order_id,)).fetchone()
    if o is None:
        print(f"{BAD}no order {args.order_id}{END}"); return 1
    if o["fill_price"] is None or o["exit_ts"] is not None:
        print(f"{BAD}order {args.order_id} is not a held position{END}"); return 1
    if not args.confirm:
        print(f"{WARN}MANUAL_CONFIRMATION_REQUIRED{END}  {o['symbol']} x{o['shares']} filled {o['fill_price']}")
        print("  after hours: no stops exist, margin is auto-liquidated at 16:00, and the")
        print("  source is measured not net profitable there. Re-run with --confirm to SELL")
        print("  at bid − 0.10, limit, extended hours. This is an exit; nothing is bought.")
        return 2
    q = L.quote_source(conn, max_age_s=120)(o["symbol"])
    if not q or q.get("bid") is None:
        print(f"{BAD}no fresh quote for {o['symbol']} in the ledger — start the desk first{END}"); return 1
    from execution.ibkr_trader import PaperTrader
    who = os.environ.get("USER") or "operator"
    qty = int(o["filled_qty"]) if o["filled_qty"] else int(o["shares"])
    with PaperTrader() as t:
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
    L.record_exit(conn, o["order_id"], reason="AH_exception", price=fill if fill else px,
                  ts=datetime.now(timezone.utc), confirmed_by=who,
                  confirmed=fill is not None, exit_order_id=exit_id)
    L.add_order_event(conn, o["order_id"], f"AH exception confirmed by {who}: SELL LMT {px} x{qty} (bid {q['bid']})"
                      + (f"; filled {fill}" if fill else "; fill NOT yet seen — row is ExitPending"))
    conn.commit()
    print(f"{OK}sent{END} SELL {qty} {o['symbol']} LMT {px}  recorded as AH_exception by {who}"
          + (f" · filled {fill}" if fill else f" · {WARN}fill not yet seen; check exercise.py stuck{END}"))
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
    print(f"\n{BOLD}CONTROLS{END}  (planned R · same rows)")
    for k, v in ctl.items():
        print(f"  {k:<12} n={v['n']:<4} mean {v['mean_R'] if v['mean_R'] is not None else '—'}  "
              f"median {v['median_R'] if v['median_R'] is not None else '—'}  win {v['win_rate'] if v['win_rate'] is not None else '—'}")
    lamp = f"{OK}✓{END}" if not rep["diverged"] else f"{BAD}✗{END}"
    print(f"\n{BOLD}REPLAY{END}  {lamp} {rep['reproduced']}/{rep['checked']}")
    from journal.risk import JournalRiskGate
    rs = JournalRiskGate(conn).state()
    print(f"\n{BOLD}RISK TODAY{END}  day {rs['day_r']} R · streak {rs['consecutive_losses']} · "
          f"entries {rs['entries']} · {'LOCKED: ' + rs['reason'] if rs['locked'] else 'open'}")
    print(f"\n{DIM}Improve the plumbing and the data, not the thresholds: FILTERS.md values and the detector are")
    print(f"frozen until the phase-D read-out (docs/preregistration.md §7). Paper only.{END}\n")
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
    ah = sub.add_parser("ah-exit"); ah.add_argument("order_id", type=int); ah.add_argument("--confirm", action="store_true")
    a1 = sub.add_parser("accept-a1", help="record the owner's acceptance of amendment A1 (monitored pre-market exit)")
    a1.add_argument("--confirm", action="store_true")
    lv = sub.add_parser("live"); lv.add_argument("--risk", type=float, default=20.0)
    lv.add_argument("--trade", action="store_true", help="place paper orders (default: LOG_ONLY)")
    lv.add_argument("--every", type=int, default=5)
    args = ap.parse_args(argv)
    return {"replay": cmd_replay, "check": cmd_check, "report": cmd_report, "live": cmd_live,
            "advance": cmd_advance, "state": cmd_state, "stuck": cmd_stuck, "review": cmd_review,
            "ah-exit": cmd_ah_exit, "accept-a1": cmd_accept_a1}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
