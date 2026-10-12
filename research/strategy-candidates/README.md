# strategy-candidates/ — every combination tested, and whether any of them is profitable

```
ASKED    · the owner, 2026-10-12: track every combination tested in one folder; run the brainstormed
           candidates on the last five years; if one is not profitable, say why and how it could be
RULES    · PREREGISTRATION.md — written and committed BEFORE any five-year run
CODE     · scripts/candidates/ (README there) · tests/test_candidates.py
DATA     · 2021-01-01 → 2026-08-21: 15,959 gapper symbol-days (candidate_days.csv), Alpaca SIP 1-minute
           bars — on the Mac; this container has no market-data keys and no bar cache
STATUS   · run 2026-10-12T1350Z (the Mac): S1, S2 and L1 fail the 2023 gate, no holdout opened —
           RESULTS.md · NEXT: the real-quote cost check (amendment 2026-10-12c), then — only if its
           verdict allows — S2's lead S2W (amendment 2026-10-12b)
```

## 1 · The board — every candidate, every combination counted

| id | candidate | combinations | where it stands | result |
|---|---|---:|---|---|
| **S1** | afternoon fade: short once the high of day is ≥ 30/60 min old and VWAP is lost | 6 | **closed** — run 2026-10-12T1350Z | ✗ fails the 2023 gate (−0.294 on 237); gross ≈ 0 in both periods, the fade is over by the setup |
| **S2** | crowded-gapper fade: short the first red 5-minute bar of a ≥ 20/40 % gap on ≥ 2 M pre-market shares | 8 + 1 | gate failed — **its lead S2W is preregistered**, waits for the Mac | ✗ fails the 2023 gate (−0.089 on 106); held to the close the gross is positive in all 8 cells, costs and the year take it |
| **S2W** | S2's lead: G20·hod·close kept only when the stop is 10-20 % above | (in S2) | amendment 2026-10-12b — **waits for the cost check**: 2016-2020 first, then S2's one opening | — |
| *cost check* | S2's close-exit trades re-priced on real Alpaca prints and quotes, train and 2023 | — | amendment 2026-10-12c — **next to run** | — |
| **L1** | real-time new-high dip: the megaday entry without knowing the day is a megaday | 6 | **closed** — run 2026-10-12T1350Z | ✗ fails the 2023 gate (−0.135 on 107); the entry does what a random minute does |
| **L2** | the #1 gainer's new-high break | 18 + 54 | **done before** — the edge hunt's F7 and F8 | ✗ F7 failed validation (net −0.270 R); F8's holdout −0.188 R over 592, every year negative. Not re-run: its holdout is read |
| **L3** | reference: the bot's entry + stop ≥ 3 % + new-low exit + done after a loss | 1 | reference only, never opens the holdout | −0.371 train · −0.091 in 2023 |
| shorts, 20 days | mirror, back side, extension, time fade, the owner's five-condition combination | 31 | first look, 2026-10-12 | ✗ every variant negative net on the selection days — 20 sessions, not evidence (`prior-20-days/`) |

Also counted in `registry.jsonl`: the megaday study's 4 hypotheses (L1's origin) and the edge
hunt's 174 exit/sizing configurations (L3's origin).

## 2 · How to run it (the Mac)

```bash
bash scripts/update.sh
python3 scripts/candidates/run.py              # the five-year run (done 2026-10-12T1350Z)
python3 scripts/candidates/requote.py          # NEXT: the real-quote cost check (amendment 2026-10-12c)
python3 scripts/candidates/run.py --lead S2W   # only if the check's verdict allows it — the runner refuses otherwise
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

**No candidate is profitable after costs on the five years** (run 2026-10-12T1350Z): S1, S2 and
L1 fail the 2023 gate and their holdouts stay unread; L2 was already answered — no. S1 and L1
are closed. S2's fade exists before costs; its wide-stop lead S2W is the one test left, gated
on 2016-2020 before it may open S2's holdout. Paper only.
