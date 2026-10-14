# strategy-candidates/ — every combination tested, and whether any of them is profitable

```
ASKED    · the owner, 2026-10-12: track every combination tested in one folder; run the brainstormed
           candidates on the last five years; if one is not profitable, say why and how it could be
RULES    · PREREGISTRATION.md — written and committed BEFORE any five-year run
CODE     · scripts/candidates/ (README there) · tests/test_candidates.py
DATA     · 2021-01-01 → 2026-08-21: 15,959 gapper symbol-days (candidate_days.csv), Alpaca SIP 1-minute
           bars — on the Mac; this container has no market-data keys and no bar cache
STATUS   · Round 1 CLOSED, none profitable. The five-year run (RESULTS.md): S1, S2 and L1 fail the
           2023 gate. The real-quote cost check (COST-CHECK.md): the cost model holds, S2's lead S2W
           fails its gate 1. No holdout was ever opened: 2024-2026 is unread for all of them.
           Round 2, the desk's levels (L4-L6 and the level read-out, amendment 2026-10-14):
           preregistered, waiting for the Mac's five-year run
```

## 1 · The board — every candidate, every combination counted

| id | candidate | combinations | where it stands | result |
|---|---|---:|---|---|
| **S1** | afternoon fade: short once the high of day is ≥ 30/60 min old and VWAP is lost | 6 | **closed** — run 2026-10-12T1350Z | ✗ fails the 2023 gate (−0.294 on 237); gross ≈ 0 in both periods, the fade is over by the setup |
| **S2** | crowded-gapper fade: short the first red 5-minute bar of a ≥ 20/40 % gap on ≥ 2 M pre-market shares | 8 + 1 | **closed** — runs 2026-10-12T1350Z and T1512Z-quotes | ✗ fails the 2023 gate (−0.089 on 106); held to the close the gross is positive in all 8 cells, but costs take it — confirmed on the real tape, where it loses even at the touch |
| **S2W** | S2's lead: G20·hod·close kept only when the stop is 10-20 % above | (in S2) | **closed** at gate 1 (amendment 2026-10-12b) | ✗ as a rule it loses on train: −0.040 on 127 (−0.019 on real quotes) |
| *cost check* | S2's close-exit trades re-priced on real Alpaca prints and quotes, train and 2023 | — | **done** — run 2026-10-12T1512Z-quotes (amendment 2026-10-12c) | the proxy holds: real execution +0.026 R a trade cheaper, inside ±0.05 |
| **L1** | real-time new-high dip: the megaday entry without knowing the day is a megaday | 6 | **closed** — run 2026-10-12T1350Z | ✗ fails the 2023 gate (−0.135 on 107); the entry does what a random minute does |
| **L2** | the #1 gainer's new-high break | 18 + 54 | **done before** — the edge hunt's F7 and F8 | ✗ F7 failed validation (net −0.270 R); F8's holdout −0.188 R over 592, every year negative. Not re-run: its holdout is read |
| **L3** | reference: the bot's entry + stop ≥ 3 % + new-low exit + done after a loss | 1 | reference only, never opens the holdout | −0.371 train · −0.091 in 2023 |
| shorts, 20 days | mirror, back side, extension, time fade, the owner's five-condition combination | 31 | first look, 2026-10-12 | ✗ every variant negative net on the selection days — 20 sessions, not evidence (`prior-20-days/`) |
| **L4** | trend-line break: a close above the desk's down-line, stop under the last 5 bars or under the line, target 2 R / trail / next resistance / high of day | 8 | **preregistered** 2026-10-14 (amendment), waiting for the five-year run · WAIT | first look on the 22 desk days: every cell negative net (`levels-first-look/`) — not evidence |
| **L5** | support hold: the fan's nearest support touched and held (Pine's retest test) | 8 | **preregistered** 2026-10-14, waiting · WAIT | first look: every cell negative net — not evidence |
| **L6** | resistance break: a close above the fan's nearest resistance + band | 8 | **preregistered** 2026-10-14, waiting · WAIT | first look: two cells positive on the early days, both negative on the later ones — not evidence |
| *level read-out* | do the desk's levels hold more often than the same levels moved ±0.5-1.5 ATR? Descriptive, 2021-2023 only | — | **preregistered** 2026-10-14, waiting | first look: none better than its placebo; the fan's support worse (−3.0 pts) — not evidence |

Also counted in `registry.jsonl`: the megaday study's 4 hypotheses (L1's origin) and the edge
hunt's 174 exit/sizing configurations (L3's origin).

## 2 · How to run it (the Mac)

```bash
bash scripts/update.sh
python3 scripts/candidates/run.py              # the five-year run (done 2026-10-12T1350Z)
python3 scripts/candidates/requote.py          # the real-quote cost check (done 2026-10-12T1512Z-quotes)
python3 scripts/candidates/run.py --lead S2W   # not needed: its gate 1 is already read (COST-CHECK.md §4)
python3 scripts/candidates/run.py --families L4,L5,L6   # the levels round (amendment 2026-10-14)
python3 scripts/candidates/level_read.py       # the level read-out, 2021-2023 only
```

The report prints on the screen: paste it back, or upload
`research/strategy-candidates/results/<run>/report.txt`. Everything the run writes stays in
`results/` — git-ignored, so `update.sh` leaves it alone. A missing session is fetched with
the Alpaca keys in `.env`; with neither the cache nor the keys the run stops and says so.

Optional first, to check the setup in a minute: `python3 scripts/candidates/run.py --sample 30`
(30 sessions a split, opens nothing, registers nothing).

## 3 · How a result reads

Per family: one table row per combination (train and validation, one position at a time, net
of costs, R a trade); the one chosen **on train only**; the validation gate; then for the
chosen one:

| line | answers |
|---|---|
| **WHY** | gross − commission − spread = net; win rate, average win and loss; MFE (how far it went the right way); how much of the result is its best 5 % of trades; random entries on the same names |
| **READING** | the rule-based diagnosis: *the signal loses before costs* · *costs take it* · *the exit gives it back* · *random entries do as well* · *a lottery* |
| **BORROW** | shorts: the borrow cost, in % of price, that would wipe the result out |
| **WHERE** | leads — slices positive on train AND validation: hypotheses for the next round, never adopted from this one |

A family that passes its gate opens its holdout **in that run, once** (the ledger is written
first), and is judged on the seven criteria of the preregistration §6. A pass is a shadow
line and the owner's decision, never a switch.

## 4 · Files

| path | what |
|---|---|
| `PREREGISTRATION.md` | the rules, the split, the gate, the seven criteria, the diagnosis — fixed before any run; amendments dated at its end |
| `RESULTS.md` | **the read-out of the five-year run**: what failed, why, how it could work, my calls scored |
| `COST-CHECK.md` | **the read-out of the real-quote cost check**: the proxy holds, S2 and S2W closed |
| `cost_check.json` | the check's verdict as printed; the Mac's own copy sits in `results/` |
| `registry.jsonl` | every combination ever evaluated here, one line each, prior reads included; the Mac's runs are appended when they come back |
| `holdout_ledger.jsonl` | one line per holdout opening (empty: none yet). The runner also refuses a second opening found in the Mac's local `results/holdout_ledger.jsonl` |
| `prior-20-days/` | the short-side reads of 2026-10-12 on the 20 exported days, scripts and output |
| `levels-first-look/` | the levels round (L4-L6, the level read-out) on the 22 exported desk days, run after its amendment was pushed: plumbing and a first look, not evidence |
| `runs/` | the reports brought back, one folder a run |
| `results/` | git-ignored: what a run writes on the machine that ran it |

## 5 · What this cannot test

Level 2, borrow availability and fees, locates, halts as such, a short-sale restriction carried
from the previous day, ten-second structure, and the pre-market for S1, S2 and L1 (the
universe knows the 09:30 open). Details in the preregistration §10.

## 6 · Verdict

**None of the brainstormed candidates is profitable after costs.** S1, S2 and L1 fail the 2023
gate (run 2026-10-12T1350Z); L2 was already answered. S2's fade exists before costs, but real
quotes confirm the costs take it — it loses even filled at the touch — and its lead S2W fails
its first gate (run 2026-10-12T1512Z-quotes). No holdout was opened: 2024-2026 stays unread for
every family here. Paper only.
