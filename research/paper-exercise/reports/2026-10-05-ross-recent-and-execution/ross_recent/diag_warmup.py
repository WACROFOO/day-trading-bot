"""POST-HOC diagnostic (chosen after seeing the ledger; decides nothing): green_run's
minute_context only arms from the 31st one-minute bar of the day (`i >= 30`).
Re-run S around each located entry with that warm-up removed (everything else
identical) to see whether the warm-up is why S stays silent at his entries.
Writes diag_warmup.json."""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path("/home/user/day-trading-bot")
sys.path[:0] = [str(HERE), str(ROOT / "scripts"), str(ROOT / "src")]
import analyze as A  # noqa: E402
import green_run as G  # noqa: E402
import runup_micro as RM  # noqa: E402


def minute_context_nowarm(day, sym):
    f = RM.HISTORY / f"{day}.json"
    rows = (json.loads(f.read_text()) if f.exists() else {}).get(sym) or []
    if len(rows) < 2:
        return None
    ts = np.array([int(datetime.fromisoformat(r[0].replace("Z", "+00:00")).timestamp()) for r in rows])
    o, h, l, c, v = (np.array([r[k] for r in rows], dtype=float) for k in (1, 2, 3, 4, 5))
    vwap = np.cumsum(v * (h + l + c) / 3) / np.maximum(1, np.cumsum(v))
    e9 = RM._ema(c, 9)
    m = RM._ema(c, 12) - RM._ema(c, 26)
    sig = RM._ema(m, 9)
    hod = np.maximum.accumulate(h)
    prev_hod = np.r_[-np.inf, hod[:-1]]
    green = c > o
    out = []
    for i in range(len(rows)):
        dv5 = float(np.sum(c[max(0, i - 4):i + 1] * v[max(0, i - 4):i + 1]))
        out.append(dict(close_t=int(ts[i]) + 60, ok=bool(
            i >= 1 and green[i] and green[i - 1] and h[i] >= prev_hod[i]
            and c[i] > vwap[i] and c[i] > e9[i] and m[i] > sig[i] and m[i] - sig[i] > 0
            and (hod[i] - c[i]) / hod[i] * 100 <= G.FADE_MAX), low=float(l[i]), dv5=dv5))
    return out


G.minute_context = minute_context_nowarm
L = json.loads((HERE / "ledger.json").read_text())
res = []
for x in L:
    if x["status"] != "LOCATED":
        continue
    E = int(datetime.fromisoformat(f"{x['date']}T{x['entry_min']}:00").replace(tzinfo=A.ET).timestamp())
    rows = A.bars_of(x["date"], x["sym"])
    nh = A.newhigh_map(rows)
    g = A.green_run(x["date"], x["sym"], E, nh)
    res.append(dict(date=x["date"], sym=x["sym"], entry_min=x["entry_min"], tier=x.get("tier"), outcome=x["outcome"],
                    bars_before=x.get("bars_before"), base_near=x.get("s_near"), **{"w_" + k: v for k, v in g.items()}))
    print(x["date"], x["sym"], x["entry_min"], x.get("bars_before"), "S", x.get("s_near"), "-> S0", g.get("s_near"), g.get("s_R"), flush=True)
(HERE / "diag_warmup.json").write_text(json.dumps(res, indent=0, default=str))
