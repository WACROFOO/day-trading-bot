# kronos-probe/ — can a candlestick foundation model rank these setups?

`research/first-pullback-edge/` closed with a negative verdict and one open
question: the **random** entry population reaches +1 R far more often than the
pattern-selected one (25.9% vs 14.3% win rate, mean MFE 1.15 R vs 0.78 R, on
the same qualifying names — `first-pullback-edge/reports/final_report.md`
§10). That says the qualifying *universe* may hold something the *pattern* is
selecting away from.

That is a question about the **conditional distribution of the next thirty
minutes**, which is the object a candlestick foundation model emits. This
folder tests whether [Kronos](https://github.com/shiyu-coder/Kronos)
(AAAI 2026, MIT) carries any information about it.

**Status: instrument built and priced. No result yet.** Nothing here is a
trading claim, and a better forecast would not rescue the First Pullback —
that strategy is negative *gross of costs*. This is a measurement of whether
one specific model can separate outcomes on a population whose outcomes are
already known.

## The one design decision that matters

Kronos ships `KronosPredictor.predict`, which ends on
`preds = np.mean(preds, axis=1)` — it averages the sampled OHLC paths in
price space. The mean of N paths has a **lower high and a higher low than any
single path**, which destroys the only quantity this project measures: did
the high touch +1 R before the low touched the stop.

`src/forecast.py` keeps the sample axis instead, without forking their code:
call `auto_regressive_inference` with `sample_count=1` and replicate anchors
in the batch dimension. Sampling is independent per batch row, so B anchors
repeated N times give B x N independent paths and their averaging line
becomes a no-op over an axis of length 1.

Their own downstream never uses the predicted high or low either — every
signal in Kronos' bundled qlib backtest is built from the close column alone.
(Paths in this section refer to the Kronos checkout, not to this repo.)

## Rules carried over from the parent study

| rule | how |
|---|---|
| anchor is the **decision** point | `setup_ts`, the pullback bar's close — not `entry_ts`. A filter must be usable before the trigger is touched |
| no window crosses a session | 150 bars back from 09:45 would reach into yesterday. Anchors without enough same-session history are **dropped and counted**, never padded |
| ambiguous bars lose | a predicted bar spanning both barriers scores as a loss, matching the backtest's pessimistic policy — with OHLC alone there is no evidence for the favourable ordering |
| exchange-local time | `TemporalEmbedding` indexes real calendar fields, so UTC would put the open at 13:30 |
| anchors sampled seeded-random | first-N would take eleven years of tape and score only 2016 |

## Measured cost — not estimated

`results/pricing.json`, this container (4 CPU cores, no GPU):

```
Kronos-small · 24,741,376 params · 8 layers · d_model 512 · vocab 1024 x 1024
context 150 bars · horizon 30 bars

1.15 s per rollout — FLAT from 4 rollouts to 128
```

The flatness is the finding: four cores saturate at batch 4, so batching buys
nothing *here*. On a GPU that inverts, so this number does not transfer.

| population | @ 8 paths | @ 20 paths |
|---|---:|---:|
| variant A (3,627 trades) | 9.3 CPU-h | 23.2 CPU-h |
| qualified ticker-days (8,505) | 21.8 CPU-h | 54.5 CPU-h |
| random-entry baseline (42,510) | 109 CPU-h | 273 CPU-h |

Setup is trivial by comparison: ~100 MB of weights, both models load in under
ten seconds. The entire bill is the rollout, because Kronos has **no KV
cache** — each of the 30 generated bars re-runs the full stack over the whole
window.

## The predicted candles are not always valid candles

Measured, not assumed — `results/bar_validity.json`, 1,080 predicted bars:

| check | rate |
|---|---:|
| high < close | 1.11% |
| high < open | 0.74% |
| low > open | 1.20% |
| low > close | 1.11% |
| **high < low** outright | **0.09%** |
| **any inconsistency** | **3.43%** |

Kronos reconstructs O/H/L/C through a quantiser trained on OHLC but not
constrained by it. Their own downstream never notices, because every signal
in their bundled backtest comes from the close column alone. This probe reads
high and low directly, so that rate is roughly **one bad bar per 30-bar
path** — enough to flip a barrier touch.

So both readings are carried: `p_win` from the raw bars and `p_win_repaired`
after a **monotone** repair (`high = max(open, high, close)`,
`low = min(open, low, close)`). Monotone matters — a repair that could
*narrow* a bar would invent barrier misses. `invalid_bar_rate` travels per
anchor, so the rate stays attached to the result instead of living only in a
diagnostic file.

## Known limitations, stated before any result

- **19% of anchors drop** for having fewer than 150 same-session bars before
  the setup minute. Small-cap tape is sparse. That is a selection effect on
  whatever comes out.
- **Pre-training coverage is undocumented.** The model card says 45 global
  exchanges without a manifest. Whether sub-$20 US small caps at one-minute
  resolution are represented at all is not answerable from the code.
- **`clip=5` on z-scored volume**, with statistics taken from the window
  itself. This universe is defined by relative-volume spikes; a 30-sigma
  minute clips to 5.
- **Weak power at n=300** (~45 realised winners). Detects a large effect, not
  a small one. That is why it runs before the 9-CPU-hour version.
- **No holdout discipline yet.** The first pass samples all eleven years. A
  result worth acting on would be re-run on the parent study's 478-session
  untouched holdout.
- Any separation still has to clear the round-trip cost before it means
  anything, through `first-pullback-edge/src/execution.py` unchanged.

## Layout

| Path | What |
|---|---|
| `src/bars.py` | session-aware slicing of the cached Alpaca minute bars; drops rather than pads |
| `src/anchors.py` | both populations — variant-A decision points, and the random-entry arm rebuilt from the parent study's own `SessionState` |
| `src/forecast.py` | Kronos inference keeping the sample axis, and the barrier reduction |
| `src/truth.py` | the matched outcome from the forward tape, graded by the same rule the model's paths are |
| `price_run.py` | measures throughput and projects the real run |
| `run_probe.py` | generates the probabilities for one population |
| `score.py` | grades them — kept separate so re-scoring never costs a rollout |
| `diagnose_bars.py` | how often a predicted candle is not a candle |
| `tests/` | 20 tests, all on assumptions that fail silently. `python3 -m pytest tests/ -q` |
| `results/` | `pricing.json`, `bar_validity.json`, then `probe_*.csv` and `probe_*_summary.json` |

## The two arms

| arm | anchors | what it asks |
|---|---|---|
| `--population pattern` | variant-A `setup_ts` | can the model sort the pullback trades? |
| `--population random` | random minute 09:35–11:30 on a qualifying ticker-day, risk = 1 ATR | the report's actual open question |

The second is the one that matters. The report found the **random**
population reaches +1 R far more often than the pattern-selected one. If the
model's `p_win` does not also rank random above pattern, it is blind to
whatever actually separates them — and that is a result, not a null.

The random anchors were never stored (`run.py` keeps only `day`, `net_r`,
`mfe_r`), so they are rebuilt under the same rule using the parent study's
own `SessionState`, which makes the ATR the identical causal one the backtest
used.

## Run

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install huggingface_hub safetensors
git clone https://github.com/shiyu-coder/Kronos /home/user/shiyu-coder/kronos

cd research/kronos-probe
python3 -m pytest tests/ -q                       # 20 tests
python3 price_run.py --anchors 16 --paths 8 --batch 16
python3 diagnose_bars.py --anchors 6 --paths 6
python3 run_probe.py --limit 300 --paths 16 --batch 16 --population pattern
python3 run_probe.py --limit 300 --paths 16 --batch 16 --population random
python3 score.py results/probe_pattern.csv results/probe_random.csv
```

Run the arms **sequentially**, not in parallel: four cores saturate at batch
4, so concurrent jobs halve each other rather than finishing sooner.

Weights come from the Hugging Face Hub on first use
(`NeoQuasar/Kronos-Tokenizer-base`, `NeoQuasar/Kronos-small`). No fine-tuning
is involved — this is inference against the released checkpoints.

Paper only.
