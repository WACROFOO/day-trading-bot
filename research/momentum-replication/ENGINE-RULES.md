# What the engine implements, and where each rule comes from

One line per rule, one citation per rule. Nothing here is invented; anything the
corpus does not specify is listed at the bottom as open rather than filled in.

## Stock selection — the five pillars

| Rule | Source |
|---|---|
| Price $2–$20 | `PARAMETERS.md` §1 |
| Gap ≥ +10% | `PARAMETERS.md` §1 |
| Relative volume ≥ 5× | `PARAMETERS.md` §1 (n=61) |
| Float under 20M | `PARAMETERS.md:26` (10M preferred — value disputed in source) |
| News catalyst | `PARAMETERS.md` §1 (n=83) — **not verifiable here; assumed** |

## Session

| Rule | Source |
|---|---|
| Watch, do not trade, until 09:35 | `PARAMETERS.md:68` |
| Trade 09:35–11:30 | `PARAMETERS.md:70` |
| Pre-market 07:00–09:30 | `PARAMETERS.md:71` — **not implemented, no volume in feed** |

## The pattern (detector)

| Rule | Source |
|---|---|
| Impulse → 2–3 candle dip → first candle over the prior candle's high | `PLAYBOOK.md:99`, `PARAMETERS.md:143` |
| Dip must be 2–4 candles (`MIN_DIP_BARS`) | `PLAYBOOK.md:99` |
| Count resets when the move ends (base, or loses VWAP) | `BUCPPCXOHbs` [52:17], `m5zu_X-_51I` [46:43] |

## Entry gate — exactly `PARAMETERS.md` §3

Six conditions, all must hold:

| Condition | n |
|---|---:|
| `pullback_volume < impulse_volume` | 168 |
| `at_support(p) >= 2` (confluence) | 157 |
| `macd_hist > 0` | 66 |
| `price > vwap` | 45 |
| `pullback_index <= 2` | 39 |
| `price > ema9` | 30 |

Two further gate conditions exist in the source and **cannot be evaluated**:
`tape_green` and `no_seller_wall` (n=47 each) need Level 2.

## Sizing and risk

| Rule | Source |
|---|---|
| Stop = low of the pullback | `PARAMETERS.md:158` (n=50) |
| Shares = risk budget ÷ risk per share | `PLAYBOOK.md:145` |
| Stop wider than $0.20 → cut size, do not skip | `PLAYBOOK.md:166` |
| Stop may not be tighter than the spread | `PARAMETERS.md:161` |
| Risk 2% / day limit 6% / max 2 trades | `PLAYBOOK_V2` |

## Targets and exits

| Rule | Source |
|---|---|
| First target = **nearest** of {HOD retest, measured move} | 5 videos; `small-cap-momentum-bull-flag.md` |
| Minimum 2:1 against that target | `hLn6LrlXgAE` [20:23] |
| Sell half at target, stop to breakeven | `4Pc_von1wS4` [40:45] |
| Exit on MACD negative / lost VWAP / big red candle on volume | `PLAYBOOK.md:185-192` |

---

## Removed in this pass

| Removed | Why |
|---|---|
| `front side of the move` | **A duplicate of the MACD condition.** `iIC62xnblLc` [26:20]: "only trade when MACD is positive and above the signal line (front side of move)". It was checked separately with an invented threshold |
| `pullback holds 50% of leg` | Not in the §3 gate; rests on one claim about first pullbacks |
| `pullback 2-4 candles` (as a gate check) | Belongs in the detector, where it lives. In the gate it was a second copy that could never fail |

Removing all three changed the result by **nothing** (6 trades, +$817.95 before
and after), which is the expected outcome for a cleanup: they were already
non-binding. The value is that the gate is now exactly the documented one.

---

## Still open — recorded, not guessed

| Question | Status |
|---|---|
| `level_tolerance` | `PARAMETERS.md:127` — "unstated". Swept, floored at spread width |
| `MIN_DIP_BARS` on a 1-minute chart | `PLAYBOOK.md:99` says 2–3 candles, but the source also reads a 10-second chart where a 1-minute pause *is* a 2–3 candle dip (`m5zu_X-_51I` [46:43]). Kept at 2 per the playbook; resolving it needs 10-second data |
| Float 20M vs 10M | Disputed in source (18 vs 16 statements) |
| `tape_green`, `no_seller_wall` | Need Level 2. Unevaluable |
| News catalyst | Not verifiable programmatically |

---

## Current state

17 days, 6 trades, +$817.95. Look-ahead audit passes at every cut-off.

460 setups, **31 pass all six conditions** (6.7%). Leave-one-out is flat — no
condition is a choke point:

| Condition | Pass rate | All-pass if dropped |
|---|---:|---:|
| `pullback_volume < impulse_volume` | 78% | 43 |
| `pullback index <= 2` | 72% | 48 |
| `price > 9 EMA` | 66% | 35 |
| `MACD histogram > 0` | 62% | 42 |
| `support confluence >= 2` | 60% | 51 |
| `price > VWAP` | 53% | 85 |

**n=6. Not a result.** The sign has moved with every structural change in this
project, and 6 trades cannot distinguish an edge from noise. The engine is now
a faithful transcription of the documented strategy; whether that strategy
works is a separate question that needs a bigger sample than free data allows.
