# Session reports

One file per session day, named by ET date, written by `scripts/day.py`
after the hard stop. Layout follows `.claude/skills/trading-report-design`:
provenance first, funnel with denominators, rejects named with the gate
that killed them, controls in planned R, replay result, limitations last.

Empty until the first live session. A report here from a synthetic fixture
says **SYNTHETIC FIXTURE** in its second line.

## Analyses (not session reports)

| file | what it is |
|---|---|
| `2026-10-01-rules-audit.md` | every operating rule (5, E, F, G) one at a time on ten years, the indicator audit, the defects fixed — verdict: no rule change, one candidate (A15) built OFF |
| `rules_audit_output*.txt`, `rules_audit_results.json`, `indicator_audit_output.txt` | the raw outputs behind it |
| `rules_audit_open_output.txt`, `rules_audit_open_results.json` | addendum 2026-10-01c: three opening-risk candidates (stop vs recent range, opening lockout, plans per name) after the NXL loss — none passes; the first plan of the day is the least-bad cohort but still negative |
| `tick_replay_output.txt`, `tick_replay_results.json` | stage 1 of the tick replay (2026-10-02): the B portfolio's 2,577 gate-passing 2024+ plans filled and exited on SIP prints with the real spread — bars and ticks agree; real costs about 0.40 R a trade |
| `desk_replay_output.txt`, `desk_replay_results.json` | stage 2 (2026-10-02): the same plans armed the way the live desk arms them, mid-minute (median 36 s before the close), gates on the half-formed minute — 243 plans pass only at desk time, 165 only at the close; B is worse at desk time: −0.534 against −0.511 R a trade with real spreads |
| `stage3_output.txt`, `stage3_results.json` | stage 3 + partial exit (2026-10-02, addendum 2026-10-02c) on 648 sessions, real spreads: D −0.542; S3-dip −0.452 (better every year, lower bound −0.004: misses); S3-confirm −0.549; P-half2R −0.529; reported only: P-half1R −0.504 and S3-dip+P2R −0.436 clear the bar but were not preregistered as deciding — switch OFF, prospective. All negative. **Later the same day:** no switch was built, and P-half1R is refuted when the target fills only on a trade through it (lb −0.0004; execution study, review M3) |
| `cadence_output.txt`, `cadence_results.json` | reaction speed (2026-10-02, addendum 2026-10-02d): arming latency × loop period on 434 sessions — the live setting (10-s candle + 4 s, 5-s loop) is the best cell overall (−0.449) and pre-market (−0.379); acting on every print is the worst (−0.531): faster is not better. One regular-hours cell (crossing print + 1 s, 10-s loop) beats live in each year by 0.014 R — meets the addendum's soft bar, has no lower bound, not built |
| `2026-10-02-full-report.md` | **the day's research in one report:** ticks stages 1–3, partial exits, reaction speed, the execution-cost study (M1–M9 with reviews), the Running Up tile study, the live defects fixed — verdict: nothing closes the gross deficit; built: execution safety only |
| `2026-10-02-execution-study/` | where the cost goes on the tape (1,873 fills: 0.387 R a trade, spread 47%), nine execution proposals and their adversarial reviews; M1 (stop of last resort) and the M4 trigger-method pin built in e58a9d2 |
| `2026-10-02-running-up-study/` | why a small-move Running Up row gets no positive evaluation (the cascade fails closed on unknown float/catalyst; nothing evaluative on the row), the swing grade and its downside tail, eight display changes with reviews |
| `runup_micro_output.txt`, `runup_micro_results.json`, `runup_micro_sample.json` | addendum 2026-10-02e (`scripts/runup_micro.py`): Running Up runner + 10-second micro pullback + 5-minute confirmation on 300 sampled symbol-days 2024–26 — 1,474 trades, **gross −0.193 R a trade, worse than random entries in the same windows (−0.109)**; the 5-minute check adds nothing (no-5-min −0.197); costs 1.08 R a trade (median stop 1.15 % of price); net −1.27 |
| `2026-10-03-ross-reverse-engineering.md`, `sel3_leader_output.txt`, `sel3_pause_output.txt` | his trades against the pillars (10-agent review + two preregistered follow-ups, addendum 2026-10-03): 90 % of his entries buy a new high of day, he does not buy a pullback-less climb either; **the leader rank (#1-2 gainer) does not help the bot's entry (−0.395 vs −0.407 net, train) and letting a green lower-high candle start a pullback is worse (−0.483 vs −0.438)** — the red-candle question is closed on the 1-minute chart; the 5-minute new high is the one open test |
| `ablation_live_costs*.txt` | the ten-year ablation at live costs (2026-09-29/30) |
| `2026-09-26-premarket-history.md`, `2026-09-25-full-assessment.md` | earlier assessments |
