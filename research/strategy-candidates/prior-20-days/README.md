# prior-20-days/ — the first short-side reads, before the preregistration

Run in the chat of 2026-10-12 on the 20 exported desk days (`research/daily/`, 2026-09-11 →
10-08, 04:00-12:00 bars), through the Reddit replay's universe, bars and live cost model
(`research/reddit-bot-rules-2026-10-12/their_rules.py`). Selection days to 2026-10-01, the
rest held out. Kept because the folder records every combination tried: **31**.

| file | what |
|---|---|
| `short_test.py` | A the mirror of every plan the detector arms (and of the live plans), B the back side (VWAP lost after an old high), C the extension (20 % over VWAP), T the 09:30 → 11:30 time fade — fixed 2R / trail 1R |
| `short_combo.py` | the owner's combination — under VWAP, MACD turning down, failed high of day, high-volume red, too deep a pullback — all five, each left out, each alone; Level 2 not testable |
| `output.txt` | both outputs, re-run 2026-10-12 |

Every variant is negative net on the selection days, gross between −0.41 and +0.28 R; the time
fade's worst trade is −206.86 % of price. Twenty sessions, in-sample, borrow not charged: **a first look,
not evidence.** These reads shaped S1 and S2 (`../PREREGISTRATION.md` §2).

```bash
python3 research/strategy-candidates/prior-20-days/short_test.py
python3 research/strategy-candidates/prior-20-days/short_combo.py
```
