---
name: trading-day
description: Answer "le plan pour aujourd'hui", "je fais quoi maintenant", "what should I be doing", or any question about the day's schedule and routine. Anchors to the current ET time and says what phase we're in and the next action — the full half-hour table only when the whole day is asked for.
---

# Trading day

**First, always:** `./now` — it prints the ET/France time, the market phase,
the countdown to the next boundary, and the watchlist tape. Anchor every
answer to its header. Never recite the schedule without saying where in it we
are right now.

Two answer shapes:

- **"je fais quoi maintenant"** → current phase + the next concrete action +
  the next checkpoint time. **≤ 10 lines.** Nothing about phases already past.
- **"le plan du jour"** → the full table below, adjusted for anything already
  known about today (yesterday's runners, scheduled news, user's notes).

## The day

| France | ET | phase |
|---|---|---|
| 13:00 | 07:00 | First scan: `premarket_stars.py --all --notify`. **The move can happen HERE** — JWEL's entire run was 07:00–07:45 while we watched the open. A vertical name on volume is live now, not later |
| 13:30 | 07:30 | `catalyst_score.py` top 2. EDGAR by hand for 6-K filers (dilution blind spot). Split test on any gapper with a weird prev close |
| 14:00 | 08:00 | Re-scan — the 08:00 ET press-release wave reshuffles the board |
| 14:30 | 08:30 | Final watchlist, 3 names max. Levels: PM high, VWAP, whole dollars. `size.py --card` so sizes are decided before emotions exist |
| 15:00 | 09:00 | Last scan. Fade check: >25% off PM high = dead. Distrust anything appearing after 09:00 |
| 15:30 | 09:30 | **Open. Hands off 5 minutes** — let the first candles print |
| 15:35–16:30 | 09:35–10:30 | **Prime window.** Pullbacks 1–2 only, `tape.py` before every entry, stop ≥ the median 1-min range, no 3¢ stops on halting names |
| 16:30–17:00 | 10:30–11:00 | **Late window.** Past the 90-minute mark — reduce, new entries must be better than the ones you took |
| 17:00 | 11:00 | Wind down. New entries only on a perfect setup |
| 17:30 | 11:30 | **Hard stop.** Green or red, done. Then, if trades were taken: trade-review |

## Boundaries

Prime 09:35–10:30, typical close 11:00, hard stop 11:30 — the **outer edge, not
the centre** (`PARAMETERS.md` §2: `prime_window` n=44, `session_close` n=16).
He frames the session as a **duration** — *"9:30 until 10:30 or 11:00, right
around that 90 minute mark"* — so a plan that runs to 11:30 trades 30–60
minutes he is not in. Corrected 2026-08-18: this table previously ran
09:35–11:00 as one flat block.

For the platform side of each block — which Dash scanner, which column —
see `knowledge-base/daytrade-dash/PLAYBOOK.md`.

## Standing reminders

- Risk per trade ≈ $150–500 on the $100k paper account; judge stops on
  enforceability, not tightness.
- A flat day is a correct output, not a failure to find something.
- Rules live in `knowledge-base/strategies/FILTERS.md` — don't restate them
  in the plan, link the phase to the command that applies them.
