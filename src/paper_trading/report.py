"""Performance / accuracy report generator.

Answers three questions in order of usefulness: which trades lost and why,
which winners were skipped and which rule skipped them, and which valid
signals the account never got to act on. Everything else is context.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import replay

GATE_LABELS = {
    "macd_hist<=0": "MACD histogram not positive (§3)",
    "price<=vwap": "price below VWAP (§3)",
    "price<=ema9": "price below EMA9 (§3)",
    "pullback_volume>=impulse": "pullback volume not lighter than impulse (§3)",
    "pullback_index>2": "3rd+ pullback of the move (§3)",
    "no_confluence": "fewer than 2 support reasons (§3)",
    "no_trigger": "no break of the prior candle high (§4)",
}


def _md(df: pd.DataFrame, floatfmt: str = "{:.2f}") -> str:
    if df is None or df.empty:
        return "_none_\n"
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].map(lambda v: "" if pd.isna(v) else floatfmt.format(v))
    head = "| " + " | ".join(str(c) for c in out.columns) + " |"
    rule = "|" + "|".join("---" for _ in out.columns) + "|"
    rows = ["| " + " | ".join(str(v) for v in r) + " |"
            for r in out.itertuples(index=False)]
    return "\n".join([head, rule, *rows]) + "\n"


def _gate_failures(logs: pd.DataFrame) -> pd.Series:
    """How often each §3/§4 condition was the blocker."""
    counts: dict[str, int] = {}
    for reason in logs.get("reason", pd.Series(dtype=str)).fillna(""):
        if str(reason).startswith("gate: "):
            for token in str(reason)[6:].split(","):
                counts[token] = counts.get(token, 0) + 1
    return pd.Series(counts).sort_values(ascending=False)


def missed_winners(logs: pd.DataFrame) -> pd.DataFrame:
    """SKIP decisions that would have won, with the rule that skipped them."""
    if logs.empty or "outcome_resolved" not in logs:
        return pd.DataFrame()
    resolved = logs["outcome_resolved"].fillna(False).astype(bool)
    missed = logs[(logs["verdict"] == "SKIP") & resolved
                  & (logs["outcome_r_multiple"] > 0)].copy()
    if missed.empty:
        return missed
    missed["blocked_by"] = missed["reason"].str.replace("gate: ", "", regex=False)
    return missed


def distinct_missed(logs: pd.DataFrame) -> pd.DataFrame:
    """Collapse overlapping missed winners into distinct opportunities.

    Every candle inside one move resolves profitably, so a naive count says
    "530 winners blocked" when the truth is a handful of moves counted many
    times over. Walk each symbol-session in time order and keep a signal
    only once the previous counterfactual would already have closed.
    """
    missed = missed_winners(logs)
    if missed.empty or "cursor" not in missed:
        return missed
    keep = []
    for _, grp in missed.groupby(["symbol", "session"], sort=False):
        free_at = -1
        for _, row in grp.sort_values("timestamp").iterrows():
            cursor = int(row["cursor"])
            if cursor > free_at:
                keep.append(row)
                held = row.get("outcome_bars_held", 0)
                free_at = cursor + int(held if pd.notna(held) else 0)
    return pd.DataFrame(keep)


def opportunity_cost_by_gate(logs: pd.DataFrame) -> pd.DataFrame:
    """Which single condition costs the most winners.

    A gate that blocks many winners is either mis-encoded or genuinely too
    strict — this table is what turns "the strategy skipped it" into an
    actionable finding.
    """
    missed = distinct_missed(logs)
    if missed.empty:
        return pd.DataFrame()
    rows = []
    for gate, label in GATE_LABELS.items():
        hit = missed[missed["blocked_by"].str.contains(gate, regex=False, na=False)]
        if hit.empty:
            continue
        sole = hit[hit["blocked_by"] == gate]      # the ONLY thing in the way
        rows.append({
            "token": gate,
            "gate": label,
            "winners_blocked": len(hit),
            "sole_blocker": len(sole),
            "median_R_forgone": float(hit["outcome_r_multiple"].median()),
            "total_R_forgone": float(hit["outcome_r_multiple"].sum()),
        })
    out = pd.DataFrame(rows)
    return out.sort_values("sole_blocker", ascending=False) if not out.empty else out


def losing_trade_diagnosis(trades: pd.DataFrame) -> pd.DataFrame:
    """Every loser with the mechanism that killed it."""
    if trades.empty:
        return pd.DataFrame()
    losers = trades[trades["net_pnl"] <= 0].copy()
    if losers.empty:
        return losers

    def why(row) -> str:
        if row["mfe_r"] >= 1.0:
            return f"reached +{row['mfe_r']:.1f}R then gave it back — exit too slow"
        if row["exit_reason"] in {"stop", "breakeven_stop"} and row["mfe_r"] < 0.3:
            return "never worked — stop hit with almost no favourable excursion"
        if row["exit_reason"] == "vwap_break":
            return "lost VWAP (§5 hard invalidation)"
        if row["exit_reason"] == "macd_negative":
            return "momentum rolled over before the target"
        if row["exit_reason"] == "first_candle_new_low":
            return "structure broke — first candle to make a new low (§6)"
        if row["exit_reason"] == "high_volume_red":
            return "heavy-volume red candle — sellers stepped in (§6)"
        if row["exit_reason"] == "session_end":
            return "still open at the §2 hard stop — no resolution"
        return row["exit_reason"]

    losers["diagnosis"] = losers.apply(why, axis=1)
    return losers


def build(logs: pd.DataFrame, sim: dict, *,
          symbols: list[str], sessions: list[str],
          data_note: str, generated: dt.datetime | None = None) -> str:
    """Render the full performance / accuracy report as markdown."""
    trades = sim.get("trades", pd.DataFrame())
    blocked = sim.get("blocked", pd.DataFrame())
    days = sim.get("days", pd.DataFrame())
    cfg = sim.get("config", {})
    start_eq = cfg.get("starting_equity", float("nan"))
    final_eq = sim.get("final_equity", float("nan"))
    stamp = (generated or dt.datetime.now()).strftime("%Y-%m-%d %H:%M")

    L: list[str] = []
    add = L.append

    add(f"# Performance & accuracy report\n")
    add(f"_Generated {stamp} · account ${start_eq:,.0f} · "
        f"{len(symbols)} symbol(s) · {len(sessions)} session(s)_\n")

    # ---------------------------------------------------------- provenance
    add("## Data provenance and what this cannot tell you\n")
    add(f"{data_note}\n")
    add("Inputs the free feed cannot supply are carried as UNKNOWN, never as "
        "passing:\n")
    add("- `tape_green`, `no_seller_wall` (§3) need Level 2 depth-of-book\n")
    add("- `float_max` ≤ 20M and `has_catalyst` (§1) need paid fundamentals and news\n")
    add("Every TAKE below therefore rests on an unverified assumption that those "
        "four conditions held. Treat the win rate as an upper bound.\n")

    # ---------------------------------------------------------- headline
    add("## Headline\n")
    if trades.empty:
        add("**No trades were executed.** Either no signal cleared the §3 gate, or "
            "every signal was blocked by §7/§8. The blocked table below says which.\n")
    else:
        wins = trades[trades["net_pnl"] > 0]
        losses = trades[trades["net_pnl"] <= 0]
        gross_win = float(wins["net_pnl"].sum())
        gross_loss = abs(float(losses["net_pnl"].sum()))
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
        win_rate = len(wins) / len(trades)
        headline = pd.DataFrame([{
            "trades": len(trades),
            "win_rate": win_rate,
            "expectancy_R": float(trades["r_multiple"].mean()),
            "profit_factor": pf,
            "avg_win_$": float(wins["net_pnl"].mean()) if len(wins) else 0.0,
            "avg_loss_$": float(losses["net_pnl"].mean()) if len(losses) else 0.0,
            "net_$": float(trades["net_pnl"].sum()),
            "return_%": sim.get("return_pct", float("nan")),
            "final_equity_$": final_eq,
        }])
        add(_md(headline, "{:.3f}"))
        sc = replay.score(logs)
        nominal = sc.get("breakeven_win_rate_nominal", 1 / (1 + replay.MIN_REWARD_RISK))
        realized_rr = sc.get("realized_reward_risk", float("nan"))
        breakeven = sc.get("breakeven_win_rate", nominal)
        add(f"\n§9's breakeven win rate is **{nominal:.1%}** at the 2:1 the rules "
            f"aim for. But the reward:risk actually achieved here was "
            f"**{realized_rr:.2f}:1**"
            + ("" if np.isfinite(realized_rr) else " (not yet measurable)")
            + f", which moves the real breakeven to **{breakeven:.1%}**. "
            f"This sample ran **{win_rate:.1%}** over **{len(trades)}** trades — "
            f"{'above' if win_rate > breakeven else 'below'} it.\n")
        add(f"\nScaling half the position at target_1 caps the upside well below "
            f"2R while a stop still costs a full R plus costs, so the achieved "
            f"ratio is structurally lower than the target one. Judging the "
            f"result against the nominal 33.3% can pass a losing system.\n")
        if len(trades) < 20:
            add(f"\n> ⚠ **N = {len(trades)}. Not significant.** Do not read an edge "
                f"into this. The corpus claims 65–75% (§9); distinguishing that from "
                f"33% at 95% confidence needs roughly 40+ trades. This sample cannot "
                f"separate skill from noise in either direction.\n")

    # ---------------------------------------------------------- losers
    add("\n## Losing trades — what killed each one\n")
    losers = losing_trade_diagnosis(trades)
    if losers.empty:
        add("_No losing trades in this sample._\n")
    else:
        cols = ["session", "symbol", "entry_time", "entry", "stop", "shares",
                "r_multiple", "net_pnl", "mfe_r", "mae_r", "exit_reason", "diagnosis"]
        view = losers[[c for c in cols if c in losers.columns]].copy()
        if "entry_time" in view:
            view["entry_time"] = pd.to_datetime(view["entry_time"]).dt.strftime("%H:%M")
        add(_md(view))
        gave_back = losers[losers["mfe_r"] >= 1.0]
        if len(gave_back):
            add(f"\n**{len(gave_back)} of {len(losers)} losers were up ≥1R before "
                f"losing.** That is an exit problem, not an entry problem — §6's "
                f"scale-at-target never fired, or fired too late. This is the single "
                f"most fixable line item in the report.\n")

    # ---------------------------------------------------------- missed
    add("\n## Winners that were skipped — and the rule that skipped them\n")
    raw = len(missed_winners(logs))
    distinct = len(distinct_missed(logs))
    if raw:
        add(f"_{raw:,} profitable SKIP candles collapse to **{distinct:,} distinct "
            f"opportunities** — every candle inside one move resolves profitably, "
            f"so the raw count would overstate this by {raw / max(distinct, 1):.0f}×._\n")
    oc = opportunity_cost_by_gate(logs)
    if oc.empty:
        add("_No resolved winning setups were skipped._\n")
    else:
        add(_md(oc, "{:.2f}"))
        add("\n`sole_blocker` is the column that matters: those are winners where "
            "that condition was the **only** thing in the way. A high count there "
            "means the rule is either mis-encoded or genuinely costing money — "
            "and per §12.3 you investigate it, you do not quietly relax it.\n")

    # ---------------------------------------------------------- never seen
    add("\n## Signals the account never got to trade\n")
    if blocked.empty:
        add("_Every valid signal was actionable._\n")
    else:
        agg = blocked.groupby("reason").agg(
            signals=("reason", "size"),
            median_would_be_R=("would_be_r", "median"),
            total_would_be_R=("would_be_r", "sum"),
            total_would_be_usd=("would_be_pnl", "sum"),
        ).reset_index().sort_values("signals", ascending=False)
        add(_md(agg, "{:.2f}"))
        add("\nThese are not strategy failures — they are capacity limits. §7 caps "
            "the day at two trades and only one position is held at a time, so a "
            "third good setup is unreachable by construction. If "
            "`total_would_be_usd` is large and positive, the binding constraint on "
            "this account is **capacity, not signal quality**.\n")
        cols = ["session", "symbol", "timestamp", "reason", "detail",
                "would_be_r", "would_be_pnl"]
        view = blocked[[c for c in cols if c in blocked.columns]].copy()
        if "timestamp" in view:
            view["timestamp"] = pd.to_datetime(view["timestamp"]).dt.strftime("%m-%d %H:%M")
        add("\n<details><summary>Every blocked signal</summary>\n\n")
        add(_md(view.head(60)))
        add("\n</details>\n")

    # ---------------------------------------------------------- diagnostics
    add("\n## Diagnostics\n")

    add("\n### Exit attribution — where the R actually came from\n")
    if trades.empty:
        add("_no trades_\n")
    else:
        ex = trades.groupby("exit_reason").agg(
            n=("r_multiple", "size"), total_R=("r_multiple", "sum"),
            mean_R=("r_multiple", "mean"), net=("net_pnl", "sum"),
        ).reset_index().sort_values("total_R", ascending=False)
        add(_md(ex, "{:.2f}"))

    add("\n### Are stops being hit by noise?\n")
    if trades.empty:
        add("_no trades_\n")
    else:
        wins = trades[trades["net_pnl"] > 0]
        add(f"- Median MAE of **winning** trades: "
            f"**{wins['mae_r'].median():.2f}R**"
            if len(wins) else "- No winners to measure MAE on.")
        add(f"\n- Median MFE of **losing** trades: "
            f"**{trades[trades['net_pnl'] <= 0]['mfe_r'].median():.2f}R**\n"
            if (trades["net_pnl"] <= 0).any() else "\n")
        add("\nIf winners routinely dip below −0.5R before working, the §5 stop at "
            "the pullback low is inside the noise band and is converting winners "
            "into losers. If losers rarely exceed +0.3R, entries are simply early.\n")

    add("\n### Time of day vs the §2 prime window\n")
    if trades.empty:
        add("_no trades_\n")
    else:
        t = trades.copy()
        t["bucket"] = pd.to_datetime(t["entry_time"]).dt.strftime("%H:%M").str[:4] + "0"
        tod = t.groupby("bucket").agg(n=("r_multiple", "size"),
                                      total_R=("r_multiple", "sum"),
                                      mean_R=("r_multiple", "mean")).reset_index()
        add(_md(tod, "{:.2f}"))
        add("\n§2 puts the edge in 09:30–10:30. If mean R is negative after 10:30, "
            "the hard stop should move earlier, not later.\n")

    add("\n### What the gate rejected, across every candle\n")
    gf = _gate_failures(logs)
    if gf.empty:
        add("_no gate failures recorded_\n")
    else:
        total = len(logs)
        gate_df = pd.DataFrame({
            "condition": [GATE_LABELS.get(k, k) for k in gf.index],
            "candles_blocked": gf.values,
            "pct_of_decisions": (gf.values / total * 100.0),
        })
        add(_md(gate_df, "{:.1f}"))
        add(f"\nOut of **{total:,}** candle decisions. A condition sitting at ~100% "
            "is a red flag: it means the gate can effectively never open, which "
            "looks identical to 'the strategy is selective' from the outside. "
            "That exact failure was found and fixed in the pullback counter.\n")

    add("\n### Cost drag — what the spread does to an 8-cent stop\n")
    if trades.empty:
        add("_no trades_\n")
    else:
        t = trades.copy()
        round_trip = 2 * (replay.SLIPPAGE_PER_SHARE + replay.COMMISSION_PER_SHARE)
        t["cost_R"] = round_trip / t["risk_per_share"]
        add(f"- Round-trip cost is **${round_trip:.3f}/share** "
            f"(${replay.SLIPPAGE_PER_SHARE:.2f} slippage + "
            f"${replay.COMMISSION_PER_SHARE:.3f} commission, each way).\n")
        add(f"- Median stop distance: **${float(t['risk_per_share'].median()):.3f}** "
            f"→ costs eat **{float(t['cost_R'].median()):.2f}R** per round trip.\n")
        add(f"\nThat is the number that decides whether this strategy is viable. "
            f"§5 wants a $0.08–0.10 stop; at $0.08 the round trip costs "
            f"{round_trip / 0.08:.2f}R, so a \"1R\" loss is really "
            f"{1 + round_trip / 0.08:.2f}R and §9's breakeven win rate moves from "
            f"33.3% to roughly {(1 + round_trip / 0.08) / (1 + round_trip / 0.08 + 2.0):.1%}. "
            f"Tight stops do not reduce risk here — they amplify the cost ratio.\n")

    add("\n### Sizing — which constraint actually bound\n")
    if trades.empty:
        add("_no trades_\n")
    else:
        if "size_bound_by" in trades:
            bound = trades["size_bound_by"].value_counts().rename_axis(
                "bound_by").reset_index(name="trades")
            add(_md(bound, "{:.0f}"))
        notional = trades["shares"] * trades["entry"]
        add(f"\n- Median position: **{int(trades['shares'].median()):,} shares**, "
            f"**${float(notional.median()):,.0f}** notional on a "
            f"${start_eq:,.0f} account "
            f"(**{float((notional / trades['equity_before']).median() * 100):.0f}%** "
            f"of equity).\n")
        add("\nWhen anything other than `risk` binds, §7's risk-based sizing is "
            "not what is being traded: realised risk per trade is below the "
            "intended 2%, and §9's expectancy scales down with it. When "
            "`liquidity` binds, the position is limited by what the tape could "
            "actually absorb — §7 concedes this itself, warning that fill "
            "quality degrades on sub-20M float and that the edge does not scale "
            "linearly. A backtest without that cap reports fills that never "
            "existed.\n")

    # ---------------------------------------------------------- accuracy
    add("\n## Decision accuracy (confusion matrix)\n")
    s = replay.score(logs)
    if s.get("n_decisions", 0) == 0:
        add("_no decisions_\n")
    else:
        cm = pd.DataFrame([
            {"": "TAKE", "won": s["true_positive"], "lost": s["false_positive"]},
            {"": "SKIP", "won": s["false_negative"], "lost": s["true_negative"]},
        ])
        add(_md(cm, "{:.0f}"))
        add(f"\n- precision **{s['precision']:.3f}** — of setups taken, the share "
            f"that won\n")
        n_distinct = len(distinct_missed(logs))
        taken = s["true_positive"]
        denom = taken + n_distinct
        dedup_recall = taken / denom if denom else float("nan")
        add(f"- recall **{dedup_recall:.3f}** — of the **{denom}** distinct "
            f"winning opportunities, the share actually taken\n")
        add(f"- raw candle recall **{s['recall']:.3f}** — the same figure before "
            f"overlapping candles inside a single move are collapsed. It "
            f"understates recall and is shown only so the two are not "
            f"confused\n")
        add(f"- decisions evaluated: **{s['n_decisions']:,}** across "
            f"{len(symbols)} symbol(s)\n")
        add("\nLow recall with high precision means the rules are leaving money on "
            "the table but are not wrong. High recall with low precision means the "
            "opposite. They are different problems with different fixes.\n")

    # ---------------------------------------------------------- days
    add("\n## Day by day (§8 risk gate)\n")
    if days.empty:
        add("_no sessions_\n")
    else:
        d = days.copy()
        d["pnl"] = d["end_equity"] - d["start_equity"]
        cols = ["date", "trades", "start_equity", "end_equity", "pnl",
                "consecutive_losses", "locked", "lock_reason"]
        add(_md(d[[c for c in cols if c in d.columns]]))
        locked_days = int(d["locked"].sum()) if "locked" in d else 0
        if locked_days:
            add(f"\n**The §8 risk gate locked the account on {locked_days} day(s).** "
                "That is the rule working as designed — every signal after the lock "
                "appears in the blocked table above.\n")

    add("\n---\n")
    add("_Generated by the blinded walk-forward replay "
        "(`scripts/paper_trade_eval.py`). Decisions were made candle by candle "
        "with the future hidden; no bar after the cursor influenced any verdict._\n")
    return "\n".join(L)
