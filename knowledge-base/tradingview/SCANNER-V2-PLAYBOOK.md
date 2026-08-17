# Scanner v2 — operating playbook

```
SCOPE · ross-style-scanner-v2.pine · Pine v6 indicator · clean-room
approximation of PUBLIC Warrior criteria. Server thresholds are UNKNOWN.
Audit + the four corrections: knowledge-base/daytrade-dash/README.md.
This tool answers WHICH NAME. It never answers WHEN — that is ross-fp-v4.
```

## What it is, in one line

A **Layer 0–1 selection instrument**: it scores the four measurable pillars,
flags high-of-day events, and exposes eleven numeric columns to Pine Screener.
It holds no position, knows no VWAP, and has no opinion on your entry.

---

## The three modes

### Mode A — Pine Screener (discovery, 07:00–09:25)

Pine Screener runs a custom indicator over a **watchlist**, not the market.
So the funnel has two stages and the first one is not this script:

```
TV native Stock Screener  →  watchlist (broad, 50-300 names)
        ↓
Pine Screener + scanner v2  →  4/4 candidates (1-10 names)
        ↓
./now --scan cross-check   →  catalyst, split test, buyout, EDGAR
        ↓
1-3 names get a chart
```

Click path: save + favourite the script → **Products → Screeners → Pine** →
pick the watchlist → pick the indicator → timeframe **1m** → add filter
`Technical 4/4 candidate = 1` → sort by `Gain from prior close %` desc.

**Two traps in this mode, both from one cause — an input applies to every
symbol at once:**

| input | in Screener mode |
|---|---|
| `Manual float` | leave at **0**. A per-symbol float is impossible here |
| `News/catalyst confirmed` | leave **off**. It would mark all names confirmed |

Consequence: in Screener mode the float column is the shares-outstanding
proxy, which **overstates** float by construction (outstanding ≥ float).
A FAIL there means "verify", never "dead" — that is where the biggest
runners hide (ONFO, WETO and SXTC all had no published float last week).

### Mode B — single chart (verification, before you commit)

Put it on the 1-minute chart of a survivor, **extended hours ON**.
Now the two inputs above become useful: type the verified float, tick the
catalyst box once you have read the headline yourself. The dashboard becomes
a per-name PASS/FAIL card, and `Technical score 4/4` finally means something
about that specific stock.

### Mode C — alerts (background, while you do something else)

Right-click → Add alert → choose the indicator → pick a condition. Use
**Once per bar close** while you are still validating the script; intrabar
alerts fire faster but can un-fire before the candle closes.

Which condition for which job:

| condition | fires when | use it for |
|---|---|---|
| Technical Five Pillars candidate | a name enters 4/4 | pre-market watch |
| Five Pillars HOD | 4/4 **and** new HOD **and** 5-min RVOL | the closest thing to his flagship alert |
| Running Up | 3% in 2 min + volume | early-move detection |
| Squeeze 5%/5min · 10%/10min | explicit bursts | halting-name warning |
| 52-week breakout | daily-level break | context, not a trigger |

---

## Reading the dashboard, row by row

| row | what it proves | what it cannot say |
|---|---|---|
| Price | inside $2–20 | nothing about tick size or spread |
| Gain vs close | today's move | not whether it is still rising (no fade check) |
| Daily RVOL | interest vs 20-day average | **biased low all morning** — see below |
| Float/supply | tagged `(manual)` or `(shs-out proxy)` | proxy ≠ float |
| News | only that YOU ticked a box | nothing automatic |
| Technical score | 4/4 gates | not a ranking, not a quality score |
| 5m RVOL | current burst vs recent 5-min bars | **biased high pre-market** — see below |
| HOD / Running | an event happened this bar | not that it will continue |
| Entry / Stop / Target | mechanical band levels | not a trade plan; candle-low stops are fiction on wide bars |

---

## The denominator problem — and the settings that work around it

Both RVOL cells are biased, in opposite directions, and knowing which way
is the difference between using them and being fooled by them.

**Daily RVOL = cumulative day volume ÷ 20-day full-day average.**
At 07:30 the numerator holds one hour of trading and the denominator holds
entire days. The cell reads ~0.2× on a name doing 10× normal business.

> **Workaround, morning:** treat `Daily RVOL` as *informational* before 10:00
> and filter on `Gain %` + `5-minute RVOL` instead. The v2 default of 2.0
> (book GR#1) already concedes this; do not raise it back to 5 to "be strict"
> — that deletes the whole pre-market population.

**5-minute RVOL average includes overnight bars** on an extended-hours chart.
Quiet 03:00 bars deflate the average, so pre-market bursts read inflated.

> **Workaround:** in pre-market require a *higher* 5-min RVOL (3–4 instead of
> 2) and cross-read against raw pre-market share volume in `./now`.

**A second contamination worth knowing:** the 20-day average is dragged up by
a name's own recent runs. A day-2 former runner therefore posts a *lower*
RVOL than a dormant name doing the same volume — exactly backwards from what
the Former Momo branch is hunting. Lower your RVOL expectation on day-2 names.

### Suggested setting profiles

| | pre-market 07:00–09:30 | open 09:30–10:30 | midday |
|---|---|---|---|
| Min daily RVOL | **0.5** (informational) | 2.0 | 2.0 |
| Min 5-min RVOL | **3.0–4.0** | 2.0 | 2.0 |
| Allow unknown float | **on** | on | on |
| Chart | 1-min, ext hours ON | 1-min | 1-min |

Save these as three indicator presets (settings → ⚙ → Save as default is
per-script; use TradingView's template dropdown for named presets).

---

## The eleven Pine Screener columns

Order matters — Pine Screener reads the first plots. `Float known` is v2's
addition so an unverified float shows as unknown instead of hiding.

```
1  Pillar score (0-4)        7  Technical 4/4 candidate
2  Price                     8  Five Pillars HOD
3  Gain from prior close %   9  HOD Momentum
4  Daily RVOL               10  Running Up
5  5-minute RVOL            11  Float known (0 = unverified)
6  Float/supply proxy M
```

Sort recipe that mirrors his own top-down reading: filter `7 = 1`, sort
`3` descending, then eyeball `6` ascending among the top rows.

**Known gap:** column 9 collapses all eleven HOD sub-strategies into one
boolean — you cannot tell from the Screener *which* branch fired. On a chart
the markers distinguish them (5/5 yellow diamond, 10/10 fuchsia, HOD triangle,
5P HOD green label). A per-branch ID column would fix this for calibration.

---

## Using it for calibration (the trial's real payoff)

The scanner's most valuable job right now is not finding stocks — it is
**triangulating the unknown thresholds** while the Warrior trial lasts.

At a fixed minute, on the same symbol, record three numbers:

| source | field |
|---|---|
| Day Trade Dash | its displayed daily RVOL / 5-min RVOL / float |
| scanner v2 dashboard | same three cells |
| `./now SYM` | our vol, rot, rvol |

Three sources, one truth, three different denominators. After ~20 samples the
gaps stop being mysterious and become a measured offset. Store pairs in
`knowledge-base/daytrade-dash/captures/`, protocol in that folder's README.

Already bounded from the 40-alert snapshot: low-float ceiling **≥5.4M**,
medium float **includes 33M**, and the platform alerts **below $2**. So
`lowFloatMaxM` 20 and the $2 price floor are *our* choices, not his.

---

## What this scanner does not check

Catalyst dating · reverse-split arithmetic · buyout pinning · dilution and
shelf/ATM · live halt state and LULD bands · spread and executable size ·
borrow · fade from the high · VWAP · MACD · pullback structure.

The first five live in `./now --scan` and `catalyst_score.py`. The last four
live in `ross-fp-v4.pine`. **A 4/4 candidate is a name worth charting, not a
trade.** Paper only — the repo's 894-session replication of this strategy
class was negative expectancy, and a green dashboard does not overturn it.
