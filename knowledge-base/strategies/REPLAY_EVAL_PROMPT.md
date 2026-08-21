# Prompt — blinded walk-forward self-assessment

Paste the block below as a single prompt. It is written to be run in an
environment that **has market-data access** (this repo's fetchers hit
Yahoo; a sandbox that blocks it will fail at step 1 — that is a correct
failure, not something to work around with synthetic bars).

---

## The prompt

> **Task: grade your own trading decisions under look-ahead blinding, then fix the code where you were wrong.**
>
> You are evaluating whether the Ross Cameron small-cap momentum strategy, as
> encoded in `knowledge-base/strategies/PARAMETERS.md`, produces profitable
> decisions — and, separately, whether *you* apply it correctly. Those are two
> different failure modes and I want them reported separately.
>
> ### 1. Build the sample (point-in-time, no hindsight)
>
> For each of the last 5 completed trading sessions:
>
> - Select the eligible tickers using **only information available by 09:25 ET
>   that morning**: prior-day close, premarket gain %, premarket cumulative
>   volume, and rvol against the 50-day average volume ending the *previous*
>   session. Apply §1: price $2–$20, day gain ≥ 10%, rvol ≥ 5.0, volume ≥
>   500,000.
> - **Do not** pick tickers because you know they ran. If you cannot reconstruct
>   a genuine point-in-time premarket scan, say so and state exactly what
>   substitute you used and how it biases the result. Selecting on the outcome
>   is the single most common way this kind of study lies.
> - §1 also requires `float_max` ≤ 20M and `has_catalyst`. Free data gives you
>   neither reliably. Mark every ticker's `float_ok` and `catalyst_ok` as
>   UNKNOWN rather than assuming true, and carry that UNKNOWN through to
>   `pillars_passed`. Report how many decisions would flip if those assumptions
>   are wrong.
>
> Pull 1-minute bars for each name with `paper_trading.history.fetch_day`
> (`prepost=True`), covering **07:00–11:30 ET** — premarket through the §2 hard
> stop. Build the 5-minute frame by resampling the 1-minute frame locally; do
> not fetch it separately, so both timeframes come from one source of truth.
>
> ### 2. Blind the future — this is the part that must not leak
>
> Replay each session bar by bar. At cursor `t`:
>
> - Construct `visible = bars.iloc[:t+1]`. **Every** indicator, level, and
>   decision must be computed from `visible` only.
> - Compute EMA9, EMA20, VWAP and MACD(12,26,9) with `paper_trading.indicators`
>   on `visible`. Then prove causality numerically: assert that each indicator's
>   value at `t` computed on `visible` equals its value at `t` computed on the
>   full session. These are causal by construction — if any assertion fails, you
>   have a leak, and the run is invalid until it is fixed.
> - The 5-minute frame at cursor `t` must include the **in-progress** 5m bar
>   built only from elapsed 1m bars. Never let a completed 5m bar appear before
>   its final minute has printed. This is the most likely place to leak.
> - Compute `at_support(p)` per §3 with `confluence_min = 2` over
>   {whole/half dollar, ema9, ema20, ma200, vwap, flipped_level}. Freeze
>   `tolerance_pct` at 0.25 for the main run.
> - Do not look at, print, plot, or reason about any bar after `t` before you
>   have committed the verdict for `t`. Emit the verdict, then advance.
>
> ### 3. Decide, one candle at a time
>
> For every 1-minute candle in 09:35–11:30 ET (§2 blackout: no entries before
> 09:35), record a row with each §3 gate evaluated independently:
> `macd_hist > 0`, `price > vwap`, `price > ema9`,
> `pullback_volume < impulse_volume`, `pullback_index <= 2`, `at_support`
> confluence count, and the §4 trigger (first candle to exceed the prior
> candle's high).
>
> `tape_green` and `no_seller_wall` need Level 2, which you do not have. Mark
> them UNTESTABLE — do not silently treat them as passing. Count how many TAKE
> verdicts depend on them.
>
> Then commit a verdict: **TAKE** or **SKIP**, with the one-line reason. On
> TAKE, record entry (§4: ask + 0.15 slippage cap), stop (§5: pullback low,
> reject if distance > $0.20 — never widen), size (§7:
> `risk_budget / risk_per_share`, 2% risk), target (§6), and the resulting
> reward:risk — reject below 2.0.
>
> ### 4. Resolve the outcome, then move forward
>
> Advance the cursor and manage the position on subsequent bars only: stop at
> the pullback low, §6 scaling 50/25/25, and the §6 hard exits (first candle to
> make a new low, MACD cross negative, VWAP break, high-volume red candle).
> Apply this repo's cost model: $0.005/share commission plus $0.02/share
> slippage per fill. Record realized R, MAE, MFE, and time in trade.
>
> Resolve **SKIP** decisions counterfactually too — what would the trade have
> done had you taken it. Without that you can measure precision but not recall.
>
> ### 5. Score yourself
>
> Report a confusion matrix over decisions: TAKE→win, TAKE→loss,
> SKIP→would-have-won, SKIP→would-have-lost. From it: precision, recall, win
> rate, and expectancy in R.
>
> Compare against the numbers the strategy itself commits to (§9): breakeven at
> 2:1 is a 33.3% win rate; the corpus claims 65–75%. State whether the sample
> clears the breakeven bar, and state N. **If fewer than 20 resolved trades,
> say the result is not significant and do not draw a conclusion from it** —
> a 5-day window on a handful of names usually lands here, and reporting it as
> if it were an edge is itself an inaccuracy I want flagged.
>
> Include the §12 baselines: buy-at-09:35 and hold to 11:30 on the same names,
> and a random-entry control on the same bars. An edge that does not beat those
> is not an edge.
>
> ### 6. Diagnose every miss, then fix the right thing
>
> For each TAKE→loss and SKIP→would-have-won, classify the cause:
>
> | Class | Fix |
> |---|---|
> | look-ahead leak | fix the code, invalidate and re-run |
> | indicator bug | fix, add a regression test |
> | rule encoded wrong vs `PARAMETERS.md` | fix, cite the § it violates |
> | data artifact (gap, delayed print, thin tape) | document, do not "fix" |
> | untestable input (Level 2, float, catalyst) | mark, quantify the exposure |
> | rule faithfully applied and still lost | **record as a finding — do not touch the parameters** |
>
> That last row is the one that matters. A rule that is correctly implemented
> and loses money is a result about the strategy, not a bug in the code. Do not
> tune thresholds until the losses go away — that is fitting noise, and §10 is
> explicit that the proxies are already the biggest source of backtest error.
>
> Where a parameter is genuinely free, sweep rather than pick: run
> `support.tolerance_pct` at 0.10 / 0.25 / 0.50 and report the spread of
> results. Per §12.3, **if the sign of the finding flips across the sweep,
> discard the finding** rather than reporting the cell that worked.
>
> ### 7. Deliverables
>
> 1. `results/replay_<date>.csv` — one row per candle decision, with every gate
>    boolean, the verdict, and the resolved outcome. This is the audit trail;
>    it must be reproducible from the archived bars.
> 2. A summary report: confusion matrix, metrics vs §9, the baselines, the
>    tolerance sweep, and N.
> 3. A **"what I got wrong"** section, listing every inaccuracy found, its
>    class from the table above, and what changed in the code. Lead with the
>    errors, not the wins.
> 4. Code changes committed with tests, on the working branch.
>
> ### Ground rules
>
> - Never fabricate a candle. If the data is missing, delayed, or the feed is
>   blocked, stop and report it — a synthetic bar invalidates the entire run.
> - Free Yahoo data is ~15 minutes delayed and retains only ~30 days of 1m
>   history. State how that constrains the sample.
> - Report the failures first and in full. I am asking for a measurement, not a
>   demonstration that the strategy works. A run that concludes "no edge
>   detectable at this sample size" is a successful run.
