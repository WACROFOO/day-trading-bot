#!/usr/bin/env python3
"""Generate the deterministic dashboard replay fixture.

Ten SYNTHETIC symbols (not real securities) over 08:00-10:30 ET on
2026-09-01, each engineered to exercise one behaviour of the workstation:

  ABCD  leader: 5/5 pillars, red flame, clean first pullback -> armed bands,
        52-week breakout late in the move
  BRXO  low float 4.2M, NO news: technical 4/4 proves news is not a gate
  CYQN  premarket gapper that fades after 09:30 -> frozen gapper snapshot
        diverges from the live gainers list; Running Down
  DVLT  halts mid-morning and resumes higher -> critical halt transitions
  EPHZ  float UNKNOWN (shares-outstanding proxy) -> float pillar fails with
        an explicit "unknown" reason instead of a silent substitution
  FGRT  squeeze ladder: 5% in 5 minutes, then 10% in 10 minutes
  HALQ  numerically qualifies but the spread is blown out -> visible in the
        list with a liquidity warning, suppressed from HOD alerts
  JMXP  quiet control: never qualifies, never alerts
  KPNS  orange flame (4h-old news) and a 25M float that fails the pillar
  LGCP  large cap: fails the price pillar, still ranks in Top Gainers

Output is byte-stable for a fixed seed so replay tests compare exactly.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
START = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)   # 08:00 ET (EDT = UTC-4)
MINUTES = 151                                      # through 10:30 ET
OPEN_M = 90                                        # 09:30 ET
SEED = 20260901


@dataclass
class Sym:
    symbol: str
    prev_close: float
    avg_daily_volume: float
    high_52w: float
    float_shares: float | None
    float_quality: str
    waypoints: list                  # [(minute, price)]
    base_volume: float               # per-minute baseline
    volume_spikes: dict = field(default_factory=dict)   # minute -> multiplier
    spread_frac: float = 0.0015      # half-spread as a fraction of price
    news: tuple | None = None        # (published_at_iso, headline, category)
    halts: list = field(default_factory=list)           # [(minute, status)]
    noise: float = 0.0015


SYMBOLS = [
    Sym("ABCD", 5.10, 250_000, 7.90, 12_000_000, "verified",
        [(0, 5.58), (55, 5.74), (56, 5.92), (89, 6.28), (90, 6.34),
         (96, 6.80), (97, 7.42),                       # impulse into HOD
         (98, 7.28), (99, 7.16), (100, 7.06),          # 3-candle pullback
         (101, 7.31),                                  # trigger: new high
         (108, 7.95), (115, 8.62), (150, 8.24)],
        base_volume=9_000,
        volume_spikes={**{m: 7.0 for m in range(90, 98)},
                       **{m: 1.6 for m in range(98, 101)},
                       **{m: 6.0 for m in range(101, 116)},
                       55: 5.0, 56: 6.0},
        news=("2026-09-01T12:55:00Z", "ABCD awarded $48M defense logistics contract", "contract")),

    Sym("BRXO", 2.30, 220_000, 3.45, 4_200_000, "verified",
        [(0, 2.33), (89, 2.41), (90, 2.44), (104, 2.86), (118, 3.12), (150, 2.98)],
        base_volume=5_000,
        volume_spikes={**{m: 8.0 for m in range(90, 120)}}),

    Sym("CYQN", 8.00, 900_000, 14.20, 18_000_000, "verified",
        [(0, 10.10), (60, 10.38), (89, 10.42), (90, 10.30),
         (99, 9.40), (110, 8.72), (150, 8.55)],
        base_volume=12_000,
        volume_spikes={**{m: 4.0 for m in range(90, 112)}},
        news=("2026-09-01T09:10:00Z", "CYQN prices $30M underwritten offering", "secondary_offering")),

    Sym("DVLT", 3.00, 200_000, 5.60, 9_000_000, "verified",
        [(0, 3.06), (89, 3.32), (90, 3.38), (105, 4.24),
         (107, 4.26), (112, 4.28),                     # halted band
         (113, 4.66), (120, 5.08), (150, 4.88)],
        base_volume=6_000,
        volume_spikes={**{m: 6.5 for m in range(90, 107)},
                       **{m: 0.02 for m in range(107, 113)},
                       **{m: 7.5 for m in range(113, 124)}},
        halts=[(107, "halted"), (112, "trading")],
        news=("2026-09-01T13:44:00Z", "DVLT receives FDA breakthrough designation", "fda")),

    Sym("EPHZ", 4.00, 350_000, 6.10, 45_000_000, "shares_outstanding_proxy",
        [(0, 4.12), (89, 4.44), (90, 4.50), (108, 4.92), (150, 4.78)],
        base_volume=7_000,
        volume_spikes={**{m: 6.0 for m in range(90, 112)}}),

    Sym("FGRT", 1.90, 160_000, 3.10, 15_000_000, "verified",
        [(0, 1.93), (94, 1.96), (95, 2.02), (100, 2.13),   # +5% in 5 min
         (105, 2.16), (115, 2.39),                          # +10% in 10 min
         (150, 2.31)],
        base_volume=5_500,
        volume_spikes={**{m: 6.5 for m in range(95, 118)}}),

    Sym("HALQ", 6.00, 280_000, 9.80, 11_000_000, "verified",
        [(0, 6.42), (89, 6.78), (90, 6.84), (112, 7.05), (150, 6.96)],
        base_volume=900, spread_frac=0.028,
        volume_spikes={**{m: 3.0 for m in range(90, 96)}}),

    Sym("JMXP", 12.00, 1_500_000, 18.40, 40_000_000, "verified",
        [(0, 12.02), (75, 11.96), (150, 12.07)],
        base_volume=3_000),

    Sym("KPNS", 3.40, 500_000, 5.20, 25_000_000, "verified",
        [(0, 3.72), (89, 3.94), (90, 3.98), (120, 4.12), (150, 4.02)],
        base_volume=8_000,
        volume_spikes={**{m: 3.5 for m in range(90, 118)}},
        news=("2026-09-01T09:30:00Z", "KPNS names new chief operating officer", "other")),

    Sym("LGCP", 145.00, 8_000_000, 168.00, 320_000_000, "verified",
        [(0, 150.20), (89, 152.40), (90, 152.90), (130, 154.60), (150, 154.10)],
        base_volume=40_000,
        volume_spikes={**{m: 3.0 for m in range(90, 105)}},
        news=("2026-09-01T11:05:00Z", "LGCP raises full-year guidance", "earnings")),
]


def interpolate(waypoints, m):
    if m <= waypoints[0][0]:
        return waypoints[0][1]
    for (m0, p0), (m1, p1) in zip(waypoints, waypoints[1:]):
        if m0 <= m <= m1:
            span = m1 - m0
            return p0 if span == 0 else p0 + (p1 - p0) * (m - m0) / span
    return waypoints[-1][1]


def build_daily_bars(sym: Sym, rng: random.Random, count: int = 260):
    """Deterministic prior daily history: a rally into the 52-week high about a
    third of the way in, then a fade to the previous close. The 52-week high
    emerges from the path instead of being stamped onto one bar."""
    bars = []
    start = sym.prev_close * 0.62
    peak_at = int(count * 0.34)
    day = datetime(2026, 9, 1, tzinfo=UTC) - timedelta(days=int(count * 1.45))
    for i in range(count):
        day += timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        if i <= peak_at:
            frac = i / max(1, peak_at)
            base = start + (sym.high_52w * 0.97 - start) * (frac ** 0.85)
        else:
            frac = (i - peak_at) / max(1, count - 1 - peak_at)
            base = sym.high_52w * 0.97 + (sym.prev_close - sym.high_52w * 0.97) * (frac ** 0.7)
        close = max(0.2, base * (1 + rng.uniform(-0.018, 0.018)))
        open_ = max(0.2, close * (1 + rng.uniform(-0.012, 0.012)))
        high = max(open_, close) * (1 + abs(rng.uniform(0, 0.016)))
        low = min(open_, close) * (1 - abs(rng.uniform(0, 0.016)))
        bars.append({"d": day.strftime("%Y-%m-%d"), "o": round(open_, 2),
                     "h": round(high, 2), "l": round(low, 2), "c": round(close, 2),
                     "v": int(sym.avg_daily_volume * rng.uniform(0.6, 1.4))})
    # Anchor both ends: the series peaks at the stated 52-week high and closes
    # on the stated previous close.
    peak_bar = max(bars, key=lambda b: b["h"])
    peak_bar["h"] = round(sym.high_52w, 2)
    bars[-1]["c"] = round(sym.prev_close, 2)
    return bars


def main() -> int:
    rng = random.Random(SEED)
    out = Path("fixtures/market_replay/workstation_open_2026-09-01.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Deterministic dashboard replay: 10 SYNTHETIC symbols, 08:00-10:30 ET",
             "# Generated by scripts/make_replay_fixture.py (seed %d) - do not hand-edit" % SEED]

    for sym in SYMBOLS:
        lines.append(json.dumps({
            "type": "reference", "symbol": sym.symbol, "prev_close": sym.prev_close,
            "avg_daily_volume": sym.avg_daily_volume, "high_52w": sym.high_52w,
            "float_shares": sym.float_shares, "float_quality": sym.float_quality,
            "daily_bars": build_daily_bars(sym, rng),
        }))
        if sym.news:
            published, headline, category = sym.news
            lines.append(json.dumps({
                "type": "news", "symbol": sym.symbol, "published_at": published,
                "headline": headline, "category": category,
                "provider_id": f"fixture-{sym.symbol.lower()}-1",
                # first_observed_at models feed latency: the platform learns of
                # the headline slightly after publication.
                "first_observed_at": (datetime.fromisoformat(published.replace("Z", "+00:00"))
                                      + timedelta(seconds=95)).isoformat().replace("+00:00", "Z"),
            }))

    halt_events = []
    for sym in SYMBOLS:
        for minute, status in sym.halts:
            halt_events.append((minute, sym.symbol, status))

    for m in range(MINUTES):
        ts = START + timedelta(minutes=m)
        iso = ts.isoformat().replace("+00:00", "Z")
        for minute, symbol, status in halt_events:
            if minute == m:
                lines.append(json.dumps({"type": "halt", "symbol": symbol,
                                         "status": status, "ts": iso}))
        for sym in SYMBOLS:
            close = interpolate(sym.waypoints, m)
            prev = interpolate(sym.waypoints, m - 1) if m else close
            jitter = rng.uniform(-sym.noise, sym.noise) * close
            o = round(prev + jitter, 4)
            c = round(close, 4)
            wick = abs(rng.uniform(0, sym.noise * 2)) * close
            h = round(max(o, c) + wick, 4)
            l = round(min(o, c) - wick, 4)
            mult = sym.volume_spikes.get(m, 1.0)
            # Premarket carries a fraction of regular-session participation.
            session_scale = 0.25 if m < OPEN_M else 1.0
            v = int(sym.base_volume * mult * session_scale * rng.uniform(0.85, 1.15))
            lines.append(json.dumps({
                "type": "bar", "symbol": sym.symbol, "ts": iso,
                "open": o, "high": h, "low": l, "close": c, "volume": v,
                "bid": round(c * (1 - sym.spread_frac), 4),
                "ask": round(c * (1 + sym.spread_frac), 4),
            }))

    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(lines)} records, {out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
