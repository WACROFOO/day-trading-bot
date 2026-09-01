# YouTube-corpus integration — merging the repo's earlier knowledge into the bundle

> Integrated 1 September 2026. Sources: `knowledge-base/` in this repository — 257 public Ross Cameron/Warrior Trading YouTube transcripts processed in earlier sessions into 7,937 claims (2,050 mechanical rules, 1,749 typed numeric figures) stored in `data/claims.db` and rendered into `strategies/PARAMETERS.md`, `PLAYBOOK_V2.md`, `STRATEGY_V2.md`, `PLATFORM.md`, `small-cap-momentum-bull-flag.md`.
>
> Evidence class for everything in this file: **Observed (public-video corpus)** — statements counted from public YouTube transcripts, weighted by how many distinct videos state them. This is weaker than **Confirmed course** (authenticated Preview) but stronger than a single anecdote. Nothing here is backtested. Counts measure repetition, not validity.

## 1. How the two knowledge bases relate

| | Bundle (`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31`) | YouTube corpus (`knowledge-base/`) |
|---|---|---|
| Source | Authenticated Preview chapters 1–6, captured Day Trade Dash platform, official support docs | 257 public YouTube videos, auto-captions |
| Strength | Confirmed course/platform facts | Breadth: execution detail, session timing, daily limits, hotkeys, exit mechanics the Preview does not cover |
| Weakness | Chapters 7–15 unseen | Paraphrased claims, caption drift, marketing framing, internal conflicts |
| Precedence | Wins on any conflict | Supplements; fills gaps; flags hypotheses |

The corpus's own epistemic rules (claim ≠ evidence, marketing numbers are not backtests, survivorship bias is default, nothing validated until walk-forward out-of-sample with costs) are retained and consistent with the bundle's hierarchy.

## 2. Confirmations (both sources agree — confidence raised)

- Five Pillars decomposition and thresholds: price $2–$20 (sweet spot $5–$10), gain ≥10%, RVOL ≥5x, float <20M (lower preferred), catalyst. The corpus names the fifth pillar "rate of change" where the Preview says "volatility/leading gainer" — same concept, demand already visible.
- Entry trigger: first 1-minute candle to break the prior candle's high after a pullback; no anticipating (corpus n=85/67 videos).
- Stop: low of the pullback; never widen; never average down.
- Volume rule: pullback volume must be lighter than impulse volume — the single most-repeated rule in the corpus (169 statements / 101 videos), matching the Preview's first-pullback volume profile.
- Minimum 2:1 reward/risk; first target HOD retest.
- Indicators kept minimal: 9 EMA, 20 EMA, 200 MA, VWAP, MACD 12/26/9, volume.
- Scanner-first discovery funnel; ~8,000 equities → ~50 scanner hits → 3–5 watchlist → 1–2 trades.
- Journal in R; expectancy/adherence over P&L.

## 3. Additions from the corpus (not in the bundle — adopt as Observed, test before trusting)

### Session timing

| Parameter | Value (ET) | Corpus weight |
|---|---|---|
| Entry blackout | 09:30–09:35 — watch only, spreads widest | 63 stmts / 42 videos |
| Prime window | 09:30–10:30 — most edge | 44 |
| Hard stop | 11:30 | 16 |
| Midday avoid | 11:30–15:00 | 16 |
| Premarket | limit orders only | 38 |

### Additional entry gates (beyond the bundle's funnel)

- `price > VWAP` (45), `price > 9 EMA` (30), `MACD hist > 0` (66) at entry.
- `pullback_index <= 2` — first or second pullback only, never the third (39).
- Support confluence: the dip must stop at a price with **≥2 independent reasons** (whole/half dollar, 9/20 EMA, 200 MA, VWAP, flipped former resistance). Tolerance is unstated in the corpus — sweep 0.10–0.50% of price, floor at spread. (226 stmts / 100 videos)
- Tape green / no seller wall on Level 2 (needs quote/book data; only seller-wall detection truly needs depth).

### Stop/exit mechanics

- Typical stop distance $0.08–$0.10, max $0.20/share — if wider, reduce size or skip.
- Breakeven stop after +$0.10 or after first scale-out.
- Scale-out 50% at target 1 (HOD retest) → stop to breakeven → 25% at next level → trail 25%.
- Hard exits (any one): first candle to make a new low, high-volume red candle, MACD crosses negative, VWAP break, large seller on Level 2, shrinking green candles.

### Daily risk limits (the corpus's strongest unique contribution)

| Rule | Value | Weight |
|---|---|---|
| Max daily loss | = daily goal magnitude; ≤6% of account | 68 |
| Giveback stop | quit after giving back 50% of day's peak gain | 68 |
| Green-to-red stop | day turns negative → stop | 68 |
| Consecutive-loss stop | 3 losses in a row → stop | 68 |
| Max trades/day | 1–2 | 22 |
| Drawdown walkaway | 20% from equity high → break | 68 |
| Risk per trade | 2% of account (conflict: 3–5% also stated); beginner flat $50 | 125 |

Corpus claim (unverified, high-leverage if true): breaking max daily loss carries ~80% probability of doubling that loss. This motivates a **hard software lockout** in any platform we build — the risk gate must be able to veto the strategy layer.

### Execution/platform detail

- Marketable limit at ask + $0.15; max slippage budget $0.15/share.
- Hotkey scheme (Lightspeed-era): Shift+1 size+buy, Ctrl+Z sell all at bid, Ctrl+X sell half, Ctrl+Q cancel all. The "90% of buying power" sizing key contradicts risk-based sizing — build the risk-based version.
- Scanning, charting, execution are three separate services in Ross's own workflow; risk gate sits between strategy and execution with veto power.
- Scanner implementation notes: refresh rate matters more than criteria (push or sub-second poll beats 60s poll); rank, don't just filter; cap output (~50 hits max).
- Halts are frequent on this universe (46 stmts / 20 videos) — a halt indicator is required, not an edge case; stops do not protect through a halt reopening lower.
- PDT rule: under $25k equity, max 3 day trades per 5 business days — invalidates naive high-frequency small-account plans.

### "Profit cushion" sizing variant (bull-flag doc; Observed, untested)

Open the day at 25% size; scale to full only after banking 25% of the daily goal; cut size or stop if the cushion is given back; end the session if no valid setup within ~30 minutes of the open.

## 4. Conflicts between the sources (both preserved)

| Topic | Bundle (Confirmed) | Corpus (Observed) | Resolution |
|---|---|---|---|
| Catalyst mandatory? | Preview: preferred, not mandatory; technical breakout can qualify; the platform scanner does not auto-require news | `has_catalyst == true` a hard universe filter (83) | Keep the bundle rule (stronger source). Treat "no catalyst" as a scored pillar miss, not auto-reject. Backtest both. |
| Pullback length | 2–4 candles; 5–6 expires the setup | 2–3 candles; only 1st or 2nd pullback of the move | Compatible: candle-count within a pullback vs. pullback index within the move. Adopt both: candles 2–4 AND pullback_index ≤2. |
| Decision rule | 4/5 pillars can qualify; 3/5 reject | `min_pillars_to_trade = 5`; B-quality = mistake | Bundle wins for candidacy (4/5 qualifies); corpus supports logging `pillars_passed` and splitting stats by grade — if the A/B gradient is real it will show in R. |
| Float | <20M, lower preferred | Disputed in corpus: ≤20M (18x) vs ≤10M (16x), 5M ideal | Use <20M as the scanner threshold; tag ≤10M as a quality flag. Sweep in backtests. |
| Risk per trade | user-supplied dollar risk only | 2% of account (3–5% also stated) | Bundle rule stands: never invent the user's risk. Corpus values are candidate personal parameters to test in simulation. |
| RVOL baseline | time-of-day median, N=20 recommended (spec) | 5x of 50-day average volume | Different baselines change the number materially. Platform computes both, labeled. |
| Exit style | plan 2R, partials only if predefined | scale 50/25/25 with breakeven move as default | Corpus is more prescriptive; adopt as a *tested personal parameter*, not a confirmed course rule. |

## 4b. Parameter distributions (the corpus is not internally settled)

The pillar thresholds are modal values, not constants. Full-corpus scan shows real spreads — backtests must sweep, not pick:

| Parameter | Modal value | Full observed range in corpus |
|---|---|---|
| Gain % | ≥10% | 2%, 4%, 5%, 25%, 30% (three videos use +30% as tightened criteria); "+10% within 5 min" appears as an *alert* condition |
| RVOL | ≥5x (vs 50-day avg) | 2x floor (full-course video) up to "prefer 100x+; 5x is only the floor"; one variant uses 100x vs 14-day avg; attribution claims: 80–90% of profits from ≥5x names |
| Float | <20M | <1M "best" → <50M ok → "never >100M"; one retrospective says the **10–20M band performed best** (lowest floats not optimal); one guest discards float entirely |
| Price | $2–$20, sweet $5–$10 | $0.75–$10, $1–$20, $3–$20; one video claims "$2–$5 for bulk of profit, avoid over $5" — directly contradicting the $5–$10 sweet spot |
| Pullback candles | 2–4 (bundle) | 1–3; max 4–5 red before deterioration; retracement must hold ≥50% of the leg, prefer top 20–25% of range |
| Stop | pullback low | overridden in several videos by flat 10–15c / 15–20c / 20–30c stops when the low is too far; must exceed spread width on wide-spread names |
| Giveback stop | 50% | also 25%, 20%, ~15%, 10–15% variants |
| Session window | 9:30–11:30 | 7–10, 8–10, 7–11 ET variants; hard noon stop; "first 5 min avoid" vs one video advocating trading them for cushion |

Setup-grade accuracy he self-reports (cold market): **A ≈ 68%, B ≈ 50–53%, C ≈ 40%**; hot market A = 75–80%. This is the concrete version of the A/B-quality gradient to test.

Notable negative finding: **the flame (news-age colors) does not appear anywhere in the YouTube corpus** — it is bundle-only, consistent with it being a platform UI feature rather than taught strategy.

The corpus also states the funnel as three explicit gates: **scanner finds it → chart shows the setup → Level 2 validates; if Level 2 fails, no trade** — a hard PASS gate consistent with the bundle's funnel.

## 4c. Setups in the corpus beyond the bundle's first/micro pullback

All Observed; none in the Preview chapters 1–6 detail:

- **Gap and Go**: gap up on overnight news, pull back to 9 EMA, entry = break of premarket high.
- **Dip and rip / halt resumption**: buy the panic dip on resumption; trade after the 1st and 2nd halt, not the 3rd; check the halt-down band is farther than your stop.
- **Red-to-green move**; **opening range breakout**; **blue-sky/all-time-high breakout** (no resistance above).
- **VWAP-reclaim**: prior failed VWAP attempts, enter the reclaim, stop on losing VWAP, target premarket high; only the first attempt is tradeable.
- **ABCD** with invalidation rule: point C must not break point A; stop at the low of the second dip.
- **Reverse-split bounce**: multi-year lows just after a reverse split.
- **Whole/half-dollar ladder** profit taking (sell half on first test of the whole dollar).
- Short selling: mostly "don't" — unlimited risk, never swing-short small caps or reverse-split names near lows.
- No-trade checklist: MACD against, high-volume selling in the profile, history of false breakouts, repeated topping tails at resistance, over-long consolidation, can't hold VWAP.

## 4d. LULD halt bands (Observed; directly buildable as a risk/target guard)

- Halt = 5 minutes minimum, triggered after price sits at the band 15 seconds; regular session only (no bands pre/post-market, where 900%+ moves happen).
- Tier 1 (S&P/large, >$3): ±5% in 5 min. Tier 2 small caps: >$3 → ±10%; $0.75–$3 → ±20%; <$0.75 → lesser of $0.15 or 75%.
- Halted up usually resumes higher, halted down lower; T1 (news pending) typically resumes ~50% lower; T12 (SEC suspension) lasts weeks.
- A stop does not protect through a halt that reopens lower.

## 5. What remains unquantifiable (corpus's own audit)

Trend lines (drawn differently by different traders), 44% of support mentions naming no level, 61% of "quality setup" mentions naming no pillar, Level 2 seller-wall reads (needs depth-of-book), emotional control (77% unresolved — but enforced as rules, which software can hard-code), reversal timing, halt-resume behavior, news quality (needs NLP).

## 6. Reliability caveats on the corpus

- **The rendered digests are samples, not complete extracts**: `rules_digest.md` hides 710 of 2,040 rules and ~90% of the 2,903 numeric figures behind "...N more" markers. Absence from the rendered file is not absence from the corpus — check `claims.db` / `scripts/search.py` before claiming something was never said.
- ASR artifacts corrupt numbers ("750" = $7.50, "accuracy: 220%"); do not parse numerics from the digest mechanically. Category tags leak (tax advice filed under position sizing); guest opinions (Jess, Danny) are not flagged except by name.
- Rules and their opposites both appear (max-loss rule vs "no strict max loss historically worked"; avoid first 5 minutes vs trade them for cushion). Example-specific prices sit beside genuine thresholds.
- Regulatory record: FTC sued Warrior Trading and Cameron (2022, D. Mass.) over deceptive earnings claims; $3M settlement, $2.9M refunded to 20,402 customers. The allegation was that publishing his results implied replicability. Expect a mechanically codified version to underperform published numbers, possibly to no edge.
- `daytradewarrior_videos.json` upload dates are synthetic below year granularity — never join them to market sessions.
- Claims layer is a paraphrase of summaries; timestamps drift a few seconds (auto-captions).
- Several parameters are internally disputed (float, position size, max loss, profit-loss ratio) — sweep, don't pick.
- The implied expectancy (~+3.2%/day at stated win rate and 2:1) is implausible; treat claimed performance (71.4% win rate, 3:1 payoff in the 51-day challenge) as marketing to be disproved.
- None of it is validated: the falsification order is universe count → trigger hit-rate vs 33.3% → parameter sensitivity → costs/slippage → regime splits, stopping at the first failure, against a buy-and-hold baseline.

## 7. Platform-build consequences (feeds `scanner-alert-platform-spec.md`)

The corpus adds these requirements on top of the spec:

1. **Hard risk-gate lockout** as a separate layer with veto power over strategy/execution: max daily loss, giveback 50%, green-to-red, 3 consecutive losses, max trades — pure arithmetic on the day's ledger, impossible for strategy code to override.
2. **Ranked, capped scanner output** (~50 rows) with fast refresh; the ordered list *is* the signal.
3. **Session-window awareness** in scanners and alerts (blackout 09:30–09:35, prime 09:30–10:30, midday suppression) as configurable notification rules.
4. **Halt indicator as a first-class widget/alert**, not an afterthought.
5. **Support-confluence calculator** (whole/half dollars, 9/20 EMA, 200 MA, VWAP, flipped levels; configurable tolerance) as a chart/planning aid.
6. **Journal fields** for pillars_passed, pullback_index, setup grade, MFE/MAE, rule adherence — so the A/B-quality gradient and daily-limit claims become testable from our own data. Slice P&L by day-of-week, time-of-day, price range and float band (the dimensions he actually reviews).
7. **Audio alert at the moment a scanner triggers** — "scanner → alert is the whole discovery path"; a 60-second poll misses the trade the scanner exists to find.
8. **Halt bands + resumption quotes as a first-class feature** — most retail platforms omit halt levels (a $150–175/month add-on elsewhere); the LULD arithmetic in §4d is computable from public rules and is both a risk guard and a differentiator.
9. **Existing `src/paper_trading` audit (2026-09-01)**: high-quality, reusable pieces — NASDAQ universe fetch with dated cache, pure indicators, SQLite ledger with tested migrations, latching risk gate keyed by ET date. Known gaps/bugs to respect when building on it: no event loop or scheduler (pull-on-click only), alert dedup never re-arms, intraday RVOL structurally understated (partial-day volume vs full-day 50-day mean), `FLOAT_MAX` declared but never applied, buy gate values open positions at cost not mark-to-market, SQLite connections never closed, CLI includes ETFs by default while the app excludes them, no premarket data (`prepost=False`), NASDAQ-only universe.
