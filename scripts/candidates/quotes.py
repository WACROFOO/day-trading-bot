"""Re-price candidate short trades on the real tape — execution model Q of
research/strategy-candidates/PREREGISTRATION.md, amendment 2026-10-12c.

  order time  the decision moment + 4 s (the desk's measured plan→runner median)
  entry       the short sale at the NBBO bid prevailing then, minus 1 cent
  stop        triggered by the first valid print at or above it after the order;
              filled at the higher of that print and the ask prevailing at it, plus 1 cent
  otherwise   covered at the ask prevailing at 15:55:04, plus 1 cent
  no data     no valid quote in the 60 s before an order: unresolved, counted, never guessed
  cancelled   the bid at the order time at or above the stop: not taken, as the rule cancels an
              open through the stop — counted apart from missing data

Prints come through `tick_replay.Fetcher` (its rate limit, retries, 10-minute print cache
under data/cache/ticks/, and its list of sale conditions that set no last sale). Quotes are
cached here, one JSON a symbol-day, under data/cache/quotes_at/. Only short, market-entry,
close-exit trades are re-priced (S2's close configurations and S2W); anything else raises.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from candidates.data import ET, ROOT, minute

QCACHE = ROOT / "data" / "cache" / "quotes_at"
LATENCY_S = 4
SLIP = 0.01
LOOKBACK_MS = 60_000
STALE_MS = 10_000
FLAT_MIN = minute(15, 55)


@dataclass(frozen=True)
class Quote:
    t: int            # epoch ms of the quote
    bid: float
    ask: float
    bid_size: float
    ask_size: float


def day0(day: str) -> int:
    """Epoch seconds of 04:00 ET on `day`."""
    return int(datetime.fromisoformat(f"{day}T04:00:00").replace(tzinfo=ET).timestamp())


def at_ms(day: str, minute_idx: int, plus_s: float = 0.0) -> int:
    return int((day0(day) + minute_idx * 60 + plus_s) * 1000)


def order_minute(fam: str, sig_min: int) -> int:
    """The minute whose first second the order follows: S2 and S2W decide at the end of the
    5-minute bar; S1 at the close of its 1-minute signal bar."""
    if fam in ("S2", "S2W"):
        return minute(9, 30) + 5 * ((sig_min - minute(9, 30)) // 5 + 1)
    if fam == "S1":
        return sig_min + 1
    raise ValueError(f"{fam}: only the short, market-entry families are re-priced")


class Tape:
    """Valid prints by minute and the NBBO prevailing at a moment, for any symbol-day."""

    def __init__(self, fetcher, cache: Path = QCACHE):
        self.fx = fetcher
        self.cache = Path(cache)
        self._q: dict[tuple[str, str], dict] = {}
        self.quote_requests = 0

    # prints
    def prints_minute(self, sym: str, day: str, mm: int) -> list[tuple[int, float]]:
        t, p = self.fx.chunk(sym, day, mm // 10, day0(day))
        lo, hi = at_ms(day, mm), at_ms(day, mm + 1)
        return [(int(a), float(b)) for a, b in zip(t, p) if lo <= a < hi]

    # quotes
    def _qfile(self, sym: str, day: str) -> Path:
        return self.cache / day / f"{sym}.json"

    def _qmap(self, sym: str, day: str) -> dict:
        k = (sym, day)
        if k not in self._q:
            f = self._qfile(sym, day)
            self._q[k] = json.loads(f.read_text()) if f.exists() else {}
        return self._q[k]

    def quote_at(self, sym: str, day: str, t_ms: int) -> Quote | None:
        """The last valid quote (bid > 0, ask > bid) at or before t, within 60 s."""
        qm = self._qmap(sym, day)
        key = str(t_ms)
        if key not in qm:
            iso = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: E731
            self.quote_requests += 1
            got = self.fx._get(f"/v2/stocks/{sym}/quotes", {"start": iso(t_ms - LOOKBACK_MS), "end": iso(t_ms + 1),
                                                              "limit": 50, "feed": "sip", "sort": "desc"})
            hit = None
            for x in got.get("quotes") or []:
                bp, ap = x.get("bp") or 0, x.get("ap") or 0
                if bp > 0 and ap > bp:
                    hit = [_ms(x["t"]), bp, ap, x.get("bs") or 0, x.get("as") or 0]
                    break
            qm[key] = hit
            f = self._qfile(sym, day)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(qm))
        hit = qm[key]
        return Quote(*hit) if hit else None


def _ms(iso: str) -> int:
    head, _, frac = iso.rstrip("Z").partition(".")
    dt = datetime.fromisoformat(head).replace(tzinfo=timezone.utc)
    return int(dt.timestamp()) * 1000 + int((frac + "000")[:3])


def reprice(tape: Tape, tr: dict, latency_s: float = LATENCY_S, slip: float = SLIP) -> dict:
    """One short trade under model Q. `tr` needs fam, day, sym, sig_min, entry (the 1-minute
    plan's fill), stop, comm (its commission in R) and cand (the minutes whose bar traded at
    or above the stop). Returns resolved=False with a reason, or the real fills and R."""
    sym, day, stop, entry = tr["sym"], tr["day"], tr["stop"], tr["entry"]
    rps = stop - entry
    if rps <= 0:
        return {"resolved": False, "unresolved": "no risk"}
    t_order = at_ms(day, order_minute(tr["fam"], tr["sig_min"]), latency_s)
    q_in = tape.quote_at(sym, day, t_order)
    if q_in is None:
        return {"resolved": False, "unresolved": "no quote at the entry"}
    if q_in.bid >= stop:                                   # the rule cancels an entry through the stop
        return {"resolved": False, "unresolved": "cancelled: the bid at or above the stop", "cancelled": True}
    trig = None
    for mm in tr["cand"]:
        if at_ms(day, mm + 1) <= t_order:
            continue
        for t, p in tape.prints_minute(sym, day, mm):
            if t >= t_order and p >= stop:                 # a print in the order's own millisecond counts against us
                trig = (t, p)
                break
        if trig:
            break
    if trig is not None:
        q_out = tape.quote_at(sym, day, trig[0])
        out_px = max(trig[1], q_out.ask) if q_out else trig[1]
        t_out, how = trig[0], "stop"
    else:
        t_out = at_ms(day, FLAT_MIN, latency_s)
        q_out = tape.quote_at(sym, day, t_out)
        if q_out is None:
            return {"resolved": False, "unresolved": "no quote at the 15:55 cover"}
        out_px, how = q_out.ask, "flat"
    fill_in, fill_out = q_in.bid - slip, out_px + slip
    gross = (fill_in - fill_out) / rps
    gross0 = (q_in.bid - out_px) / rps
    return {"resolved": True, "how": how, "t_order": t_order, "t_out": t_out,
            "bid_in": q_in.bid, "ask_in": q_in.ask, "age_in": t_order - q_in.t, "bid_size_in": q_in.bid_size,
            "spread_in": q_in.ask - q_in.bid,
            "ask_out": q_out.ask if q_out else None, "spread_out": (q_out.ask - q_out.bid) if q_out else None,
            "age_out": (t_out - q_out.t) if q_out else None, "trigger_px": trig[1] if trig else None,
            "fill_in": fill_in, "fill_out": fill_out,
            "q_gross": gross, "q_net": gross - tr["comm"], "q0_net": gross0 - tr["comm"],
            "exit_min_q": (t_out // 1000 - day0(day)) // 60}
