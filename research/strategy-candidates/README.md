# strategy-candidates/ — every combination tested, and whether any of them is profitable

```
ASKED    · the owner, 2026-10-12: track every combination tested in one folder; run the brainstormed
           candidates on the last five years; if one is not profitable, say why and how it could be
RULES    · PREREGISTRATION.md — written and committed BEFORE any five-year run
CODE     · scripts/candidates/ (README there) · tests/test_candidates.py
DATA     · 2021-01-01 → 2026-08-21: 15,959 gapper symbol-days (candidate_days.csv), Alpaca SIP 1-minute
           bars — on the Mac; this container has no market-data keys and no bar cache
STATUS   · nothing measured on the five years yet. One smoke run on the 20 exported desk days
           (runs/2026-10-12-smoke/) checked the plumbing; it is not evidence
```

## 1 · The board — every candidate, every combination counted

| id | candidate | combinations | where it stands | result |
|---|---|---:|---|---|
| **S1** | afternoon fade: short once the high of day is ≥ 30/60 min old and VWAP is lost | 6 | preregistered · waiting for the Mac run | — |
| **S2** | crowded-gapper fade: short the first red 5-minute bar of a ≥ 20/40 % gap on ≥ 2 M pre-market shares | 8 | preregistered · waiting for the Mac run | — |
| **L1** | real-time new-high dip: the megaday entry without knowing the day is a megaday | 6 | preregistered · waiting for the Mac run | — |
| **L2** | the #1 gainer's new-high break | 18 + 54 | **done before** — the edge hunt's F7 and F8 | ✗ F7 failed validation (net −0.270 R); F8's holdout −0.188 R over 592, every year negative. Not re-run: its holdout is read |
| **L3** | reference: the bot's entry + stop ≥ 3 % + new-low exit + done after a loss | 1 | preregistered · reference only, never opens the holdout | — |
| shorts, 20 days | mirror, back side, extension, time fade, the owner's five-condition combination | 31 | first look, 2026-10-12 | ✗ every variant negative net on the selection days — 20 sessions, not evidence (`prior-20-days/`) |

Also counted in `registry.jsonl`: the megaday study's 4 hypotheses (L1's origin) and the edge
hunt's 174 exit/sizing configurations (L3's origin).

## 2 · How to run it (the Mac)

```bash
bash scripts/update.sh
python3 scripts/candidates/run.py
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
| `PREREGISTRATION.md` | the rules, the split, the gate, the seven criteria, the diagnosis — fixed before any run |
| `registry.jsonl` | every combination ever evaluated here, one line each, prior reads included; the Mac's runs are appended when they come back |
| `holdout_ledger.jsonl` | one line per holdout opening (empty: none yet). The runner also refuses a second opening found in the Mac's local `results/holdout_ledger.jsonl` |
| `prior-20-days/` | the short-side reads of 2026-10-12 on the 20 exported days, scripts and output |
| `runs/` | the reports brought back, one folder a run |
| `results/` | git-ignored: what a run writes on the machine that ran it |

## 5 · What this cannot test

Level 2, borrow availability and fees, locates, halts as such, a short-sale restriction carried
from the previous day, ten-second structure, and the pre-market for S1, S2 and L1 (the
universe knows the 09:30 open). Details in the preregistration §10.

## 6 · Verdict

None yet: no candidate has been measured on the five years. L2 is already answered — no.
Paper only.
