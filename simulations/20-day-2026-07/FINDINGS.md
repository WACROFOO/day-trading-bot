# Why my results did not match his — nine bugs and one architectural error

**All P&L conclusions in the earlier reports are withdrawn.** Every "structural
finding" I reported was an artifact of my own implementation. The challenge was
correct: a 21% win rate against a claimed ~68% is a bug signature, not a result.

---

## The nine bugs

Each is verifiable against a source document, not a judgement call.

| # | Bug | Source it violates | Effect |
|---|---|---|---|
| 1 | Target set to `entry + 2R` | 5 videos: target is the **HOD retest**; 2:1 is a *filter* ([hLn6LrlXgAE 20:23](https://www.youtube.com/watch?v=hLn6LrlXgAE&t=1223s)) | Guaranteed every winner = exactly +1.00R. **This manufactured the "all winners made +1R" finding I reported as a discovery.** |
| 2 | "New low" exit fired on any lower-low red bar | *"new low **below flag**"* ([Xdw5azEqs6o](https://www.youtube.com/watch?v=Xdw5azEqs6o)) | Killed 5 of 14 trades inside 4 min. Median hold was 2 minutes. |
| 3 | `stop_min_distance` never implemented | `PARAMETERS.md:161` | Allowed a 2-cent stop on a $15 stock |
| 4 | 1-bar pullbacks accepted | `PLAYBOOK.md:99` ("2–3 candles") | A single red print counted as a retracement |
| 5 | Wide stop = skip | `PLAYBOOK.md:166`: **"cut your size OR skip"** | **Rejected every strong mover.** The engine was left trading whichever watchlist name was moving *least*. |
| 6 | Leg measured from 1–2 "impulse bars" | — | The 50%-retracement rule was computed against a meaningless leg |
| 7 | Confluence used `abs(price - level)` | "the dip should **stop at** a level" | Approved dips that had **broken** support and were bouncing underneath. Measured: pullback low was below the 9 EMA in **87%** of setups, median −1.23% |
| 8 | **Trigger tested *after* leg extension** | `PLAYBOOK.md:132` | On a strong mover the trigger bar usually takes out the leg high too, so it was filed as "leg continues" and the setup discarded. **An anti-momentum detector: the faster a stock ran, the fewer signals it produced.** |
| 9 | Losing VWAP wiped all swing structure | my invention — VWAP is an *entry gate* | These names are below VWAP 57–68% of the session, so structure was destroyed continuously |

Bug 8 is the clearest single illustration. VEEE on 2026-07-13 ran **$12.20 →
$29.19 (+139%)**, was on the watchlist, and produced **5 setups all morning,
the first at 10:37** — after the prime window. My engine traded SKYQ and MIMI
that day instead and lost on both. After fixing 8 and 9 it produces 10 setups
starting 10:09.

Fixing all nine took setups from 481 (mostly noise) to 835 (real structure).

---

## The architectural error — this is the actual answer

After all nine fixes, requiring the entry conditions to hold **simultaneously**
passes **1 setup in 835**.

A leave-one-out test shows there is no single culprit — dropping *any one*
condition still leaves 1–4 passing:

| Drop this condition | Then passing | Passes individually |
|---|---:|---:|
| MACD histogram > 0 | 1 | 63% |
| front side of the move | 4 | 42% |
| price > 9 EMA | 1 | 74% |
| price > VWAP | 1 | 61% |
| pullback 2–4 candles | 1 | 46% |
| pullback holds 50% of leg | 1 | 24% |
| pullback index ≤ 2 | 1 | 50% |
| pullback volume < impulse | 1 | 79% |
| support confluence ≥ 2 | 3 | **7%** |

The median setup fails 4–5 of 9. Multiply the individual rates:
`0.63 × 0.42 × 0.74 × 0.61 × 0.46 × 0.24 × 0.50 × 0.79 × 0.07 ≈ 1 in 10,000`.

**That is the answer to "he made money applying these rules and you didn't."**
He applies them as holistic visual judgement — approximately, together, on a
chart. I encoded them as nine hard AND-gates with numeric thresholds I invented
where the corpus gives none. A conjunction of nine approximate rules is
exponentially stricter than the judgement it approximates. Even if every one of
my thresholds were 90% faithful, requiring all nine would pass only 39% of what
he takes; at my measured fidelity it passes ~0.01%.

**My implementation is not his strategy.** It is a far more restrictive strategy
that reuses his vocabulary. Nothing it produces — profit or loss — is evidence
about his rules.

---

## What I will not claim

Relaxing the gate to a *score* (PARAMETERS.md §12 step 3) gives:

| Min pillars | Trades | Win % | P&L | Exp R |
|---:|---:|---:|---:|---:|
| 9 | 0 | — | 0.00 | — |
| 8 | 4 | 25.0 | −225.29 | −0.457 |
| 7 | 21 | 19.0 | −1894.72 | −1.252 |
| 6 | 41 | 26.8 | −803.06 | +0.508 |
| 5 | 62 | 37.1 | **+245.89** | +0.383 |

**The +$245 at 5 pillars is not a finding and I am not reporting it as one.**
The gradient is non-monotonic (7 is far worse than 6, which is worse than 5),
which is precisely the test `PARAMETERS.md` §12 step 3 specifies for whether
the pillar structure captures quality. It fails. Picking the best of five cells
on n=62 with a noisy gradient is curve-fitting — the same error, in the
opposite direction, as the one that produced the bogus findings above.

---

## Honest status

- The strategy is **neither validated nor refuted**. I never tested it.
- Nine implementation bugs are found, documented and fixed.
- The blocking problem is now understood and is **architectural**: a
  discretionary visual pattern cannot be faithfully expressed as a conjunction
  of independently-thresholded booleans.
- A faithful test needs the conditions expressed as a *graded* match calibrated
  against setups he actually took — i.e. labelled examples from the videos,
  where the timestamps in `claims.db` give the entry moments. That is a
  different and much larger piece of work than a rule translation, and it is
  the honest next step.
