"""Why a configuration fails, and where it might work — PREREGISTRATION.md §7.

Everything here reads train or validation trades, never a holdout that stayed shut.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from candidates.data import minute


def mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def stats(ts: list[dict]) -> dict:
    """The decomposition of one set of trades (a portfolio)."""
    n = len(ts)
    if not n:
        return {"n": 0}
    net = [t["net"] for t in ts]
    wins = [x for x in net if x > 0]
    losses = [x for x in net if x <= 0]
    mfe = sorted(t["mfe"] for t in ts)
    reached = [t for t in ts if t["mfe"] >= 1.0]
    best_first = sorted(net, reverse=True)
    rest = best_first[max(1, n // 20):]
    rnd = [t for t in ts if t.get("rnd") is not None]
    years = defaultdict(list)
    for t in ts:
        years[t["day"][:4]].append(t["net"])
    return {
        "n": n, "net": mean(net), "gross": mean(t["gross"] for t in ts),
        "comm": mean(t["comm"] for t in ts), "spread": mean(t["spread"] for t in ts),
        "win": len(wins) / n, "avg_win": mean(wins) if wins else None, "avg_loss": mean(losses) if losses else None,
        "mfe_med": mfe[n // 2], "mfe1": len(reached) / n,
        "gave_back": (sum(1 for t in reached if t["gross"] <= 0) / len(reached)) if reached else None,
        "wo_top5": mean(rest) if rest else None, "worst": min(net),
        "beyond1": sum(1 for t in ts if t["gross"] < -1.0 - 1e-9),
        "rnd": mean(t["rnd"] for t in rnd) if rnd else None,
        "vs_rnd": mean(t["net"] - t["rnd"] for t in rnd) if rnd else None,
        "why": {k: v / n for k, v in Counter(t["why"] for t in ts).most_common()},
        "years": {y: (mean(v), len(v)) for y, v in sorted(years.items())},
    }


def compact(s: dict) -> dict:
    """What the registry keeps of `stats`."""
    if not s.get("n"):
        return {"n": 0}
    keep = ("n", "net", "gross", "comm", "spread", "win", "mfe_med", "vs_rnd", "rnd")
    return {k: (round(s[k], 6) if isinstance(s.get(k), float) else s.get(k)) for k in keep}


# ------------------------------------------------------------------ slices (fixed with the runner, before any run)
def _bucket(x, edges, labels, missing="?"):
    if x is None or x != x:
        return missing
    for e, lab in zip(edges, labels):
        if x < e:
            return lab
    return labels[-1]


DIMS = {
    "year": lambda t: t["day"][:4],
    "time": lambda t: _bucket(t["fill_min"], [minute(9, 30), minute(10, 0), minute(11, 0), minute(12, 0), minute(14, 0), 10_000],
                              ["pre-09:30", "09:30-10", "10-11", "11-12", "12-14", "14-16"]),
    "price": lambda t: _bucket(t["entry"], [2, 5, 10, 20, 1e9], ["<$2", "$2-5", "$5-10", "$10-20", "$20+"]),
    "stop%": lambda t: _bucket(t["risk_pct"], [3, 6, 10, 20, 1e9], ["<3", "3-6", "6-10", "10-20", "20+"]),
    "gap": lambda t: _bucket(None if t.get("gap") is None else 100 * t["gap"], [10, 20, 40, 100, 1e9],
                             ["<10", "10-20", "20-40", "40-100", "100+"]),
    "dv20": lambda t: _bucket(t.get("dv20"), [1e6, 5e6, 1e18], ["<$1M", "$1-5M", "$5M+"]),
}


def slices(ts: list[dict]) -> dict:
    out = {}
    for dim, f in DIMS.items():
        g = defaultdict(list)
        for t in ts:
            g[f(t)].append(t["net"])
        out[dim] = {b: (mean(v), len(v)) for b, v in sorted(g.items())}
    return out


def leads(tr: list[dict], va: list[dict], min_tr: int = 100, min_va: int = 30) -> list[tuple]:
    """Slices positive net on train AND validation, with enough trades in each — hypotheses
    for the next round, never adopted from this one."""
    st, sv = slices(tr), slices(va)
    out = []
    for dim in DIMS:
        if dim == "year":
            continue
        for b, (m_tr, n_tr) in st[dim].items():
            m_va, n_va = sv[dim].get(b, (float("nan"), 0))
            if n_tr >= min_tr and n_va >= min_va and m_tr > 0 and m_va > 0:
                out.append((dim, b, m_tr, n_tr, m_va, n_va))
    return sorted(out, key=lambda x: -min(x[2], x[4]))


# ------------------------------------------------------------------ the reading
def reading(s: dict) -> list[str]:
    """The rule-based lines of PREREGISTRATION.md §7, in its order."""
    if not s.get("n"):
        return ["no trades"]
    out = []
    cost = s["comm"] + s["spread"]
    if s["gross"] <= 0:
        out.append(f"the signal loses before costs ({s['gross']:+.3f} R gross): no cost or exit change fixes it")
    elif s["net"] <= 0:
        out.append(f"costs take it: {s['gross']:+.3f} R gross against {cost:.3f} R of costs (commission "
                   f"{s['comm']:.3f}, spread + 1c {s['spread']:.3f}); the levers are cost per R: wider stops, "
                   f"fewer orders, regular hours, higher-priced names")
    else:
        out.append(f"positive after costs here ({s['net']:+.3f} R a trade)")
    if s["mfe_med"] >= 1.0 and s["net"] <= 0:
        out.append(f"the price moves the right way first (median MFE {s['mfe_med']:.2f} R) and the exit gives it "
                   f"back: the exit is the lever")
    if s.get("vs_rnd") is not None and s["vs_rnd"] <= 0:
        out.append(f"random entries on the same names do as well ({s['vs_rnd']:+.3f} R against them): the trigger "
                   f"adds nothing, the names carry the result ({s['rnd']:+.3f} R at random)")
    if s["net"] > 0 and s.get("wo_top5") is not None and s["wo_top5"] <= 0:
        out.append(f"a lottery: without its best 5 % of trades it loses ({s['wo_top5']:+.3f} R)")
    return out
