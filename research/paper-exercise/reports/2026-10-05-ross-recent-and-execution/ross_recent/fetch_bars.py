"""Step 1: 1-minute SIP bars (backtest_history.fetch_day, cached in data/cache/history)
for every candidate symbol on its session date, plus daily bars (raw and
split-adjusted) for the previous close. Writes daily.json and avail.json here."""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("/home/user/day-trading-bot")
sys.path[:0] = [str(HERE), str(ROOT / "scripts"), str(ROOT / "src")]
import backtest_history as H  # noqa: E402
import trades  # noqa: E402

client = H.alpaca_client()
need = defaultdict(set)
for r in trades.rows():
    for s in r["cands"]:
        need[r["date"]].add(s)
avail = {}
for day in sorted(need):
    got = H.fetch_day(client, day, sorted(need[day]), H.CACHE)
    for s, raw in got.items():
        rows = [x for x in H.to_rows(raw) if H.E.dtime(4, 0) <= x[0].time() < H.E.dtime(16, 0)]
        avail[f"{day}|{s}"] = dict(n=len(rows), lo=min((x[3] for x in rows), default=None),
                                   hi=max((x[2] for x in rows), default=None))
        print(day, s, avail[f"{day}|{s}"])

syms = sorted({s for v in need.values() for s in v})
daily = {}
for adj in ("raw", "split"):
    for i in range(0, len(syms), 50):
        chunk = syms[i:i + 50]
        token = None
        while True:
            pl = client._get(client.data_base, "/v2/stocks/bars", {
                "symbols": ",".join(chunk), "timeframe": "1Day", "start": "2026-05-20T00:00:00Z",
                "end": "2026-08-05T00:00:00Z", "limit": 10000, "feed": "sip", "adjustment": adj,
                "page_token": token})
            for s, bars in (pl.get("bars") or {}).items():
                for b in bars or []:
                    daily.setdefault(s, {}).setdefault(b["t"][:10], {})[adj] = b["c"]
            token = pl.get("next_page_token")
            if not token:
                break
(HERE / "daily.json").write_text(json.dumps(daily, indent=0))
(HERE / "avail.json").write_text(json.dumps(avail, indent=0))
print("daily symbols", len(daily))
