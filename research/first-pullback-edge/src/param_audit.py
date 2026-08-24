"""Parameter inventory and degrees-of-freedom estimate (brief section 22).

Reads config/strategy.yaml - which carries a `provenance` tag and a Pine line
number on every value - and cross-checks it against the markers the Pine puts
on its own inputs. Anything the script itself labels `[UNTESTED local]` is a
knob somebody chose, and the study says so.

Effective degrees of freedom is deliberately crude: it counts the parameters
that could have been moved to change results, weighted by how free they were.
A precise number would be false precision; the point is the order of magnitude
against the sample size.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent
PINE = REPO / "knowledge-base" / "tradingview" / "ross-fp-v4.pine"

# What each config section affects, for the section-22 breakdown.
AFFECTS = {
    "universe": "universe selection",
    "impulse": "entry",
    "pullback": "entry",
    "momentum": "entry",
    "confluence": "entry",
    "hod_room": "entry",
    "risk": "stop / sizing",
    "execution": "entry / exit",
    "lanes": "entry",
    "session": "entry / exit",
    "governor": "exit / risk",
    "costs": "study only",
    "ambiguity": "study only",
    "splits": "study only",
}

# provenance -> section-22 class
CLASS = {
    "sourced": "externally sourced rule",
    "measured": "empirically validated",
    "local": "local heuristic",
    "study": "study parameter (not the strategy's)",
    "display": "display-only",
}

# How much freedom each class represents, for the DoF estimate. A sourced
# threshold quoted verbatim by the trader is not a free parameter; a local
# heuristic with a plausible range is close to fully free.
FREEDOM = {"externally sourced rule": 0.2, "empirically validated": 0.3,
           "local heuristic": 1.0, "study parameter (not the strategy's)": 0.0,
           "display-only": 0.0}


def pine_untested_markers() -> set[int]:
    """Line numbers whose input the Pine itself flags as untested/local."""
    if not PINE.exists():
        return set()
    out = set()
    for n, line in enumerate(PINE.read_text().splitlines(), 1):
        if re.search(r"\[(UNTESTED local|local[^]]*|UNCALIBRATED)\]", line):
            out.add(n)
    return out


def inventory(cfg: dict) -> list[dict]:
    marked = pine_untested_markers()
    rows = []
    for section, body in cfg.items():
        if section in ("meta", "seed", "variants"):
            continue
        if not isinstance(body, dict):
            continue
        for key, node in body.items():
            if not isinstance(node, dict):
                continue
            if "value" not in node:
                # nested block (ladder, arm_window_et, scenarios ...)
                if "pine" in node or "provenance" in node:
                    node = {"value": str({k: v for k, v in node.items()
                                          if k not in ("pine", "provenance")}),
                            **node}
                else:
                    continue
            prov = node.get("provenance", "local")
            cls = CLASS.get(prov, prov)
            line = node.get("pine")
            rows.append(dict(
                section=section, parameter=key, value=node.get("value"),
                affects=AFFECTS.get(section, "unclassified"),
                provenance=prov, classification=cls,
                pine_line=line,
                pine_flags_it_local=bool(line and line in marked),
                freedom_weight=FREEDOM.get(cls, 0.5)))
    return rows


def degrees_of_freedom(rows: list[dict]) -> dict:
    strategy_rows = [r for r in rows
                     if r["classification"] != "study parameter (not the strategy's)"]
    eff = sum(r["freedom_weight"] for r in strategy_rows)
    counts: dict[str, int] = {}
    for r in strategy_rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    return dict(
        total_strategy_parameters=len(strategy_rows),
        by_class=counts,
        effective_degrees_of_freedom=round(eff, 1),
        note=("A rough weight, not a statistic: sourced thresholds count 0.2, "
              "measured 0.3, local heuristics 1.0. The comparison that matters "
              "is against the number of independent SESSIONS in the sample, "
              "not the number of trades - trades inside one session are not "
              "independent observations of a parameter choice."))


def load(path: Path | None = None) -> dict:
    return yaml.safe_load((path or (ROOT / "config" / "strategy.yaml")).read_text())


if __name__ == "__main__":
    import csv
    import json

    cfg = load()
    rows = inventory(cfg)
    out = ROOT / "results"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "parameter_inventory.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    dof = degrees_of_freedom(rows)
    (out / "degrees_of_freedom.json").write_text(json.dumps(dof, indent=2))
    print(json.dumps(dof, indent=2))
    for cls in sorted({r["classification"] for r in rows}):
        names = [f"{r['section']}.{r['parameter']}" for r in rows
                 if r["classification"] == cls]
        print(f"\n{cls} ({len(names)}):")
        print("  " + ", ".join(names))
