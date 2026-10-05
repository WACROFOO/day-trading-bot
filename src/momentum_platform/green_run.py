"""Setup S, the green-run continuation, for the live desk. SHADOW ONLY.

The setup was preregistered as addendum 2026-10-05
(`research/edge-hunt/PREREGISTRATION.md`) and frozen in
`scripts/green_run.py` at commit 20aa85f. On 300 runner symbol-days it was
positive before costs and negative after them, so the addendum's own rule
applies: "the green run is logged on the desk (no orders) and not traded".
This module is that log's detector. It decides nothing, sizes nothing and
sends nothing; `tests/test_green_run.py` proves the runner never reads what
it writes.

What it does, on the last CLOSED 10-second candle of one symbol:

  context  the last COMPLETED 1-minute bar (bars since 04:00 ET): it and the
           bar before are green, it makes a new high of day, closes above the
           session VWAP and the 9 EMA, MACD (12,26,9) line > signal, <= 25 %
           off the high; read from the 31st bar on (the frozen code's i >= 30)
  pause    the 6 ten-second bars before the pause have >= 3 green and span
           >= 1 %; a pause of 1-3 bars, none above the leg's high, its low not
           under the leg's midpoint (`scripts/runup_micro.py` `_signals`)
  levels   entry = the last pause bar's high + 1c; stop = that 1-minute bar's
           low - 1c
  refusals price outside $2-20, stop >= entry, stop < 2 % of price (A13),
           stop < 4x the spread (A6: the live spread when the caller has one,
           else the repo's calibrated proxy, which is what the test used)

Every evaluation returns an `Evaluation` with one `Check` per condition and
the reason it passed or failed, never a bare boolean.

Parity with the frozen research code is a test, not a claim:
`tests/test_green_run.py` feeds the same synthetic bars to this module and to
`scripts/green_run.py` / `scripts/runup_micro.py` and asserts identical
signals, entries and stops. The formulas below therefore copy the frozen
code's arithmetic exactly (EMA seeded on the first close, VWAP on the typical
price), not the desk's `indicators.py`.

Two things are the desk's and not the research's, and both are labelled in
the record: the session window 07:00-11:30 ET (the research tape covered only
that window: ticks from 07:00, flat 11:30) and the live spread. The research
universe was `running_up` scanner symbol-days; the desk evaluates whatever is
on the desk.

Standard library only.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

#: The setup's name in the ledger: the addendum and the commit that froze it.
SETUP = "S green-run continuation · addendum 2026-10-05 · scripts/green_run.py 20aa85f"

# -- parameters: each one is the frozen code's, cited where it lives ---------
STOP_FLOOR_PCT = 2.0      # A13 · scripts/green_run.py STOP_FLOOR_PCT; src/execution/runner.py SELECTIVE_MIN_STOP_PCT
SPREAD_K = 4.0            # A6  · scripts/green_run.py SPREAD_K; src/execution/intent.py SPREAD_K
FADE_MAX = 25.0           # scripts/green_run.py FADE_MAX: <= 25 % off the high
PRICE_MIN, PRICE_MAX = 2.0, 20.0     # scripts/green_run.py run_day: 2.0 <= entry <= 20.0
WARMUP_INDEX = 30         # scripts/green_run.py minute_context: i >= 30
LEG_BARS, LEG_MIN_PCT, MIN_GREEN = 6, 1.0, 3     # scripts/runup_micro.py
MAX_PAUSE = 3             # scripts/runup_micro.py _signals: npause in (1, 2, 3)
TTL_ENTRY_S = 20          # scripts/runup_micro.py TTL_ENTRY_S: the entry order lives 20 s
CAP_PCT = 0.3             # A10 · scripts/tick_replay.py CAP_PCT; src/execution/intent.py ENTRY_LIMIT_OFFSET_PCT
TRAIL_R = 1.0             # A3  · scripts/tick_replay.py TRAIL_R
TRAIL_EVERY_S = 5         # scripts/tick_replay.py TRAIL_EVERY_S (the runner loop)
#: The window the research tape covered: ticks from 07:00 ET
#: (`runup_micro._chunks`, chunk 18 of 600 s after 04:00) to the 11:30 flat.
WINDOW_ET = ("07:00", "11:30")

_PROXY_FILE = Path(__file__).resolve().parents[2] / "research" / "edge-hunt" / "results" / "spread_proxy.json"

#: A bar here is (start_epoch_s, open, high, low, close[, volume]).
BarT = Sequence[float]


# =========================================================== the record
@dataclass(frozen=True)
class Check:
    """One condition: did it hold, on what value, and why."""

    name: str
    ok: Optional[bool]          # None = could not be judged (data missing)
    value: Any
    why: str


@dataclass
class Evaluation:
    """What setup S said at one 10-second close. `status`:

    SIGNAL          every condition held: the shadow log records a would-be entry
    REFUSED         the chart said yes (context + pause) but a risk rule said no
    OUT_OF_WINDOW   the chart said yes outside 07:00-11:30 ET (not tested there)
    NO_CONTEXT      a 10-second pause, but the 1-minute bar is not a green run
    NO_PAUSE        no qualifying 10-second pause at this close
    """

    symbol: str
    t_arm: int                               # epoch s: the close of the last pause bar
    status: str
    checks: List[Check] = field(default_factory=list)
    entry: Optional[float] = None
    stop: Optional[float] = None
    stop_pct: Optional[float] = None
    spread: Optional[float] = None
    spread_source: Optional[str] = None      # live | proxy
    proxy_spread: Optional[float] = None
    premarket: Optional[bool] = None
    pause_id: Optional[int] = None           # epoch s of the 10-s bar that set the leg high
    minute_t: Optional[int] = None           # epoch s, start of the 1-minute context bar
    setup: str = SETUP

    @property
    def signal(self) -> bool:
        return self.status == "SIGNAL"

    @property
    def chart_ok(self) -> bool:
        return self.status in ("SIGNAL", "REFUSED", "OUT_OF_WINDOW")

    def failed(self) -> List[Check]:
        return [c for c in self.checks if c.ok is not True]

    def reasons(self) -> List[str]:
        """Every condition, in order, as 'name: why' with a pass/fail mark."""
        mark = {True: "ok", False: "NO", None: "??"}
        return [f"[{mark[c.ok]}] {c.name}: {c.why}" for c in self.checks]

    def refusals(self) -> List[str]:
        return [f"{c.name}: {c.why}" for c in self.failed()]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["checks"] = [asdict(c) for c in self.checks]
        return d


# =========================================================== helpers
def _ema(x: Sequence[float], n: int) -> List[float]:
    """runup_micro._ema: seeded on the first value, alpha = 2/(n+1)."""
    a = 2 / (n + 1)
    out = [float(x[0])] if len(x) else []
    for i in range(1, len(x)):
        out.append(a * x[i] + (1 - a) * out[-1])
    return out


def _clock(t: int, seconds: bool = False) -> str:
    return datetime.fromtimestamp(t, ET).strftime("%H:%M:%S" if seconds else "%H:%M")


def is_premarket(t: int) -> bool:
    """green_run.run_day: datetime.fromtimestamp(t_arm, ET).strftime('%H:%M') < '09:30'."""
    return datetime.fromtimestamp(t, ET).strftime("%H:%M") < "09:30"


class SpreadProxy:
    """`scripts/edge_hunt/costs.SpreadProxy.spread`, the same table and keys,
    without numpy. Estimated quoted spread in dollars from price tier x
    session x 5-minute dollar-volume tercile; 2c when no table exists."""

    def __init__(self, path: Path = _PROXY_FILE) -> None:
        try:
            self.table = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            self.table = None

    @staticmethod
    def key(price: float, premarket: bool, dollar_vol_5m: float) -> str:
        tier = "2-5" if price < 5 else ("5-10" if price < 10 else "10-20+")
        vol = "lo" if dollar_vol_5m < 50_000 else ("mid" if dollar_vol_5m < 500_000 else "hi")
        return f"{tier}|{'pm' if premarket else 'rth'}|{vol}"

    def spread(self, price: float, premarket: bool, dollar_vol_5m: float) -> float:
        if not self.table:
            return 0.02
        rel = self.table["cells"].get(self.key(price, premarket, dollar_vol_5m), self.table["default"])
        return max(0.01, rel * price)


_PROXY: Optional[SpreadProxy] = None


def default_proxy() -> SpreadProxy:
    global _PROXY
    if _PROXY is None:
        _PROXY = SpreadProxy()
    return _PROXY


# =========================================================== 1-minute context
@dataclass
class MinuteSeries:
    """The frozen `minute_context` arithmetic over completed 1-minute bars."""

    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: List[float]
    vwap: List[float]
    e9: List[float]
    macd: List[float]
    sig: List[float]
    hod: List[float]
    prev_hod: List[float]
    dv5: List[float]

    @property
    def close_t(self) -> List[int]:
        return [x + 60 for x in self.t]

    def ok(self, i: int) -> bool:
        """The frozen boolean, term for term (scripts/green_run.py minute_context)."""
        g = lambda k: self.c[k] > self.o[k]                          # noqa: E731
        return bool(i >= WARMUP_INDEX and g(i) and g(i - 1) and self.h[i] >= self.prev_hod[i]
                    and self.c[i] > self.vwap[i] and self.c[i] > self.e9[i] and self.macd[i] > self.sig[i]
                    and self.macd[i] - self.sig[i] > 0
                    and (self.hod[i] - self.c[i]) / self.hod[i] * 100 <= FADE_MAX)

    def checks(self, i: int) -> List[Check]:
        """The same conditions, one Check each, with the numbers they were judged on."""
        out = []
        n = i + 1
        out.append(Check("warm-up", i >= WARMUP_INDEX, n,
                         f"1-minute bar #{n} since 04:00 ET" + (" (>= 31st)" if i >= WARMUP_INDEX
                                                               else f" — the context is read from the 31st bar")))
        green = self.c[i] > self.o[i]
        out.append(Check("bar green", green, (self.o[i], self.c[i]),
                         f"{_clock(self.t[i])} bar o {self.o[i]:.4g} -> c {self.c[i]:.4g}"))
        if i >= 1:
            pg = self.c[i - 1] > self.o[i - 1]
            out.append(Check("bar before green", pg, (self.o[i - 1], self.c[i - 1]),
                             f"{_clock(self.t[i - 1])} bar o {self.o[i - 1]:.4g} -> c {self.c[i - 1]:.4g}"))
        else:
            out.append(Check("bar before green", False, None, "no bar before it"))
        nh = self.h[i] >= self.prev_hod[i]
        prev = "none" if self.prev_hod[i] == float("-inf") else f"{self.prev_hod[i]:.4g}"
        out.append(Check("new high of day", nh, self.h[i], f"high {self.h[i]:.4g} vs prior high {prev}"))
        out.append(Check("above VWAP", self.c[i] > self.vwap[i], self.vwap[i],
                         f"close {self.c[i]:.4g} vs session VWAP {self.vwap[i]:.4g}"))
        out.append(Check("above EMA9", self.c[i] > self.e9[i], self.e9[i],
                         f"close {self.c[i]:.4g} vs 9 EMA {self.e9[i]:.4g}"))
        mo = self.macd[i] > self.sig[i] and self.macd[i] - self.sig[i] > 0
        out.append(Check("MACD > signal", mo, (self.macd[i], self.sig[i]),
                         f"MACD {self.macd[i]:+.4f} vs signal {self.sig[i]:+.4f}"))
        fade = (self.hod[i] - self.c[i]) / self.hod[i] * 100
        out.append(Check("off the high", fade <= FADE_MAX, fade,
                         f"close {fade:.1f}% under the high of day {self.hod[i]:.4g} (max {FADE_MAX:g}%)"))
        return out


def minute_series(bars_1m: Sequence[BarT]) -> Optional[MinuteSeries]:
    """bars_1m: completed 1-minute bars since 04:00 ET, oldest first,
    (start_epoch, o, h, l, c, v)."""
    if not bars_1m:
        return None
    t = [int(b[0]) for b in bars_1m]
    o, h, l, c, v = ([float(b[k]) for b in bars_1m] for k in (1, 2, 3, 4, 5))
    vwap, cpv, cv = [], 0.0, 0.0
    for i in range(len(t)):
        cpv += v[i] * (h[i] + l[i] + c[i]) / 3
        cv += v[i]
        vwap.append(cpv / max(1.0, cv))
    e9 = _ema(c, 9)
    e12, e26 = _ema(c, 12), _ema(c, 26)
    m = [a - b for a, b in zip(e12, e26)]
    sig = _ema(m, 9)
    hod, run = [], float("-inf")
    for x in h:
        run = max(run, x)
        hod.append(run)
    prev_hod = [float("-inf")] + hod[:-1]
    dv5 = []
    for i in range(len(t)):
        s = 0.0
        for k in range(max(0, i - 4), i + 1):
            s += c[k] * v[k]
        dv5.append(s)
    return MinuteSeries(t, o, h, l, c, v, vwap, e9, m, sig, hod, prev_hod, dv5)


def context_index(series: MinuteSeries, t: int) -> int:
    """green_run._ctx_at: the last bar completed at or before t (-1: none)."""
    return bisect_right(series.close_t, t) - 1


# =========================================================== 10-second pause
@dataclass
class Pause:
    t_arm: int
    entry: float
    stop10: float
    npause: int
    leg_high: float
    leg_low: float
    pause_low: float
    pause_id: int
    checks: List[Check]


def find_pause(bars10: Sequence[BarT]) -> Tuple[Optional[Pause], List[Check]]:
    """`runup_micro._signals` at the newest close: the first pause length
    (1, 2, 3) whose shape qualifies. Returns (pause or None, what was tried)."""
    i = len(bars10)
    tried: List[Check] = []
    for npause in range(1, MAX_PAUSE + 1):
        a = i - npause
        if a - LEG_BARS < 0:
            tried.append(Check(f"{npause}-bar pause", False, None,
                               f"needs {LEG_BARS} ten-second bars before the pause, has {max(0, a)}"))
            break
        leg, pause = bars10[a - LEG_BARS:a], bars10[a:i]
        lh, ll = max(b[2] for b in leg), min(b[3] for b in leg)
        greens = sum(1 for b in leg if b[4] > b[1])
        span = (lh - ll) / ll * 100
        if greens < MIN_GREEN or span < LEG_MIN_PCT:
            tried.append(Check(f"{npause}-bar pause", False, (greens, span),
                               f"leg {greens} green of {LEG_BARS} (need {MIN_GREEN}), span {span:.2f}% "
                               f"(need {LEG_MIN_PCT:g}%)"))
            continue
        top = max(b[2] for b in pause)
        if top > lh:
            tried.append(Check(f"{npause}-bar pause", False, top,
                               f"a pause bar made a new high {top:.4g} over the leg high {lh:.4g}"))
            continue
        pl = min(b[3] for b in pause)
        mid = (lh + ll) / 2
        if pl < mid:
            tried.append(Check(f"{npause}-bar pause", False, pl,
                               f"pause low {pl:.4g} under the leg midpoint {mid:.4g}"))
            continue
        hb = max(int(b[0]) for b in leg if b[2] == lh)        # the leg high's own bar (the latest on a tie)
        t_arm = int(bars10[i - 1][0]) + 10
        # Shorter pauses tried first and not matching are not failures of the
        # setup (the frozen code tries 1, 2, 3 bars in turn), so they stay out.
        checks = [
            Check("10-s leg", True, (greens, span),
                  f"{LEG_BARS} bars {_clock(int(leg[0][0]), True)}-{_clock(int(leg[-1][0]) + 10, True)}: "
                  f"{greens} green (>= {MIN_GREEN}), span {span:.2f}% (>= {LEG_MIN_PCT:g}%)"),
            Check("10-s pause", True, npause,
                  f"{npause} bar(s), high {top:.4g} not over the leg high {lh:.4g}, low {pl:.4g} "
                  f"above the leg midpoint {mid:.4g}"),
        ]
        return (Pause(t_arm, round(bars10[i - 1][2] + 0.01, 4), round(pl - 0.01, 4), npause,
                      lh, ll, pl, hb, checks), checks)
    return None, tried


# =========================================================== the evaluation
def in_window(t: int, window: Optional[Tuple[str, str]] = WINDOW_ET) -> bool:
    if window is None:
        return True
    hm = datetime.fromtimestamp(t, ET).strftime("%H:%M")
    return window[0] <= hm < window[1]


def evaluate(symbol: str, bars_1m: Sequence[BarT], bars10: Sequence[BarT], *,
             live_spread: Optional[float] = None, proxy: Optional[SpreadProxy] = None,
             window: Optional[Tuple[str, str]] = WINDOW_ET,
             series: Optional[MinuteSeries] = None) -> Evaluation:
    """Setup S at the close of `bars10[-1]`.

    bars_1m  completed 1-minute bars since 04:00 ET (a bar still forming at
             the 10-second close is ignored: only bars whose end <= t_arm count)
    bars10   closed 10-second bars, oldest first, each one with at least one
             trade (the research built them from prints; an empty bar is not a bar)
    live_spread  ask - bid now, when the caller has a live quote; else the proxy
    window   (start, end) ET wall clock, None = no window (the parity test)
    """
    if not bars10:
        return Evaluation(symbol, 0, "NO_PAUSE", [Check("10-s bars", False, 0, "no closed ten-second bar")])
    t_arm = int(bars10[-1][0]) + 10
    pause, tried = find_pause(bars10)
    if pause is None:
        return Evaluation(symbol, t_arm, "NO_PAUSE", tried)
    checks = list(pause.checks)
    ms = series if series is not None else minute_series(bars_1m)
    j = context_index(ms, t_arm) if ms is not None else -1
    if j < 0:
        checks.append(Check("1-min context", None, None, "no completed 1-minute bar at this close"))
        return Evaluation(symbol, t_arm, "NO_CONTEXT", checks, pause_id=pause.pause_id)
    checks += ms.checks(j)
    ev = Evaluation(symbol, t_arm, "NO_CONTEXT", checks, pause_id=pause.pause_id, minute_t=ms.t[j])
    if not ms.ok(j):
        return ev

    # -- levels and refusals, in the frozen run_day's terms
    entry = pause.entry
    low = ms.l[j]
    stop = round(low - 0.01, 4)
    pm = is_premarket(t_arm)
    prox = (proxy or default_proxy()).spread(entry, pm, ms.dv5[j])
    if live_spread is not None and live_spread > 0:
        spread, src = float(live_spread), "live"
    else:
        spread, src = prox, "proxy"
    rps = entry - stop
    stop_pct = rps / entry * 100 if entry else 0.0
    ev.entry, ev.stop, ev.stop_pct = entry, stop, stop_pct
    ev.spread, ev.spread_source, ev.proxy_spread, ev.premarket = spread, src, prox, pm
    risk: List[Check] = [
        Check("entry", True, entry, f"pause high {entry - 0.01:.4g} + 1c = {entry:.4g} "
                                    f"(buy stop-limit, cap +{CAP_PCT:g}%, live {TTL_ENTRY_S} s)"),
        Check("stop", stop < entry, stop,
              f"the {_clock(ms.t[j])} 1-minute bar's low {low:.4g} - 1c = {stop:.4g}"
              + ("" if stop < entry else " — not under the entry")),
        Check("price band", PRICE_MIN <= entry <= PRICE_MAX, entry,
              f"entry {entry:.4g} {'inside' if PRICE_MIN <= entry <= PRICE_MAX else 'outside'} "
              f"${PRICE_MIN:g}-{PRICE_MAX:g}"),
    ]
    if stop < entry:
        k = rps / spread if spread > 0 else float("inf")
        risk += [
            Check("stop >= 2% (A13)", stop_pct >= STOP_FLOOR_PCT, stop_pct,
                  f"stop {stop_pct:.2f}% of the entry (floor {STOP_FLOOR_PCT:g}%)"),
            Check("stop >= 4x spread (A6)", not (spread > 0 and k < SPREAD_K), k,
                  f"stop ${rps:.4f} = {k:.1f}x the {src} spread ${spread:.4f} (need {SPREAD_K:g}x)"
                  + (f"; proxy ${prox:.4f}" if src == "live" else "")),
        ]
    if window is not None:
        win_ok = in_window(t_arm, window)
        risk.append(Check("tested window", win_ok, _clock(t_arm),
                          f"{_clock(t_arm, True)} ET {'inside' if win_ok else 'outside'} "
                          f"{window[0]}-{window[1]} (the only hours the research tape covered)"))
    checks += risk
    bad = [c for c in risk if c.ok is not True]
    if not bad:
        ev.status = "SIGNAL"
    elif any(c.name == "tested window" for c in bad):
        ev.status = "OUT_OF_WINDOW"     # outside the tested hours nothing is logged, refusal or not
    else:
        ev.status = "REFUSED"
    return ev


def signals_over_day(symbol: str, bars_1m: Sequence[BarT], bars10: Sequence[BarT], *,
                     window: Optional[Tuple[str, str]] = WINDOW_ET,
                     proxy: Optional[SpreadProxy] = None) -> List[Evaluation]:
    """Every chart-approved evaluation over a day, one per 10-second close,
    as the desk would have produced them close by close. Replay and tests."""
    ms = minute_series(bars_1m)
    out = []
    for n in range(LEG_BARS + 1, len(bars10) + 1):
        ev = evaluate(symbol, bars_1m, bars10[:n], window=window, proxy=proxy, series=ms)
        if ev.chart_ok:
            out.append(ev)
    return out


# =========================================================== desk adapters
def bars10_from_candles(candles: Iterable[Any]) -> List[tuple]:
    """Closed 10-second candles (objects with ts/open/high/low/close/volume, or
    tuples (start_epoch, o, h, l, c, v)) -> research bars. A candle with no
    volume or no price is dropped: the research built its 10-second bars from
    prints, so an interval without a trade was never a bar."""
    out = []
    for b in candles:
        if isinstance(b, (tuple, list)):
            t, o, h, l, c = b[0], b[1], b[2], b[3], b[4]
            v = b[5] if len(b) > 5 else 1
        else:
            t, o, h, l, c, v = b.ts, b.open, b.high, b.low, b.close, b.volume
        if isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if isinstance(t, datetime):
            t = t.timestamp()
        if v is None or v <= 0 or not o or not h or not l or not c or min(o, h, l, c) <= 0:
            continue
        out.append((int(t), float(o), float(h), float(l), float(c), float(v)))
    return out


def minutes_from_records(records: Iterable[dict], until: Optional[int] = None) -> List[tuple]:
    """Bar records (1-minute and/or 10-second, as `ibkr_desk.merge_minutes`
    returns them) -> 1-minute bars (start_epoch, o, h, l, c, v), aggregated
    the way `session_builder` aggregates, keeping only minutes COMPLETED by
    `until` (start + 60 <= until)."""
    groups: dict = {}
    for r in records:
        if min(float(r[k] or 0) for k in ("open", "high", "low", "close")) <= 0:
            continue                    # a priceless record is not a bar
        iso = r["ts"]
        key = iso[:17] + "00Z" if len(iso) > 17 else iso
        groups.setdefault(key, []).append(r)
    out = []
    for key in sorted(groups):
        chunk = sorted(groups[key], key=lambda r: r["ts"])
        start = int(datetime.fromisoformat(key.replace("Z", "+00:00")).timestamp())
        if until is not None and start + 60 > until:
            continue
        out.append((start, float(chunk[0]["open"]), max(float(c["high"]) for c in chunk),
                    min(float(c["low"]) for c in chunk), float(chunk[-1]["close"]),
                    float(sum(c["volume"] or 0 for c in chunk))))
    return out


# =========================================================== after the close
def cap_of(entry: float, cap_pct: float = CAP_PCT) -> float:
    """A10's limit: trigger + max(1c, 0.3 %) — scripts/rules_audit.py cap_of."""
    return round(entry + max(0.01, entry * cap_pct / 100.0), 4)


def score(entry: float, stop: float, t_arm: int, bars10: Sequence[BarT], bars1m: Sequence[BarT] = (), *,
          flat_t: Optional[int] = None, ttl_s: int = TTL_ENTRY_S, cap_pct: float = CAP_PCT,
          trail_r: float = TRAIL_R) -> dict:
    """One signal on BARS, the way `runup_micro._trade` scores it on prints,
    with the approximations a bar forces stated here:

    fill   the order lives `ttl_s` from t_arm: the 10-second bars starting in
           [t_arm, t_arm + ttl_s). A bar whose high reaches the entry triggers
           it; it fills at the entry when the bar opened under it, at the open
           when it opened between the entry and the cap, and at the cap when it
           opened over the cap but traded back to it. Over the cap and never
           back inside the window: not filled. No 10-second bar: unscored.
    exit   A3: the stop trails 1 R under the highest price since the fill. On
           prints it moves every 5 s; on 10-second bars it can move only at
           each bar's close, and a bar's low is tested against the level set
           by the bars BEFORE it (a bar's high and low have no order). The
           fill bar's own low is not tested — it may precede the fill. A
           minute with no 10-second candle is walked on its 1-minute bar.
           Flat at `flat_t` (the last close before it), else the last bar.
    R      (exit - fill) / (entry - stop), gross: no commission, no spread.
    """
    rps = entry - stop
    res = {"filled": False, "fill": None, "fill_t": None, "fill_kind": None, "exit": None,
           "exit_t": None, "how": None, "r": None, "rps": rps, "bars": 0, "minutes_from_1m": 0}
    if rps <= 0:
        res["how"] = "bad levels"
        return res
    cap = cap_of(entry, cap_pct)
    window = [b for b in bars10 if t_arm <= b[0] < t_arm + ttl_s]
    fi = None
    trig = False
    for b in window:
        o, h, l = b[1], b[2], b[3]
        if not trig and h >= entry:
            trig = True
            if o > cap:
                if l <= cap:
                    fi, price, kind = b, cap, "cap_return"
                    break
                continue
            fi, price, kind = b, (o if o > entry else entry), ("open" if o > entry else "entry")
            break
        if trig and l <= cap:
            fi, price, kind = b, min(cap, max(entry, o)), "cap_return"
            break
    if fi is None:
        res["how"] = "not filled" if window else "no 10-s tape in the entry window"
        return res
    res.update(filled=True, fill=price, fill_t=int(fi[0]), fill_kind=kind)
    # A cap-return fill came AFTER the bar's high: only its close is known to follow it
    # (scripts/rules_audit.py run_exit does the same for kind 'cap_return').
    high = max(price, fi[4] if kind == "cap_return" else fi[2])
    level = max(stop, round(high - trail_r * rps, 4))
    last = fi
    path, res["minutes_from_1m"] = forward_path([b for b in bars10 if b[0] > fi[0]],
                                                [b for b in bars1m if b[0] // 60 * 60 > fi[0] // 60 * 60])
    for b in path:
        if flat_t is not None and b[0] >= flat_t:
            res.update(exit=float(last[4]), exit_t=int(last[0]) + 10, how="flat")
            break
        o, h, l = b[1], b[2], b[3]
        if o <= level:
            res.update(exit=float(o), exit_t=int(b[0]), how="trail" if level > stop else "stop")
            break
        if l <= level:
            res.update(exit=float(level), exit_t=int(b[0]), how="trail" if level > stop else "stop")
            break
        high = max(high, h)
        level = max(level, round(high - trail_r * rps, 4))
        last = b
        res["bars"] += 1
    else:
        res.update(exit=float(last[4]), exit_t=int(last[0]) + 10, how="end of tape")
    res["r"] = (res["exit"] - price) / rps
    return res


def forward_path(bars10: Sequence[BarT], bars1m: Sequence[BarT]) -> Tuple[List[tuple], int]:
    """The ledger's 10-second candles, with any minute that has NO 10-second
    candle filled by that minute's 1-minute bar (one coarse bar). Returns the
    path and how many minutes were filled that way."""
    b10 = [tuple(b) for b in bars10]
    have = {int(b[0]) // 60 * 60 for b in b10}
    fill = [tuple(b) for b in bars1m if int(b[0]) not in have]
    return sorted(b10 + fill, key=lambda b: b[0]), len(fill)
