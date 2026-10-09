"""Shadow strategies: the month study's results, logged forward, never traded.

The owner, 2026-10-09: build the best combination for a paper track record that
measures accuracy. `research/month-study/REPORT.md`:

  S6 — the best found: stop >= 3 % of price, price $2-20, armed in regular
       hours, above VWAP, pullback volume lighter than the push, still rising
       (within 25 % of the high). Exit: break-even after 1 R, then 2 R.
       Selection +0.41 R a trade on 31 trades; holdout -0.73 on 7. NOT a
       candidate under its own preregistered rule — this log is the test.
  S3 — its first three steps, the ones that cut the loss in BOTH periods:
       stop >= 3 %, price $2-20, regular hours. Same exit.

A shadow strategy reads a plan's own numbers — trigger, stop, the minute it
armed, last, VWAP, the high so far, pullback volume — and says whether it would
take it, with the levers that failed. It sends nothing and changes no gate: the
bot's rules are the bot's (docs/preregistration.md §5 decides those).
"""
from __future__ import annotations

from datetime import time
from typing import Optional

from .cascade import FADE_MAX_PCT, PRICE_MAX, PRICE_MIN
from .order_math import ENTRY_CUTOFF

RTH_OPEN = time(9, 30)
STOP_MIN_PCT = 3.0                       # the month study's SW lever, level 3 %
STILL_RISING = 1 - FADE_MAX_PCT / 100.0  # gate 4: within 25 % of the high

STRATEGIES = {
    "S6": {"label": "best found", "levers": ("price", "stop", "regular", "vwap", "pullback", "rising"), "exit": "be"},
    "S3": {"label": "wider stops", "levers": ("price", "stop", "regular"), "exit": "be"},
}
LEVER_WORDS = {"price": f"price ${PRICE_MIN:.0f}–{PRICE_MAX:.0f}", "stop": f"stop ≥ {STOP_MIN_PCT:g} %",
               "regular": "armed 09:30–11:20", "vwap": "above VWAP", "pullback": "pullback volume lighter",
               "rising": "within 25 % of the high"}


def levers(trigger: Optional[float], stop: Optional[float], armed: Optional[time], last: Optional[float],
           vwap: Optional[float], hod: Optional[float], volume_ok: Optional[bool]) -> dict:
    """{lever: True / False / None}; None is a value the plan does not carry,
    and it fails closed."""
    out = {}
    out["price"] = None if trigger is None else PRICE_MIN <= trigger <= PRICE_MAX
    out["stop"] = (None if not (trigger and stop is not None and trigger > stop)
                   else (trigger - stop) / trigger * 100 >= STOP_MIN_PCT)
    out["regular"] = None if armed is None else RTH_OPEN <= armed < ENTRY_CUTOFF
    out["vwap"] = None if (last is None or vwap is None) else last > vwap
    out["pullback"] = None if volume_ok is None else bool(volume_ok)
    out["rising"] = None if (last is None or not hod) else last >= STILL_RISING * hod
    return out


def judge(values: dict) -> list[dict]:
    """[{id, label, takes, failed}] for every shadow strategy."""
    lv = levers(**values)
    out = []
    for sid, s in STRATEGIES.items():
        failed = [k for k in s["levers"] if lv.get(k) is not True]
        out.append({"id": sid, "label": s["label"], "takes": not failed, "exit": s["exit"],
                    "failed": [LEVER_WORDS[k] for k in failed]})
    return out
