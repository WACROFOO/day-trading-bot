"""R5: the free baselines every result has to beat before it means anything.

`2026-08-score-basket.md`: equal weight beat the pillar score in 16 of 16
matched pairs. A selection rule that loses to its own equal-weight baseline
looks identical to one that works until the baseline is run, so it is run
here, on the same decisions, from the same actuals, in the same units.

Three series, all in PLANNED R so they are comparable to each other:

  strategy    the plan as armed: +target_R if the target was hit first,
              −1 if the stop was hit first, else the close in R
  hold_close  enter at the trigger, no stop, no target, sell at the close.
              Same names, same instants — isolates what the stop and target
              add or cost
  random_bar  enter at the CLOSE of the decision bar instead of the trigger,
              same stop distance, same close. Isolates the trigger

DEFINITIONS, stated after the 2026-09-21 external review asked for them
(each is a fact about the code below, not a choice defended here):

  entry       the plan's trigger, on the first bar strictly after the
              decision bar whose HIGH touches it (`actuals.compute`). A plan
              the tape never touched is not in any series ("untriggered").
  "close"     `actuals.c_close` = the close of the LAST bar the desk recorded
              for that symbol on the decision's ET date. The desk stops
              writing bars when `scripts/day.py` ends at the 11:30 ET hard
              stop, so in a normal session this is the 11:30 cutoff, NOT the
              16:00 market close. If the desk was stopped earlier or ran
              later, it is that moment instead; the report prints the last
              bar time so the reader can tell.
  hold_close  keeps NO stop. It is exposure from the trigger to the cutoff
              with nothing in between. So the +6.3 R against the strategy's
              +0.46 R in the 2026-09-21 pack is the effect of removing the
              stop AND the target together, not of the target alone.
  random_bar  keeps NO stop either, and enters at the decision bar's own
              close (`decisions.last`) instead of the trigger; the risk
              denominator is the plan's trigger − stop, which was knowable at
              that bar because the plan was armed on it. Hold_close and
              random_bar therefore differ ONLY in entry price; their gap is
              the value of waiting for the trigger, nothing else.
  costs       none, in every series: no spread, no commission, no slippage,
              a fill exactly at the level. Every series is optimistic by the
              same amount and none is a claim about a fillable price.

`exit_variants` below is the comparison the review asked for: three exit
rules on the SAME entry fill, SAME initial stop and SAME cutoff, differing
in nothing but the exit — baseline (fixed +2 R target), no_target (stop
only) and trail_1r (Amendment A3, simulated bar by bar with no within-bar
look-ahead). They are simulations on the desk's tape; the trailing exit that
runs live is `execution.runner.Runner.trail_stops`.

No confidence intervals are computed. With the sample sizes this exercise
will have for months, a CI would be decoration; the honest output is n and
the raw series, and the reader is told that.
"""

from __future__ import annotations

import sqlite3
import json
from statistics import mean, median

from . import ledger as L


def series(conn: sqlite3.Connection, cohort: str | None = None) -> dict[str, list[float]]:
    """cohort: None = every prospective decision; 'allowed' = the cascade let
    the plan through; 'killed' = the cascade suppressed it. Backfill rows
    (armed on loaded history) are never in any series (audit F3)."""
    where = ""
    if cohort == "allowed":
        where = "AND d.plan_allowed = 1"
    elif cohort == "killed":
        where = "AND d.plan_allowed = 0"
    elif cohort == "news":            # A2: gate 3 flags; these two split by what it said
        where = "AND d.catalyst = 1"
    elif cohort == "no-news":
        where = "AND d.catalyst = 0"
    rows = conn.execute(f"""
        SELECT d.decision_id, d.trigger, d.stop, d.target, d.last, d.reward_multiple,
               a.first_hit, a.c_close, a.risk_share
        FROM decisions d JOIN actuals a USING(decision_id)
        WHERE a.risk_share IS NOT NULL AND a.risk_share > 0
          AND COALESCE(a.trigger_hit, 1) = 1
          AND (d.data_status IS NULL OR d.data_status NOT LIKE '%-backfill')
          {where}
    """).fetchall()
    # Plans whose trigger was never touched are not trades; they are counted
    # separately (see summary) instead of being charged −1 R.
    out = {"strategy": [], "hold_close": [], "random_bar": []}
    for r in rows:
        rps = r["risk_share"]
        close_r = (r["c_close"] - r["trigger"]) / rps
        if r["first_hit"] == "stop":
            strat = -1.0
        elif r["first_hit"] == "target" and r["target"]:
            strat = (r["target"] - r["trigger"]) / rps
        else:
            strat = close_r
        out["strategy"].append(round(strat, 4))
        out["hold_close"].append(round(close_r, 4))
        if r["last"]:
            out["random_bar"].append(round((r["c_close"] - r["last"]) / rps, 4))
    return out


# ---------------------------------------------------------------- exit variants
TRAIL_R_SIM = 1.0          # mirrors execution.intent.TRAIL_R; a simulation, restated here on purpose
VARIANTS = ("baseline", "no_target", "trail_1r")


def simulate_exit(entry_bars: list, trigger: float, stop: float, variant: str,
                  target: float | None = None, trail_r: float = TRAIL_R_SIM) -> dict:
    """One trade, one exit rule, bar by bar from the ENTRY bar onward.

    `entry_bars` are (ts, o, h, l, c, v) starting at the bar whose high first
    touched the trigger. The fill is at the trigger; exits fill at their level
    with no slippage (stated in the module docstring).

    Ordering inside a bar is unknown, so every bar is judged in the order
    that cannot flatter the rule: the LOW is tested against the stop that was
    in force BEFORE the bar, and only then may the bar's HIGH raise a trailing
    stop or hit a target. A bar that touches both stop and target counts the
    stop (same convention as `actuals.compute`).

    Returns {"r", "exit", "bars_held"}; exit is stop | trail | target | close.
    """
    rps = trigger - stop
    if rps <= 0 or not entry_bars:
        return {"r": None, "exit": "none", "bars_held": 0}
    live_stop = stop
    for i, (ts, o, h, l, c, v) in enumerate(entry_bars):
        # 1. the stop in force before this bar
        if l <= live_stop:
            why = "trail" if variant == "trail_1r" and live_stop > stop else "stop"
            return {"r": round((live_stop - trigger) / rps, 4), "exit": why, "bars_held": i + 1}
        # 2. the target, this bar's high
        if variant == "baseline" and target is not None and h >= target:
            return {"r": round((target - trigger) / rps, 4), "exit": "target", "bars_held": i + 1}
        # 3. only now may this bar's high raise the trail
        if variant == "trail_1r":
            live_stop = max(live_stop, round(h - trail_r * rps, 4))
    last_close = entry_bars[-1][4]
    return {"r": round((last_close - trigger) / rps, 4), "exit": "close", "bars_held": len(entry_bars)}


def exit_variants(conn: sqlite3.Connection, bars_by_symbol: dict,
                  cohort: str | None = None) -> dict[str, list[dict]]:
    """The three exit rules on the same rows `series()` uses, from the same
    entry bar `actuals.compute` found. Needs the tape: the ledger stores the
    decision, not the bars (`journal.bars.from_ledger` / `from_fixture`)."""
    from . import actuals as A
    where = ""
    if cohort == "allowed":
        where = "AND d.plan_allowed = 1"
    elif cohort == "killed":
        where = "AND d.plan_allowed = 0"
    rows = conn.execute(f"""
        SELECT d.decision_id, d.symbol, d.ts_et, d.trigger, d.stop, d.target, a.risk_share, a.trigger_hit_ts
        FROM decisions d JOIN actuals a USING(decision_id)
        WHERE a.risk_share IS NOT NULL AND a.risk_share > 0
          AND COALESCE(a.trigger_hit, 1) = 1 AND a.trigger_hit_ts IS NOT NULL
          AND (d.data_status IS NULL OR d.data_status NOT LIKE '%-backfill')
          {where}
    """).fetchall()
    out: dict[str, list[dict]] = {v: [] for v in VARIANTS}
    for r in rows:
        bars = bars_by_symbol.get(r["symbol"], [])
        day = r["ts_et"][:10]
        fwd = [b for b in A.forward(bars, A._utc(r["ts_et"]))
               if A._bar_dt(b[0]).astimezone(L.ET).date().isoformat() == day]
        entry = [b for b in fwd if b[0] >= r["trigger_hit_ts"]]
        if not entry:
            continue
        trigger, stop = float(r["trigger"]), float(r["stop"])
        target = float(r["target"]) if r["target"] else round(trigger + 2.0 * (trigger - stop), 4)
        for v in VARIANTS:
            res = simulate_exit(entry, trigger, stop, v, target=target)
            if res["r"] is not None:
                out[v].append({"decision_id": r["decision_id"], "symbol": r["symbol"], **res})
    return out


def per_decision(conn: sqlite3.Connection, bars_by_symbol: dict, day: str | None = None) -> list[dict]:
    """Every armed plan of `day` (or all days), whatever the runner did with
    it, with what the tape did next: was the trigger touched, best and worst
    excursion in planned R, the strategy series' R (fixed +2R target, as
    `series()` scores it) and the A3 trail_1r R from `simulate_exit`. This is
    the "missed entry" question asked of the ledger instead of memory: a
    REFUSED or SUPPRESSED row scored exactly like a TAKEN one, fill at the
    trigger, no slippage, no costs. Backfill rows are returned flagged so
    the caller can keep them out of any statistic."""
    from . import actuals as A
    where = "WHERE substr(d.ts_et, 1, 10) = ?" if day else ""
    rows = conn.execute(f"""
        SELECT d.decision_id, d.symbol, d.ts_et, d.session, d.verdict, d.outcome, d.killed_by,
               d.refusal_reasons_json, d.plan_allowed, d.data_status, d.trigger, d.stop, d.target, d.last,
               a.risk_share, a.trigger_hit, a.trigger_hit_ts, a.first_hit, a.c_close,
               a.mfe_r_planned, a.mae_r_planned, a.bars_available
        FROM decisions d LEFT JOIN actuals a USING(decision_id)
        {where} ORDER BY d.ts_et""", (day,) if day else ()).fetchall()
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        d["backfill"] = bool(r["data_status"] and r["data_status"].endswith("-backfill"))
        d["has_actuals"] = r["risk_share"] is not None
        # A9 measurement (not a gate): a stop within THIN_STOP_PCT of the
        # trigger. Such a plan sizes to a notional the account refuses and its
        # planned R inflates every excursion figure (VEEE 16.33/16.31 on
        # 09-21 showed an MFE of 326 R; GRML 17.19/17.17 on 09-22 an MAE of
        # -153 R). Counted so the amendment can be written from a number.
        rps_plan = (r["trigger"] - r["stop"]) if r["trigger"] and r["stop"] else None
        d["thin_stop"] = bool(rps_plan is not None and r["trigger"] > 0
                              and rps_plan / r["trigger"] < THIN_STOP_PCT)
        rps = r["risk_share"]
        d["strategy_r"] = d["trail_r"] = d["trail_exit"] = None
        if rps and rps > 0 and r["trigger_hit"] == 1 and r["c_close"] is not None:
            if r["first_hit"] == "stop":
                d["strategy_r"] = -1.0
            elif r["first_hit"] == "target" and r["target"]:
                d["strategy_r"] = round((r["target"] - r["trigger"]) / rps, 4)
            else:
                d["strategy_r"] = round((r["c_close"] - r["trigger"]) / rps, 4)
            bars = bars_by_symbol.get(r["symbol"], [])
            if bars and r["trigger_hit_ts"]:
                dd = r["ts_et"][:10]
                fwd = [b for b in A.forward(bars, A._utc(r["ts_et"]))
                       if A._bar_dt(b[0]).astimezone(L.ET).date().isoformat() == dd]
                entry = [b for b in fwd if b[0] >= r["trigger_hit_ts"]]
                if entry:
                    res = simulate_exit(entry, float(r["trigger"]), float(r["stop"]), "trail_1r")
                    d["trail_r"], d["trail_exit"] = res["r"], res["exit"]
        out.append(d)
    return out


THIN_STOP_PCT = 0.005      # measurement cut for the A9 count; NOT a gate, nothing refuses on it


def reason_key(d: dict) -> str:
    """One short label per row: the kill gate for a suppressed plan, the first
    refusal reason for a refused one, the outcome otherwise."""
    if d["outcome"] == "SUPPRESSED":
        return f"killed: {d['killed_by'] or '?'}"
    if d["outcome"] == "REFUSED":
        try:
            reasons = json.loads(d["refusal_reasons_json"] or "[]")
        except ValueError:
            reasons = []
        first = reasons[0] if reasons else "?"
        return "refused: " + first.split(" — ")[0].split(":")[0].split(";")[0][:44]
    return d["outcome"]


KILL_RULE_MIN_N = 10       # A3 kill rule binds from this many CLEAN fills (owner decision, delegated, 2026-09-22)


def kill_rule_read(conn: sqlite3.Connection, bars_by_symbol: dict, min_n: int = KILL_RULE_MIN_N) -> dict:
    """Amendment A3's kill rule, as amended 2026-09-22: on the CLEAN closed
    fills (no defect note), compare the live exit's mean realised R with the
    simulated `baseline` (fixed +2 R target) mean on the same fills. Printed
    from the first fill; BINDING only from `min_n` clean fills. Returns the
    per-fill rows and the verdict: READ-ONLY (n below min_n), MET (live below
    baseline — revert A3), NOT MET. Rows without actuals are listed and
    skipped in the means."""
    from . import ledger as L
    fills = L.clean_closed_fills(conn)
    excluded = conn.execute("SELECT COUNT(*) FROM orders WHERE fill_price IS NOT NULL AND status='Closed' "
                            "AND defect_note IS NOT NULL").fetchone()[0]
    by_id = {d["decision_id"]: d for d in per_decision(conn, bars_by_symbol)}
    rows, live, base, trail = [], [], [], []
    for o in fills:
        d = by_id.get(o["decision_id"])
        qty = o["filled_qty"] if o["filled_qty"] else o["shares"]
        live_r = round((o["exit_price"] - o["fill_price"]) * qty / o["planned_risk"], 4) if o["planned_risk"] else None
        row = {"order_id": o["order_id"], "symbol": o["symbol"], "fill_ts": o["fill_ts"], "exit_reason": o["exit_reason"],
               "live_r": live_r, "baseline_r": d["strategy_r"] if d else None, "trail_r": d["trail_r"] if d else None}
        rows.append(row)
        if live_r is not None and row["baseline_r"] is not None:
            live.append(live_r); base.append(row["baseline_r"])
            if row["trail_r"] is not None:
                trail.append(row["trail_r"])
    n = len(live)
    live_mean = round(mean(live), 4) if live else None
    base_mean = round(mean(base), 4) if base else None
    trail_mean = round(mean(trail), 4) if trail else None
    if n < min_n:
        verdict = "READ-ONLY"
    elif live_mean < base_mean:
        verdict = "MET"
    else:
        verdict = "NOT MET"
    return {"rows": rows, "n": n, "min_n": min_n, "excluded_defect": excluded,
            "live_mean": live_mean, "baseline_mean": base_mean, "trail_sim_mean": trail_mean, "verdict": verdict}


def exit_summary(conn: sqlite3.Connection, bars_by_symbol: dict) -> dict[str, dict]:
    """n, mean, median, share stopped, share reaching the close — per variant."""
    ev = exit_variants(conn, bars_by_symbol)
    out = {}
    for v, rows in ev.items():
        rs = [x["r"] for x in rows]
        st = _stats(rs)
        st["stopped"] = round(sum(1 for x in rows if x["exit"] in ("stop", "trail")) / len(rows), 3) if rows else None
        st["to_close"] = round(sum(1 for x in rows if x["exit"] == "close") / len(rows), 3) if rows else None
        out[v] = st
    return out


def units(conn: sqlite3.Connection) -> dict:
    """The statistical unit, made visible (review 2026-09-21, item 9). The
    strategy series has one row per triggered prospective decision; several
    rows can be one name on one morning, so the report says how many unique
    symbol-days and sessions the rows come from, gives the series per
    session, and shows what the three largest winning symbol-days contribute
    to the mean. Large winners stay in the primary result; a momentum method
    may legitimately depend on them, and the reader must be able to see it."""
    rows = conn.execute("""
        SELECT d.decision_id, d.symbol, substr(d.ts_et, 1, 10) AS day, d.trigger, d.stop, d.target,
               a.first_hit, a.c_close, a.risk_share
        FROM decisions d JOIN actuals a USING(decision_id)
        WHERE a.risk_share IS NOT NULL AND a.risk_share > 0
          AND COALESCE(a.trigger_hit, 1) = 1
          AND (d.data_status IS NULL OR d.data_status NOT LIKE '%-backfill')
    """).fetchall()
    per_row = []
    for r in rows:
        rps = r["risk_share"]
        if r["first_hit"] == "stop":
            v = -1.0
        elif r["first_hit"] == "target" and r["target"]:
            v = (r["target"] - r["trigger"]) / rps
        else:
            v = (r["c_close"] - r["trigger"]) / rps
        per_row.append((r["symbol"], r["day"], round(v, 4)))
    n = len(per_row)
    sym_days: dict[tuple, list[float]] = {}
    sessions: dict[str, list[float]] = {}
    for sym, day, v in per_row:
        sym_days.setdefault((sym, day), []).append(v)
        sessions.setdefault(day, []).append(v)
    total = sum(v for _, _, v in per_row)
    by_symday = sorted(((k, sum(v)) for k, v in sym_days.items()), key=lambda kv: -kv[1])
    top3 = by_symday[:3]
    top3_sum = sum(v for _, v in top3)
    rest = [v for (sym, day, v) in per_row if (sym, day) not in {k for k, _ in top3}]
    return {
        "rows": n,
        "unique_setups": n,                                   # one decision_id per row
        "unique_symbol_days": len(sym_days),
        "sessions": len(sessions),
        "mean_R": round(total / n, 4) if n else None,
        "per_session": {day: {"n": len(v), "mean_R": round(mean(v), 4), "median_R": round(median(v), 4)}
                        for day, v in sorted(sessions.items())},
        "top3_symbol_days": [{"symbol": k[0], "day": k[1], "sum_R": round(v, 4), "rows": len(sym_days[k])}
                             for k, v in top3],
        "top3_share_of_total": (round(top3_sum / total, 3) if total > 0 else None),
        "mean_R_without_top3": (round(mean(rest), 4) if rest else None),
    }


def last_bar_time(conn: sqlite3.Connection) -> str | None:
    """When the desk stopped writing bars — what "close" means in every series."""
    row = conn.execute("SELECT MAX(ts) FROM bars").fetchone()
    return row[0] if row and row[0] else None


def _stats(v: list[float]) -> dict:
    return {"n": len(v), "mean_R": round(mean(v), 4) if v else None,
            "median_R": round(median(v), 4) if v else None,
            "win_rate": round(sum(1 for x in v if x > 0) / len(v), 3) if v else None}


def summary(conn: sqlite3.Connection) -> dict[str, dict]:
    s = series(conn)
    out = {k: _stats(v) for k, v in s.items()}
    # The question the exercise exists to answer is whether the cascade's
    # kills were right: the same plan series, split by what the cascade said.
    # "strategy" above mixes both; these two rows separate them.
    out["strat·allowed"] = _stats(series(conn, "allowed")["strategy"])
    out["strat·killed"] = _stats(series(conn, "killed")["strategy"])
    # Amendment A2: the catalyst gate no longer kills, so whether a catalyst
    # was present is the split the read-out needs to judge the rule itself.
    out["strat·news"] = _stats(series(conn, "news")["strategy"])
    out["strat·no-news"] = _stats(series(conn, "no-news")["strategy"])
    out["untriggered"] = {"n": conn.execute(
        "SELECT COUNT(*) FROM actuals WHERE trigger_hit = 0").fetchone()[0],
        "mean_R": None, "median_R": None, "win_rate": None}
    return out
